"""Heuristic scope classifier for NER mentions (diagnostic + filtering aid).

These are transparent heuristics, NOT ground truth. They exist to separate mentions that can never be
corporate-graph nodes (market indices, exchanges, bare job titles, generic nouns) from real candidates
for linking, so that link-rate statistics are not deflated by out-of-domain NER output."""
from __future__ import annotations

import re

from vckg.entity_linking.normalize import normalize_name
from vckg.models import EntityType, Mention

_INDEX = re.compile(r"^(?:vn|hnx|upcom|vn30|vnx|vn100|vnallshare|vnmidcap|vnsmallcap)\s*-?\s*(?:index|30)?$|-index$|\bindex\b", re.IGNORECASE)
_EXCHANGE = re.compile(r"^(?:sàn\s+)?(?:hose|hnx|upcom|hsx)$|^sở giao dịch|^sàn giao dịch", re.IGNORECASE)
_GENERIC = re.compile(
    r"^(?:cơ quan(?: quản lý| chức năng| nhà nước)?|trung ương|chính quyền|nhà nước|doanh nghiệp|công ty|ngân hàng|"
    r"tập đoàn|ban|bộ|ủy ban|hội đồng|cổ đông|nhà đầu tư|thị trường|ctcp|tnhh|cp|công ty cổ phần|công ty tnhh|hđqt|hđtv|hội đồng quản trị|hội đồng thành viên|ban kiểm soát|ban giám đốc|đhđcđ|đại hội đồng cổ đông)$", re.IGNORECASE)
_TITLE_WORDS = {
    "ông", "bà", "anh", "chị", "phó", "thủ", "tướng", "chủ", "tịch", "tổng", "giám", "đốc", "thượng", "trung",
    "đại", "thiếu", "bộ", "trưởng", "thường", "trực", "thường vụ", "vụ", "hđqt", "ceo", "mr", "mrs", "ms",
    "tiến", "sĩ", "ts", "pgs", "gs", "ths", "kiêm", "điều", "hành", "tá", "úy",
}
_MEMBER_NOUNS = re.compile(r"viên\s+quốc hội|đại biểu", re.IGNORECASE)


def classify_scope(m: Mention) -> tuple[bool, str]:
    """Returns (in_domain, reason). in_domain False => cannot be a corporate-graph entity candidate."""
    t = m.text.strip()
    if m.label == EntityType.PERSON:
        toks = [w for w in re.split(r"\s+", t) if w]
        name_toks = [w for w in toks if w.lower() not in _TITLE_WORDS]
        if not name_toks:
            return False, "PERSON_TITLE_ONLY"
        if len(name_toks) < 2 and not any(w[0].isupper() for w in name_toks):
            return False, "PERSON_NOT_A_NAME"
        return True, "PERSON_SINGLE_TOKEN" if len(name_toks) == 1 else "PERSON"
    key = normalize_name(t, drop_prefix=False)
    if _INDEX.search(t) or _INDEX.search(key):
        return False, "ORG_MARKET_INDEX"
    if _EXCHANGE.search(t):
        return False, "ORG_EXCHANGE"
    if _GENERIC.match(t) or _MEMBER_NOUNS.search(t):
        return False, "ORG_GENERIC_TERM"
    if m.label in (EntityType.GOVERNMENT_AGENCY, EntityType.REGULATOR):
        return True, "AUTHORITY"
    if t.isupper() and 2 <= len(t) <= 5 and " " not in t:
        return True, "ORG_TICKER_LIKE"
    return True, "ORG"


