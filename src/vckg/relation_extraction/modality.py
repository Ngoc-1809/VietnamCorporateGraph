"""Rule-based factuality (modality) detection, evaluated on a WINDOW around the matched relation,
not on the whole sentence (so 'từng làm ở X' in another clause does not taint the relation).

Status names: CONFIRMED(=FACT), PLANNED, NEGATED(=DENIED), ALLEGED, HISTORICAL, ENDED, UNKNOWN.
Priority: NEGATED > ALLEGED > ENDED > INCOMPLETE/PLANNED > HISTORICAL > CONFIRMED (explicit 'đã hoàn tất' etc.).
Conservative by design: anything unclear is not promoted to CONFIRMED by an LLM alone (see EdgeStore)."""
from __future__ import annotations

import re

from vckg.models import FactualStatus

_F = re.IGNORECASE
_INCOMPLETE = re.compile(r"\b(?:chưa hoàn tất|chưa hoàn thành|chưa thể|đang đàm phán|đang xem xét|đang tìm hiểu|"
                         r"đang thảo luận|đang chờ|chờ phê duyệt)\b", _F)
_NEGATED = re.compile(
    r"\b(?:không phải|không có|không hề|không còn|không giữ|không sở hữu|không nắm|chưa từng|chưa hề|chưa phải|chưa có|"
    r"phủ nhận|bác bỏ|đính chính|được tuyên vô tội|tuyên vô tội|vô tội|hủy bỏ|hủy thương vụ|không thành công|"
    r"không được|không thể|bị bác)\b|\bkhông\b(?!\s+chỉ)|\bchưa\b", _F)
_ALLEGED = re.compile(r"\b(?:bị cáo buộc|cáo buộc|nghi vấn|nghi ngờ|nghi (?:can|phạm)|được cho là|theo tin đồn|tin đồn|bị tố|"
                      r"đang bị điều tra|đang điều tra|bị điều tra|đang bị xem xét xử lý)\b|\bbị\b[^.,;]{0,40}?\bđiều tra\b", _F)
_ENDED = re.compile(r"\b(?:đã thôi giữ|thôi giữ chức|thôi giữ|đã từ nhiệm|từ nhiệm|đã nghỉ|miễn nhiệm|bãi nhiệm|"
                    r"không còn giữ|đã rời|rời vị trí|chấm dứt|kết thúc nhiệm kỳ|hết nhiệm kỳ|thoái vốn)\b", _F)
_PLANNED = re.compile(r"\b(?:dự kiến|sẽ|kế hoạch|dự định|đề xuất|đề cử|trình đại hội|trình cổ đông|có thể|muốn|lên kế hoạch|"
                      r"chuẩn bị|sắp|tiến tới|nhằm|ứng cử|đề nghị)\b", _F)
_HISTORICAL = re.compile(r"\b(?:nguyên|cựu|từng|trước đây|trước kia|ngày trước)\b", _F)
_CONFIRM = re.compile(r"\b(?:đã hoàn tất|đã hoàn thành|đã chính thức|chính thức|đã được|đã ký|đã bổ nhiệm|vừa bổ nhiệm|"
                      r"vừa hoàn tất)\b", _F)
LEFT, RIGHT = 55, 30


def window(sentence: str, start: int, end: int) -> str:
    """Left: up to LEFT chars before the relation. Right: up to RIGHT chars but cut at the first clause break
    (comma/semicolon), so a trailing clause such as ", từng làm việc tại X" does not taint the relation."""
    right = sentence[end: end + RIGHT]
    cut = re.search(r"[,;]", right)
    if cut:
        right = right[: cut.start()]
    return sentence[max(0, start - LEFT): end] + right


def detect_modality(sentence: str, start: int | None = None, end: int | None = None) -> tuple[FactualStatus, list[str]]:
    """Return (status, matched cue strings). Without a span the whole sentence is used."""
    w = sentence if start is None else window(sentence, start, end if end is not None else start)
    for status, rx in ((FactualStatus.PLANNED, _INCOMPLETE),):  # 'chưa hoàn tất' means not completed -> not a fact yet
        m = rx.search(w)
        if m:
            return status, [m.group(0).lower()]
    for status, rx in ((FactualStatus.DENIED, _NEGATED), (FactualStatus.ALLEGED, _ALLEGED), (FactualStatus.ENDED, _ENDED)):
        m = rx.search(w)
        if m:
            return status, [m.group(0).lower()]
    m = _PLANNED.search(w)
    if m:
        c = _CONFIRM.search(w)
        if c and c.start() > m.start():  # 'dự kiến ..., đã hoàn tất' - completion stated after the plan
            return FactualStatus.FACT, [c.group(0).lower()]
        return FactualStatus.PLANNED, [m.group(0).lower()]
    m = _HISTORICAL.search(w)
    if m:
        return FactualStatus.HISTORICAL, [m.group(0).lower()]
    c = _CONFIRM.search(w)
    return FactualStatus.FACT, [c.group(0).lower()] if c else []


def detect_factuality(sentence: str) -> FactualStatus:
    """Back-compat helper (whole sentence)."""
    return detect_modality(sentence)[0]

