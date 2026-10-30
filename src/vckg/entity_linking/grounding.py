"""Article-grounded identity rules. Identity confidence is independent of relation confidence.

ARTICLE_GROUNDED means the press text itself identifies the entity well enough to be a graph endpoint:
  * organization: legal-form prefix + capitalised proper name, or a full multi-word capitalised name, or a
    "<Name> Group/Holdings/Bank/..." name; a bare acronym or a bare single common word never qualifies;
  * person: a full name (>=2 capitalised name tokens after removing titles) that holds a role at a linked
    organization in the same sentence (the identity cluster stays article-scoped; it is NOT merged by name);
  * authority: an explicit authority prefix (Bo, Uy ban, Cuc, So, Tong cuc, Co quan, Cong an, Thanh tra...) + a name.
Any name that has near-duplicate registry candidates (identity conflict) is never grounded."""
from __future__ import annotations

import re

from vckg.entity_linking.normalize import normalize_name
from vckg.models import EntityType, Mention

_LEGAL = re.compile(
    r"^(?:tổng công ty cổ phần|tổng công ty|công ty cổ phần|công ty tnhh(?: mtv)?|công ty cp|công ty|ctcp|tập đoàn|"
    r"ngân hàng(?: tmcp| thương mại cổ phần)?|nhà máy)\s+", re.IGNORECASE)
_ORG_SUFFIX = re.compile(r"\b(?:group|holdings?|corp(?:oration)?|jsc|ltd|inc|bank|capital)\b", re.IGNORECASE)
_AUTH = re.compile(r"^(?:bộ|ủy ban|cục|sở|tổng cục|cơ quan|công an|thanh tra|ngân hàng nhà nước|viện|tòa án|kiểm toán|hội đồng nhân dân|"
                   r"văn phòng)\b", re.IGNORECASE)
_GENERIC_NAME = {"việt nam", "nhà nước", "quốc gia", "trung ương", "thành phố", "tỉnh", "nước"}
_TITLE = {"ông", "bà", "anh", "chị", "ts", "pgs", "gs", "ths", "mr", "ms", "mrs"}


def _cap(tok: str) -> bool:
    return bool(tok) and (tok[0].isupper() or tok[0].isdigit())


def org_grounded(m: Mention, ner_min: float = 0.8) -> bool:
    text = m.text.strip()
    if text.isupper() and " " not in text:
        return False  # bare acronym
    toks = text.split()
    if len(toks) > 9:
        return False
    if m.label in (EntityType.REGULATOR, EntityType.GOVERNMENT_AGENCY):
        return bool(_AUTH.match(text)) and len(toks) >= 2 and all(_cap(t) or t.lower() in {"và", "của", "nhà", "nước"} for t in toks[1:2])
    low_score = m.ner_score is not None and m.ner_score < ner_min
    lm = _LEGAL.match(text)
    if lm:
        rest = text[lm.end():].split()
        while rest and rest[-1].lower() in ("việt", "nam"):
            rest = rest[:-2] if len(rest) >= 2 and rest[-2].lower() == "việt" else rest[:-1]
        name = " ".join(rest)
        return bool(rest) and all(_cap(t) or t in {"-", "–", "&"} for t in rest) and name.lower() not in _GENERIC_NAME and not low_score
    if _ORG_SUFFIX.search(text) and (len(toks) >= 2 or "-" in text) and _cap(toks[0]) and not low_score:
        return True
    return len(toks) >= 3 and all(_cap(t) for t in toks) and not low_score and normalize_name(text) not in {n.replace(" ", "") for n in _GENERIC_NAME}


def person_grounded(m: Mention, has_org_context: bool) -> bool:
    toks = [t for t in m.text.split() if t.lower() not in _TITLE]
    return has_org_context and len(toks) >= 2 and all(_cap(t) for t in toks)
