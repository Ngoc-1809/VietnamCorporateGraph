"""Phase 6B.2 - hybrid relation validation (versioned; the Phase 6A auto_auditor is untouched and still runnable as baseline).

Two tiers
  1. HARD validation (mandatory, predicate independent): evidence exists and matches the article, endpoints map to real mentions inside
     the evidence, entity types fit the predicate, no self-loop, negation, factual status (history/ended/planned/alleged), prosecution
     stage, conservative identity (short/generic/truncated names, article-scoped person ids belong to this article).
  2. SEMANTIC conditions per predicate, written against the SENTENCE (not against the candidate generator).
Rule agreement is only a SIGNAL: RULE_SUPPORTED | SEMANTIC_ONLY | CONTRADICTED | INSUFFICIENT_EVIDENCE.
 - PASS / AUTO_CORRECT require hard OK + semantic OK + RULE_SUPPORTED + official status.
 - SEMANTIC_ONLY is never promoted to PASS: it is QUARANTINE with class SEMANTIC_ONLY_CLEAN (best review priority).
 - Qwen is NOT used here: the same model that discovers a relation cannot independently verify it.
Corrections are limited to what the text proves (status keywords, direction by sub/parent grammar, Phó Chủ tịch -> BOARD_MEMBER_OF,
ownership still positive -> not ENDED). No dates are inferred."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from vckg.entity_linking.normalize import normalize_name
from vckg.models import FactualStatus, RelationCandidate
from vckg.reasons import suspect_span
from vckg.relation_extraction.modality import detect_modality

VALIDATOR_VERSION = "hybrid-validator-v1"
OFFICIAL = {"FACT", "HISTORICAL", "ENDED"}
ROLE_PREDS = {"CHAIR_OF", "CEO_OF", "BOARD_MEMBER_OF"}
I = re.IGNORECASE

_KIN = re.compile(r"\b(vợ|chồng|con gái|con trai|con|cha|bố|mẹ|anh trai|em trai|chị gái|em gái|chị dâu|anh rể|em dâu|người liên quan)\b", I)
_TENURE = re.compile(r"trong giai đoạn từ[^.;]{0,50}?\bđến\b", I)
_ENDED = re.compile(r"\bđã\s+(?:thôi giữ chức|từ nhiệm|miễn nhiệm|nghỉ hưu|rời)\b|\bmiễn nhiệm\b", I)
_FORMER = re.compile(r"\b(?:nguyên|cựu|từng là|từng giữ)\b", I)
_RESIGN_REQ = re.compile(r"(?:đơn\s+)?xin\s+từ nhiệm|đề nghị\s+từ nhiệm|dự kiến\s+từ nhiệm|có đơn\s+từ nhiệm|tờ trình miễn nhiệm", I)
_CRIMINAL = re.compile(r"\b(?:vụ án|bản án|bị cáo|bị can|thi hành án|bị bắt|bị khởi tố|bị truy tố|lừa đảo|bồi hoàn)\b", I)
_CAPTION = re.compile(r"Ảnh\s*:|\(đứng giữa\)|\(bên (?:trái|phải)\)", I)
_GENERIC_ORG = {"viet nam", "cong ty", "ctcp", "tap doan", "ngan hang", "nha nuoc", "doanh nghiep", "ubnd", "hdqt"}
_OWN_CUE = re.compile(r"hoàn tất mua|đã mua|mua vào|mua thêm|sở hữu|nắm giữ|\bnắm\b|giữ (?:lại )?\d|cổ đông|góp \d|chiếm \d|tỷ lệ sở hữu|\d[\d.,]*\s*%\s*(?:vốn|cổ phần|cổ phiếu)", I)
_OWN_HOLD = re.compile(r"hoàn tất mua|đã mua|mua vào|mua thêm|(?:đang\s+|hiện\s+)?(?:sở hữu|nắm giữ|nắm)\s+(?:hơn|gần|trên|khoảng)?\s*\d|tỷ lệ sở hữu (?:hiện tại|từ|của)|giữ (?:lại )?\d|cổ đông (?:lớn|sở hữu|kiểm soát)|chiếm \d|nâng tỷ lệ sở hữu lên|đang nắm|trong đó[^.;]{0,80}nắm", I)
_INTENT = re.compile(r"đăng ký (?:mua|bán)|dự kiến (?:mua|bán)|muốn (?:mua|bán)|đăng ký giao dịch", I)
_EXIT = re.compile(r"thoái (?:toàn bộ|hết)|bán (?:toàn bộ|hết)|rút hoàn toàn|không còn (?:sở hữu|nắm)", I)
_REMAIN = re.compile(r"(?:xuống|còn|giảm)[^.;]{0,35}?(\d[\d.,]*)\s*%", I)
_ACQ_VERB = re.compile(r"mua lại|thâu tóm|hoàn tất mua|nhận chuyển nhượng|sáp nhập|\bmua\b", I)
_ACQ_SELL = re.compile(r"(?:thoái|bán|chuyển nhượng)[^.;]{0,90}?\bcho\b", I)
_FOUND_CUE = re.compile(r"sáng lập|đồng sáng lập|thành lập", I)
_PROXY = re.compile(r"\bthuê\b|nhờ|đứng tên|vỏ bọc", I)
_SUB_CUE = re.compile(r"công ty con|công ty mẹ|trực thuộc|thuộc tập đoàn|đơn vị thành viên|công ty thành viên|đều thuộc", I)
_LEND_CUE = re.compile(r"cho vay|cấp tín dụng|hợp đồng tín dụng|khoản vay|giải ngân|tài trợ vốn|hạn mức", I)
_LEND_GENERIC = re.compile(r"lãi suất cho vay|cho vay ký quỹ|margin|dư nợ cho vay|hoạt động cho vay", I)
_JV_CUE = re.compile(r"liên doanh|joint venture|góp vốn thành lập", I)
_PART_CUE = re.compile(r"hợp tác chiến lược|ký(?: kết)? (?:thỏa thuận |biên bản ghi nhớ )?hợp tác|bắt tay|đối tác chiến lược", I)
_SANC_VERB = re.compile(r"xử phạt|\bphạt\b|đình chỉ|cảnh cáo", I)
_PROS_VERB = re.compile(r"khởi tố|truy tố|bắt tạm giam|\bbắt\b|tạm giam", I)
_ALLEGED = re.compile(r"\b(?:bị cáo buộc|cáo buộc|nghi vấn|nghi ngờ|xác định)\b", I)
_CODE = re.compile(r"[A-Z]{2,5}\d{2}[A-Z0-9.\-]{2,}|[A-Z0-9]{3,}[-.]\d{4}[A-Z0-9.\-]*")
_AMOUNT = re.compile(r"\d[\d.,]*(?:nghìntỷ|tỷđồng|tỷusd|triệuusd|triệuđồng)", I)
_ROLE = {"CHAIR_OF": re.compile(r"(?<!phó )(?<!phó\s)chủ tịch(?!\s+(?:công đoàn|danh dự|ủy ban nhân dân|ubnd|nước))", I),
         "CEO_OF": re.compile(r"tổng giám đốc|giám đốc(?!\s+(?:khối|chi nhánh|tài chính|chiến lược|điều hành khu vực))|\bceo\b", I),
         "BOARD_MEMBER_OF": re.compile(r"thành viên\s+(?:độc lập\s+)?(?:hđqt|hđtv|hội đồng)|phó chủ tịch|ủy viên\s+(?:hđqt|hđtv)", I)}
_PHO = re.compile(r"phó\s+chủ tịch", I)
_FOUNDER_COUNCIL = re.compile(r"hội đồng sáng lập", I)


def _nospace(s: str) -> str:
    return re.sub(r"\s+", "", s.lower())


@dataclass
class Verdict:
    decision: str = "PASS"
    agreement: str = "SEMANTIC_ONLY"
    quarantine_class: str = ""
    hard_failed: list[str] = field(default_factory=list)
    hard_passed: list[str] = field(default_factory=list)
    semantic: str = "OK"            # OK | INSUFFICIENT | CONTRADICTED
    semantic_code: str = ""
    reasons: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    corrections: dict = field(default_factory=dict)
    final_status: str = ""
    possible_inference: bool = False

    def as_dict(self) -> dict:
        return {**self.__dict__, "validator_version": VALIDATOR_VERSION}


def _between(text: str, a, b) -> tuple[str, str, str]:
    x, y = sorted((a, b), key=lambda m: m.start)
    return text[max(0, x.start - 70):x.start], text[x.end:y.start], text[y.end:y.end + 70]


# ----------------------------------------------------------------------------- hard validation
def hard_validate(c: RelationCandidate, text: str, ments: list[dict], info: dict, canon, spec: dict) -> tuple[Verdict, str]:
    v = Verdict()
    ev = text[c.evidence_start:c.evidence_end] if text else ""
    if not text or ev != c.evidence_text:
        v.hard_failed.append("EVIDENCE_MISMATCH")
        v.decision, v.quarantine_class = "QUARANTINE", "HARD_BLOCK"
        v.reasons.append("EVIDENCE_MISMATCH: evidence missing or not equal to the article slice (fail-safe)")
        return v, ev
    v.hard_passed.append("evidence_exact_match")
    if len(ev.strip()) < 40 or ev.lstrip().startswith("|") or _CAPTION.search(ev):
        v.hard_failed.append("EVIDENCE_CAPTION_OR_SHORT")
        v.decision, v.quarantine_class = "QUARANTINE", "HARD_BLOCK"
        v.reasons.append("EVIDENCE_CAPTION_OR_SHORT: caption/fragment is not sole support")
        return v, ev
    s, o = c.subject, c.object
    for role, m in (("subject", s), ("object", o)):
        if text[m.start:m.end] != m.text or not (c.evidence_start <= m.start and m.end <= c.evidence_end):
            v.hard_failed.append("MENTION_NOT_IN_EVIDENCE")
            v.decision, v.quarantine_class = "QUARANTINE", "HARD_BLOCK"
            v.reasons.append(f"MENTION_NOT_IN_EVIDENCE: {role} span does not match the evidence text")
            return v, ev
    v.hard_passed.append("mentions_map_to_evidence")
    if s.entity_id and o.entity_id and canon(s.entity_id) == canon(o.entity_id):
        v.hard_failed.append("SELF_LOOP")
        v.decision = "REJECT"
        v.reasons.append("SELF_LOOP: subject and object are the same entity")
        return v, ev
    fwd = s.label.value in spec["subject"] and o.label.value in spec["object"]
    rev = o.label.value in spec["subject"] and s.label.value in spec["object"]
    if fwd:
        v.hard_passed.append("entity_types_valid")
    elif rev and not spec.get("symmetric") and c.predicate != "ISSUED_BOND":
        v.corrections["direction"] = "SWAP"
        v.notes.append("types fit only the reversed direction")
    else:
        v.hard_failed.append("INVALID_ENTITY_TYPES")
        v.decision = "REJECT"
        v.reasons.append(f"INVALID_ENTITY_TYPES: {s.label.value}/{o.label.value} fit neither direction of {c.predicate}")
        return v, ev
    # conservative identity
    for role, m in (("subject", s), ("object", o)):
        st = info.get(m.entity_id or "", {}).get("status", "")
        toks = [t for t in normalize_name(m.text, is_person=m.label.value == "PERSON").split() if t]
        if st not in ("VERIFIED", "ARTICLE_GROUNDED"):
            v.hard_failed.append("IDENTITY_NOT_GROUNDED")
            v.reasons.append(f"IDENTITY_NOT_GROUNDED: {role} '{m.text}' status '{st}'")
        elif m.label.value == "PERSON" and len(toks) < 2:
            v.hard_failed.append("IDENTITY_SHORT_PERSON_NAME")
            v.reasons.append(f"IDENTITY_SHORT_PERSON_NAME: {role} '{m.text}' is a single-token person mention (ambiguous)")
        elif m.label.value not in ("PERSON", "BOND_ISSUE") and (normalize_name(m.text) in _GENERIC_ORG or len(normalize_name(m.text)) < 3 or (m.text[:1].islower() and not m.text.isupper())):
            v.hard_failed.append("IDENTITY_GENERIC_ORG_NAME")
            v.reasons.append(f"IDENTITY_GENERIC_ORG_NAME: {role} '{m.text}' is generic/truncated")
        elif m.label.value == "PERSON" and "@art:" in (m.entity_id or "") and not (m.entity_id or "").endswith(c.article_id) and canon(m.entity_id) == m.entity_id:
            v.hard_failed.append("SAME_NAME_CONFUSION")
            v.reasons.append(f"SAME_NAME_CONFUSION: {role} person id is scoped to another article and was not merged by evidence")
        elif suspect_span(text, m):
            v.hard_failed.append("SPAN_BOUNDARY_SUSPECT")
            v.reasons.append(f"SPAN_BOUNDARY_SUSPECT: {role} '{m.text}' is followed by a capitalised word (possibly truncated name)")
    if v.hard_failed:
        v.quarantine_class = "HARD_BLOCK"
    else:
        v.hard_passed.append("identity_conservative")
    return v, ev



# ----------------------------------------------------------------------------- status
def status_check(c: RelationCandidate, text: str, ev: str, v: Verdict) -> str:
    """Returns the corrected status; records quarantine/reject reasons. Predicate-aware (ownership reduction is not ENDED)."""
    s, o = c.subject, c.object
    lo = min(s.start, o.start) - c.evidence_start
    hi = max(s.end, o.end) - c.evidence_start
    label = c.factual_status.value
    mod, cues = detect_modality(ev, lo, hi)
    if mod == FactualStatus.DENIED:
        if cues and cues[0] in ("không", "chưa"):  # bare 'không/chưa' is too ambiguous to reject on
            v.hard_failed.append("NEGATION_AMBIGUOUS")
            v.reasons.append(f"NEGATION_AMBIGUOUS: only the generic cue {cues} (not rejected, not trusted)")
            v.quarantine_class = "HARD_BLOCK"
            return label
        v.hard_failed.append("NEGATED_RELATION")
        v.decision = "REJECT"
        v.reasons.append(f"NEGATED_RELATION: negation cue {cues}")
        return label
    new = label
    p = c.predicate
    if p in ROLE_PREDS:
        if _RESIGN_REQ.search(ev):
            v.hard_failed.append("RESIGNATION_REQUEST_ONLY")
            v.reasons.append("RESIGNATION_REQUEST_ONLY: resignation requested/submitted, not stated as effective")
        elif _TENURE.search(ev) or _FORMER.search(ev[max(0, lo - 30):hi + 5]):
            new = "HISTORICAL"
        elif _ENDED.search(ev):
            new = "ENDED"
        elif mod in (FactualStatus.HISTORICAL, FactualStatus.ENDED, FactualStatus.PLANNED, FactualStatus.ALLEGED) and label == "FACT":
            new = mod.value
        if new == "FACT" and _CRIMINAL.search(ev):
            v.hard_failed.append("ROLE_IN_CRIMINAL_CONTEXT")
            v.reasons.append("ROLE_IN_CRIMINAL_CONTEXT: role is mentioned inside a criminal-case sentence; tenure not established")
    elif p == "OWNS_SHARES_IN":
        after = ev[max(0, s.start - c.evidence_start):max(0, s.start - c.evidence_start) + 90]
        rm = _REMAIN.search(after)
        positive = bool(rm and float(rm.group(1).replace(".", "").replace(",", ".") or 0) > 0)
        if label in ("ENDED", "HISTORICAL") and positive and not re.search(r"không còn (?:sở hữu|nắm)", after, I):
            new = "FACT"
            v.notes.append("ownership still positive after the reduction; ENDED was wrong")
        elif mod in (FactualStatus.PLANNED, FactualStatus.ALLEGED) and label == "FACT":
            new = mod.value
    elif p in ("ACQUIRED", "SANCTIONED_BY", "PROSECUTED_BY", "LENDS_TO", "JOINT_VENTURE_WITH", "PARTNERS_WITH", "FOUNDED", "SUBSIDIARY_OF"):
        if mod in (FactualStatus.PLANNED, FactualStatus.ALLEGED, FactualStatus.HISTORICAL, FactualStatus.ENDED) and label == "FACT":
            new = mod.value
        if p == "ACQUIRED" and re.search(r"đăng ký (?:mua|nhận)|dự kiến mua|sẽ mua", ev, I) and new == "FACT":
            new = "PLANNED"
    return new


# ----------------------------------------------------------------------------- semantic conditions (predicate-specific, sentence-level)
def semantic_check(c: RelationCandidate, text: str, ev: str, ments: list[dict], canon, v: Verdict) -> tuple[str, str, str]:
    """-> (state OK|INSUFFICIENT|CONTRADICTED, code, note). May set v.corrections."""
    s, o = c.subject, c.object
    p = c.predicate
    _left, seg, _right = _between(text, s, o)
    near = ev[max(0, min(s.start, o.start) - c.evidence_start - 60):max(s.end, o.end) - c.evidence_start + 60]
    if p in ROLE_PREDS:
        rx = _ROLE[p]
        cues = [m for m in rx.finditer(near)]
        if p == "CHAIR_OF" and not cues and _PHO.search(near):
            v.corrections["predicate"] = "BOARD_MEMBER_OF"
            return "OK", "DEPUTY_CHAIR_IS_BOARD_MEMBER", "Phó Chủ tịch without bare Chủ tịch"
        if p == "CHAIR_OF" and cues and _FOUNDER_COUNCIL.search(near) and not rx.search(re.sub(r"chủ tịch\s+hội đồng sáng lập", "", near, flags=I)):
            return "INSUFFICIENT", "DIFFERENT_OFFICE", "Chủ tịch Hội đồng sáng lập is not the board chair"
        if not cues:
            return "INSUFFICIENT", "ROLE_CUE_MISSING", f"no {p} role wording next to the endpoints"
        sub_edge_s, sub_edge_e = s.start - c.evidence_start, s.end - c.evidence_start
        base = max(0, min(s.start, o.start) - c.evidence_start - 60)
        best = min(cues, key=lambda m: min(abs(base + m.start() - sub_edge_e), abs(base + m.end() - sub_edge_s)))
        cs, ce = base + best.start(), base + best.end()
        dist = min(abs(cs - sub_edge_e), abs(ce - sub_edge_s)) if not (sub_edge_s <= cs < sub_edge_e) else 0
        if dist > 70:
            return "INSUFFICIENT", "ROLE_CUE_NOT_ADJACENT", f"role cue is {dist} chars from the subject"
        a, b = (sub_edge_e, cs) if cs >= sub_edge_e else (ce, sub_edge_s)
        between = ev[min(a, b):max(a, b)]
        others = [m for m in ments if m["label"] == "PERSON" and m.get("alias_of") is None and m.get("entity_id")
                  and canon(m["entity_id"]) != canon(s.entity_id or "") and min(a, b) <= m["start"] - c.evidence_start and m["end"] - c.evidence_start <= max(a, b)]
        if others:
            if _KIN.search(between):
                return "CONTRADICTED", "FAMILY_MEMBER_ATTRIBUTION", f"role stated for/after relative '{others[0]['text']}', not for the subject"
            return "INSUFFICIENT", "OTHER_PERSON_BETWEEN", f"person '{others[0]['text']}' stands between subject and role cue"
        return "OK", "ROLE_ATTACHED_TO_SUBJECT", ""
    if p == "OWNS_SHARES_IN":
        if not _OWN_CUE.search(near):
            return "INSUFFICIENT", "OWNERSHIP_CUE_MISSING", "no ownership/holding wording"
        if _INTENT.search(near) and not _OWN_HOLD.search(near):
            return "INSUFFICIENT", "REGISTRATION_ONLY", "buy/sell registration without a holding statement"
        return "OK", "OWNERSHIP_STATED", ""
    if p == "ACQUIRED":
        sell = _ACQ_SELL.search(near)
        rel_s = s.start - c.evidence_start
        k = ev.rfind(" cho ", 0, rel_s + 1)
        if sell and k >= 0 and rel_s - k <= 60 and not re.search(r"[.;,]", ev[k:rel_s]):
            return "OK", "ACQUISITION_AS_RECIPIENT_OF_SALE", ""
        if not _ACQ_VERB.search(near):
            return "INSUFFICIENT", "ACQUISITION_ACT_MISSING", "no mua lại/thâu tóm/nhận chuyển nhượng act (holding after an issuance is not acquisition)"
        if re.search(r"thoái|bán", near, I) and not re.search(r"\bmua\b|mua lại|thâu tóm|nhận chuyển nhượng", near, I):
            return "CONTRADICTED", "SALE_NOT_ACQUISITION", "text describes a sale"
        pv = _ACQ_VERB.search(ev)
        if pv:
            def appositive(m):  # "công ty con của <X>": X is the parent, not the actor
                return bool(re.search(r"(?:của|thuộc)\s*$", ev[max(0, m["start"] - c.evidence_start - 12):m["start"] - c.evidence_start], I))
            heads = [m for m in ments if m.get("alias_of") is None and m.get("entity_id") and c.evidence_start <= m["start"] and m["end"] - c.evidence_start <= pv.start()
                     and not appositive(m)]
            if heads:
                agent = max(heads, key=lambda m: m["end"])
                if canon(agent["entity_id"]) != canon(s.entity_id or ""):
                    return "INSUFFICIENT", "ACQUIRER_NOT_AGENT", f"the buyer in the sentence is '{agent['text']}', not '{s.text}'"
        return "OK", "ACQUISITION_ACT_STATED", ""
    if p == "FOUNDED":
        if not _FOUND_CUE.search(near):
            return "INSUFFICIENT", "FOUNDER_CUE_MISSING", "capital contribution is not founding"
        if _PROXY.search(near):
            return "INSUFFICIENT", "PROXY_FOUNDER", "set up through proxy/hire ('thuê', 'vỏ bọc'), not a genuine founder statement"
        if not re.search(r"sáng lập|đồng sáng lập|\bthành lập\b", near, I) or (not re.search(r"sáng lập", near, I) and "do " + s.text[:8] not in near and not re.search(re.escape(s.text[:10]) + r"[^.;]{0,40}thành lập", near, I)):
            return "INSUFFICIENT", "FOUNDER_NOT_AGENT", "'thành lập' appears but the subject is not stated as the founder"
        return "OK", "FOUNDER_STATED", ""
    if p == "SUBSIDIARY_OF":
        if not _SUB_CUE.search(near):
            return "INSUFFICIENT", "PARENT_CHILD_CUE_MISSING", "no công ty con/mẹ/trực thuộc wording"
        first_is_s = s.start < o.start
        t = seg.strip()
        if first_is_s:
            if re.search(r"(?:là\s+)?(?:một\s+)?công ty mẹ(?:\s+của)?\s*$", t, I):
                v.corrections["direction"] = "SWAP"
                return "OK", "REVERSED_PARENT_FIRST", "parent named first"
            if re.search(r"công ty con[^,;]{0,30}?\s(?:của|thuộc)\s*$|(?:trực\s+)?thuộc\s*$|đều thuộc\s*$|công ty thành viên(?:\s+của)?\s*$", t, I) or re.search(r"công ty con\s*$", t, I):
                return "OK", "SUBSIDIARY_OF_PARENT", ""
        else:
            if re.search(r"(?:là\s+)?công ty mẹ(?:\s+của)?\s*$|công ty con[^,;]{0,25}?(?:là)?\s*$|với công ty con\s*$", t, I):
                return "OK", "PARENT_FIRST", ""
            if re.search(r"(?:là\s+)?(?:một\s+)?công ty con[^,;]{0,30}?\s(?:của|thuộc)\s*$|(?:trực\s+)?thuộc\s*$", t, I):
                v.corrections["direction"] = "SWAP"
                return "OK", "REVERSED_SUBSIDIARY_FIRST", ""
        return "INSUFFICIENT", "PARENT_CHILD_DIRECTION_UNPROVEN", "cue present but grammar does not tie it to these two entities (same group / cooperation is not subsidiary)"
    if p == "LENDS_TO":
        if _LEND_GENERIC.search(near) and not re.search(r"hợp đồng tín dụng|giải ngân|cấp tín dụng", near, I):
            return "INSUFFICIENT", "GENERIC_LENDING_TERM", "generic lending wording"
        return ("OK", "LENDING_STATED", "") if _LEND_CUE.search(near) else ("INSUFFICIENT", "LENDING_CUE_MISSING", "")
    if p == "JOINT_VENTURE_WITH":
        return ("OK", "JV_STATED", "") if _JV_CUE.search(near) else ("INSUFFICIENT", "JV_CUE_MISSING", "")
    if p == "PARTNERS_WITH":
        return ("OK", "PARTNERSHIP_STATED", "") if _PART_CUE.search(near) else ("INSUFFICIENT", "PARTNERSHIP_CUE_MISSING", "")
    if p == "SANCTIONED_BY":
        if not _SANC_VERB.search(near):
            return "INSUFFICIENT", "SANCTION_VERB_MISSING", ""
        if re.search(r"(?:gửi|nộp|báo cáo|công bố)(?:\s+(?:cho|tới|đến))?\s*$", ev[max(0, o.start - c.evidence_start - 25):o.start - c.evidence_start], I):
            return "CONTRADICTED", "AUTHORITY_IS_RECIPIENT", "authority is the recipient of a filing, not the sanctioning party"
        return "OK", "SANCTION_STATED", ""
    if p == "PROSECUTED_BY":
        if not _PROS_VERB.search(near):
            return "INSUFFICIENT", "PROSECUTION_VERB_MISSING", "no khởi tố/truy tố/bắt (investigation or allegation only)"
        stage = "INDICTMENT" if re.search("truy tố", near, I) else "INITIATED_OR_ARRESTED"
        v.notes.append(f"prosecution_stage={stage}; charged/prosecuted, never convicted")
        if stage == "INDICTMENT" and not re.search(r"viện|ksnd|kiểm sát", o.text, I):
            return "INSUFFICIENT", "INDICTMENT_AUTHORITY_MISMATCH", "'truy tố' with a non-prosecutor authority"
        return "OK", "PROSECUTION_STATED", ""
    if p == "ISSUED_BOND":
        return "OK", "BOND_CHECKED_ELSEWHERE", ""
    return "INSUFFICIENT", "NO_SEMANTIC_RULE", ""


def bond_check(c: RelationCandidate, ev: str, bond_name: str) -> tuple[str, str, str]:
    if not re.search(r"phát hành|chào bán", ev, I) or "trái phiếu" not in ev.lower():
        return "INSUFFICIENT", "BOND_CUE_MISSING", ""
    ns = _nospace(ev)
    for tok in _AMOUNT.findall(_nospace(bond_name)) + [x.lower() for x in _CODE.findall(bond_name)]:
        if _nospace(tok) not in ns:
            return "INSUFFICIENT", "BOND_FACT_NOT_IN_EVIDENCE", f"'{tok}' not printed in the evidence"
    return "OK", "BOND_FACTS_IN_EVIDENCE", ""


# ----------------------------------------------------------------------------- orchestration
def validate_candidate(c: RelationCandidate, text: str, ments: list[dict], info: dict, canon, relations: dict,
                       methods: set[str], rule_reproduced: bool = False, bond_name: str = "") -> Verdict:
    spec = relations[c.predicate]
    v, ev = hard_validate(c, text, ments, info, canon, spec)
    if v.decision == "REJECT":
        v.agreement = "CONTRADICTED"
        return v
    if "EVIDENCE_MISMATCH" in v.hard_failed or "EVIDENCE_CAPTION_OR_SHORT" in v.hard_failed or "MENTION_NOT_IN_EVIDENCE" in v.hard_failed:
        v.agreement = "INSUFFICIENT_EVIDENCE"
        v.possible_inference = True
        return v
    new_status = status_check(c, text, ev, v)
    if v.decision == "REJECT":
        v.agreement = "CONTRADICTED"
        return v
    if c.predicate == "ISSUED_BOND":
        state, code, note = bond_check(c, ev, bond_name)
    else:
        state, code, note = semantic_check(c, text, ev, ments, canon, v)
    v.semantic, v.semantic_code = state, code
    if note:
        v.notes.append(note)
    if state == "CONTRADICTED":
        v.decision, v.agreement = "REJECT", "CONTRADICTED"
        v.reasons.append(f"{code}: {note}")
        return v
    if state == "INSUFFICIENT":
        v.agreement, v.possible_inference = "INSUFFICIENT_EVIDENCE", True
        v.hard_failed.append(code)  # recorded as a blocking semantic failure
        v.reasons.append(f"{code}: {note}")
        v.decision, v.quarantine_class = "QUARANTINE", "INSUFFICIENT_EVIDENCE"
        return v
    rule_ok = "RULE" in methods or rule_reproduced
    v.agreement = "RULE_SUPPORTED" if rule_ok else "SEMANTIC_ONLY"
    if new_status != c.factual_status.value:
        v.corrections["factual_status"] = new_status
    v.final_status = new_status
    if v.hard_failed:
        v.decision, v.quarantine_class = "QUARANTINE", "HARD_BLOCK"
        return v
    if new_status not in OFFICIAL:
        v.decision, v.quarantine_class = "QUARANTINE", "NON_OFFICIAL_STATUS"
        v.reasons.append(f"NON_OFFICIAL_STATUS: {new_status} stays a candidate")
        return v
    if not rule_ok:
        v.decision, v.quarantine_class = "QUARANTINE", "SEMANTIC_ONLY_CLEAN"
        v.reasons.append("SEMANTIC_ONLY: hard and semantic checks passed but no rule support; never auto-promoted, review priority")
        return v
    v.decision = "AUTO_CORRECT" if v.corrections else "PASS"
    return v

