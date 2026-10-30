"""Name normalization used for alias matching (a candidate generator only - never a merge decision).

Order matters: accent-fold + lowercase FIRST, then strip prefixes written accent-free, so accented article
text and accent-free identity-provider slugs normalize to the same key."""
from __future__ import annotations

import re
import unicodedata

_PERSON_TITLES = re.compile(
    r"^(?:(?:ong|ba|anh|chi|ts|pgs\.?\s*ts|pgs|gs|ths|ks|bs|mr|mrs|ms|dr|tien si|thac si|giao su|"
    r"thuong tuong|dai tuong|trung tuong|thieu tuong|dai ta|thuong ta|pho thu tuong thuong truc|"
    r"pho thu tuong|thu tuong|bo truong|thu truong|chu tich(?: hdqt)?|pho chu tich|tong giam doc|pho tong giam doc|"
    r"giam doc|chu tich kiem tong giam doc|nha sang lap|ceo)\.?\s+)+")
_ORG_NOISE = re.compile(
    r"^(?:(?:hdqt|hoi dong quan tri|ban kiem soat|ngan hang thuong mai co phan|ngan hang tmcp|ngan hang|"
    r"tap doan|tong cong ty co phan|tong cong ty|cong ty co phan|cong ty tnhh mtv|cong ty tnhh|cong ty cp|"
    r"cong ty|ctcp|cty cp|cty|tmcp|cp|tnhh)\s+)+")
_ORG_SUFFIX = re.compile(r"\s+(?:ctcp|cp|jsc|tnhh|co ltd|joint stock company)$")
_TRAIL_NOISE = re.compile(r"\s+(?:giam sat|cho biet|noi|thong tin|cong bo|hom nay|ngay \d.*)$")


def strip_accents(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def clean_surface(s: str) -> str:
    s = unicodedata.normalize("NFC", s).strip(" \t\n,.;:\"'“”()[]-–")
    return re.sub(r"\s+", " ", s)


def fold(s: str) -> str:
    s = strip_accents(clean_surface(s)).lower()
    s = re.sub(r"[^\w\s&]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_name(s: str, *, is_person: bool = False, drop_prefix: bool = True) -> str:
    k = _TRAIL_NOISE.sub("", fold(s))
    if is_person:
        k = _PERSON_TITLES.sub("", k + " ").strip()
    elif drop_prefix:
        prev = None
        while prev != k:
            prev = k
            k = _ORG_SUFFIX.sub("", _ORG_NOISE.sub("", k + " ").strip())
    return re.sub(r"\s+", " ", k).strip()


def slugify(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", key).strip("-")

