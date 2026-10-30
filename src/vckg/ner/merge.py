"""Merge NER mentions with dictionary mentions and repair systematic span-boundary errors.

Boundary repairs (found in Phase 4 diagnostics on real articles):
  * PERSON spans that include a title ('ông Zhang Qiang') or role ('HĐQT ...') -> trimmed to the name;
  * ORG spans that start with a role word ('HĐQT Công ty ...') -> trimmed;
  * ORG spans cut inside a legal name ('China Railway Sixth Group' of 'Công ty TNHH China Railway Sixth Group Việt Nam')
    -> extended over the directly adjacent legal-form prefix / country suffix.
All offsets stay exact (text[start:end] == mention.text)."""
from __future__ import annotations

import re

from vckg.entity_linking.normalize import clean_surface
from vckg.models import EntityType, Mention, Sentence
from vckg.preprocessing.text import sentence_index_for

_PERSON_LEAD = re.compile(
    r"^(?:(?:ông|bà|anh|chị|ts|pgs|gs|ths|ks|bs|mr|mrs|ms|dr|thượng tướng|đại tướng|trung tướng|thiếu tướng|thượng tá|đại tá|"
    r"phó thủ tướng(?: thường trực)?|thủ tướng|bộ trưởng|thứ trưởng|chủ tịch(?: hđqt)?|phó chủ tịch|tổng giám đốc|"
    r"phó tổng giám đốc|giám đốc|hđqt|cố vấn|nhà sáng lập)\.?\s+)+", re.IGNORECASE)
_ORG_LEAD = re.compile(r"^(?:(?:hđqt|hđtv|hội đồng quản trị|hội đồng thành viên|ban kiểm soát|ban lãnh đạo)\s+)+", re.IGNORECASE)
_LEFT_FORM = re.compile(
    r"((?:(?:công ty(?: cổ phần| tnhh(?: mtv)?| cp)?|tập đoàn|tổng công ty(?: cổ phần)?|ngân hàng(?: tmcp| thương mại cổ phần)?|ctcp)\s+)+)$",
    re.IGNORECASE)
_RIGHT_COUNTRY = re.compile(r"^\s+(Việt Nam)(?![\w])")
_RIGHT_FORM = re.compile(r"^\s*[-–]\s*(CTCP|TNHH|Công ty cổ phần)(?![\w])")
_EDGE = " ,.;:\"'“”()[]"


def _trim_lead(text: str, m: Mention, rx: re.Pattern) -> Mention:
    s = rx.match(m.text)
    if not s or s.end() >= len(m.text):
        return m
    ns = m.start + s.end()
    return m.model_copy(update={"start": ns, "text": text[ns:m.end]})


def repair_span(text: str, m: Mention) -> Mention | None:
    s, e = m.start, m.end
    while s < e and text[s] in _EDGE:
        s += 1
    while e > s and text[e - 1] in _EDGE:
        e -= 1
    if e <= s:
        return None
    m = m.model_copy(update={"start": s, "end": e, "text": text[s:e]})
    if m.method != "gliner2.5":
        return m
    if m.label == EntityType.PERSON:
        m = _trim_lead(text, m, _PERSON_LEAD)
    elif m.label != EntityType.GOVERNMENT_AGENCY and m.label != EntityType.REGULATOR:
        m = _trim_lead(text, m, _ORG_LEAD)
        left = _LEFT_FORM.search(text[max(0, m.start - 40):m.start])
        if left and not _LEFT_FORM.match(m.text + " "):
            ns = m.start - len(left.group(1))
            m = m.model_copy(update={"start": ns, "text": text[ns:m.end]})
        rf = _RIGHT_FORM.match(text[m.end:m.end + 24])
        if rf:  # "Tổng Công ty Phát điện 2 - CTCP": the legal form belongs to the name
            ne = m.end + rf.end()
            m = m.model_copy(update={"end": ne, "text": text[m.start:ne]})
        right = _RIGHT_COUNTRY.match(text[m.end:m.end + 12])
        if right and not m.text.lower().endswith("việt nam"):
            ne = m.end + right.end()
            m = m.model_copy(update={"end": ne, "text": text[m.start:ne]})
    return m if clean_surface(m.text) else None


