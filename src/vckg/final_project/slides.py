"""Generate a compact academic presentation from the current final-project snapshot."""
from __future__ import annotations

import argparse
import html
import json
import sqlite3
import subprocess
from pathlib import Path

from vckg.final_project.app import snapshot_dir
from vckg.final_project.report import CHROME, EDGE, OUTPUT, ROOT, vi_float, vi_int

CSS = """
@page{size:13.333in 7.5in;margin:0}*{box-sizing:border-box}body{font-family:Arial,sans-serif;color:#172536;margin:0}
.slide{height:7.5in;width:13.333in;padding:.54in .7in;break-after:page;page-break-after:always;position:relative;overflow:hidden}
.slide:last-child{break-after:auto}.kicker{font-size:13px;color:#5b6c80;letter-spacing:.12em;text-transform:uppercase}
h1{font-size:36px;line-height:1.16;max-width:1100px;margin:16px 0 24px;font-weight:650}h2{font-size:22px;margin:8px 0 14px}
p,li{font-size:19px;line-height:1.4}ul,ol{padding-left:27px}li{margin:11px 0}.small{font-size:15px;color:#506176}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}.card{border:1px solid #aebac5;padding:21px;border-radius:4px}
.card b{font-size:30px;display:block}.card span{font-size:15px;color:#506176}.flow{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:26px 0}
.step{border:1px solid #7d8b99;padding:13px 18px;font-size:17px;border-radius:4px}.arrow{color:#778ba1;font-size:25px}
.metric-row{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin:25px 0}.metric{background:#edf1f5;padding:19px}.metric strong{font-size:35px;display:block}.metric span{font-size:14px}
table{border-collapse:collapse;width:100%;font-size:16px}td,th{border-bottom:1px solid #b6c0c9;padding:11px;text-align:left}
.foot{position:absolute;bottom:.28in;left:.7in;right:.7in;border-top:1px solid #bbc6d1;padding-top:8px;color:#667588;font-size:12px;display:flex;justify-content:space-between}
.highlight{color:#1c5078}.warning{border-left:4px solid #586b80;background:#f1f3f5;padding:14px 18px;margin:21px 0;font-size:18px}
"""


def slide(number: int, kicker: str, title: str, body: str) -> str:
    return (f"<section class='slide'><div class='kicker'>{html.escape(kicker)}</div><h1>{title}</h1>{body}"
            f"<div class='foot'><span>VCKG · Nhóm 2 · Báo cáo cuối kỳ</span><span>{number:02d} / 09</span></div></section>")


