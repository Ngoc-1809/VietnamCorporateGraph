"""ISSUED_BOND with a BondIssue node. Only the facts printed in the article are used: amount, term, rate, date, code.
Nothing is invented (no bond codes, no dates). A BondIssue is ARTICLE_GROUNDED only if the article gives an amount plus at
least one of term/rate/date/code, or an explicit bond code; otherwise it stays PROVISIONAL (candidate for human review)."""
from __future__ import annotations

import hashlib
import re

from vckg.entity_linking.store import RegistryStore
from vckg.models import EntityType, Mention, RelationCandidate, ResolutionStatus, Sentence
from vckg.relation_extraction.candidates import _PH, CLOSE, OPEN, _mask
from vckg.relation_extraction.modality import detect_modality

_ISSUE = re.compile(
    r"(?P<S>" + OPEN + r"\d+" + CLOSE + r")\s+(?:(?:dự kiến|dự định|đang|chuẩn bị|đã|sẽ|vừa|chính thức|thành công|tiếp tục)\s+){0,3}"
    r"(?:phát hành|chào bán)\b(?P<rest>[^;]{0,200})", re.IGNORECASE)
_BY = re.compile(r"(?P<rest>trái phiếu[^;" + OPEN + CLOSE + r"]{0,60}?)\s(?:do|của)\s+(?P<S>" + OPEN + r"\d+" + CLOSE + r")\s+phát hành", re.IGNORECASE)
_AMOUNT = re.compile(r"(\d[\d.,]*)\s*(nghìn tỷ|tỷ đồng|tỷ|triệu USD|triệu đô la|triệu đồng|tỷ USD)", re.IGNORECASE)
_TERM = re.compile(r"kỳ hạn\s+(\d+(?:[.,]\d+)?)\s*(năm|tháng)", re.IGNORECASE)
_RATE = re.compile(r"lãi suất\s+(?:cố định\s+|thả nổi\s+)?(?:từ\s+)?(\d+(?:[.,]\d+)?)\s*%", re.IGNORECASE)
_DATE = re.compile(r"ngày\s+(\d{1,2}/\d{1,2}(?:/\d{4})?)", re.IGNORECASE)
_CODE = re.compile(r"\bmã\s*:?\s*([A-Z]{2,5}\d{2}[A-Z0-9.\-]{2,}|[A-Z0-9]{3,}[-.]\d{4}[A-Z0-9.\-]*)")
_BOND = re.compile(r"trái phiếu", re.IGNORECASE)


def _norm(x: str) -> str:
    return re.sub(r"\s+", "", x.lower().replace(",", "."))


def bond_candidates(sentences: list[Sentence], mentions: list[Mention], store: RegistryStore, article_id: str,
                    text: str) -> tuple[list[RelationCandidate], list[Mention]]:
    by: dict[int, list[Mention]] = {}
    for m in mentions:
        if m.sentence_index is not None:
            by.setdefault(m.sentence_index, []).append(m)
    cands: list[RelationCandidate] = []
    new_mentions: list[Mention] = []
    for sent in sentences:
        ms = sorted(by.get(sent.index, []), key=lambda x: x.start)
        heads = [m for m in ms if m.alias_of is None]
        if not heads or not _BOND.search(sent.text):
            continue
        masked = _mask(sent, heads, [m for m in ms if m.alias_of is not None])
        found = []
        for mt in _ISSUE.finditer(masked):
            if _BOND.search(mt.group("rest")):
                found.append((mt.group("S"), mt.group("rest"), mt.start("rest")))
        for mt in _BY.finditer(masked):
            found.append((mt.group("S"), mt.group("rest"), mt.start("rest")))
        for s_ph, rest, _pos in found:
            s_m = heads[int(_PH.fullmatch(s_ph).group(1))]
            if s_m.label not in (EntityType.ORGANIZATION, EntityType.BANK) or not s_m.entity_id:
                continue
            rest_txt = _PH.sub(lambda g, hs=heads: hs[int(g.group(1))].text, rest)
            bm = _BOND.search(rest_txt)
            if not bm:
                continue
            # descriptor: from the bond word to the end of the clause, located in the ORIGINAL sentence for exact offsets
            k = sent.text.lower().find("trái phiếu", max(0, s_m.start - sent.start) if s_m.start >= sent.start else 0)
            if k < 0:
                continue
            tail = re.split(r"[;]|\s(?:để|nhằm|với mục đích|trong đó)\s", sent.text[k:], maxsplit=1)[0]
            desc = sent.text[k:k + min(len(tail), 140)].rstrip(" ,.")
            region = sent.text[max(0, sent.text.lower().find("phát hành")): k + len(desc)] if "phát hành" in sent.text.lower() else desc
            am, tm, rt, dt, cd = (_AMOUNT.search(region), _TERM.search(region), _RATE.search(region), _DATE.search(region), _CODE.search(region))
            parts = [f"{_norm(am.group(1))}{_norm(am.group(2))}" if am else "", tm.group(0).lower() if tm else "",
                     f"rate{_norm(rt.group(1))}" if rt else "", dt.group(1) if dt else "", cd.group(1) if cd else ""]
            specific = bool(cd) or (bool(am) and any((tm, rt, dt)))
            scope = "" if (cd or dt) else article_id  # no code/date: the event cannot be matched across articles
            bid = "bond:" + hashlib.sha1("|".join([s_m.entity_id, *parts, scope]).encode()).hexdigest()[:12]
            label = f"Trái phiếu {s_m.text} " + " ".join(p for p in parts if p)
            store.add_entity(label.strip(), EntityType.BOND_ISSUE, entity_id=bid, status=ResolutionStatus.PROVISIONAL,
                             source_type="article")
            if specific:
                store.set_status(bid, ResolutionStatus.ARTICLE_GROUNDED, f"article={article_id}; amount/term/date/code present")
            row = store.get_entity(bid)
            start = sent.start + k
            b_m = Mention(text=desc, start=start, end=start + len(desc), label=EntityType.BOND_ISSUE, ner_score=None, method="bond_rule",
                          article_id=article_id, sentence_index=sent.index, entity_id=bid,
                          link_status="grounded" if row["resolution_status"] == "ARTICLE_GROUNDED" else "provisional",
                          linking_method="bond_descriptor")
            if text[b_m.start:b_m.end] != b_m.text or b_m.end <= b_m.start:
                continue
            status, cues = detect_modality(sent.text, max(0, s_m.start - sent.start), start + len(desc) - sent.start)
            cid = hashlib.sha1(f"{article_id}|ISSUED_BOND|{s_m.start}|{b_m.start}".encode()).hexdigest()[:16]
            if any(c.candidate_id == cid for c in cands):
                continue
            cands.append(RelationCandidate(
                candidate_id=cid, article_id=article_id, subject=s_m, object=b_m, predicate="ISSUED_BOND",
                sentence_index=sent.index, evidence_text=sent.text, evidence_start=sent.start, evidence_end=sent.end,
                cue="phát hành trái phiếu", pattern_id="ISSUED_BOND.issues", direction_source="pattern",
                factual_status=status, modality_cues=cues, method="pattern"))
            new_mentions.append(b_m)
    return cands, new_mentions
