"""Article ranking / controlled selection tests (synthetic entries; no network)."""
from vckg.crawlers.discovery import Ranked, _tokens, group_duplicates, score_entry, select
from vckg.crawlers.targeted import Entry


def E(title, summary="", source="cafef", url=None):
    return Entry(url or f"https://x.test/{abs(hash(title))}", title, summary, source)


def test_topic_detection_title_weighs_more_and_folds_accents():
    r = score_entry(E("Vingroup thâu tóm công ty con của đối tác, hoàn tất thương vụ"))
    assert r.topic == "mna" and r.score >= 8
    r2 = score_entry(E("Thị trường đi ngang", "tóm tắt nhắc tới bổ nhiệm"))
    assert r2.topic == "appointment" and r2.score < r.score
    assert score_entry(E("Giá vàng hôm nay tăng nhẹ")).topic == "none"


def test_feed_hint_boosts_topic():
    base = score_entry(E("Công bố thông tin doanh nghiệp"), "")
    hinted = score_entry(E("Công bố thông tin doanh nghiệp"), "https://vietstock.vn/3118/doanh-nghiep/trai-phieu-doanh-nghiep.rss")
    assert hinted.topic == "bond" and hinted.score > base.score


def test_duplicate_groups_and_known_titles():
    a, b, c = (Ranked(url=u, source="s", title=t, summary="") for u, t in [
        ("u1", "VPBank phát hành trái phiếu 5.000 tỷ đồng"), ("u2", "VPBank phát hành trái phiếu 5.000 tỷ đồng trong quý 4"),
        ("u3", "Hòa Phát bổ nhiệm tổng giám đốc mới")])
    group_duplicates([a, b, c], [])
    assert a.dup_group == b.dup_group != c.dup_group
    d = Ranked(url="u4", source="s", title="Hòa Phát bổ nhiệm tổng giám đốc mới", summary="")
    group_duplicates([d], [_tokens("Hòa Phát bổ nhiệm tổng giám đốc mới")])
    assert d.dup_group == -2


def _pool():
    items = []
    topics = ["Bổ nhiệm tổng giám đốc", "Mua lại cổ phần thâu tóm", "Phát hành trái phiếu", "Xử phạt hành chính", "Khởi tố bị can", "Cổ đông lớn thoái vốn"]
    for i in range(60):
        t = topics[i % 6] + f" alpha{i} beta{i * 3 + 1}"
        items.append(score_entry(E(t, source=["cafef", "vietstock", "vneconomy"][i % 3], url=f"https://x.test/t{i}")))
    for i in range(80):
        items.append(score_entry(E(f"Giá hàng hóa gamma{i} biến động delta{i * 7 + 2}", source=["cafef", "vietstock", "vneconomy"][i % 3], url=f"https://x.test/c{i}")))
    group_duplicates(items, [])
    return items


def test_select_split_topics_control_and_no_leakage():
    sel = select(_pool(), n=40, targeted_share=0.75, seed=7)
    t = [r for r in sel if r["subset"] == "targeted"]
    c = [r for r in sel if r["subset"] == "control"]
    assert len(t) == 30 and len(c) == 10
    assert len({r["topic"] for r in t}) >= 5  # topic round-robin, not just the highest-scoring topic
    assert not ({r["dup_group"] for r in t} & {r["dup_group"] for r in c})
    assert all(r["selection_reason"] for r in sel) and all(r["selection_score"] >= 4 for r in t)
    assert "random control" in c[0]["selection_reason"]
    assert sel == select(_pool(), n=40, targeted_share=0.75, seed=7)  # deterministic
    assert sel != select(_pool(), n=40, targeted_share=0.75, seed=8)  # control changes with seed


def test_source_cap_and_staged_duplicates_excluded():
    items = _pool()
    for it in items[:6]:
        it.dup_group = -2
    sel = select(items, n=40, seed=1)
    assert not {r["url"] for r in sel} & {it.url for it in items[:6]}
    from collections import Counter
    cnt = Counter(r["source"] for r in sel if r["subset"] == "targeted")
    assert max(cnt.values()) <= 14  # ceil(30 * 0.45)
