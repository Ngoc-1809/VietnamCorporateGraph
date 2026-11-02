"""Global Entity Resolution v2 - deterministic building blocks (pure functions + a read-only world loader).

Nothing here writes to source databases. The world is loaded from the graph-preview SNAPSHOT copy of the aggregate (src_edges / src_evidence / entities / collisions /
person_merges), the cumulative registry (read-only) and the corpus (read-only). Decisions are classified VERIFIED_MERGE | DISTINCT | AMBIGUOUS | UNRESOLVED and only a
deterministic verifier produces VERIFIED_MERGE (an LLM, when used, can only add evidence that the verifier re-checks)."""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from vckg.entity_linking.normalize import normalize_name

VERSION = "er-v2.0"
TIERS = ("LEGACY_OFFICIAL", "QA_PASS", "QUARANTINE")
VALIDATED = ("LEGACY_OFFICIAL", "QA_PASS")
ORG_TYPES = ("ORGANIZATION", "BANK", "GOVERNMENT_AGENCY", "REGULATOR")
STATUS_RANK = {"VERIFIED": 4, "EXTERNAL_VERIFIED": 4, "ARTICLE_GROUNDED": 3, "PROVISIONAL": 2, "AMBIGUOUS": 1, "UNKNOWN": 0}
RELATED_PREDS = ("SUBSIDIARY_OF", "OWNS_SHARES_IN", "ACQUIRED", "JOINT_VENTURE_WITH", "PARTNERS_WITH", "LENDS_TO", "FOUNDED")
LEADERSHIP = ("CHAIR_OF", "CEO_OF", "BOARD_MEMBER_OF", "FOUNDED")


# ------------------------------------------------------------------------------------------------ text helpers
def fold1(text: str) -> str:
    """Length-preserving accent fold + lowercase (so offsets in the folded text are valid in the original NFC text)."""
    out = []
    for ch in text.replace("đ", "d").replace("Đ", "D"):
        d = unicodedata.normalize("NFD", ch)
        out.append(d[0].lower() if d else ch)
    return "".join(out)


def fold_name(s: str) -> str:
    s = fold1(s)
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s&]", " ", s)).strip()


def mk_tokens(s: str) -> str:
    return r"\s+".join(re.escape(t) for t in s.split())


def article_date(s: str | None) -> date | None:
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    except ValueError:
        return None


# ------------------------------------------------------------------------------------------------ world
@dataclass
class Ent:
    key: str
    name: str
    etype: str | None
    status: str
    sources: set[str] = field(default_factory=set)
    names: Counter = field(default_factory=Counter)
    degree: int = 0
    validated_degree: int = 0


@dataclass
class World:
    ents: dict[str, Ent]
    edges: list[dict]  # src_edges rows (3 tiers) with s_key/o_key (ID_CONFLICT keys already applied)
    evidence: dict[tuple, list[dict]]  # (source_id, edge_id, tier) -> rows
    prior_person_merges: list[tuple[str, str]]
    conflict_ids: set[str]
    adj: dict[str, list[int]]


def ekey(eid: str, source: str, conflict_ids: set[str]) -> str:
    return f"{eid}@{source}" if eid in conflict_ids else eid


