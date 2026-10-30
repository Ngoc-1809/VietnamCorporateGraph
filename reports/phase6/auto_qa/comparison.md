# Phase 6A - so sánh graph gốc vs graph staging đã QA (44 cạnh official)
Không có gold: đây là kết quả kiểm tra tự động theo luật, không phải Precision/Recall. Neo4j production không bị sửa (chỉ đọc; 44 edge_id khớp 100%).

| Chỉ số | Gốc | Staging QA |
|---|---|---|
| Cạnh | 44 | 25 validated (24 PASS + 1 cạnh trái phiếu sau gộp) |
| Domain entities | 74 | 44 |
| Loại quan hệ | 8 | 7 (mất PROSECUTED_BY) |
| PASS / AUTO_CORRECT / QUARANTINE / REJECT | - | 24 / 2 / 18 / 0 |
| BondIssue trùng giải quyết | - | 1 sự kiện (Vinhomes VHML12618: 80.000 TP x 100 triệu = 8.000 tỷ) |
| Qwen (lần chạy nguội đầu) | - | 46 lần gọi, 44 s; các lần sau dùng cache |

Quarantine/validated nằm ở `quarantine.jsonl`, `validated_edges.jsonl`; mỗi quyết định có lý do ở `audit_results.csv/jsonl`.
