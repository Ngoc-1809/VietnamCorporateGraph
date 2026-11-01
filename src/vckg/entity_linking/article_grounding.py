"""Phase 6B.3 - automated article-grounded identity promotion (staging only).

Reuses the Phase 5 registry (RegistryStore, ARTICLE_GROUNDED, grounding.org_grounded / person_grounded). Adds rules for endpoints that
stayed PROVISIONAL or unresolved although the article itself identifies them:
  A  full legal name (legal form + at least one capitalised non-generic proper token; lowercase sector words allowed) -> ARTICLE_GROUNDED
  B  short name defined in parentheses next to a grounded full name in the SAME article ("... An Bình (ABBank)") -> mention-level resolution
  C  short name that is a contiguous token run of exactly ONE longer grounded org name of the same article -> mention-level resolution
  P  person: full name (>=2 capitalised tokens) + organization mention or role wording in the same sentence, article-scoped id -> ARTICLE_GROUNDED
Safety
  * B and C never merge registry entities: they produce an overlay (article, span) -> entity id, so a short name in one article cannot drag
    other articles' entities (org entities are keyed by name across the corpus).
  * Never touches single-token person names, generic names ("Việt Nam", "Xây dựng"), truncated NER spans, near-duplicate names, bond nodes.
  * Never promotes to VERIFIED. Nothing outside the supplied (staging) registry is changed; set_status/overlay are idempotent.
  * Every decision stores original id, resolved id, evidence span, method, checks passed and conflicts."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from vckg.entity_linking.grounding import _LEGAL, org_grounded
from vckg.entity_linking.normalize import normalize_name
from vckg.entity_linking.store import RegistryStore
from vckg.models import EntityType, Mention, ResolutionStatus
from vckg.reasons import suspect_span

METHOD_VERSION = "article-grounding-v1"
_GENERIC_WORDS = {"dau", "tu", "thuong", "mai", "xay", "dung", "san", "xuat", "dich", "vu", "cong", "nghe", "chung", "khoan", "bat", "dong", "ha", "tang", "tai", "chinh", "nang", "luong", "viet", "nam", "quoc", "te", "phat", "trien", "kinh", "doanh", "nghiep", "van", "tap", "doan", "ty", "ngan", "hang", "co", "phan", "tnhh", "ctcp", "vang", "bac", "da", "quy", "tieu", "thuc", "pham", "dia", "oc", "du", "lich", "khong", "dien", "nuoc", "bao", "hiem", "hiep", "hoi", "tong", "chi", "nhanh", "trung", "tam", "uy", "ban", "so", "bo", "cuc", "nha", "may"}
_TITLES = {"ông", "bà", "anh", "chị", "ts", "pgs", "gs", "ths", "mr", "ms", "mrs"}
_ROLE = re.compile(r"chủ tịch|tổng giám đốc|giám đốc|phó chủ tịch|thành viên hđqt|thành viên hội đồng|\bceo\b|người đại diện|cổ đông|sáng lập", re.IGNORECASE)
_PAREN = re.compile(r"^\s*\(([^()]{1,80})\)")
_TICKER_CUE = re.compile(r"HOSE|HNX|UPCOM|MCK|\bmã\b", re.IGNORECASE)
_GEO = {"han quoc", "nhat ban", "trung quoc", "my", "singapore", "ha noi", "tp hcm", "viet nam", "thai lan", "an do", "hoa ky", "duc", "phap", "indonesia", "dai loan"}
ORG_LABELS = {"ORGANIZATION", "BANK", "REGULATOR", "GOVERNMENT_AGENCY"}


def _cap(t: str) -> bool:
    return bool(t) and (t[0].isupper() or t[0].isdigit())


def core_tokens(text: str) -> list[str]:
    return [t for t in normalize_name(text).split() if t]


def non_generic(tokens: list[str]) -> bool:
    return any(t not in _GENERIC_WORDS for t in tokens)


def alias_proven(piece: str, head_text: str, has_ticker_cue: bool) -> bool:
    """A parenthetical is only an alias if it is (a) next to an exchange/ticker cue, (b) a token run of the head name, or (c) starts with the
    initials of the head's proper tokens (ABBank <- An Bình). Countries/cities in parentheses ("(Hàn Quốc)") are never aliases."""
    pt = core_tokens(piece)
    if not pt or " ".join(pt) in _GEO or not piece[:1].isupper():
        return False
    ht = core_tokens(head_text)
    if has_ticker_cue:
        return len(pt) <= 4
    if len(ht) > len(pt) and (ht[:len(pt)] == pt or ht[-len(pt):] == pt):
        return True
    ini = "".join(t[0] for t in ht if t not in _GENERIC_WORDS)
    return len(ini) >= 2 and "".join(pt).startswith(ini)


