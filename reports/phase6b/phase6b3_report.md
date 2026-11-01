# Phase 6B.3 - Automated entity grounding (60 bài; deterministic; không Qwen, không crawl)

Không có gold: tăng số PASS KHÔNG phải bằng chứng accuracy tăng. Staging only: registry gốc, Neo4j, official edges không đổi. Hard validation của hybrid QA không bị thay đổi (chạy lại đúng validator 6B.2; có kiểm tra hồi quy: chạy mặc định vẫn cho đúng 105/10/2).
Code: `entity_linking/article_grounding.py` (rule A/B/C/P, tái dùng `RegistryStore`, `ARTICLE_GROUNDED`, `grounding.org_grounded`), `validation/grounding_qa.py` (runner). Outputs: `data/experiments/phase6b/grounding/` (registry staging, promotions.jsonl, overlay.json, hybrid_qa/), `reports/phase6b/grounding/` (identity_cause_analysis.json, identity_blocked_endpoints.csv, comparison.json, hybrid_qa/).

## 1. 53 candidate bị chặn chỉ vì IDENTITY_NOT_GROUNDED (65 endpoint)
Phân loại bằng dry-run các luật trên registry gốc (trước khi áp dụng thay đổi):
| nguyên nhân chính của candidate | số candidate | endpoint |
|---|---|---|
| Tổ chức chưa niêm yết, không có tên đầy đủ/nguồn định danh trong bài | 14 | 16 |
| Span NER bị cắt ("Công ty Cổ phần Chứng khoán An", "... TP.") | 12 | 10 |
| Tên viết tắt có tên đầy đủ trong cùng bài (ABBank, Novaland...) | 6 | 8 |
| Mention NER điểm thấp, không link được | 6 | 10 |
| Tên người ngắn/mơ hồ ("Bình", "Ngọc") | 5 | 5 (+2 chất lượng tên) |
| Tên chung / ngoài miền ("Việt Nam", "Xây dựng") | 5 | 6 |
| Tên pháp nhân đầy đủ nhưng chưa có registry | 3 | 4 |
| BondIssue chưa đủ cụ thể (không có số tiền/mã đọc được) | 2 | 2 |
| Người: tên đầy đủ + chức vụ/tổ chức trong câu | (trong nhóm khác) | 2 |
(Mỗi candidate gán một nguyên nhân theo thứ tự ưu tiên: nguyên nhân không giải quyết được trước.)

## 2. Cách grounding (không nâng lên VERIFIED, không gộp xuyên bài)
- A: tên pháp nhân đầy đủ (dạng pháp lý + tên riêng viết hoa, cho phép từ ngành viết thường) -> ARTICLE_GROUNDED nếu không bị cắt, NER >= 0.8, không trùng/gần trùng entity khác (cả fuzzy >= 93).
- B: viết tắt chỉ được coi là alias khi có định nghĩa trong ngoặc cạnh tên đầy đủ VÀ được chứng minh (cạnh mã sàn, hoặc là một đoạn tên, hoặc bắt đầu bằng chữ cái đầu của tên riêng). "(Hàn Quốc)" không phải alias.
- C: tên ngắn là đoạn liền kề của đúng MỘT tên đầy đủ đã grounded trong cùng bài, và registry không có thực thể khác chứa tên đó (AMBIGUOUS_WITH_REGISTRY). Đoạn nằm giữa tên, hoặc khớp nhiều tên (mẹ/công ty chị em) -> giữ nguyên.
- P: người: họ tên >= 2 từ viết hoa, id phạm vi một bài, có từ chỉ chức vụ gần tên (hoặc "ông/bà" + tổ chức cùng câu), không tên trùng khác id trong bài, không phải phần tên quỹ/tổ chức.
- B và C chỉ tạo overlay (bài, span) -> entity id; không merge entity trong registry (org được khóa theo tên toàn corpus nên merge sẽ kéo các bài khác). Mỗi quyết định lưu id gốc, id đã resolve, bằng chứng + span, phương pháp, điều kiện đã kiểm tra, xung đột (`promotions.jsonl`; set_status ghi vào lịch sử registry staging).
- Toàn bộ 60 bài: 43 PROMOTE (16 tên pháp nhân, 27 người) + 69 RESOLVE_TO (59 theo định nghĩa trong ngoặc, 10 theo tên ngắn duy nhất); 1.427 mention giữ nguyên.

