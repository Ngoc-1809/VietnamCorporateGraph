"""Basic graph statistics (Phase 1 interface; small-world metrics come in a later phase)."""
from __future__ import annotations

from collections import Counter

import networkx as nx

from vckg.models import Edge


def edge_stats(edges: list[Edge]) -> dict:
    preds = Counter(e.predicate for e in edges)
    nodes = {e.subject_id for e in edges} | {e.object_id for e in edges}
    return {"nodes_in_edges": len(nodes), "edges": len(edges), "predicate_types": len(preds),
            "by_predicate": dict(preds), "evidence_records": sum(len(e.evidence) for e in edges)}


def graph_summary(g: nx.Graph) -> dict:
    if g.number_of_nodes() == 0:
        return {"nodes": 0, "edges": 0}
    comps = sorted((len(c) for c in nx.connected_components(g)), reverse=True)
    return {"nodes": g.number_of_nodes(), "edges": g.number_of_edges(), "components": len(comps),
            "largest_component": comps[0], "avg_clustering": nx.average_clustering(g),
            "degree_histogram": nx.degree_histogram(g)}
