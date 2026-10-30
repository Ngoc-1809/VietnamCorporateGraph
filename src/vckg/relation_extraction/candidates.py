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
    """Relation specs with compiled patterns under spec['_compiled'] = [(pattern_id, regex, status_hint, typed, raw, elided)]."""
    cfg = load_config(path)
    macros = cfg.get("macros", {})
    rels = {}
    for pred, spec in cfg["relations"].items():
        spec = dict(spec)
        comp = []
        for p in spec.get("patterns", []):
            comp.append((f"{pred}.{p['id']}", re.compile(_expand(p["re"], macros), re.IGNORECASE),
                         p.get("status"), bool(p.get("typed")), bool(p.get("raw")), bool(p.get("elided"))))
        spec["_compiled"] = comp
        rels[pred] = spec
    return rels


def load_status_policy(path: str) -> dict[str, str]:
    return load_config(path).get("status_policy", {})


def _mask(sent: Sentence, heads: list[Mention], aliases: list[Mention], strip_paren: bool = True) -> str:
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
    return _PAREN.sub("", masked) if strip_paren else masked


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


_LIST_TAIL = re.compile(r"^\s*(?:,|và|cùng với|hay)\s*(" + OPEN + r"\d+" + CLOSE + r")")
_LIST_PREDS = {"CHAIR_OF", "CEO_OF", "BOARD_MEMBER_OF", "OWNS_SHARES_IN", "FOUNDED", "SUBSIDIARY_OF"}
_PRONOUN = re.compile(r"(?<![\w])(?:ông|bà)(?![\w])(?!\s*" + OPEN + ")", re.IGNORECASE)
MAX_CONTEXT_CHARS = 700


def _cid(article_id: str, pred: str, s_m: Mention, o_m: Mention) -> str:
    return hashlib.sha1(f"{article_id}|{pred}|{s_m.start}|{s_m.end}|{o_m.start}|{o_m.end}".encode()).hexdigest()[:16]