def render(snapshot: Path, output: Path = OUTPUT, *, pdf: bool = False) -> dict:
    meta = json.loads((snapshot / "metrics.json").read_text(encoding="utf-8"))
    m = meta["analysis"]
    with sqlite3.connect(snapshot / "profile.sqlite") as db:
        top = db.execute("SELECT name,degree,pagerank FROM nodes ORDER BY pagerank DESC LIMIT 4").fetchall()
    top_rows = "".join(f"<tr><td>{html.escape(name)}</td><td>{vi_int(degree)}</td><td>{vi_float(rank, 5)}</td></tr>"
                       for name, degree, rank in top)
    p = []
    p.append(slide(1, "Phân tích mạng phương tiện xã hội trong kinh doanh",
                   "Chân dung một node trên đồ thị tri thức doanh nghiệp Việt Nam",
                   "<p>Trịnh Thanh Ngọc (23020560) · Nguyễn Tự Anh Tuấn (23020570)</p><p>TS. Trần Mai Vũ · Dữ liệu báo chí · Snapshot "
                   f"{html.escape(meta['snapshot_id'])}</p><p class='small'>github.com/Ngoc-1809/VietnamCorporateGraph</p>"))
    p.append(slide(2, "Bài toán", "Từ bài báo đến một mạng có thể kiểm chứng",
                   "<div class='grid'><div class='card'><h2>Yêu cầu</h2><ul><li>Nhận dạng node và quan hệ từ văn bản</li><li>Phân tích khoảng cách, PageRank, cộng đồng, k-core</li><li>Ứng dụng chân dung node và hỏi đáp nhiều bước</li></ul></div>"
                   "<div class='card'><h2>Nguyên tắc</h2><ul><li>Chỉ dùng báo chí cho cạnh</li><li>Mỗi cạnh có đoạn chứng cứ và URL</li><li>Không tạo cạnh từ đồng xuất hiện</li></ul></div></div>"))
    p.append(slide(3, "Pipeline", "Hai nhánh nhận dạng · hai nhánh trích xuất",
                   "<div class='flow'><span class='step'>Crawl & parse</span><span class='arrow'>→</span><span class='step'>GLiNER ∥ Registry</span><span class='arrow'>→</span><span class='step'>Entity Linking & Grounding</span></div>"
                   "<div class='flow'><span class='step'>Rule-based RE ∥ Qwen3.5:9b</span><span class='arrow'>→</span><span class='step'>Fusion & QA</span><span class='arrow'>→</span><span class='step'>Global ER v2</span><span class='arrow'>→</span><span class='step'>Neo4j</span></div>"
                   "<p class='small'>Qwen chỉ đề xuất quan hệ; luật kiểm tra schema, bằng chứng, chiều cạnh, trạng thái và định danh.</p>"))
    p.append(slide(4, "Chất lượng", "Cổng ứng dụng kiểm lại định danh sau ER",
                   f"<div class='metric-row'><div class='metric'><strong>{vi_int(meta['node_count'])}</strong><span>node có cạnh</span></div>"
                   f"<div class='metric'><strong>{vi_int(meta['edge_count'])}</strong><span>dòng cạnh</span></div>"
                   f"<div class='metric'><strong>{meta['relation_types']}</strong><span>loại quan hệ</span></div>"
                   f"<div class='metric'><strong>{vi_int(meta['evidence_count'])}</strong><span>evidence</span></div></div>"
                   "<p>Chỉ nhận FACT / HISTORICAL / ENDED và hai đầu VERIFIED hoặc ARTICLE_GROUNDED. "
                   "Loại tên tổ chức một từ chỉ được grounding từ bài.</p>"
                   "<div class='warning'>PASS là nhãn QA, không phải precision. Chưa có gold độc lập để tuyên bố ≥90%.</div>"))
    p.append(slide(5, "Cấu trúc mạng", "Mạng có hạt nhân nhưng còn phân mảnh",
                   f"<div class='metric-row'><div class='metric'><strong>{vi_int(m['connected_components'])}</strong><span>thành phần</span></div>"
                   f"<div class='metric'><strong>{vi_int(m['largest_component'])}</strong><span>node ở thành phần lớn nhất</span></div>"
                   f"<div class='metric'><strong>{vi_int(m['communities'])}</strong><span>cộng đồng Louvain</span></div>"
                   f"<div class='metric'><strong>{m['max_core']}</strong><span>k-core cao nhất</span></div></div>"
                   f"<p>Thành phần lớn nhất chiếm {vi_float(100*m['largest_component_share'], 1)}% node. Không có khoảng cách trung bình hữu hạn cho mọi cặp toàn mạng.</p>"))
    p.append(slide(6, "Small-world", "So sánh trên thành phần liên thông lớn nhất",
                   f"<div class='grid'><div class='card'><h2>Mạng quan sát</h2><p>L = {vi_float(m['largest_component_average_shortest_path'], 3)}<br>C = {vi_float(m['largest_component_clustering'], 4)}</p></div>"
                   f"<div class='card'><h2>Baseline giữ bậc · {m['random_trials']} lượt</h2><p>Lᵣ = {vi_float(m['random_baseline_path_length'], 3)}<br>Cᵣ = {vi_float(m['random_baseline_clustering'], 4)}</p></div></div>"
                   f"<p><b>σ = (C/Cᵣ)/(L/Lᵣ) = {vi_float(m['small_world_sigma_largest_component'], 2)}</b></p>"
                   "<p class='small'>Kết luận có điều kiện cho thành phần lớn nhất, không áp dụng nguyên xi cho toàn graph phân mảnh.</p>"))
    p.append(slide(7, "Xếp hạng & chân dung", "Một node, nhiều góc nhìn",
                   "<div class='grid'><div><h2>PageRank cao trong snapshot</h2><table><tr><th>Node</th><th>Bậc</th><th>PageRank</th></tr>"
                   f"{top_rows}</table></div><div><img src='app_profile_preview2.png' alt='Giao diện chân dung node' "
                   "style='width:100%;height:410px;object-fit:cover;object-position:top;border:1px solid #bcc8d3'></div></div>"))
    p.append(slide(8, "GraphRAG", "Tìm đường trước · Qwen giải thích sau",
                   "<div class='flow'><span class='step'>Node A + Node B</span><span class='arrow'>→</span><span class='step'>Neo4j: đường ≤3 bước</span><span class='arrow'>→</span><span class='step'>Evidence từng cạnh</span><span class='arrow'>→</span><span class='step'>Qwen + [1][2][3]</span></div>"
                   "<p>Không có đường hoặc không đủ chứng cứ → hệ thống nói rõ chưa thể trả lời. "
                   "Đường A→B→C là liên hệ gián tiếp, không được diễn đạt thành cạnh A→C.</p>"
                   "<p class='small'>Demo: scripts/start-final-project.ps1 · http://127.0.0.1:8765</p>"))
    p.append(slide(9, "Kết luận", "Đạt ứng dụng và phân tích · còn thiếu gold và số cạnh",
                   f"<ul><li>{vi_int(meta['node_count'])} node, {vi_int(meta['edge_count'])} cạnh, {meta['relation_types']} loại: đạt node/loại, chưa đạt 5.000 cạnh.</li>"
                   "<li>Có PageRank, Louvain, k-core, small-world có baseline và giới hạn đúng.</li>"
                   "<li>Chưa có precision/NER F1 độc lập; mẫu 200+80+20 cần người đọc bài gốc.</li>"
                   "<li>Không đẩy QUARANTINE vào KPI để lấp khoảng thiếu.</li></ul>"
                   "<p class='small'>Mã nguồn và hướng dẫn tái lập: github.com/Ngoc-1809/VietnamCorporateGraph</p>"))
    output.mkdir(parents=True, exist_ok=True)
    html_path = output / "topic17_final_slides.html"
    html_path.write_text("<!doctype html><html lang='vi'><head><meta charset='utf-8'>"
                         f"<style>{CSS}</style></head><body>{''.join(p)}</body></html>", encoding="utf-8")
    result = {"html": str(html_path), "slides": len(p), "snapshot": meta["snapshot_id"]}
    if pdf:
        browser = EDGE if EDGE.exists() else CHROME
        pdf_path = output / "topic17_final_slides.pdf"
        subprocess.run([str(browser), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={ROOT / 'tmp/final-slides-browser'}", f"--print-to-pdf={pdf_path}",
                        html_path.as_uri()], check=True, timeout=120, capture_output=True)
        if not pdf_path.exists() or pdf_path.stat().st_size < 10_000:
            raise RuntimeError("Slides PDF print failed")
        result["pdf"] = str(pdf_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()
    print(json.dumps(render(args.snapshot or snapshot_dir(), pdf=args.pdf), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
