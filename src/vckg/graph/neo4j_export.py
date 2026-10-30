"""Export to Neo4j-importable CSV + Cypher. Article/Evidence are separate labels and are NOT entity nodes.

Model:  (:Entity:Person|Organization|Bank|Regulator)-[:REL {predicate-specific type}]->(:Entity)
        each relationship carries evidence_ids; (:Evidence)-[:FROM]->(:Article)
Idempotent: uses MERGE on stable keys."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from vckg.models import Article, Edge, RegistryEntry

CONSTRAINTS = """\
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE;
CREATE CONSTRAINT article_id IF NOT EXISTS FOR (a:Article) REQUIRE a.article_id IS UNIQUE;
CREATE CONSTRAINT evidence_id IF NOT EXISTS FOR (e:Evidence) REQUIRE e.evidence_id IS UNIQUE;
"""

_LABEL = {"PERSON": "Person", "ORGANIZATION": "Organization", "BANK": "Organization:Bank",
          "REGULATOR": "Organization:Regulator", "GOVERNMENT_AGENCY": "Organization:Authority"}


def export_csv(out_dir: str | Path, entities: list[RegistryEntry], edges: list[Edge], articles: list[Article]) -> dict[str, int]:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)

    def w(name: str, header: list[str], rows: list[list]):
        with (d / name).open("w", encoding="utf-8", newline="") as f:
            cw = csv.writer(f)
            cw.writerow(header)
            cw.writerows(rows)

    w("entities.csv", ["entity_id", "name", "type", "labels"],
      [[e.entity_id, e.canonical_name, e.type.value, _LABEL[e.type.value]] for e in entities])
    w("articles.csv", ["article_id", "url", "source", "title", "published_at"],
      [[a.article_id, a.url, a.source, a.title, a.published_at or ""] for a in articles])
    rel_rows, ev_rows = [], []
    for e in edges:
        for r in e.evidence:
            eid = hashlib.sha1(f"{e.key}|{r.article_id}|{r.evidence_start}|{r.evidence_end}".encode()).hexdigest()[:16]
            rel_rows.append([e.subject_id, e.predicate, e.object_id, eid])
            ev_rows.append([eid, r.article_id, r.evidence_text, r.evidence_start, r.evidence_end, r.extraction_method,
                            r.confidence, r.review_status.value, r.factual_status.value, r.valid_from or "", r.valid_to or "",
                            r.published_at or ""])
    w("relations.csv", ["subject_id", "predicate", "object_id", "evidence_id"], rel_rows)
    w("evidence.csv", ["evidence_id", "article_id", "evidence_text", "start", "end", "method", "confidence",
                       "review_status", "factual_status", "valid_from", "valid_to", "published_at"], ev_rows)
    (d / "schema.cypher").write_text(CONSTRAINTS, encoding="utf-8")
    return {"entities": len(entities), "articles": len(articles), "evidence": len(ev_rows),
            "edges": len(edges)}