def generate_candidates(sentences: list[Sentence], mentions: list[Mention], relations: dict,
                        article_id: str = "", text: str | None = None) -> list[RelationCandidate]:
    """Pattern candidates per sentence. Beyond plain in-sentence matches (direction_source=pattern|types|symmetric):
      * object lists ("Chu tich ... cua ca A va B") expand to one candidate per listed object;
      * parenthetical roles ("X (Chu tich Y)") use the raw (unstripped) mask;
      * ELIDED object (ownership of unnamed company) and PRONOUN subject ("ong/ba ...") are resolved from the nearest
        preceding sentence and flagged direction_source='elided_object'|'coref': candidate-only (never official),
        evidence is the contiguous multi-sentence slice so the verifier and reviewer see the antecedent."""
    by: dict[int, list[Mention]] = {}
    for m in mentions:
        if m.sentence_index is not None:
            by.setdefault(m.sentence_index, []).append(m)
    out: list[RelationCandidate] = []
    seen: set[str] = set()
    last_owns_obj: tuple[Mention, Sentence] | None = None

    def emit(pred, spec, pid, hint, s_m, o_m, source, sent, ev_sent_start, mt, heads_ref, extra_cues=None):
        nonlocal last_owns_obj
        cid = _cid(article_id, pred, s_m, o_m)
        if cid in seen:
            return
        seen.add(cid)
        ev_start = ev_sent_start
        ev_text = text[ev_start:sent.end] if text is not None else sent.text
        lo = max(0, min(s_m.start, o_m.start, sent.start) - ev_start) if source in ("coref", "elided_object") else min(s_m.start, o_m.start) - sent.start
        hi = max(s_m.end, o_m.end) - (ev_start if source in ("coref", "elided_object") else sent.start)
        win_text = ev_text if source in ("coref", "elided_object") else sent.text
        status, cues = detect_modality(win_text, lo, hi)
        if hint == "ENDED" and status in (FactualStatus.FACT, FactualStatus.UNKNOWN, FactualStatus.HISTORICAL):
            status, cues = FactualStatus.ENDED, cues or ["ended-pattern"]
        cue_text = _PH.sub(lambda g: heads_ref[int(g.group(1))].text if int(g.group(1)) < len(heads_ref) else "", mt.group(0))
        out.append(RelationCandidate(
            candidate_id=cid, article_id=article_id, subject=s_m, object=o_m, predicate=pred,
            sentence_index=sent.index, evidence_text=ev_text, evidence_start=ev_start, evidence_end=sent.end,
            cue=cue_text, pattern_id=pid, direction_source=source, direction_ambiguous=False,
            factual_status=status, modality_cues=(extra_cues or []) + cues, method="pattern"))
        if pred == "OWNS_SHARES_IN" and source == "pattern":
            last_owns_obj = (o_m, sent)

    for sent in sentences:
        ms = sorted((m for m in by.get(sent.index, []) if not m.linking_method.startswith("out_of_scope")), key=lambda x: x.start)
        heads = [m for m in ms if m.alias_of is None]  # out-of-scope spans (HDQT, indices, generic nouns) stay as plain text
        aliases = [m for m in ms if m.alias_of is not None]
        if not heads:
            continue
        variants = {False: _mask(sent, heads, aliases, True), True: _mask(sent, heads, aliases, False)}
        produced_subjects: set[int] = set()
        for pred, spec in relations.items():
            for pid, rx, hint, typed, raw, elided in spec["_compiled"]:
                if elided:
                    continue
                masked = variants[raw]
                for mt in rx.finditer(masked):
                    si = int(_PH.fullmatch(mt.group("S")).group(1))
                    oi = int(_PH.fullmatch(mt.group("O")).group(1))
                    targets = [oi]
                    if pred in _LIST_PREDS and mt.end("O") == mt.end():
                        tail = masked[mt.end():]
                        while True:
                            lm = _LIST_TAIL.match(tail)
                            if not lm:
                                break
                            targets.append(int(_PH.fullmatch(lm.group(1)).group(1)))
                            tail = tail[lm.end():]
                    for k, oj in enumerate(targets):
                        s_m, o_m = heads[si], heads[oj]
                        if si == oj or (s_m.entity_id and s_m.entity_id == o_m.entity_id):
                            continue
                        source = "pattern"
                        if typed and not _types_ok(spec, s_m, o_m) and _types_ok(spec, o_m, s_m):
                            s_m, o_m, source = o_m, s_m, "types"
                        if not _types_ok(spec, s_m, o_m):
                            continue
                        if spec.get("symmetric"):
                            source = "symmetric"
                        before = len(out)
                        emit(pred, spec, pid + ("+list" if k else ""), hint, s_m, o_m, source, sent, sent.start, mt, heads)
                        if len(out) > before and pred == "OWNS_SHARES_IN":
                            produced_subjects.add(si)
        # ---- elided object: ownership with an unnamed company, object taken from the preceding OWNS candidate
        if last_owns_obj is not None and text is not None:
            o_m, o_sent = last_owns_obj
            if 0 < sent.index - o_sent.index <= 3 and sent.end - o_sent.start <= MAX_CONTEXT_CHARS:
                spec = relations["OWNS_SHARES_IN"]
                for pid, rx, hint, typed, raw, elided in spec["_compiled"]:
                    if not elided:
                        continue
                    for mt in rx.finditer(variants[raw]):
                        si = int(_PH.fullmatch(mt.group("S")).group(1))
                        s_m = heads[si]
                        if si in produced_subjects or s_m.entity_id == o_m.entity_id or not _types_ok(spec, s_m, o_m):
                            continue
                        emit("OWNS_SHARES_IN", spec, pid, hint, s_m, o_m, "elided_object", sent, o_sent.start, mt, heads)
        # ---- pronoun subject: "ong/ba ..." resolved to the single person of the preceding sentence(s)
        if text is not None and not any(h.label == EntityType.PERSON for h in heads):
            prev_person = None
            prev_sent = None
            for back in (1, 2):
                idx = sent.index - back
                if idx < 0:
                    break
                ps = [m for m in by.get(idx, []) if m.label == EntityType.PERSON and m.alias_of is None]
                if ps:
                    ids = {m.entity_id or m.text for m in ps}
                    if len(ids) == 1:
                        prev_person, prev_sent = ps[0], sentences[idx]
                    break
            if prev_person is not None and sent.end - prev_sent.start <= MAX_CONTEXT_CHARS:
                pm = _PRONOUN.search(variants[False][:70])
                if pm:
                    ext = [*heads, prev_person]
                    cm = variants[False][:pm.start()] + f"{OPEN}{len(heads)}{CLOSE}" + variants[False][pm.end():]
                    for pred, spec in relations.items():
                        if pred not in ("CHAIR_OF", "CEO_OF", "BOARD_MEMBER_OF", "FOUNDED"):
                            continue
                        for pid, rx, hint, typed, raw, elided in spec["_compiled"]:
                            if elided or raw:
                                continue
                            for mt in rx.finditer(cm):
                                si = int(_PH.fullmatch(mt.group("S")).group(1))
                                oi = int(_PH.fullmatch(mt.group("O")).group(1))
                                if si != len(heads) or oi >= len(heads) or not _types_ok(spec, prev_person, heads[oi]):
                                    continue
                                emit(pred, spec, pid, hint, prev_person, heads[oi], "coref", sent, prev_sent.start, mt, ext)
    return out


__all__ = ["EntityType", "count_pairs", "generate_candidates", "load_config", "load_relations", "load_status_policy"]


