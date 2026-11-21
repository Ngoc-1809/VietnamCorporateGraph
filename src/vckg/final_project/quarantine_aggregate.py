"""Quarantine-only identity and relation aggregation with evidence-level provenance.

This is a read model. It never changes ER, QA decisions or the Passed graph.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict

from vckg.entity_linking.generic import is_generic_entity
from vckg.entity_linking.normalize import normalize_name
from vckg.entity_resolution.core import fold1
from vckg.preprocessing.text import split_sentences

VERSION = "q-aggregate-v1"
ROLE_CUES = {
    "CEO_OF": re.compile(r"\b(?:tong giam doc|giam doc dieu hanh|ceo)\b"),
    "CHAIR_OF": re.compile(r"\bchu tich(?:\s+(?:hdqt|hoi dong quan tri))?\b"),
    "BOARD_MEMBER_OF": re.compile(r"\b(?:thanh vien\s+(?:hdqt|hoi dong quan tri)|pho chu tich\s+hdqt)\b"),
}
_FUTURE_ROLE = re.compile(r"\b(?:se|du kien|sap|de cu|de xuat|nham|co the)\b")
_FORMER = re.compile(r"\b(?:nguyen|cuu|tung)\s+$")
_FUTURE_OTHER_EVENT = re.compile(
    r"\b(?:se\s+(?:duoc\s+(?:phan\s+phoi|phan\s+bo|mua|trao|cap)|nhan\s+(?:co\s+phieu|esop)|tiep\s+tuc)"
    r"|co\s+the\s+tiep\s+tuc)\b"
)


def _positions(sentence: str, name: str) -> list[tuple[int, int]]:
    key = fold1(name)
    return [(m.start(), m.end()) for m in re.finditer(rf"(?<!\w){re.escape(key)}(?!\w)", sentence)] if key else []


def _role_sentence(row: dict, nodes: dict[str, dict]) -> tuple[str, re.Match[str]] | None:
    cue = ROLE_CUES.get(row["relation_type"])
    if cue is None or nodes[row["subject_id"]]["entity_type"] != "PERSON":
        return None
    person, org = nodes[row["subject_id"]]["name"], nodes[row["object_id"]]["name"]
    if len(normalize_name(person, is_person=True).split()) < 3:
        return None
    for part in split_sentences(row["evidence_text"]):
        sentence = part.text
        plain = fold1(sentence)
        people, orgs = _positions(plain, person), _positions(plain, org)
        if not people or not orgs:
            continue
        for role in cue.finditer(plain):
            for person_start, person_end in people:
                if person_start >= role.end():
                    gap = plain[role.end():person_start]
                    person_local = len(gap) <= 95 and not re.search(r"[,;:.!?]", gap)
                else:
                    gap = plain[person_end:role.start()]
                    person_local = len(gap) <= 65 and not re.search(r"[;.!?]", gap)
                if not person_local:
                    continue
                for org_start, org_end in orgs:
                    if org_start >= role.end():
                        middle = plain[role.end():org_start]
                        org_local = len(middle) <= 140 and not re.search(r"[,;.!?]", middle)
                    else:
                        middle = plain[org_end:role.start()]
                        org_local = len(middle) <= 130 and not re.search(r"[;.!?]", middle)
                    if org_local:
                        return sentence, role
    return None


def role_anchor(row: dict, nodes: dict[str, dict]) -> bool:
    """A title, full person name and named organization occur in one source sentence."""
    return _role_sentence(row, nodes) is not None


def status_for_role(row: dict, nodes: dict[str, dict]) -> tuple[str, str]:
    """Correct only PLANNED leaked from another event after a present-tense title."""
    if row["factual_status"] != "PLANNED":
        return row["factual_status"], ""
    found = _role_sentence(row, nodes)
    if found is None:
        return "PLANNED", ""
    sentence, role = found
    before = fold1(sentence[max(0, role.start() - 90):role.start()])
    if _FUTURE_ROLE.search(before):
        return "PLANNED", ""
    if _FORMER.search(before):
        return "HISTORICAL", "FORMER_ROLE_TITLE_FUTURE_OTHER_EVENT"
    # A future ESOP allotment or forecast after a title is a different event.
    if _FUTURE_OTHER_EVENT.search(fold1(sentence[role.end():])):
        return "FACT", "PRESENT_ROLE_TITLE_FUTURE_OTHER_EVENT"
    return "PLANNED", ""


def person_overlay(rows: list[dict], nodes: dict[str, dict]) -> tuple[dict[str, str], dict[str, dict]]:
    """Group article-scoped people only when full name, organization and role agree.

    The Q-only ID is an exploratory profile key; original person IDs remain in the audit map.
    """
    anchors: dict[str, set[str]] = defaultdict(set)
    roles: dict[str, set[str]] = defaultdict(set)
    articles: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        person_id, org_id = row["subject_id"], row["object_id"]
        if person_id not in nodes or org_id not in nodes or not role_anchor(row, nodes):
            continue
        org = nodes[org_id]
        if (org["entity_type"] not in {"ORGANIZATION", "BANK"}
                or org["identity_status"] not in {"VERIFIED", "EXTERNAL_VERIFIED", "ARTICLE_GROUNDED"}
                or is_generic_entity(org["name"])):
            continue
        name = normalize_name(nodes[person_id]["name"], is_person=True)
        if len(name.split()) < 3:
            continue
        anchors[person_id].add(org_id)
        roles[person_id].add(row["relation_type"])
        articles[person_id].add(row["article_id"])
    groups: dict[tuple[str, str], set[str]] = defaultdict(set)
    for person_id, orgs in anchors.items():
        if len(orgs) == 1:
            groups[(normalize_name(nodes[person_id]["name"], is_person=True), next(iter(orgs)))].add(person_id)
    mapping: dict[str, str] = {}
    audit: dict[str, dict] = {}
    for (name, org_id), members in sorted(groups.items()):
        if len(members) < 2 or len(set().union(*(articles[m] for m in members))) < 2:
            continue
        common_roles = set.intersection(*(roles[m] for m in members))
        if not common_roles:
            continue
        canonical = "qperson:" + hashlib.sha1(f"{name}|{org_id}".encode()).hexdigest()[:18]
        representative = min(members, key=lambda member: (-len(nodes[member]["name"]), member))
        nodes[canonical] = {**nodes[representative], "node_id": canonical,
                            "identity_status": "PROVISIONAL", "source_node_ids": json.dumps(sorted(members)),
                            "aggregation_method": "SAME_FULL_NAME_ORG_ROLE_QUARANTINE"}
        mapping.update({member: canonical for member in members})
        audit[canonical] = {"name": nodes[canonical]["name"], "anchor_org_id": org_id,
                            "roles": sorted(common_roles), "source_node_ids": sorted(members),
                            "article_count": len(set().union(*(articles[m] for m in members)))}
    return mapping, audit


def edge_uid(row: dict) -> str:
    """One visible candidate relationship per directed triple, independent of QA reason/status."""
    key = "|".join((row["subject_id"], row["relation_type"], row["object_id"]))
    return "QUARANTINE:agg:" + hashlib.sha1(key.encode()).hexdigest()[:20]


def aggregate(rows: list[tuple[dict, dict]], nodes: dict[str, dict]) -> tuple[dict, dict, dict, dict, dict, dict]:
    """Aggregate corrected evidence by directed triple while retaining every source decision."""
    person_map, person_audit = person_overlay([row for _, row in rows], nodes)
    edges: dict[str, dict] = {}
    evidence: dict[tuple, dict] = {}
    sources: dict[str, set[str]] = defaultdict(set)
    pre_to_agg: dict[str, str] = {}
    corrected = 0
    for original, row in rows:
        status, adjustment = status_for_role(row, nodes)
        corrected += bool(adjustment)
        changed = dict(row)
        for side in ("subject", "object"):
            old_id = changed[f"{side}_id"]
            new_id = person_map.get(old_id, old_id)
            if new_id != old_id:
                changed[f"{side}_id"] = new_id
                changed[f"{side}_name"] = nodes[new_id]["name"]
                changed[f"{side}_identity_status"] = nodes[new_id]["identity_status"]
        uid = edge_uid(changed)
        pre_to_agg[row["qa_tier"] + ":" + row["edge_id"]] = uid
        reasons = set(json.loads(row["quarantine_classes"] or "[]"))
        methods = set(json.loads(row["discovery_methods"] or "[]"))
        windows = (row["valid_from"] or "", row["valid_to"] or "")
        if uid not in edges:
            edges[uid] = {**changed, "edge_id": uid.rsplit(":", 1)[-1],
                          "_statuses": set(), "_reasons": set(), "_methods": set(),
                          "_windows": set(), "_repair_methods": set()}
        item = edges[uid]
        item["_statuses"].add(status)
        item["_reasons"].update(reasons)
        item["_methods"].update(methods)
        item["_windows"].add(windows)
        if row.get("_repair_method"):
            item["_repair_methods"].add(row["_repair_method"])
        sources[uid].add(original["qa_tier"] + ":" + original["edge_id"])
        key = (uid, row["article_id"], row["evidence_start"], row["evidence_end"], row["evidence_text"])
        if key not in evidence:
            evidence[key] = {**changed, "edge_uid": uid, "_statuses": set(), "_original_statuses": set(),
                             "_reasons": set(), "_source_uids": set(), "_adjustments": set()}
        ev = evidence[key]
        ev["_statuses"].add(status)
        ev["_original_statuses"].add(original["factual_status"])
        ev["_reasons"].update(reasons)
        ev["_source_uids"].add(original["qa_tier"] + ":" + original["edge_id"])
        if adjustment:
            ev["_adjustments"].add(adjustment)
    for item in edges.values():
        statuses = sorted(item.pop("_statuses"))
        windows = sorted(item.pop("_windows"))
        item["factual_status"] = statuses[0] if len(statuses) == 1 else "MIXED"
        item["factual_statuses"] = json.dumps(statuses)
        item["quarantine_classes"] = json.dumps(sorted(item.pop("_reasons")))
        item["discovery_methods"] = json.dumps(sorted(item.pop("_methods")))
        item["valid_from"], item["valid_to"] = windows[0] if len(windows) == 1 else ("", "")
        item["validity_windows"] = json.dumps(windows)
        item["_repair_method"] = ";".join(sorted(item.pop("_repair_methods")))
    final_evidence: dict[str, dict] = {}
    for key, ev in evidence.items():
        statuses = sorted(ev.pop("_statuses"))
        ev["factual_status"] = statuses[0] if len(statuses) == 1 else "MIXED"
        ev["source_factual_statuses"] = json.dumps(sorted(ev.pop("_original_statuses")))
        ev["quarantine_classes"] = json.dumps(sorted(ev.pop("_reasons")))
        ev["source_edge_uids"] = json.dumps(sorted(ev.pop("_source_uids")))
        ev["status_adjustment"] = ";".join(sorted(ev.pop("_adjustments")))
        evidence_id = hashlib.sha1("|".join(key).encode()).hexdigest()[:20]
        final_evidence[evidence_id] = ev
    metrics = {"source_evidence_rows": len(rows), "aggregated_evidence_rows": len(final_evidence),
               "role_status_corrections": corrected, "person_groups": len(person_audit),
               "person_source_ids_grouped": len(person_map),
               "mixed_status_edges": sum(row["factual_status"] == "MIXED" for row in edges.values())}
    return edges, final_evidence, sources, pre_to_agg, person_audit, metrics
