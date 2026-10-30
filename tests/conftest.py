from pathlib import Path

import pytest

from vckg.entity_linking.dictionary import DictionaryMatcher
from vckg.entity_linking.linker import EntityLinker
from vckg.entity_linking.registry import Registry
from vckg.relation_extraction.candidates import load_relations

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def registry():
    return Registry.load(ROOT / "data" / "registry" / "seed_registry.json")


@pytest.fixture(scope="session")
def matcher(registry):
    return DictionaryMatcher(registry)


@pytest.fixture(scope="session")
def linker(registry):
    return EntityLinker(registry)


@pytest.fixture(scope="session")
def relations():
    return load_relations(str(ROOT / "config" / "relations.yaml"))
