"""Phase 6B.4 - safe NER span recovery (post-processing of GLiNER + dictionary mentions; no model change, no fuzzy matching).

Observed causes on the 60-article experiment
  FALSE_ALARM        org followed by a PERSON mention ("Chủ tịch ABBank Vũ Văn Tiền"): the span is complete; the truncation heuristic was wrong
  DICTIONARY_PARTIAL a generic registry alias ("CTCP Đầu tư", "Xây dựng", "Việt Nam") won the dictionary-over-NER merge inside a longer proper name
  GLINER_TRUNCATED   GLiNER stopped inside a legal name ("Công cổ phần Nhất" | "Phong Vận")
Rules (all must hold, otherwise the ORIGINAL span is kept and the candidate stays quarantined)
  * extend only over a contiguous run of capitalised tokens (+ "và"/"&" between capitalised tokens) inside one sentence, <= 6 extra tokens;
  * the run must be bounded by lowercase/punctuation/line break; left extension only up to a legal-form start (Công ty, CTCP, Tập đoàn, Ngân hàng...);
  * evidence: the new span starts with a legal form (LEGAL_FORM_RUN) OR the same full string occurs >= 2 times in the article (REPEATED_FULL_NAME);
  * never swallow a PERSON mention, a title word, or a non-generic other mention; generic dictionary mentions inside the run may be absorbed;
  * the extended core must contain a non-generic token ("Việt Nam", "Xây dựng", "Đông Anh" alone are never promoted to a legal entity);
  * the new text equals the source slice (Unicode NFC checked) and stays inside the sentence."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from vckg.entity_linking.article_grounding import _GENERIC_WORDS, core_tokens, non_generic
from vckg.preprocessing.text import sentence_index_for, split_sentences

RECOVERY_VERSION = "span-recovery-v1"
_TOKEN = re.compile(r"[\w+&\-]+(?:\.\w+)*", re.UNICODE)
_LEGAL_START = re.compile(r"^(?:công\s+ty(?:\s+(?:cổ phần|tnhh|cp))?|công\s+(?:cổ phần|tnhh)|ctcp|tập đoàn|tổng công ty|ngân hàng|cty)\b", re.IGNORECASE)
_TITLE = re.compile(r"^(?:ông|bà|anh|chị|chủ tịch|tổng giám đốc|giám đốc|phó|ts|pgs|gs|ths|mr|ms|ceo|thành viên|hđqt)$", re.IGNORECASE)
_CONNECTORS = {"và", "&"}
MAX_EXTRA_TOKENS = 6
# lowercase sector phrases that legitimately sit INSIDE Vietnamese company names (matched as whole phrases only)
_SECTOR_PHRASES = ["xây dựng", "hạ tầng", "đầu tư", "thương mại", "sản xuất", "dịch vụ", "công nghệ", "chứng khoán", "bất động sản", "tài chính", "năng lượng",
                   "phát triển", "kinh doanh", "công nghiệp", "vận tải", "cổ phần", "hàng không", "bảo hiểm", "thực phẩm", "địa ốc", "du lịch", "khoáng sản",
                   "truyền thông", "giải trí", "y tế", "giáo dục", "nông nghiệp", "thủy sản", "vật liệu", "kỹ thuật", "tư vấn", "thiết bị", "điện lực"]
_SECTOR_WORDS = {w for p in _SECTOR_PHRASES for w in p.split()}
_SECTOR_RX = re.compile(r"(?:" + "|".join(sorted((re.escape(p) for p in _SECTOR_PHRASES), key=len, reverse=True)) + r")(?![\w])", re.IGNORECASE)
# capitalised function words that start sentences/clauses and are never part of a name
_NOT_NAME = {"Một", "Các", "Những", "Theo", "Tại", "Ông", "Bà", "Việc", "Đây", "Đó", "Khi", "Sau", "Trước", "Với", "Do", "Để", "Nếu", "Tuy", "Ngoài", "Từ", "Hiện",
             "Năm", "Tháng", "Ngày", "Quý", "Trong", "Cả", "Cùng", "Như", "Và", "Còn", "Đồng", "Tổng", "Thứ"}
# the first lowercase word after a complete name must be one of these (or punctuation / end), otherwise the boundary is unknown
_BOUNDARY = {"là", "có", "đã", "được", "sẽ", "vừa", "của", "với", "cho", "từ", "do", "để", "tại", "trong", "thuộc", "góp", "nắm", "sở", "phát", "công", "thông", "ký",
             "hoàn", "tăng", "mua", "bán", "chuyển", "trở", "bị", "đang", "cũng", "mới", "vẫn", "khi", "sau", "theo", "như", "nhằm", "gồm", "chiếm", "giữ", "đạt",
             "báo", "nói", "thành", "ở", "về", "trên", "dưới", "và", "hay", "hoặc", "cùng", "đều", "thì", "mà", "khiến", "nên", "vì", "bởi", "qua", "sang", "đến",
             "tới", "hết", "gần", "hơn", "không", "chưa", "hút", "huy", "dự", "tiếp", "bắt", "trúng", "đưa", "cần", "muốn", "lên", "xuống", "nhận", "chi", "thoái",
             "đăng", "ra", "vào", "tổ", "đại", "lãnh", "ban", "hội", "công bố", "phê", "thông qua", "kêu", "thay", "bổ", "miễn", "xin", "yêu", "đề"}
_LEGAL_WORD = re.compile(r"^(?:công|ty|ctcp|tnhh|cp|tập|đoàn|ngân|hàng|tmcp|tổng|cty)$", re.IGNORECASE)


@dataclass
class SpanFix:
    article_id: str
    original: tuple[int, int]
    original_text: str
    kind: str                      # EXTEND | CONFIRMED_COMPLETE | UNRESOLVED
    cause: str                     # FALSE_ALARM | DICTIONARY_PARTIAL | GLINER_TRUNCATED | OTHER
    new: tuple[int, int] | None = None
    new_text: str = ""
    evidence: str = ""
    reason: str = ""
    absorbed: list[tuple[int, int]] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    version: str = RECOVERY_VERSION

    def as_dict(self) -> dict:
        return {**self.__dict__, "original": list(self.original), "new": list(self.new) if self.new else None, "absorbed": [list(a) for a in self.absorbed]}


def _cap(tok: str) -> bool:
    return bool(tok) and (tok[0].isupper() or tok[0].isdigit())


def _is_generic_dictionary(m: dict) -> bool:
    toks = core_tokens(m["text"])
    return m.get("method", "").startswith("dictionary") and (not toks or not non_generic(toks) or all(t in _GENERIC_WORDS for t in toks))


def _right_run(text: str, pos: int, limit: int) -> list[tuple[int, int, str]]:
    """Tokens directly following `pos` (single spaces only): capitalised tokens, "và"/"&" between capitalised proper tokens (never across a
    legal-form word), and whole lowercase SECTOR phrases inside the name. The run must END on a capitalised token."""
    out, i = [], pos
    while len(out) < MAX_EXTRA_TOKENS + 4:
        if i >= limit or text[i:i + 1] != " ":
            break
        m = _TOKEN.match(text, i + 1)
        if not m or m.end() > limit:
            break
        tok = m.group()
        sm = _SECTOR_RX.match(text, m.start())
        if sm and sm.end() <= limit:  # whole sector phrase ("Hạ tầng", "xây dựng"), in any case
            out.append((m.start(), sm.end(), sm.group()))
            i = sm.end()
            continue
        if _cap(tok) and tok not in _NOT_NAME:
            out.append((m.start(), m.end(), tok))
            i = m.end()
            continue
        if tok.lower() in _CONNECTORS:
            nxt = _TOKEN.match(text, m.end() + 1) if text[m.end():m.end() + 1] == " " else None
            prev = out[-1][2] if out else ""
            if nxt and _cap(nxt.group()) and nxt.group() not in _NOT_NAME and not _LEGAL_START.match(text[nxt.start():]) and not _LEGAL_WORD.match(prev) \
                    and not nxt.group().startswith("UBND") and nxt.end() <= limit:
                out.append((m.start(), m.end(), tok))
                i = m.end()
                continue
            break
        break
    while out and not (_cap(out[-1][2]) or _SECTOR_RX.fullmatch(out[-1][2])):
        out.pop()
    return out


def _boundary_ok(text: str, end: int) -> bool:
    rest = text[end:end + 40]
    if not rest or rest[0] in ".,;:)]\n\"”-–/":
        return True
    m = re.match(r" (\S+)", rest)
    if not m:
        return True
    w = m.group(1).strip(".,;:()\"”").lower()
    return w in _BOUNDARY or not w or w[0] in "(["


def _left_to_legal(text: str, start: int, lo: int) -> int | None:
    """If the capitalised/connector run immediately left of `start` begins with a legal form, return that start; else None."""
    toks, i = [], start
    while i > lo and text[i - 1:i] == " ":
        j = i - 1
        k = j
        while k > lo and (text[k - 1].isalnum() or text[k - 1] in "+&-."):
            k -= 1
        tok = text[k:j]
        if not tok or not (_cap(tok) or tok.lower() in _CONNECTORS or tok.lower() in ("ty", "cổ", "phần", "tnhh", "cp") or tok.lower() in _SECTOR_WORDS):
            break
        if tok.lower() in _CONNECTORS:  # "Công ty và UBND ...": a connector right after a legal-form word joins two entities
            j2 = k - 1
            k2 = j2
            while k2 > lo and (text[k2 - 1].isalnum() or text[k2 - 1] in "+&-."):
                k2 -= 1
            if _LEGAL_WORD.match(text[k2:j2]):
                return None
        toks.append((k, tok))
        i = k
    best = None  # farthest-left legal-form start wins
    for k, _t in toks:
        if _LEGAL_START.match(text[k:]):
            best = k
    return best


def recover_article(article_id: str, text: str, mentions: list[dict], truncated_flag) -> list[SpanFix]:
    """truncated_flag(text, mention) -> bool is the existing suspicion heuristic (kept as the trigger, not as the judge)."""
    if unicodedata.normalize("NFC", text) != text:
        return []
    sents = split_sentences(text)
    heads = [m for m in mentions if m.get("alias_of") is None and not str(m.get("linking_method", "")).startswith("out_of_scope")]
    persons = [m for m in heads if m["label"] == "PERSON"]
    fixes: list[SpanFix] = []
    for m in heads:
        if m["label"] == "PERSON":
            continue
        trig_trunc = truncated_flag(text, m)
        trig_dict = _is_generic_dictionary(m)
        if not (trig_trunc or trig_dict):
            continue
        sidx = sentence_index_for(sents, m["start"])
        sent = next(s for s in sents if s.index == sidx) if sidx is not None else None
        if sent is None:
            continue
        orig = (m["start"], m["end"])
        run = _right_run(text, m["end"], sent.end)
        left = _left_to_legal(text, m["start"], sent.start)
        cause = "DICTIONARY_PARTIAL" if m.get("method", "").startswith("dictionary") else "GLINER_TRUNCATED"
        if not run and left is None:
            if trig_trunc:
                nxt_p = [p for p in persons if m["end"] <= p["start"] <= m["end"] + 2]
                if nxt_p:
                    fixes.append(SpanFix(article_id, orig, m["text"], "CONFIRMED_COMPLETE", "FALSE_ALARM", reason=f"followed by PERSON mention '{nxt_p[0]['text']}' (title + organization + person)",
                                         checks=["next_capitalised_run_is_person_mention"]))
                else:
                    fixes.append(SpanFix(article_id, orig, m["text"], "UNRESOLVED", "OTHER", reason="flagged but no extendable capitalised run"))
            continue
        # person guard: a PERSON mention at the start of the run means title + org + person, not a longer name
        if run and any(p["start"] == run[0][0] for p in persons):
            fixes.append(SpanFix(article_id, orig, m["text"], "CONFIRMED_COMPLETE", "FALSE_ALARM",
                                 reason="the capitalised continuation is a PERSON mention (title + organization + person)", checks=["next_capitalised_run_is_person_mention"]))
            continue
        run = [r for r in run if not _TITLE.match(r[2])]
        take = run[:MAX_EXTRA_TOKENS]
        # stop before any token that starts a non-swallowable other mention
        others = [o for o in heads if o is not m]
        cut = len(take)
        absorbed: list[tuple[int, int]] = []
        for idx, (s0, e0, _tok) in enumerate(take):
            hit = [o for o in others if o["start"] <= s0 < o["end"] or (s0 <= o["start"] < e0)]
            bad = [o for o in hit if o["label"] == "PERSON" or not _is_generic_dictionary(o)]
            if bad:
                cut = idx
                break
            absorbed += [(o["start"], o["end"]) for o in hit if _is_generic_dictionary(o)]
        take = take[:cut]
        if _is_generic_dictionary(m) and any(t[2].lower() in _CONNECTORS for t in take) and left is None:
            take = take[:next(i for i, t in enumerate(take) if t[2].lower() in _CONNECTORS)]  # "Việt Nam và Lào" is two entities, not one name
            while take and not _cap(take[-1][2]):
                take.pop()
        new_start = left if left is not None else m["start"]
        new_end = take[-1][1] if take else m["end"]
        if (new_start, new_end) == orig:
            fixes.append(SpanFix(article_id, orig, m["text"], "UNRESOLVED", cause, reason="no safe extension (blocked by person/other-entity guard)"))
            continue
        new_text = text[new_start:new_end]
        absorbed = [a for a in absorbed if new_start <= a[0] and a[1] <= new_end]
        # quality gates
        if "\n" in new_text or not (sent.start <= new_start and new_end <= sent.end) or text[new_start:new_end] != new_text:
            fixes.append(SpanFix(article_id, orig, m["text"], "UNRESOLVED", cause, reason="extension crosses a sentence/line boundary"))
            continue
        if re.search(r"[,;:()]", new_text):
            fixes.append(SpanFix(article_id, orig, m["text"], "UNRESOLVED", cause, reason="extension contains punctuation"))
            continue
        toks = core_tokens(new_text)
        if not toks or not non_generic(toks):
            fixes.append(SpanFix(article_id, orig, m["text"], "UNRESOLVED", cause, reason="extended name is still generic"))
            continue
        if any(p["text"] == new_text or p["text"] in new_text.split(" ", 1)[-1:] and p["text"] == new_text for p in persons):
            fixes.append(SpanFix(article_id, orig, m["text"], "UNRESOLVED", cause, reason="extended text is a PERSON mention elsewhere (type conflict)"))
            continue
        legal = bool(_LEGAL_START.match(new_text))
        repeated = len(re.findall(r"(?<!\w)" + re.escape(new_text) + r"(?!\w)", text)) >= 2
        if not (legal or repeated):
            fixes.append(SpanFix(article_id, orig, m["text"], "UNRESOLVED", cause, reason="no legal-form start and the full string is not repeated in the article"))
            continue
        if not _boundary_ok(text, new_end):
            fixes.append(SpanFix(article_id, orig, m["text"], "UNRESOLVED", cause, reason="unknown boundary after the extended span (next word is not a known function word)"))
            continue
        clash = [o for o in others if o["label"] != "PERSON" and not (o["start"], o["end"]) in absorbed and new_start < o["end"] and o["start"] < new_end and (o["start"], o["end"]) != orig]
        if clash and any(not _is_generic_dictionary(o) and not (new_start <= o["start"] and o["end"] <= new_end) for o in clash):
            fixes.append(SpanFix(article_id, orig, m["text"], "UNRESOLVED", cause, reason="would overlap another entity"))
            continue
        fixes.append(SpanFix(article_id, orig, m["text"], "EXTEND", cause, new=(new_start, new_end), new_text=new_text,
                             evidence=("LEGAL_FORM_RUN" if legal else "REPEATED_FULL_NAME"), absorbed=absorbed,
                             reason=f"{cause}: '{m['text']}' -> '{new_text}'",
                             checks=["contiguous_capitalised_run", "same_sentence", "no_person_or_title_swallowed", "non_generic_core", "nfc_exact_slice",
                                     "legal_form_start" if legal else "repeated_in_article"]))
    return fixes
