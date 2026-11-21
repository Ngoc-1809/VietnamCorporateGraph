"""Read-only, bounded graph views over the active final-project snapshot."""
from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict, deque
from functools import lru_cache
from pathlib import Path
from typing import Literal

GraphMode = Literal["passed", "quarantine"]


@lru_cache(maxsize=6)
def load_graph(snapshot: str, mode: GraphMode) -> tuple[dict[str, dict], list[dict]]:
    """Cache only graph metadata; evidence text is loaded on demand."""
    path = Path(snapshot) / ("profile.sqlite" if mode == "passed" else "quarantine.sqlite")
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        nodes = {row["node_id"]: dict(row) for row in connection.execute(
            "SELECT node_id,name,entity_type,identity_status,degree,pagerank,community,component,core_number "
            "FROM nodes")}
        where = " WHERE endpoint_quality='ELIGIBLE'" if mode == "quarantine" else ""
        edges = [dict(row) for row in connection.execute(
            "SELECT edge_uid,subject_id,object_id,predicate,factual_status,article_count,evidence_count "
            "FROM edges" + where)]
    finally:
        connection.close()
    return nodes, edges


def filtered_graph(snapshot: str, mode: GraphMode, predicates: tuple[str, ...],
                   types: tuple[str, ...], min_incident_edges: int) -> tuple[dict[str, dict], list[dict], Counter]:
    """Count incident edge rows after type/predicate filters, before display limits."""
    all_nodes, all_edges = load_graph(snapshot, mode)
    type_set, predicate_set = set(types), set(predicates)
    allowed = {key for key, node in all_nodes.items() if not type_set or node["entity_type"] in type_set}
    edges = [edge for edge in all_edges if edge["subject_id"] in allowed and edge["object_id"] in allowed
             and (not predicate_set or edge["predicate"] in predicate_set)]
    degree: Counter = Counter()
    for edge in edges:
        degree[edge["subject_id"]] += 1
        if edge["object_id"] != edge["subject_id"]:
            degree[edge["object_id"]] += 1
    selected = {key: all_nodes[key] for key in allowed if degree[key] >= min_incident_edges}
    edges = [edge for edge in edges if edge["subject_id"] in selected and edge["object_id"] in selected]
    return selected, edges, degree


def options(snapshot: str, mode: GraphMode) -> dict:
    nodes, edges = load_graph(snapshot, mode)
    return {"mode": mode, "types": dict(sorted(Counter(node["entity_type"] for node in nodes.values()).items())),
            "predicates": dict(sorted(Counter(edge["predicate"] for edge in edges).items())),
            "eligible_edges": len(edges), "all_nodes": len(nodes)}


def _node_payload(key: str, node: dict, degree: Counter) -> dict:
    return {"id": key, "name": node["name"], "type": node["entity_type"],
            "identity_status": node["identity_status"], "degree": node["degree"],
            "incident_edges": degree[key], "pagerank": node["pagerank"],
            "community": node["community"], "component": node["component"],
            "core_number": node["core_number"]}


def _edge_payload(edge: dict) -> dict:
    return {"uid": edge["edge_uid"], "source": edge["subject_id"], "target": edge["object_id"],
            "predicate": edge["predicate"], "status": edge["factual_status"],
            "article_count": edge["article_count"], "evidence_count": edge["evidence_count"]}


def overview(snapshot: str, mode: GraphMode, predicates: tuple[str, ...] = (),
             types: tuple[str, ...] = (), min_incident_edges: int = 1, max_communities: int = 60) -> dict:
    nodes, edges, _degree = filtered_graph(snapshot, mode, predicates, types, min_incident_edges)
    members: dict[int, list[str]] = defaultdict(list)
    for key, node in nodes.items():
        members[node["community"]].append(key)
    selected = {key for key, _ in sorted(members.items(), key=lambda item: (-len(item[1]), item[0]))
                [:max_communities]}
    group_id = lambda key: f"community:{key}" if key in selected else "community:other"
    sizes: Counter = Counter()
    internal: Counter = Counter()
    for key, values in members.items():
        sizes[group_id(key)] += len(values)
    links: Counter = Counter()
    for edge in edges:
        source = group_id(nodes[edge["subject_id"]]["community"])
        target = group_id(nodes[edge["object_id"]]["community"])
        if source == target:
            internal[source] += 1
        else:
            links[tuple(sorted((source, target)))] += 1
    groups = [{"id": key, "name": "Các cộng đồng khác" if key == "community:other" else
               f"Cộng đồng {key.split(':')[1]}", "member_count": value,
               "internal_edges": internal[key], "community_id": None if key == "community:other" else
               int(key.split(":")[1])} for key, value in sorted(sizes.items(), key=lambda item: (-item[1], item[0]))]
    return {"mode": mode, "view": "overview", "snapshot": Path(snapshot).name,
            "nodes": groups, "edges": [{"uid": f"{a}|{b}", "source": a, "target": b, "weight": count}
                                      for (a, b), count in sorted(links.items())],
            "counts": {"filtered_nodes": len(nodes), "filtered_edges": len(edges),
                       "total_communities": len(members), "shown_communities": len(selected),
                       "other_communities": len(members) - len(selected)}}