## 3. Kết quả trên đúng 60 bài (A/B/C của 6B.1)
| | trước (6B.2) | sau grounding |
|---|---|---|
| C: PASS / QUARANTINE / REJECT | 10 / 105 / 2 | 11 / 104 / 2 (117 candidate; 1 candidate gộp do ABBank và An Bình cùng entity) |
| Trong 53: identity đã giải quyết | - | 8 |
| ...-> PASS | - | 1 (ABBank PARTNERS_WITH ABS, cả RULE và LLM) |
| ...-> QUARANTINE SEMANTIC_ONLY_CLEAN | - | 5 |
| ...-> QUARANTINE NON_OFFICIAL_STATUS | - | 2 |
| ...-> vẫn bị chặn danh tính | - | 45 |
| PASS theo RULE_ONLY / LLM_ONLY / BOTH | 4 / 0 / 6 | 4 / 0 / 7 |
| Staging: cạnh validated / entity unique / loại quan hệ | 10 / 17 / 4 | 11 / 19 / 5 (thêm PARTNERS_WITH) |
Candidate ngoài nhóm 53 không đổi quyết định (51 QUARANTINE, 10 PASS, 2 REJECT giữ nguyên).
Thực tế: chỉ 8/53 (15%) được giải quyết và 1 PASS. Phần lớn danh tính bị chặn vì tổ chức không niêm yết không có nguồn định danh, span NER bị cắt, mention điểm thấp - những trường hợp bài báo không cung cấp đủ bằng chứng nên giữ QUARANTINE.

## 4. Ví dụ grounding hợp lệ
- Công ty TNHH Đầu tư và Thương mại Thiên Hải; CTCP Quốc tế Việt Thái: tên pháp nhân đầy đủ -> ARTICLE_GROUNDED (rule A).
- "Ngân hàng TMCP An Bình (ABBank)" -> mọi "ABBank" trong bài trỏ về entity An Bình (rule B); "Novaland" <- "Tập đoàn Đầu tư Địa ốc No Va (Novaland, HOSE: NVL)"; "TTC Land" <- "CTCP Địa ốc Sài Gòn Thương Tín (TTC Land, ...)".
- Người: Bùi Thành Nhơn, Bùi Xuân Huy (Novaland) có chức vụ trong câu, id vẫn gắn với đúng một bài.
- Tên ngắn duy nhất (rule C): "Công ty CP Nextpay" -> "Công ty CP Tập đoàn chuyển đổi số Nextpay"; "Hải Phát" -> "CTCP Đầu tư Hải Phát".

## 5. Còn mơ hồ / rủi ro false-merge
- Collision: 0 self-loop sau overlay, 0 promotion người không thuộc đúng bài, 0 merge người xuyên bài, 0 org promoted bị nhiều bài dùng chung.
- 9 resolution có thực thể khác trong registry chứa tên ngắn: toàn bộ là "Sabeco" (trỏ về pháp nhân đã VERIFIED nhờ định nghĩa trong bài, nhưng registry cũng có "Quản lý quỹ Sabeco"). Cần người duyệt nếu dùng.
- Rủi ro khác thấy khi đọc tay: "Moller Capital" (rút gọn của "A.P. Moller Capital"), "Mitorient"/"Cargill" -> tên đầy đủ có "Pte"/"Inc": đúng nhưng chỉ nhờ độ duy nhất trong bài; các candidate này nằm ở SEMANTIC_ONLY_CLEAN/NON_OFFICIAL_STATUS, không PASS.
- Lỗi phát hiện và đã sửa trong lúc phát triển (có test): "(Hàn Quốc)" bị coi là alias; địa danh "Đông Anh"/"Hưng Thịnh" bị gán sang tên dài hơn; "quỹ Terry Fox" bị coi là người; so sánh gần-trùng bị bỏ qua khi đã có khớp chính xác.
- Chưa giải quyết: span NER bị cắt (10 endpoint) cần sửa ở bước NER; mention điểm thấp; người tên một từ; BondIssue chưa đủ cụ thể.

## 6. Kiểm thử
pytest 215 passed (11 test mới: tên pháp nhân chưa có registry, alias trong bài, người tên đầy đủ rồi tên ngắn, trùng tên hai công ty/hai bài, tên một từ, span bị cắt, mẹ/con, tên gần giống, xung đột xuyên bài, rerun idempotent), ruff sạch. Rerun runner không `--fresh`: không phát sinh set_status mới, kết quả giống hệt.

## 7. Lệnh chạy độc lập
```powershell
cd T:\VietnamCorporateGraph
.\scripts\run-job.ps1 -Name p6b3-grounding -Command ". .\scripts\enter-project.ps1; uv run python -m vckg.validation.grounding_qa --fresh"
.\scripts\status-phase5.ps1
```
Job `p6b3-grounding` đã COMPLETED (exit 0).

## 8. Đề xuất bước tiếp theo
1. Sửa span NER bị cắt (tên pháp nhân + "TP.HCM", "An Bình") trước khi grounding: 12 candidate bị chặn vì lý do này.
2. Cho người duyệt 8 resolution mới + review_sample_40 để có nhãn thật; chưa có nhãn nào nên chưa thể đo độ đúng của grounding.
3. Cân nhắc nguồn định danh hợp lệ cho tổ chức chưa niêm yết (sau khi rà điều khoản) - đây vẫn là nút thắt lớn nhất.
