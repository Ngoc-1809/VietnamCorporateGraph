"""Article extraction with parser fallback (trafilatura -> BeautifulSoup) and quality gates."""
from __future__ import annotations

from dataclasses import dataclass

from bs4 import BeautifulSoup

from vckg.preprocessing.text import normalize_text

MIN_CHARS = 400
MAX_REPLACEMENT_RATIO = 0.01


@dataclass
class Extracted:
    title: str
    text: str
    published_at: str | None
    parser: str


class ExtractionRejected(Exception):
    pass


def decode_response(content: bytes, declared: str | None) -> str:
    for enc in ([declared] if declared else []) + ["utf-8"]:
        try:
            return content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return content.decode("utf-8", errors="replace")


def _bs4_extract(html: str) -> tuple[str, str, str | None]:
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style", "nav", "footer", "aside", "form", "noscript"]):
        t.decompose()
    title = (soup.find("meta", property="og:title") or {}).get("content") or (soup.title.string if soup.title else "")
    pub = (soup.find("meta", property="article:published_time") or {}).get("content")
    root = soup.find("article") or soup.find(attrs={"itemprop": "articleBody"}) or soup.body or soup
    paras = [p.get_text(" ", strip=True) for p in root.find_all("p")]
    return (title or "").strip(), "\n".join(p for p in paras if len(p) > 40), pub


def quality_check(text: str) -> None:
    if len(text) < MIN_CHARS:
        raise ExtractionRejected(f"too_short:{len(text)}")
    if text.count("\ufffd") / max(len(text), 1) > MAX_REPLACEMENT_RATIO:
        raise ExtractionRejected("encoding_errors")


def extract_article(html: str, url: str = "") -> Extracted:
    title, text, pub, parser = "", "", None, ""
    try:
        import trafilatura
        out = trafilatura.bare_extraction(html, url=url or None, with_metadata=True, favor_precision=True)
        if out is not None:
            d = out if isinstance(out, dict) else out.as_dict()
            text, title, pub, parser = d.get("text") or "", d.get("title") or "", d.get("date"), "trafilatura"
    except Exception:  # noqa: BLE001 - fall through to fallback parser
        text = ""
    if len(text) < MIN_CHARS:
        t2, x2, p2 = _bs4_extract(html)
        if len(x2) > len(text):
            title, text, pub, parser = t2 or title, x2, p2 or pub, "bs4"
    text = normalize_text(text)
    quality_check(text)
    return Extracted(title=normalize_text(title), text=text, published_at=pub, parser=parser)