def merge_mentions(ner: list[Mention], dic: list[Mention], text: str, sentences: list[Sentence]) -> list[Mention]:
    """Dictionary (registry) spans win over overlapping NER spans; NER spans are boundary-repaired first."""
    out: list[Mention] = list(dic)
    for n in sorted(ner, key=lambda x: (x.start, -(x.end - x.start))):
        n = repair_span(text, n)
        if n is None:
            continue
        if any(n.start < d.end and d.start < n.end for d in out):
            continue
        out.append(n)
    out.sort(key=lambda x: (x.start, x.end))
    return [m.model_copy(update={"sentence_index": sentence_index_for(sentences, m.start)}) for m in out]




# ---------------------------------------------------------------- Phase 5 recall helpers
_ORG_HEAD = re.compile(r"^(?:tổng công ty|công ty|tập đoàn|ngân hàng|nhà máy|ctcp|công ty cổ phần)\b", re.IGNORECASE)
_NOT_ORG_LABEL = {EntityType.PERSON}


def merge_split_orgs(text: str, mentions: list[Mention]) -> list[Mention]:
    """GLiNER sometimes splits one legal name ('Nha may' + 'In' + 'tien Quoc gia'). Re-join two NER org spans when the first is a
    short legal-form head (<=3 tokens) and the gap is whitespace or <=2 capitalised tokens without punctuation."""
    ms = sorted(mentions, key=lambda m: m.start)
    out: list[Mention] = []
    i = 0
    while i < len(ms):
        a = ms[i]
        if (i + 1 < len(ms) and a.method == "gliner2.5" and a.label not in _NOT_ORG_LABEL and _ORG_HEAD.match(a.text)
                and len(a.text.split()) <= 3):
            b = ms[i + 1]
            gap = text[a.end:b.start]
            gtoks = gap.split()
            if (b.method == "gliner2.5" and b.label not in _NOT_ORG_LABEL and b.start >= a.end and not re.search(r"[,.;:()\[\]]", gap)
                    and len(gtoks) <= 2 and all(t[0].isupper() for t in gtoks) and text[b.start:b.end] and len(b.text.split()) <= 4):
                out.append(a.model_copy(update={"end": b.end, "text": text[a.start:b.end], "label": EntityType.ORGANIZATION}))
                i += 2
                continue
        out.append(a)
        i += 1
    return out


def propagate_mentions(text: str, mentions: list[Mention]) -> list[Mention]:
    """Article-scope exact-repeat propagation: a name that NER found once is also tagged at its other exact occurrences
    (NER often misses repeats inside lists/headlines). Same article only, capitalised, >=2 tokens (or >=6 chars), not an
    acronym, not truncating a longer capitalised name. Added mentions have method='propagated' and no ner_score."""
    have = list(mentions)
    sources = {}
    for m in mentions:
        if m.method != "gliner2.5" or m.text.isupper() or m.label in (EntityType.REGULATOR, EntityType.GOVERNMENT_AGENCY):
            continue
        if len(m.text.split()) >= 2 or len(m.text) >= 6:
            sources.setdefault((m.text, m.label), m)
    added: list[Mention] = []
    for (surface, label), src in sources.items():
        for mt in re.finditer(r"(?<![\w])" + re.escape(surface) + r"(?![\w])", text):
            s, e = mt.span()
            if any(s < x.end and x.start < e for x in have + added):
                continue
            if re.match(r"\s+[A-ZĐ]", text[e:e + 3]) and label != EntityType.PERSON:
                continue
            added.append(src.model_copy(update={"start": s, "end": e, "text": surface, "method": "propagated", "ner_score": None,
                                                "sentence_index": None, "alias_of": None}))
    return sorted(have + added, key=lambda m: (m.start, m.end))