def load_world(snapshot_db: Path) -> World:
    db = sqlite3.connect(f"file:{Path(snapshot_db).as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    conflict = {r["key"] for r in db.execute("SELECT key FROM collisions WHERE kind='ID_CONFLICT'")}
    q = ",".join("?" * len(TIERS))
    en = [r[0] for r in db.execute("SELECT source_id FROM sources WHERE enabled=1")]
    qs = ",".join("?" * len(en))
    edges = [dict(r) for r in db.execute(f"SELECT * FROM src_edges WHERE tier IN ({q}) AND source_id IN ({qs}) ORDER BY source_id, tier, edge_id", (*TIERS, *en))]
    evid: dict[tuple, list[dict]] = defaultdict(list)
    for r in db.execute(f"SELECT * FROM src_evidence WHERE tier IN ({q}) AND source_id IN ({qs}) ORDER BY source_id, tier, edge_id, article_id, evidence_start", (*TIERS, *en)):
        evid[(r["source_id"], r["edge_id"], r["tier"])].append(dict(r))
    ents: dict[str, Ent] = {}
    adj: dict[str, list[int]] = defaultdict(list)
    for i, e in enumerate(edges):
        e["s_key"], e["o_key"] = ekey(e["subject_id"], e["source_id"], conflict), ekey(e["object_id"], e["source_id"], conflict)
        for role in ("subject", "object"):
            k = e["s_key" if role == "subject" else "o_key"]
            n = ents.setdefault(k, Ent(k, e[f"{role}_name"] or k, e[f"{role}_type"], e[f"{role}_status"] or "UNKNOWN"))
            n.sources.add(e["source_id"])
            n.names[e[f"{role}_name"] or k] += 1
            n.degree += 1
            n.validated_degree += e["tier"] in VALIDATED
            if STATUS_RANK.get(e[f"{role}_status"] or "UNKNOWN", 0) < STATUS_RANK.get(n.status, 0):
                n.status = e[f"{role}_status"]  # most conservative status, as the aggregator does
            adj[k].append(i)
    for n in ents.values():
        n.name = n.names.most_common(1)[0][0]
    prior = [(r["kept"], r["dropped"]) for r in db.execute("SELECT kept, dropped FROM person_merges")]
    db.close()
    return World(ents, edges, evid, prior, conflict, adj)


def prior_map(prior: list[tuple[str, str]]) -> dict[str, str]:
    parent: dict[str, str] = {}

    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x
    for kept, dropped in prior:
        a, b = find(kept), find(dropped)
        if a != b:
            parent[b] = a
    return {x: find(x) for x in list(parent)}


class UF:
    """Union-find over entity keys that refuses unions violating constraints (checked by the caller via `can_union`)."""

    def __init__(self):
        self.p: dict[str, str] = {}

    def find(self, x: str) -> str:
        r = x
        while self.p.get(r, r) != r:
            r = self.p[r]
        while self.p.get(x, x) != r:
            self.p[x], x = r, self.p[x]
        return r

    def members(self) -> dict[str, list[str]]:
        g: dict[str, list[str]] = defaultdict(list)
        for x in set(self.p) | set(self.p.values()):
            g[self.find(x)].append(x)
        return g

    def union(self, a: str, b: str, rep: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        keep = rep if rep in (ra, rb) else min(ra, rb)
        drop = rb if keep == ra else ra
        self.p[drop] = keep
        self.p.setdefault(keep, keep)


def has_cycle(mapping: dict[str, str]) -> bool:
    for k, first in mapping.items():
        seen, x = {k}, first
        while x in mapping and mapping[x] != x:
            if x in seen:
                return True
            seen.add(x)
            x = mapping[x]
    return False


# ------------------------------------------------------------------------------------------------ organisations
LEGAL = (("tnhh", r"\btnhh\b|\btrach nhiem huu han\b"), ("cp", r"\bctcp\b|\bcp\b|\bco phan\b|\bjsc\b"))


def legal_forms(name: str) -> set[str]:
    f = fold1(name)
    return {k for k, rx in LEGAL if re.search(rx, f)}


def legal_conflict(a: str, b: str) -> bool:
    fa, fb = legal_forms(a), legal_forms(b)
    return bool(fa and fb and not (fa & fb))


GENERIC_ORG = {"mtv", "tnhh", "cp", "jsc", "ctcp", "chi nhanh", "viet nam", "tong cong ty", "cong ty", "cong ty me", "cong ty con", "cong ty lien ket", "ngan hang", "tap doan", "du an", "chi", "thanh", "quoc te", "cong nghiep", "logistics",
               "thai binh duong", "toan cau", "long hung", "binh phuoc", "bat dong san", "nha nuoc", "bo", "so", "cuc", "uy ban", "ubnd", "chinh phu", "hdqt", "chung khoan", "nha may"}


PLACES = {fold_name(x) for x in ["An Giang", "Bà Rịa Vũng Tàu", "Bạc Liêu", "Bắc Giang", "Bắc Kạn", "Bắc Ninh", "Bến Tre", "Bình Dương", "Bình Định", "Bình Phước", "Bình Thuận", "Cà Mau", "Cao Bằng", "Cần Thơ", "Đà Nẵng", "Đắk Lắk", "Đắk Nông", "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai", "Hà Giang", "Hà Nam", "Hà Nội", "Hà Tĩnh", "Hải Dương", "Hải Phòng", "Hậu Giang", "Hòa Bình", "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu", "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Long An", "Nam Định", "Nghệ An", "Ninh Bình", "Ninh Thuận", "Phú Thọ", "Phú Yên", "Quảng Bình", "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị", "Sóc Trăng", "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên", "Thanh Hóa", "Thừa Thiên Huế", "Huế", "Tiền Giang", "TP.HCM", "TPHCM", "Hồ Chí Minh", "Sài Gòn", "Trà Vinh", "Tuyên Quang", "Vĩnh Long", "Vĩnh Phúc", "Yên Bái", "Việt Trì", "Thủ Đức", "Việt Nam", "Trung Quốc", "Nhật Bản", "Hàn Quốc", "Singapore", "Thái Lan", "Indonesia", "Malaysia", "Mỹ", "Hoa Kỳ", "Đài Loan", "Hồng Kông", "Ấn Độ", "Campuchia", "Lào", "Úc", "Anh", "Pháp", "Đức", "Nga", "Philippines", "Châu Á", "Châu Âu"]}
AGENCY_START = ("bo ", "cuc ", "so ", "uy ban", "co quan", "cong an", "toa an", "vien kiem sat", "ubnd", "chi cuc", "tong cuc", "van phong", "phong ", "thanh tra", "kho bac", "hai quan", "hoi dong nhan dan")


INDUSTRY_WORDS = {"vien", "thong", "cong", "nghiep", "dau", "khi", "xay", "dung", "bat", "dong", "san", "van", "tai", "nong", "thuy", "luong", "thuc", "xi", "mang", "dien", "luc", "phat", "than", "khoang",
                  "du", "lich", "thuong", "mai", "bao", "hiem", "chung", "khoan", "tu", "trien", "nghe", "thep", "hoa", "chat", "duoc", "pham", "y", "te", "giao", "duc", "quoc", "toan", "cau", "dich", "vu",
                  "kinh", "doanh", "tong", "hop", "sai", "gon", "ha", "noi", "viet", "nam", "mien", "bac", "trung", "tay", "ngan", "hang", "xuat", "nhap", "khau"}


def is_generic_org(name: str) -> bool:
    k = fold_name(name)
    toks = k.split()
    rest = re.sub(r"\b(?:cong ty|cty|ctcp|tnhh|mtv|cp|co phan|tap doan|tong cong ty|ngan hang|tmcp|jsc|chi nhanh)\b", " ", k).split()
    if not rest:
        return True
    return (k in GENERIC_ORG or k in PLACES or len(k) < 3 or k.isdigit() or k.startswith(("co dong", "nha dau tu")) or (len(toks) <= 2 and all(t in INDUSTRY_WORDS for t in toks)))


def is_agency_name(name: str) -> bool:
    k = fold_name(name)
    return k.startswith(AGENCY_START) or k in ("hdqt",)


_BOUND = r"(?:cua|tai|boi|voi|cho|la|tu|den|tren|duoi|nhu|giua|gom|vao|ong|ba|mua|ban|nhan|thanh lap)"
_PREFIX = r"(?:cong ty|cty|ctcp|tnhh|mtv|cp|co phan|tap doan|tong cong ty|tcty|ngan hang|nhtm|tmcp|thuong mai|quy|jsc|chi nhanh|doanh nghiep)"


def left_chain(ft: str, start: int) -> tuple[bool, str]:
    """(ok, chain): ok = the name starting at `start` (folded text) is NOT the tail of a longer name - what stands to its left is a clause boundary, a function word or a chain of legal/class prefix
    words that itself starts at a boundary ('Cong ty co phan <core>' is fine, 'Khoang san va Luyen kim <core>' is not). chain = the consumed prefix words (used for class checks)."""
    b = ft[max(0, start - 100):start].rstrip()
    chain: list[str] = []
    for _ in range(8):
        if not b or b[-1] in ',;:(-.\"\u201c\u201d\n':
            return True, " ".join(reversed(chain))
        if re.search(r"(?:^|\s)" + _BOUND + r"$", b):
            return True, " ".join(reversed(chain))
        m = re.search(r"(?:^|[\s(])" + _PREFIX + r"$", b)
        if not m:
            return False, ""
        chain.append(m.group(0).strip(" ("))
        b = b[:m.start()].rstrip()
    return False, ""


def left_ok(ft: str, start: int) -> bool:
    return left_chain(ft, start)[0]


def name_classes(s: str) -> set[str]:
    f = fold1(s)
    out = set()
    if re.search(r"\bngan hang\b|\bnhtm\b|\btmcp\b", f):
        out.add("BANK")
    if re.search(r"\btong cong ty\b|\btcty\b", f):
        out.add("CORP")
    if re.search(r"\btap doan\b", f):
        out.add("GROUP")
    if re.search(r"\bquy\b", f):
        out.add("FUND")
    return out


def class_conflict(chain: str, canonical: str) -> bool:
    """The class words written in the article right before a name (bank / corporation / group / fund) must agree with the class words of the registry's legal name of that entity."""
    a, b = name_classes(chain), name_classes(canonical)
    return bool(a and b and a != b)


@dataclass
class Verdict:
    decision: str  # VERIFIED_MERGE | DISTINCT | AMBIGUOUS | UNRESOLVED
    reason: str
    evidence: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    conflicts: list = field(default_factory=list)


# ------------------------------------------------------------------------------------------------ persons
NAME_OK = re.compile(r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)+$", re.UNICODE)
PERSON_STOP = {"ca nhan", "doi tuong", "nguoi", "nguoi dan", "ong", "ba", "chu tich", "tong giam doc", "cong an", "bi can", "bi cao", "nha dau tu", "co dong", "ban lanh dao"}
RELATIVE_RX = re.compile(r"(con trai|con gai|con dau|con re|vo|chong|anh trai|em trai|chi gai|em gai|bo|me|cha|nguoi than|nguoi lien quan|anh ruot|chi ruot)\s+(?:cua\s+)?(?:ong|ba|chu tich|tong giam doc)?\s*$")


def person_name_ok(name: str, name_key: str) -> bool:
    toks = name_key.split()
    return bool(NAME_OK.match(name.strip())) and len(toks) >= 2 and name_key not in PERSON_STOP and not any(t.isdigit() for t in toks)


def person_context(text: str, name: str, pub: date | None) -> dict:
    """Facts about ONE mention of a person in an article: gender cue before the name, relative-of cue, birth year / age cue after the name. Offsets are valid in `text`."""
    ft, fn = fold1(text), fold_name(name)
    out = {"found": False, "gender": None, "relative": False, "birth": None, "snippet": ""}
    if not fn:
        return out
    m = re.search(r"(?<!\w)" + mk_tokens(fn) + r"(?!\w)", ft)
    if not m:
        return out
    out["found"] = True
    before, after = ft[max(0, m.start() - 70):m.start()], ft[m.end():m.end() + 220]
    g = re.search(r"\b(ong|ba)\s*$", before)
    out["gender"] = {"ong": "M", "ba": "F"}[g.group(1)] if g else None
    out["relative"] = bool(RELATIVE_RX.search(before.rstrip(" ,:-")))
    b = re.search(r"(?:sinh nam|sn|nam sinh|sinh)\s*:?\s*(19\d{2}|20[0-2]\d)", after)
    if b:
        out["birth"] = int(b.group(1))
    else:
        a = re.search(r"\(\s*(\d{2})\s*tuoi\s*\)|,\s*(\d{2})\s*tuoi", after[:60])
        if a and pub:
            age = int(a.group(1) or a.group(2))
            out["birth"] = pub.year - age
    out["snippet"] = text[max(0, m.start() - 160):m.end() + 240].replace("\n", " ")
    return out


def birth_conflict(a: int | None, b: int | None) -> bool:
    return a is not None and b is not None and abs(a - b) > 1


def role_family(pred: str) -> str:
    return "LEAD" if pred in LEADERSHIP else ("OWN" if pred == "OWNS_SHARES_IN" else pred)


def json_dumps(o) -> str:
    return json.dumps(o, ensure_ascii=False, sort_keys=True, default=list)


def person_key(name: str) -> str:
    return normalize_name(name, is_person=True)


def person_key_org(name: str) -> str:
    """Normalised ORGANISATION name key (legal prefixes/suffixes stripped, accent-folded)."""
    return normalize_name(name)


PLACEHOLDER_DATE = date(2002, 1, 1)  # the crawler stored this default for ~14.8k articles whose page had no parsable date: it is NOT a publication date


def url_date(url: str | None) -> date | None:
    """Publication date recovered from the URL when the stored one is missing/placeholder: Vietstock /YYYY/MM/ (day unknown -> 15th), CafeF id 188yymmdd... ."""
    if not url:
        return None
    m = re.search(r"vietstock\.vn/(20\d{2})/(\d{2})/", url)
    try:
        if m:
            return date(int(m.group(1)), int(m.group(2)), 15)
        m = re.search(r"-188(\d{2})(\d{2})(\d{2})\d{6,}\.chn", url)
        if m:
            return date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    return None


def best_date(published_at: str | None, url: str | None) -> date | None:
    d = article_date(published_at)
    return url_date(url) if d is None or d == PLACEHOLDER_DATE else d
