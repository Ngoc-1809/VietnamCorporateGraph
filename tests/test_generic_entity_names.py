"""Generic endpoints must remain reviewable without forming false network hubs."""
import pytest

from vckg.entity_linking.generic import is_generic_entity
from vckg.entity_linking.grounding import org_grounded
from vckg.final_project.quarantine import _network
from vckg.models import EntityType, Mention
from vckg.ner.scope import classify_scope


@pytest.mark.parametrize("name", ["Công an", "Công an tỉnh", "công ty con", "Group",
                                          "Cục Thuế", "Cục Thuế tỉnh", "Thanh tra",
                                          "Cơ quan cảnh sát điều tra", "Cơ quan CSĐT",
                                          "ngân hàng đầu tư", "công ty liên doanh", "Việt Nam"])
def test_bare_names_are_not_grounded_or_linked(name):
    mention = Mention(text=name, start=0, end=len(name), label=EntityType.GOVERNMENT_AGENCY)
    assert is_generic_entity(name)
    assert not org_grounded(mention)
    assert classify_scope(mention)[0] is False


@pytest.mark.parametrize("name", ["Công an TP.HCM", "Cục Thuế tỉnh Bình Dương",
                                          "Thanh tra Chứng khoán Nhà nước", "Sun Group", "Bộ Công an"])
def test_specific_names_remain_eligible(name):
    assert not is_generic_entity(name)


def test_generic_candidate_remains_in_snapshot_but_not_in_network_metrics():
    edges = {"bad": {"subject_id": "person", "object_id": "generic"},
             "good": {"subject_id": "person", "object_id": "specific"}}
    metrics, nodes = _network(edges, {"good"})
    assert set(nodes) == {"person", "generic", "specific"}
    assert nodes["generic"]["degree"] == 0
    assert metrics["simple_undirected_pairs"] == 1
