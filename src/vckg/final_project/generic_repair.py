"""Conservative, evidence-local repairs for generic Quarantine endpoints.

This never changes a QA tier. A proposal needs a single named endpoint, the other
endpoint and a relation cue in the same source sentence. The caller verifies the
evidence offsets against the article before applying it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from vckg.entity_linking.generic import is_generic_entity
from vckg.entity_linking.normalize import fold, slugify
from vckg.entity_resolution.core import PLACES
from vckg.preprocessing.text import split_sentences

VERSION = "generic-repair-v3"
_UPPER = "A-ZĐÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ"
_PROPER = rf"[{_UPPER}][\wÀ-ỹĐđ.&-]*"
_RUN = rf"{_PROPER}(?:\s+{_PROPER}){{0,4}}"
_LOCALITY = r"(?:(?:tỉnh|Tỉnh|thành phố|Thành phố|thị xã|Thị xã|quận|Quận|huyện|Huyện|xã|Xã|phường|Phường)\s+|TP\.?\s*)?"
_POLICE = re.compile(rf"\b[Cc]ông\s+[Aa]n\s+{_LOCALITY}{_RUN}")
_TAX = re.compile(rf"\b[Cc]ục\s+[Tt]huế\s+{_LOCALITY}{_RUN}")
_INSPECTOR = re.compile(
    r"\b[Tt]hanh\s+tra\s+(?:Chứng khoán Nhà nước|Ủy ban Chứng khoán Nhà nước|UBCKNN|"
    r"Bộ Y tế|Bộ Thông tin và Truyền thông|Bộ Tài chính|Bộ Công Thương|"
    rf"(?:tỉnh|TP\.?)\s+{_RUN})"
)
_GROUP = re.compile(rf"(?<!\w)(?:{_PROPER}\s+){{1,4}}Group\b")
_CHILD_AFTER = re.compile(
    r"\bcông ty con\s+là\s+((?:Công ty|CTCP|Tổng công ty)\s+[^,.;()\n]{4,90})", re.IGNORECASE)
_CHILD_BEFORE = re.compile(
    rf"(?<!\w)((?:{_PROPER}\s+){{1,5}}{_PROPER})\s*[-–,]?\s+công ty con"
    r"(?:\s+100% vốn)?\s+của\b")
_CUES = {
    "SANCTIONED_BY": r"\b(?:xu phat|phat|truy thu|quyet dinh xu ly vi pham)\b",
    "PROSECUTED_BY": r"\b(?:khoi to|truy to|bat tam giam|dieu tra)\b",
}
_GROUP_CUES = {
    "PARTNERS_WITH": r"\b(?:hop tac|doi tac)\b",
    "JOINT_VENTURE_WITH": r"\b(?:lien doanh|hop tac)\b",
    "LENDS_TO": r"\b(?:cho vay|vay|cap tin dung)\b",
    "OWNS_SHARES_IN": r"\b(?:so huu|nam giu|co dong|co phan)\b",
    "ACQUIRED": r"\b(?:mua lai|thau tom|chuyen nhuong)\b",
    "CHAIR_OF": r"\b(?:chu tich|hdqt)\b",
    "CEO_OF": r"\b(?:tong giam doc|giam doc|ceo)\b",
    "BOARD_MEMBER_OF": r"\b(?:hdqt|thanh vien hoi dong)\b",
    "FOUNDED": r"\b(?:sang lap|thanh lap)\b",
}
_CITIES = {"ha noi", "hai phong", "da nang", "can tho", "ho chi minh", "hcm", "tphcm", "thu duc", "viet tri"}


@dataclass(frozen=True)
class RepairProposal:
    side: str
    name: str
    sentence: str
    rule: str
    reverse: bool = False


def agency_key(name: str) -> str | None:
    """One stable identity for spelling variants of the same named office."""
    key = fold(name)
    if key.startswith("cong an "):
        family, place = "police", key.removeprefix("cong an ")
    elif key.startswith("cuc thue "):
        family, place = "tax", key.removeprefix("cuc thue ")
    elif key.startswith("thanh tra "):
        family, place = "inspector", key.removeprefix("thanh tra ")
    else:
        return None
    place = re.sub(r"^(?:tinh|thanh pho|tp|thi xa|quan|huyen|xa|phuong)\s+", "", place)
    place = {"tp hcm": "ho chi minh", "tphcm": "ho chi minh", "hcm": "ho chi minh",
             "sai gon": "ho chi minh", "ubcknn": "uy ban chung khoan nha nuoc",
             "chung khoan nha nuoc": "uy ban chung khoan nha nuoc"}.get(place, place)
    return f"{family}:{slugify(place)}" if place else None


def _has_name(sentence: str, name: str) -> bool:
    key = fold(name)
    return bool(key and re.search(rf"(?<!\w){re.escape(key)}(?!\w)", fold(sentence)))


def _agency_candidates(sentence: str, key: str) -> list[str]:
    matcher = _TAX if key.startswith(("cuc thue", "chi cuc thue")) else (
        _POLICE if "cong an" in key else _INSPECTOR if "thanh tra" in key else None)
    if matcher is None:
        return []
    out = []
    for match in matcher.finditer(sentence):
        name = match.group().strip(" ,.;:")
        if is_generic_entity(name):
            continue
        if matcher in (_POLICE, _TAX):
            prefix = re.match(r"(?i)^(?:công an|cục thuế)\s+", name)
            tail = name[prefix.end():] if prefix else ""
            suffix = re.sub(r"(?i)^(?:tỉnh|thành phố|thị xã|quận|huyện|xã|phường|TP\.?)\s*", "", tail).strip()
            if not suffix or (fold(suffix) not in PLACES and not
                              (fold(tail).startswith("tp ") and fold(suffix) == "hcm")):
                continue
            if fold(tail).startswith(("tp ", "thanh pho ")) and fold(suffix) not in _CITIES:
                continue
        out.append(name)
    return out


def _child_name_after(sentence: str) -> list[str]:
    names = []
    for match in _CHILD_AFTER.finditer(sentence):
        if re.search(r"(?i)\b(?:\d+|hai|ba|bốn|nhiều|các)\s+công ty con\s+là\s+$",
                     sentence[max(0, match.start() - 20):match.start(1)]):
            continue
        name = match.group(1).strip()
        name = re.split(r"\s+(?:do|được|với|trong đó|hiện|vừa)\s+", name, maxsplit=1, flags=re.IGNORECASE)[0]
        if len(name.split()) >= 4 and not re.search(r"(?i)\s+và\s+", name) and not is_generic_entity(name):
            names.append(name)
    return names


def _group_name(match: re.Match[str], sentence: str) -> str | None:
    name = match.group().strip()
    if sentence[max(0, match.start() - 3):match.start()].rstrip().endswith("&"):
        return None
    if fold(name).split()[0] in {"ceo", "hdqt", "chu", "pho", "tong", "ong", "ba"}:
        return None
    return None if is_generic_entity(name) else name


def propose(row: dict[str, str]) -> RepairProposal | None:
    """Return one evidence-local specific replacement, or None on ambiguity."""
    sides = [side for side in ("subject", "object") if is_generic_entity(row[f"{side}_name"])]
    if len(sides) != 1:
        return None
    side = sides[0]
    key = fold(row[f"{side}_name"])
    other = row["object_name" if side == "subject" else "subject_name"]
    found: dict[str, tuple[str, str]] = {}
    for item in split_sentences(row["evidence_text"]):
        sentence = item.text
        if not _has_name(sentence, other):
            continue
        if side == "object" and row["relation_type"] in _CUES and re.search(
                _CUES[row["relation_type"]], fold(sentence)):
            for name in _agency_candidates(sentence, key):
                found[fold(name)] = (name, sentence)
        if key == "group" and row["relation_type"] in _GROUP_CUES and re.search(
                _GROUP_CUES[row["relation_type"]], fold(sentence)):
            for match in _GROUP.finditer(sentence):
                name = _group_name(match, sentence)
                if name:
                    found[fold(name)] = (name, sentence)
        if key == "cong ty con" and row["relation_type"] in {"SUBSIDIARY_OF", "OWNS_SHARES_IN"}:
            if side == "object":
                names = _child_name_after(sentence)
            else:
                names = [name for match in _CHILD_BEFORE.finditer(sentence)
                         if fold(sentence[match.end():]).startswith(fold(other) + " ") or
                         fold(sentence[match.end():]) == fold(other)
                         for name in [match.group(1).strip(" -–,")]
                         if len(name.split()) >= 2 and not is_generic_entity(name)]
            for name in names:
                found[fold(name)] = (name, sentence)
    if len(found) != 1:
        return None
    name, sentence = next(iter(found.values()))
    if key == "group":
        return RepairProposal(side, name, sentence, "NAMED_GROUP_SAME_SENTENCE")
    if key == "cong ty con":
        return RepairProposal(side, name, sentence, "EXPLICIT_SUBSIDIARY_SAME_SENTENCE",
                              side == "object" and row["relation_type"] == "SUBSIDIARY_OF")
    return RepairProposal(side, name, sentence, "NAMED_AUTHORITY_SAME_SENTENCE")