def _priority(edge: dict, degree: Counter, depth: dict[str, int] | None = None) -> tuple:
    if depth is not None:
        a, b = depth[edge["subject_id"]], depth[edge["object_id"]]
        return (max(a, b), min(a, b), -edge["article_count"], edge["edge_uid"])
    return (-(degree[edge["subject_id"]] + degree[edge["object_id"]]),
            -edge["article_count"], edge["edge_uid"])


def _bounded_edges(edges: list[dict], degree: Counter, limit: int,
                   depth: dict[str, int] | None = None) -> list[dict]:
    """Keep a spanning forest first, then the strongest remaining induced edges."""
    ordered = sorted(edges, key=lambda edge: _priority(edge, degree, depth))
    parent: dict[str, str] = {}

    def find(key: str) -> str:
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    forest, extras = [], []
    for edge in ordered:
        a, b = find(edge["subject_id"]), find(edge["object_id"])
        if a != b:
            parent[a] = b
            forest.append(edge)
        else:
            extras.append(edge)
    return (forest + extras)[:limit]


def subgraph(snapshot: str, mode: GraphMode, scope: Literal["global", "community", "neighborhood"],
             max_nodes: int, max_edges: int, min_incident_edges: int = 1,
             predicates: tuple[str, ...] = (), types: tuple[str, ...] = (),
             node_id: str | None = None, community_id: int | None = None, hops: int = 1) -> dict:
    nodes, edges, degree = filtered_graph(snapshot, mode, predicates, types, min_incident_edges)
    if scope == "neighborhood" and not node_id:
        raise ValueError("node_id is required for neighborhood")
    if scope == "neighborhood" and node_id not in load_graph(snapshot, mode)[0]:
        raise KeyError(node_id)
    if scope == "community" and community_id is None:
        raise ValueError("community_id is required for community")
    if scope == "community":
        nodes = {key: node for key, node in nodes.items() if node["community"] == community_id}
        edges = [edge for edge in edges if edge["subject_id"] in nodes and edge["object_id"] in nodes]
    total_nodes, total_edges = len(nodes), len(edges)
    depth: dict[str, int] | None = None
    if scope == "neighborhood":
        assert node_id is not None
        adjacency: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        for edge in edges:
            adjacency[edge["subject_id"]].append((edge["object_id"], edge))
            adjacency[edge["object_id"]].append((edge["subject_id"], edge))
        depth = {node_id: 0}
        queue = deque([node_id])
        while queue and len(depth) < max_nodes:
            key = queue.popleft()
            if depth[key] >= hops:
                continue
            neighbors = sorted(adjacency[key], key=lambda item: (-item[1]["article_count"],
                                                                  -degree[item[0]], item[0], item[1]["edge_uid"]))
            for neighbor, _ in neighbors:
                if neighbor not in nodes or neighbor in depth:
                    continue
                depth[neighbor] = depth[key] + 1
                queue.append(neighbor)
                if len(depth) >= max_nodes:
                    break
        chosen = set(depth)
        # Counts for a focused view describe the full reachable neighborhood before display limits.
        reachable = {node_id}
        frontier = {node_id}
        for _ in range(hops):
            frontier = {neighbor for key in frontier for neighbor, _ in adjacency[key] if neighbor in nodes} - reachable
            reachable.update(frontier)
        total_nodes = len(reachable)
        total_edges = sum(edge["subject_id"] in reachable and edge["object_id"] in reachable for edge in edges)
    else:
        rank = lambda key: (-degree[key], -(nodes[key]["pagerank"] or 0), key)
        if len(nodes) <= max_nodes:
            chosen = set(nodes)
        else:
            communities: dict[int, list[str]] = defaultdict(list)
            for key, node in nodes.items():
                communities[node["community"]].append(key)
            seeds = [min(values, key=rank) for _, values in sorted(
                communities.items(), key=lambda item: (-len(item[1]), item[0]))[:min(20, max_nodes)]]
            chosen = set(seeds)
            for key in sorted(nodes, key=rank):
                if len(chosen) >= max_nodes:
                    break
                chosen.add(key)
    induced = [edge for edge in edges if edge["subject_id"] in chosen and edge["object_id"] in chosen]
    drawn_edges = _bounded_edges(induced, degree, max_edges, depth)
    if scope == "neighborhood":
        used = {key for edge in drawn_edges for key in (edge["subject_id"], edge["object_id"])}
        chosen = used | {node_id}
    return {"mode": mode, "view": scope, "snapshot": Path(snapshot).name,
            "focus_id": node_id if scope == "neighborhood" else None,
            "nodes": [{**_node_payload(key, nodes[key] if key in nodes else load_graph(snapshot, mode)[0][key], degree),
                       "hop": depth.get(key) if depth is not None else None} for key in sorted(chosen)],
            "edges": [_edge_payload(edge) for edge in drawn_edges],
            "counts": {"filtered_nodes": total_nodes, "filtered_edges": total_edges,
                       "drawn_nodes": len(chosen), "drawn_edges": len(drawn_edges),
                       "truncated_nodes": total_nodes > len(chosen),
                       "truncated_edges": total_edges > len(drawn_edges)},
            "filters": {"min_incident_edges": min_incident_edges, "predicates": list(predicates),
                        "types": list(types), "hops": hops}}
