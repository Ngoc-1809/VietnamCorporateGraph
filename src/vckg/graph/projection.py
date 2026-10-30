"""Graph projections for small-world analysis. Derived edges are labelled and never mixed with
direct press edges. Registry/entity-type info is passed in; nothing here reads from the web."""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations

import networkx as nx

from vckg.models import Edge

PERSON_ORG_PREDICATES = {"CHAIR_OF", "CEO_OF", "BOARD_MEMBER_OF"}  # governance roles -> person-person projection
COMPANY_PREDICATES = {"OWNS_SHARES_IN", "SUBSIDIARY_OF", "ACQUIRED", "LENDS_TO", "ISSUED_BOND",
                      "JOINT_VENTURE_WITH", "PARTNERS_WITH"}


def _overlap(a: Edge, b: Edge) -> bool:
    """Tenure overlap check on valid_from/valid_to (year/ISO strings). Unknown bounds => assume overlap."""
    def span(e: Edge):
        f = [r.valid_from for r in e.evidence if r.valid_from]
        t = [r.valid_to for r in e.evidence if r.valid_to]
        return (min(f) if f else "0000", max(t) if t else "9999")
    (af, at), (bf, bt) = span(a), span(b)
    return af <= bt and bf <= at


def person_person_projection(edges: list[Edge], tenure_aware: bool = False) -> nx.Graph:
    """Persons linked when they hold governance roles in the same organization. Edge attr
    derived=True, kind='SHARED_GOVERNANCE', plus the list of shared org ids (weight = #shared orgs)."""
    by_org: dict[str, list[Edge]] = defaultdict(list)
    for e in edges:
        if e.predicate in PERSON_ORG_PREDICATES:
            by_org[e.object_id].append(e)
    g = nx.Graph(kind="person_person", derived=True)
    for org, es in by_org.items():
        for a, b in combinations(es, 2):
            if a.subject_id == b.subject_id or (tenure_aware and not _overlap(a, b)):
                continue
            u, v = a.subject_id, b.subject_id
            if g.has_edge(u, v):
                g[u][v]["orgs"].add(org)
                g[u][v]["weight"] = len(g[u][v]["orgs"])
            else:
                g.add_edge(u, v, orgs={org}, weight=1, derived=True, kind="SHARED_GOVERNANCE")
    return g


def company_company_projection(edges: list[Edge], include_shared_leaders: bool = True) -> nx.Graph:
    g = nx.Graph(kind="company_company")
    for e in edges:
        if e.predicate in COMPANY_PREDICATES:
            if g.has_edge(e.subject_id, e.object_id):
                g[e.subject_id][e.object_id]["weight"] += 1
                g[e.subject_id][e.object_id]["predicates"].add(e.predicate)
            else:
                g.add_edge(e.subject_id, e.object_id, weight=1, predicates={e.predicate}, derived=False, kind="DIRECT")
    if include_shared_leaders:
        by_person: dict[str, set[str]] = defaultdict(set)
        for e in edges:
            if e.predicate in PERSON_ORG_PREDICATES:
                by_person[e.subject_id].add(e.object_id)
        for p, orgs in by_person.items():
            for a, b in combinations(sorted(orgs), 2):
                if g.has_edge(a, b):
                    if g[a][b].get("derived"):
                        g[a][b]["weight"] += 1
                        g[a][b]["via_persons"].add(p)
                    else:
                        g[a][b].setdefault("shared_leaders", set()).add(p)  # direct edge keeps its own label
                else:
                    g.add_edge(a, b, weight=1, derived=True, kind="SHARED_LEADER", via_persons={p})
    return g


def to_unweighted(g: nx.Graph) -> nx.Graph:
    h = nx.Graph(**g.graph)
    h.add_nodes_from(g.nodes)
    h.add_edges_from(g.edges)
    return h
