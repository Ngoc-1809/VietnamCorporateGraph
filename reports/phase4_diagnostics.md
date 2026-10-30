# Phase 4 - Task A: vì sao 0 cạnh (baseline Phase 3, 9 bài thật)

Dữ liệu: `data/outputs/baseline_phase3/` (bản sao bất biến của output Phase 3), staging SQLite, `reports/phase4_candidate_diagnostics.csv`
(14 dòng, đủ cột: article, URL, subject/object text-type-ID, predicate, câu bằng chứng, verdict Qwen, verdict luật, trạng thái cuối, mọi mã lý do).
Sinh lại: `uv run python -m vckg.diagnostics`. Chưa sửa ngưỡng hay pipeline nào trước báo cáo này.

## 1. Kết luận

**Nguyên nhân trực tiếp của 0 cạnh: 14/14 candidate có CẢ HAI endpoint chưa link (SUBJECT_UNRESOLVED + OBJECT_UNRESOLVED).**
`EdgeStore.add()` loại ngay các candidate này (cổng `unresolved_entity`) trước khi xét verdict. Entity Registry chỉ có 19 mục seed
và không chứa người/công ty nào trong các quan hệ thật (Viettel, Ngân Lượng, China Railway Sixth Group...).

Phân tích sâu hơn - kể cả khi registry đầy đủ, 0 cạnh cũng chưa chắc là 14:

| Nhóm | Số candidate | Giải thích |
|---|---|---|
| Qua được mọi kiểm tra nếu endpoint được định danh (`would_pass_if_endpoints_resolved`) | **5** | Tào Đức Thắng CHAIR_OF/CEO_OF Viettel; Nguyễn Hòa Bình & "Shark Bình" CHAIR_OF Ngân Lượng (2 bề mặt cùng 1 người); "ông Zhang Qiang" CEO_OF China Railway Sixth Group |
| Bị Qwen từ chối đúng (đọc câu thấy không có quan hệ) | 6 | "Ông Ge Jun, Chủ tịch kiêm TGĐ **TOJOY**, từng làm việc tại Intel, Apple, Nvidia": candidate cue-based nối Ge Jun với Intel/Apple/Nvidia là **sai**; Qwen từ chối cả 6 |
| Subject sai / Qwen trả entity khác (VERIFIER_ENTITY_MISMATCH) | 2 | "Phó Đức Nam (Mr Pips)" không phải chủ tịch; câu chỉ nói Nguyễn Hòa Bình là Chủ tịch HĐQT |
| Qwen từ chối vì ranh giới span | 1 | Câu nói "Công ty TNHH China Railway Sixth Group **Việt Nam**" nhưng GLiNER cắt span thành "China Railway Sixth Group" |

Đánh giá "đúng/sai" ở bảng này là đọc tay 14 câu của tôi, **không phải ground truth** và không đủ để ước lượng precision.

## 2. Các lỗi kỹ thuật phát hiện ngoài registry

1. **Generator cue-based không ràng buộc cue với endpoint**: cue "chủ tịch" nằm gần person bất kỳ -> person nối với *mọi* org trong cửa sổ (Ge Jun -> Intel/Apple/Nvidia). Các candidate này chỉ không thành cạnh nhờ Qwen và cổng unresolved.
2. **Candidate cho từng bề mặt alias của cùng một người** ("Nguyễn Hòa Bình" / "Shark Bình" / "Mr Pips" trong ngoặc): 4 candidate cho 1 quan hệ, và alias trong ngoặc ("Phó Đức Nam (Mr Pips)") bị gán nhầm cho người khác.
3. **Ranh giới span của GLiNER**: object chứa chức danh ("HĐQT Công ty cổ phần Ngân Lượng") hoặc cắt thiếu hậu tố ("... Việt Nam").
4. **Qwen gán nhãn factual_status chưa nhất quán**: các câu "từng làm việc tại" được gán DENIED (4 lần), một lần HISTORICAL cho câu hiện tại; nhãn này gây mã NEGATED_RELATION sai về bản chất (nên là HISTORICAL/NO_RELATION). Verdict `valid=False` vẫn kèm `confidence=0.95` -> confidence của Qwen là tự khai, không phải xác suất.
5. **`candidates.jsonl` không có `article_id`** (phải suy ngược bằng khớp offset) - lỗi truy vết, sẽ sửa.
6. `confidence=0.0` từng gặp ở verdict cũ do default trong schema; sau sửa Phase 3 không còn default, nhưng giá trị 0.95 lặp lại ở hầu hết verdict cho thấy đó là số tự khai của LLM.

## 3. Counters theo bước (baseline, 9 bài)

