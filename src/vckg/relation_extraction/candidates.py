"""Structure-aware relation candidate generation.

Every sentence is masked (mentions -> placeholders, parenthetical aliases removed) and matched against the
patterns in config/relations.yaml. A candidate exists only if a pattern ties a cue to BOTH endpoints; direction
is the pattern's S/O assignment, not the order mentions appear in. Co-occurrence alone never yields a candidate."""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import yaml

from vckg.models import EntityType, FactualStatus, Mention, RelationCandidate, Sentence
from vckg.relation_extraction.modality import detect_modality

OPEN, CLOSE = "\ue000", "\ue001"
_PH = re.compile(OPEN + r"(\d+)" + CLOSE)
_PAREN = re.compile(r"(?<=" + CLOSE + r")\s*\((?:[^()\ue000\ue001]|" + OPEN + r"\d+" + CLOSE + r"){0,70}\)")


def _expand(template: str, macros: dict[str, str]) -> str:
    out = template
    for name, val in macros.items():
        out = out.replace("{" + name + "}", val)
    out = out.replace("{S}", f"(?P<S>{OPEN}\\d+{CLOSE})").replace("{O}", f"(?P<O>{OPEN}\\d+{CLOSE})")
    return out


@lru_cache(maxsize=4)
def load_config(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def load_relations(path: str) -> dict:
    """Relation specs with compiled patterns under spec['_compiled'] = [(pattern_id, regex, status_hint, typed)]."""
    cfg = load_config(path)
    macros = cfg.get("macros", {})
    rels = {}
    for pred, spec in cfg["relations"].items():
        spec = dict(spec)
        comp = []
        for p in spec.get("patterns", []):
            comp.append((f"{pred}.{p['id']}", re.compile(_expand(p["re"], macros), re.IGNORECASE),
                         p.get("status"), bool(p.get("typed"))))
        spec["_compiled"] = comp
        rels[pred] = spec
    return rels


def load_status_policy(path: str) -> dict[str, str]:
    return load_config(path).get("status_policy", {})


def _mask(sent: Sentence, heads: list[Mention], aliases: list[Mention]) -> str:
    reps: list[tuple[int, int, str]] = []
    for i, m in enumerate(heads):
        reps.append((m.start - sent.start, m.end - sent.start, f"{OPEN}{i}{CLOSE}"))
    for a in aliases:
        s, e = a.start - sent.start, a.end - sent.start
        k = s
        while k > 0 and sent.text[k - 1] in " (":
            k -= 1
        e2 = e + 1 if e < len(sent.text) and sent.text[e] == ")" else e
        reps.append((k, e2, ""))
    reps.sort()
    out, pos = [], 0
    for s, e, r in reps:
        if s < pos:
            continue
        out.append(sent.text[pos:s])
        out.append(r)
        pos = e
    out.append(sent.text[pos:])
    masked = "".join(out)
    # a parenthetical right after an entity is an aside (ticker, alias, birth year, "mã: PHR"): drop it so that the
    # cue pattern sees the entity and its predicate directly
    return _PAREN.sub("", masked)


def _types_ok(spec: dict, s: Mention, o: Mention) -> bool:
    return s.label.value in spec["subject"] and o.label.value in spec["object"]


def count_pairs(sentences: list[Sentence], mentions: list[Mention], relations: dict) -> int:
    """Unordered same-sentence mention pairs whose types fit at least one relation (for funnel counters)."""
    by: dict[int, list[Mention]] = {}
    for m in mentions:
        if m.sentence_index is not None and m.alias_of is None:
            by.setdefault(m.sentence_index, []).append(m)
    n = 0
    for ms in by.values():
        for a, b in combinations(ms, 2):
            if any(_types_ok(sp, a, b) or _types_ok(sp, b, a) for sp in relations.values()):
                n += 1
    return n


def generate_candidates(sentences: list[Sentence], mentions: list[Mention], relations: dict,
                        article_id: str = "") -> list[RelationCandidate]:
    by: dict[int, list[Mention]] = {}
    for m in mentions:
        if m.sentence_index is not None:
            by.setdefault(m.sentence_index, []).append(m)
    out: list[RelationCandidate] = []
    seen: set[str] = set()
    for sent in sentences:
        ms = sorted(by.get(sent.index, []), key=lambda x: x.start)
        heads = [m for m in ms if m.alias_of is None]
        aliases = [m for m in ms if m.alias_of is not None]
        if len(heads) < 2:
            continue
        masked = _mask(sent, heads, aliases)
        for pred, spec in relations.items():
            for pid, rx, hint, typed in spec["_compiled"]:
                for mt in rx.finditer(masked):
                    si = int(_PH.fullmatch(mt.group("S")).group(1))
                    oi = int(_PH.fullmatch(mt.group("O")).group(1))
                    s_m, o_m = heads[si], heads[oi]
                    if si == oi or (s_m.entity_id and s_m.entity_id == o_m.entity_id):
                        continue
                    source = "pattern"
                    if typed and not _types_ok(spec, s_m, o_m) and _types_ok(spec, o_m, s_m):
                        s_m, o_m, source = o_m, s_m, "types"
                    if not _types_ok(spec, s_m, o_m):
                        continue
                    if spec.get("symmetric"):
                        source = "symmetric"
                    cid = hashlib.sha1(f"{article_id}|{pred}|{s_m.start}|{s_m.end}|{o_m.start}|{o_m.end}".encode()).hexdigest()[:16]
                    if cid in seen:
                        continue
                    seen.add(cid)
                    lo = min(s_m.start, o_m.start) - sent.start
                    hi = max(s_m.end, o_m.end) - sent.start
                    status, cues = detect_modality(sent.text, lo, hi)
                    if hint == "ENDED" and status in (FactualStatus.FACT, FactualStatus.UNKNOWN, FactualStatus.HISTORICAL):
                        status, cues = FactualStatus.ENDED, cues or ["ended-pattern"]
                    cue_text = _PH.sub(lambda g, hs=heads: hs[int(g.group(1))].text, mt.group(0))
                    out.append(RelationCandidate(
                        candidate_id=cid, article_id=article_id, subject=s_m, object=o_m, predicate=pred,
                        sentence_index=sent.index, evidence_text=sent.text, evidence_start=sent.start,
                        evidence_end=sent.end, cue=cue_text, pattern_id=pid, direction_source=source,
                        direction_ambiguous=False, factual_status=status, modality_cues=cues, method="pattern"))
    return out


__all__ = ["EntityType", "count_pairs", "generate_candidates", "load_config", "load_relations", "load_status_policy"]