def org_full_name_ok(text: str, ner_score: float | None, ner_min: float = 0.8) -> tuple[bool, str]:
    """Extension of grounding.org_grounded: legal form + >=1 capitalised proper token; lowercase sector words allowed in between."""
    if ner_score is not None and ner_score < ner_min:
        return False, "LOW_NER_SCORE"
    lm = _LEGAL.match(text.strip())
    if not lm:
        return False, "NO_LEGAL_FORM"
    rest = text.strip()[lm.end():].split()
    if not rest or len(rest) > 9:
        return False, "NAME_LENGTH"
    proper = [t for t in rest if _cap(t) and normalize_name(t) not in _GENERIC_WORDS and t not in ("-", "–", "&")]
    if not proper:
        return False, "NO_PROPER_TOKEN"
    if not _cap(rest[-1]) and not rest[-1][-1].isdigit():
        return False, "ENDS_LOWERCASE"
    return True, "FULL_LEGAL_NAME"


@dataclass
class Decision:
    article_id: str
    start: int
    end: int
    text: str
    label: str
    original_entity_id: str | None
    original_status: str
    action: str = "KEEP"                 # PROMOTE | RESOLVE_TO | KEEP
    resolved_entity_id: str | None = None
    method: str = ""
    reason: str = ""                     # for KEEP: cause code
    evidence: str = ""
    evidence_span: tuple[int, int] | None = None
    checks_passed: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    version: str = METHOD_VERSION

    def as_dict(self) -> dict:
        return {**self.__dict__, "evidence_span": list(self.evidence_span) if self.evidence_span else None}


def _status(store: RegistryStore, eid: str | None) -> str:
    if not eid:
        return "UNRESOLVED"
    r = store.get_entity(eid)
    return r["resolution_status"] if r else "UNRESOLVED"


def _is_grounded(s: str) -> bool:
    return s in ("VERIFIED", "ARTICLE_GROUNDED")


def _truncated(text: str, m: dict) -> bool:
    nxt = text[m["end"]:m["end"] + 1]
    if nxt.isalnum() and m["text"].endswith("."):  # span cut inside 'TP.HCM'
        return True
    mm = Mention(text=m["text"], start=m["start"], end=m["end"], label=EntityType(m["label"]))
    return bool(suspect_span(text, mm))


def has_run(gt: list[str], toks: list[str]) -> bool:
    n = len(toks)
    return n > 0 and any(gt[i:i + n] == toks for i in range(len(gt) - n + 1))


def registry_others(store: RegistryStore, toks: list[str], own: set[str]) -> list[str]:
    cache = getattr(store, "_core_cache", None)
    if cache is None or cache[0] != store.version:
        rows = store.db.execute("SELECT entity_id, canonical_name FROM entities WHERE merged_into IS NULL AND entity_type!='PERSON'").fetchall()
        cache = (store.version, {r[0]: core_tokens(r[1]) for r in rows})
        store._core_cache = cache
    return sorted(e for e, ct in cache[1].items() if e not in own and len(ct) >= len(toks) and has_run(ct, toks))


