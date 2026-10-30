"""Test doubles/fixtures. FakeNER and AcceptAll exist ONLY for offline unit tests; they are never used for live runs
and no test using them is reported as evidence of GLiNER/Qwen quality."""
from __future__ import annotations

import json
from pathlib import Path

from vckg.entity_linking.resolver import EntityResolver
from vckg.entity_linking.store import RegistryStore
from vckg.models import Article, EntityType, FactualStatus, Mention, ResolutionStatus, Verdict

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "registry" / "seed_registry.json"


class FakeNER:
    def __init__(self, spec: dict[str, EntityType]):
        self.spec = spec

    def extract(self, text: str) -> list[Mention]:
        out = []
        for surface, label in self.spec.items():
            i = text.find(surface)
            while i != -1:
                out.append(Mention(text=surface, start=i, end=i + len(surface), label=label, ner_score=0.9, method="test_double"))
                i = text.find(surface, i + 1)
        return out


def make_resolver(org_status: ResolutionStatus = ResolutionStatus.VERIFIED) -> EntityResolver:
    """Registry built from the hand-written seed; orgs get `org_status` (tests emulate an identity provider)."""
    store = RegistryStore(":memory:")
    for e in json.loads(SEED.read_text(encoding="utf-8"))["entries"]:
        t = EntityType(e["type"])
        if t == EntityType.PERSON:
            store.add_entity(e["canonical_name"], t, entity_id=e["entity_id"], source_type="seed_handwritten")
        else:
            eid, _ = store.add_entity(e["canonical_name"], t, ticker=(e.get("tickers") or [None])[0], status=org_status,
                                      provider="test_identity", source_url="test://seed", identity_only=True,
                                      source_type="identity_provider")
            for a in e.get("aliases", []):
                store.add_alias(eid, a, "alias", source_type="identity_provider", provider="test_identity")
    return EntityResolver(store)


def art(text: str, aid: str = "a1", url: str = "https://example.com/a1") -> Article:
    return Article(article_id=aid, url=url, source="test", title="", text=text, published_at="2026-01-01")


class AcceptAll:
    """Verifier test double: confirms the rule-proposed direction and status."""
    model = "test-double"
    prompt_version = "test"

    def __init__(self):
        self.calls = 0

    def verify(self, c, definition=""):
        self.calls += 1
        st = c.factual_status if c.factual_status != FactualStatus.UNKNOWN else FactualStatus.FACT
        return Verdict(valid=True, relation_type=c.predicate, subject_mention=c.subject.text, object_mention=c.object.text,
                       direction="AS_LISTED", evidence_text="", factual_status=st, rejection_reason="NONE")


def verdict_for(c, **kw):
    base = {"valid": True, "relation_type": c.predicate, "subject_mention": c.subject.text, "object_mention": c.object.text,
                "direction": "AS_LISTED", "evidence_text": "", "factual_status": FactualStatus.FACT, "rejection_reason": "NONE"}
    base.update(kw)
    return Verdict(**base)