| Bước | Số |
|---|---|
| Mentions tổng | 173 (88 bề mặt duy nhất) |
| Theo nhãn | ORGANIZATION 58, PERSON 55, GOVERNMENT_AGENCY 37, BANK 19, REGULATOR 4 |
| PERSON/ORGANIZATION/BANK | 132 |
| ...trong đó trong domain (heuristic `ner/scope.py`) | 122 |
| Out-of-scope (tất cả nhãn) | 15: chỉ số thị trường 7, từ chung 5, sàn 2, chức danh đơn thuần 1 |
| Linked | 23 (đều thuộc dictionary seed; 0 mention nào do GLiNER+linker tự link) |
| Unresolved | 150 (135 trong scope) |
| Candidate pairs có cue | 14 |
| Gọi Qwen | 14 (tất cả, kể cả khi endpoint unresolved - lãng phí) |
| Qwen valid=true / false | 6 / 8 |
| Validator accepted | 0 |
| Official edges | 0 |

## 4. Tỷ lệ link 23/173 có thấp giả tạo không?

**Không đáng kể.** Loại hết mention ngoài domain chỉ giảm mẫu số từ 173 xuống 158: tỷ lệ link 13,3% -> 14,6%. Tính riêng mention PERSON/ORG/BANK trong domain: 17 linked (14 ORG + 2 BANK + 1 PERSON) / 122 = 13,9%.
Nguyên nhân chính là độ phủ registry: 135 mention trong domain chưa link, phần lớn là người (54) và công ty/ticker không có trong seed.
Lưu ý: 37 mention GOVERNMENT_AGENCY (Bộ Xây dựng 13 lần, HĐND...) là đối tượng hợp lệ của SANCTIONED_BY/PROSECUTED_BY nhưng đa số không liên quan đồ thị doanh nghiệp.
Mã chứng khoán viết hoa (KSB, TCB, MBB...) được GLiNER gán BANK: đây chỉ là chuỗi viết hoa, không phải ticker đã xác minh.

## 5. Hệ quả cho thiết kế Phase 4

- Cần registry tăng trưởng từ bài báo + nguồn định danh phụ, và mention->entity phải tách bảng (Task B).
- Cho phép candidate với endpoint PROVISIONAL, nhưng chỉ official khi endpoint đủ rõ (Task C1).
- Gắn cue vào endpoint theo cấu trúc câu (Task C2) và dedupe alias cùng người.
- Lọc trước LLM: không gọi Qwen khi endpoint ngoài scope / candidate trùng (Task C5).

## 6. Sau Phase 4 (cùng 9 bài, mã cuối; chi tiết số liệu: `phase4_real_news_results.md`)

| Chỉ số | Phase 3 (baseline) | Phase 4 registry seed | Phase 4 registry provider |
|---|---|---|---|
| Entity registry (hàng) | 19 seed | 15 -> 180 (PROVISIONAL) | 2.267 VERIFIED (identity-only) -> 2.416 |
| Mentions | 173 | 392 | 395 |
| Trong scope | 158 | 342 | 345 |
| Linked tổng | 23 (14,6% trong scope) | 304 (88,9%) toàn PROVISIONAL | 292 (84,6%): 17 VERIFIED (4,9%) + 275 PROVISIONAL |
| Candidate | 14 | 8 | 8 |
| Candidate sai rõ ràng (đọc tay) | >=7 (Ge Jun/Intel...) | 0 | 0 |
| Cạnh candidate-only (có bằng chứng, chờ duyệt) | 0 | 7 | 7 |
| Cạnh official | 0 | 0 | 0 |

- Mentions tăng gấp đôi phần lớn do GLiNER chạy cấp câu (xem `phase4_real_news_results.md` §6.4), không phải do tìm đúng nhiều thực thể hơn: **không so sánh trực tiếp tỷ lệ link**.
- 0 official trên 9 bài là kết quả của chính sách (endpoint tổ chức phải VERIFIED): Viettel, Ngân Lượng, China Railway Sixth Group Việt Nam không có trong nguồn định danh. 5 quan hệ đúng ở §1 nay xuất hiện thành candidate-edge có bằng chứng.
- Lỗi đã sửa tương ứng §2: (1) cue gắn với endpoint theo cấu trúc câu (mẫu quan hệ trên câu đã che mention) -> hết Ge Jun/Intel; (2) alias trong ngoặc gộp vào đầu mention -> hết candidate cho "Mr Pips"; (3) sửa ranh giới span (chức danh, HĐQT/HĐTV, "Công ty TNHH ... Việt Nam", "- CTCP"); (4) trạng thái LLM chỉ được làm chặt thêm, HISTORICAL/ENDED của LLM cần dấu hiệu từ vựng; (5) `article_id` trong candidate, mã lý do thống nhất `reasons.py`; (6) `confidence` bị bỏ, điểm số tách `ner_score`/`linking_score`/`relation_score` (null khi không có).
- Ghi chú: sau khi đổi schema, `vckg.diagnostics` đọc dữ liệu Phase 3 qua lớp tương thích; mã NEGATED_RELATION chỉ tính khi verdict `valid=true` (4 lần ở bảng cũ là Qwen gán DENIED cho verdict `valid=false`).