def ground_article(store: RegistryStore, article_id: str, text: str, mentions: list[dict], apply: bool = True,
                   confirmed_complete: set[tuple[int, int]] | None = None) -> list[Decision]:
    """Decisions for every PROVISIONAL/unresolved head mention of one article. `apply=False` is a dry run (analysis)."""
    complete = confirmed_complete or set()

    def trunc(m) -> bool:  # span recovery may have proven the span complete (e.g. org followed by a person name)
        return (m["start"], m["end"]) not in complete and _truncated(text, m)

    heads = [m for m in mentions if m.get("alias_of") is None and not str(m.get("linking_method", "")).startswith("out_of_scope")]
    out: list[Decision] = []
    dec: dict[tuple, Decision] = {}
    for m in heads:
        st = _status(store, m.get("entity_id"))
        if _is_grounded(st):
            continue
        d = Decision(article_id, m["start"], m["end"], m["text"], m["label"], m.get("entity_id"), st)
        dec[(m["start"], m["end"])] = d
        out.append(d)
    by_span = {(m["start"], m["end"]): m for m in heads}
    cur_status = {k: _status(store, by_span[k].get("entity_id")) for k in by_span}

    def conflicts_for(m) -> list[str]:
        et = EntityType(m["label"])
        own = store.canonical_id(m["entity_id"]) if m.get("entity_id") else None
        ids = {c.entity_id for c in store.find_candidates(m["text"], et, fuzzy_min=101.0)}
        key = normalize_name(m["text"])
        if len(key) >= 5:  # near-identical but distinct names (find_candidates skips fuzzy when an exact hit exists, so ask for it explicitly)
            ids |= {eid for eid, _score in store._fuzzy(key, et, 93.0)}
        return sorted(store.canonical_id(i) for i in ids if store.canonical_id(i) != own)

    # ---- A: full legal name -> ARTICLE_GROUNDED
    for k, d in dec.items():
        m = by_span[k]
        if d.label not in ORG_LABELS or not m.get("entity_id"):
            continue
        if trunc(m):
            d.reason = "NER_TRUNCATED"
            continue
        ok, why = (True, "FULL_LEGAL_NAME") if org_grounded(Mention(text=m["text"], start=m["start"], end=m["end"], label=EntityType(m["label"]), ner_score=m.get("ner_score"))) \
            else org_full_name_ok(m["text"], m.get("ner_score"))
        if not ok:
            d.reason = why
            continue
        toks = core_tokens(m["text"])
        if not toks or not non_generic(toks):
            d.reason = "GENERIC_NAME"
            continue
        conf = conflicts_for(m)
        if conf:
            d.reason, d.conflicts = "NEAR_DUPLICATE_NAME", conf
            continue
        d.action, d.method, d.resolved_entity_id = "PROMOTE", "FULL_LEGAL_NAME", store.canonical_id(m["entity_id"])
        d.checks_passed = ["legal_form_and_proper_token", "ner_score_ok", "no_near_duplicate", "not_truncated", "not_generic"]
        d.evidence, d.evidence_span = m["text"], (m["start"], m["end"])
        cur_status[k] = "ARTICLE_GROUNDED"
    grounded_orgs = [m for k, m in by_span.items() if m["label"] in ORG_LABELS and m.get("entity_id") and _is_grounded(cur_status[k])]
    # ---- B: parenthetical definition next to a grounded full name
    alias_map: dict[str, list[tuple[dict, tuple[int, int]]]] = {}
    for h in grounded_orgs:
        pm = _PAREN.match(text[h["end"]:])
        if not pm:
            continue
        base = h["end"] + pm.start(1)
        cue = bool(_TICKER_CUE.search(pm.group(1)))
        pos = 0
        for piece in re.split(r"[,;]", pm.group(1)):
            p = piece.strip()
            if p and ":" not in p and len(p) <= 40 and alias_proven(p, h["text"], cue):
                s0 = base + pm.group(1).index(piece, pos) + piece.index(p)
                alias_map.setdefault(p, []).append((h, (s0, s0 + len(p))))
            pos += len(piece) + 1
    for k, d in dec.items():
        if d.action != "KEEP" or d.label not in ORG_LABELS:
            continue
        m = by_span[k]
        if d.reason in ("NER_TRUNCATED",) or trunc(m):
            d.reason = "NER_TRUNCATED"
            continue
        hits = alias_map.get(m["text"], [])
        targets = {store.canonical_id(h["entity_id"]) for h, _ in hits}
        if len(targets) == 1 and not (hits[0][1][0] <= m["start"] < hits[0][1][1]):
            h, span = hits[0]
            d.action, d.method, d.resolved_entity_id = "RESOLVE_TO", "PARENTHETICAL_DEFINITION", next(iter(targets))
            d.evidence, d.evidence_span = text[h["start"]:span[1] + 1], (h["start"], span[1] + 1)
            d.checks_passed = ["alias_defined_in_same_article", "unique_target", "target_grounded"]
        elif len(targets) > 1:
            d.reason, d.conflicts = "AMBIGUOUS_ALIAS", sorted(targets)
    # ---- C: short name = contiguous run of exactly one longer grounded name in the same article
    for k, d in dec.items():
        if d.action != "KEEP" or d.label not in ORG_LABELS or d.reason in ("NER_TRUNCATED", "NEAR_DUPLICATE_NAME", "AMBIGUOUS_ALIAS"):
            continue
        m = by_span[k]
        toks = core_tokens(m["text"])
        if not toks or not non_generic(toks) or not _cap(m["text"].split()[-1]):
            d.reason = d.reason if d.reason not in ("", "NO_LEGAL_FORM") else "GENERIC_OR_UNPROVEN_SHORT_NAME"
            continue
        cands: dict[str, dict] = {}
        for g in grounded_orgs:
            gt = core_tokens(g["text"])
            if len(gt) > len(toks) and has_run(gt, toks):  # a run anywhere counts for ambiguity (parent vs sister company)
                cands.setdefault(store.canonical_id(g["entity_id"]), g)
        edge_ok = len(cands) == 1 and (core_tokens(next(iter(cands.values()))["text"])[:len(toks)] == toks or core_tokens(next(iter(cands.values()))["text"])[-len(toks):] == toks)
        if len(cands) == 1 and not edge_ok:
            d.reason = "SHORT_NAME_ONLY_MID_NAME_RUN"
        elif len(cands) == 1:
            eid, g = next(iter(cands.items()))
            d.action, d.method, d.resolved_entity_id = "RESOLVE_TO", "SHORT_NAME_OF_UNIQUE_FULL_NAME", eid
            d.evidence, d.evidence_span = g["text"], (g["start"], g["end"])
            d.checks_passed = ["token_run_of_longer_name", "unique_longer_name_in_article", "target_grounded", "not_generic"]
            others = registry_others(store, toks, {eid, store.canonical_id(m["entity_id"]) if m.get("entity_id") else ""})
            if others:  # the same short name is also part of other registry entities (place names, funds, subsidiaries): do not guess
                d.action, d.method, d.resolved_entity_id, d.checks_passed = "KEEP", "", None, []
                d.reason, d.conflicts, d.evidence, d.evidence_span = "AMBIGUOUS_WITH_REGISTRY", others[:6], "", None
        elif len(cands) > 1:
            d.reason, d.conflicts = "AMBIGUOUS_MULTI_MATCH", sorted(cands)
        elif d.reason in ("", "NO_LEGAL_FORM", "NO_PROPER_TOKEN"):
            d.reason = "NO_FULL_NAME_IN_ARTICLE"
    # ---- P: persons
    sents_bounds = {m["sentence_index"] for m in heads}
    for k, d in dec.items():
        if d.label != "PERSON":
            continue
        m = by_span[k]
        toks = [t for t in m["text"].split() if t.lower() not in _TITLES]
        if len(toks) < 2:
            d.reason = "SHORT_PERSON_NAME"
            continue
        if not all(_cap(t) for t in toks) or (m.get("ner_score") is not None and m["ner_score"] < 0.8):
            d.reason = "PERSON_NAME_QUALITY"
            continue
        if trunc(m):
            d.reason = "NER_TRUNCATED"
            continue
        eid = m.get("entity_id")
        if not eid or "@art:" not in eid or not store.canonical_id(eid).endswith(article_id):
            d.reason = "PERSON_ID_NOT_ARTICLE_SCOPED"
            continue
        same = [o for o in heads if o["label"] == "PERSON" and o is not m and normalize_name(o["text"], is_person=True) == normalize_name(m["text"], is_person=True)
                and o.get("entity_id") and store.canonical_id(o["entity_id"]) != store.canonical_id(eid)]
        if same:
            d.reason, d.conflicts = "SAME_NAME_DIFFERENT_IDS_IN_ARTICLE", sorted({o["entity_id"] for o in same})
            continue
        sidx = m.get("sentence_index")
        near_org = [o for o in heads if o["label"] in ORG_LABELS and o.get("sentence_index") == sidx and abs(o["start"] - m["end"]) <= 200]
        sent_window = text[max(0, m["start"] - 60):m["end"] + 60]
        title_before = bool(re.search(r"(?:ông|bà|anh|chị|ts\.?|pgs\.?|gs\.?|ths\.?)\s*$", text[max(0, m["start"] - 8):m["start"]], re.IGNORECASE))
        if re.search(r"(?:quỹ|giải|hội|trường|công ty|tập đoàn|ngân hàng)\s*$", text[max(0, m["start"] - 12):m["start"]], re.IGNORECASE):
            d.reason = "NAME_PART_OF_ORG_OR_FUND"
            continue
        if not (_ROLE.search(sent_window) or (title_before and near_org)):  # an organization nearby alone is not identity evidence
            d.reason = "NO_ROLE_OR_ORG_CONTEXT"
            continue
        d.action, d.method, d.resolved_entity_id = "PROMOTE", "PERSON_FULL_NAME_WITH_CONTEXT", store.canonical_id(eid)
        d.checks_passed = ["full_name_2plus_tokens", "article_scoped_id", "no_same_name_conflict_in_article", "org_or_role_in_sentence"]
        d.evidence = text[max(0, m["start"] - 60):m["end"] + 60]
        d.evidence_span = (max(0, m["start"] - 60), m["end"] + 60)
    for d in out:
        if d.action == "KEEP" and not d.reason:
            d.reason = "OTHER_AMBIGUOUS"
    if apply:
        apply_decisions(store, out)
    del sents_bounds
    return out


def apply_decisions(store: RegistryStore, decisions: list[Decision]) -> int:
    """PROMOTE -> set_status ARTICLE_GROUNDED (logged, never downgrade, never VERIFIED). RESOLVE_TO is an overlay only (no registry write)."""
    n = 0
    for d in decisions:
        if d.action == "PROMOTE" and d.resolved_entity_id:
            n += store.set_status(d.resolved_entity_id, ResolutionStatus.ARTICLE_GROUNDED,
                                  f"{METHOD_VERSION}:{d.method}; article={d.article_id}; span={d.start}-{d.end}; evidence={d.evidence[:80]!r}")
    return n


def overlay_from(decisions: list[Decision]) -> dict[str, str]:
    return {f"{d.article_id}|{d.start}|{d.end}": d.resolved_entity_id for d in decisions if d.action == "RESOLVE_TO" and d.resolved_entity_id}
