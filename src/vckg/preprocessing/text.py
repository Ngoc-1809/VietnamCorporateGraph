"""Unicode normalization and offset-preserving sentence splitting."""
from __future__ import annotations

import re
import unicodedata

from vckg.models import Sentence

_ZW = re.compile("[\u200b\u200c\u200d\ufeff]")
_WS = re.compile(r"[ \t\u00a0]+")

# Vietnamese abbreviations that end with a period but do not end a sentence.
_ABBREV = ("TS", "PGS", "GS", "ThS", "TP", "TMCP", "TNHH", "CTCP", "Tp", "Q", "P", "Mr", "Dr", "No", "vs", "v.v")
_BOUNDARY = re.compile(r"(?<=[.!?…])[\"”’)\]]*\s+(?=[\"“‘(\[]?[A-ZÀ-ỸĐ0-9])|\n{1,}")


def normalize_text(text: str) -> str:
    """NFC, drop zero-width chars, collapse horizontal whitespace. Newlines are preserved."""
    text = unicodedata.normalize("NFC", text)
    text = _ZW.sub("", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS.sub(" ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return text.strip()


def _is_abbrev_end(chunk: str) -> bool:
    m = re.search(r"([\w.]+)\.$", chunk)
    return bool(m and m.group(1) in _ABBREV)


def split_sentences(text: str) -> list[Sentence]:
    """Split text; every Sentence satisfies text[start:end] == sentence.text (no stripping drift)."""
    spans: list[tuple[int, int]] = []
    pos = 0
    for m in _BOUNDARY.finditer(text):
        chunk_end = m.start()
        is_punct_boundary = "\n" not in m.group()
        if is_punct_boundary and _is_abbrev_end(text[pos:chunk_end].rstrip("\"”’)] ")):
            continue
        if is_punct_boundary:
            # keep the closing quote/bracket inside the sentence
            q = re.match(r"[\"”’)\]]*", m.group())
            chunk_end += len(q.group()) if q else 0
        spans.append((pos, chunk_end))
        pos = m.end()
    spans.append((pos, len(text)))
    out: list[Sentence] = []
    for s, e in spans:
        while s < e and text[s].isspace():
            s += 1
        while e > s and text[e - 1].isspace():
            e -= 1
        if e > s:
            out.append(Sentence(index=len(out), text=text[s:e], start=s, end=e))
    return out


def sentence_index_for(sentences: list[Sentence], offset: int) -> int | None:
    for s in sentences:
        if s.start <= offset < s.end:
            return s.index
    return None
