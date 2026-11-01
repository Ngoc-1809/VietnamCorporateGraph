# Phase 6B.4 - NER span recovery (60 bài; deterministic; không đổi model, không Qwen, không crawl)

Không có gold: tăng PASS KHÔNG phải bằng chứng accuracy tăng. Staging only (registry gốc, Neo4j, official edges không đổi). Hard validation không bị sửa.
Code: `ner/span_recovery.py`, `validation/span_qa.py` (runner), thay đổi nhỏ: `article_grounding.ground_article(confirmed_complete=...)`, `hybrid_qa.apply_overlay` nhận overlay dạng span, `candidate_fusion` lưu span gốc.
Outputs: `data/experiments/phase6b/span_recovery/` (fixes.jsonl, decisions.jsonl, overlay_span_recovery.json, registry staging, before_6b3/, after/), `reports/phase6b/span_recovery/` (span_diagnostics.csv: article, URL, text, span, context, nguyên nhân, có sửa được không; comparison.json).

## 1. Nguyên nhân của 12 candidate (thực tế là 8 endpoint)
| Endpoint | Nguyên nhân | Phân loại | Sửa an toàn? |
|---|---|---|---|
| "ABBank" (2 bài), "Fed" | Span ĐẦY ĐỦ; heuristic "sau tổ chức là từ viết hoa" báo sai vì liền sau là tên người ("Chủ tịch ABBank Vũ Văn Tiền") | lỗi của bộ dò, không phải NER | Có: CONFIRMED_COMPLETE (không đổi span) |
| "CTCP Đầu tư" -> "CTCP Đầu tư Lepus" | alias chung trong từ điển registry thắng NER khi merge | lỗi mention-merge (dictionary override) | Có (LEGAL_FORM_RUN) |
| "Xây dựng" -> "Xây dựng Hạ tầng Crystal"; "Xây dựng"/"Việt Nam" trong "Công ty TNHH Thương mại và Xây dựng Việt Nam Korea" | alias chung của registry chiếm span bên trong tên riêng | mention-merge | Có (lặp lại trong bài / dạng pháp lý) |
| "Công cổ phần Nhất" -> "Công cổ phần Nhất Phong Vận" | GLiNER dừng giữa tên | GLiNER | Có (dạng pháp lý, dù gõ thiếu "ty") |
Không có ca nào do tách câu, chuẩn hóa văn bản hay chuyển offset (đã kiểm tra: text NFC, offset khớp). Toàn bộ 60 bài: 158 mention bị báo nghi cắt; 72 EXTEND (66 từ điển + 6 GLiNER), 16 CONFIRMED_COMPLETE, 109 giữ nguyên vì không đủ bằng chứng.

## 2. Quy tắc khôi phục và quality gates
Chỉ mở rộng trên chuỗi liền kề viết hoa (+ "và"/"&" giữa hai token riêng, từ ngành viết thường nguyên cụm như "hạ tầng"), cùng một câu, <= 6 token; mở rộng trái chỉ tới điểm bắt đầu dạng pháp lý; bằng chứng bắt buộc: bắt đầu bằng dạng pháp lý hoặc chuỗi đầy đủ lặp >= 2 lần; ranh giới sau span phải là dấu câu hoặc từ chức năng đã biết; không nuốt người/chức danh/thực thể khác; lõi tên phải có token không chung ("Việt Nam", "Xây dựng", "Đông Anh" không bao giờ thành pháp nhân; "Việt Nam và Lào" không thành một tên); text không NFC bị từ chối; tên một từ của người không đổi; chuỗi trùng một mention PERSON bị loại. Mỗi sửa lưu span gốc/mới, nguyên nhân, bằng chứng, các kiểm tra, phiên bản. Không dùng fuzzy matching.
Lỗi phát hiện và đã sửa trong lúc làm (có test): run bị dừng ở từ ngành viết thường ("CTCP Đầu tư và Xây"), từ ngành bị tách thành mảnh trùng từ chức năng ("tại"), "Công ty và UBND tỉnh Khánh Hòa" bị nối, "Việt Nam và Lào" bị nối, "Shark" -> "Shark Bình" (tên người), tên bị cắt tại từ không rõ ranh giới.

## 3. Kết quả QA trước/sau (cấu hình 6B.3 chạy lại cùng code vs có span recovery + grounding lại)
| | 6B.3 | 6B.4 |
|---|---|---|
| Mention nghi bị cắt (60 bài) | 158 | 79 (16 là báo động giả đã xác nhận đầy đủ) |
| 12 candidate bị chặn vì span (theo dõi được 10 sau gộp trùng) | 10 chặn | 1 PASS, 3 SEMANTIC_ONLY_CLEAN, 5 vẫn chặn danh tính, 1 còn bị SPAN_BOUNDARY_SUSPECT của hard validation (không đổi) |
| C: PASS / QUARANTINE / REJECT | 11 / 104 / 2 | 13 / 102 / 2 |
| PASS theo RULE_ONLY / LLM_ONLY / BOTH | 4 / 0 / 7 | 6 / 0 / 7 |
| Staging: cạnh / entity unique / loại quan hệ | 11 / 19 / 5 | 13 / 23 / 5 |
- PASS mới: "CTCP Tập đoàn Masan sở hữu CTCP Đầu tư Lepus" (98% vốn) và "Đinh Hữu Thật CEO_OF CTCP Sunshine Tây Hồ".
- Thêm 5 SEMANTIC_ONLY_CLEAN (không tự PASS): ví dụ CTCP Chứng khoán ASEAN -> HTM, Phùng Minh Tuyến -> Xây dựng Hạ tầng Crystal, Nguyễn Văn Lực -> Việt Nam Korea.
- Candidate ngoài nhóm bị ảnh hưởng: 86 QUARANTINE, 11 PASS, 2 REJECT giữ nguyên quyết định.
- Identity collision mới: 0 self-loop. Thay đổi trên entity trước đây đã grounded: **1** (mention "Công ty CP Nextpay" từng trỏ về "... Tập đoàn chuyển đổi số Nextpay"; sau khi tìm thêm "Công ty CP Nextpay Việt Nam" trong bài có hai tên dài, nên luật tên ngắn lùi về mơ hồ - kết quả thận trọng đúng thiết kế, nhưng là một resolution bị mất).

## 4. Không sửa được an toàn
109 mention giữ nguyên: 38 không có dạng pháp lý và tên đầy đủ không lặp lại; 35 tên mở rộng vẫn chung; 30 không rõ ranh giới sau span; 16 bị chặn bởi người/thực thể khác. Hai ca đáng ghi nhận: (1) hard validation vẫn đánh dấu SPAN_BOUNDARY_SUSPECT cho dạng "tổ chức + tên người" (ABBank, Fed): heuristic dùng chung `reasons.suspect_span` có cùng lỗi báo động giả; tôi KHÔNG đổi hard validation như yêu cầu, chỉ nêu đề xuất. (2) Một số mở rộng "Sunshine -> Sunshine Homes/Center/Bay Retreat" là các pháp nhân khác nhau theo câu gốc; đúng theo văn bản nhưng cần người duyệt nếu dùng.

## 5. Kiểm thử
pytest 228 passed (13 test mới), ruff sạch. Gồm: báo động giả tổ chức+người, GLiNER cắt tên pháp nhân, từ điển chung thắng NER, từ ngành viết thường và nuốt mention chung, tên chung không thành pháp nhân, "và" không nối hai thực thể, ranh giới không rõ, tên người không đổi/xung đột kiểu, không qua dòng/câu và NFC, mention hiệu chỉnh tái dùng entity + idempotent, overlay span chỉ trong evidence, rerun xác định.

## 6. File thay đổi
Mới: `src/vckg/ner/span_recovery.py`, `src/vckg/validation/span_qa.py`, `tests/test_span_recovery.py`, `reports/phase6b/phase6b4_report.md`, outputs ở trên. Sửa nhẹ: `entity_linking/article_grounding.py`, `validation/hybrid_qa.py`, `relation_extraction/candidate_fusion.py`, `relation_extraction/discovery_benchmark.py` (tham số registry cho `_canon_fn`).

## 7. Lệnh chạy độc lập
```powershell
cd T:\VietnamCorporateGraph
.\scripts\run-job.ps1 -Name p6b4-span-recovery -Command ". .\scripts\enter-project.ps1; uv run python -m vckg.validation.span_qa"
.\scripts\status-phase5.ps1
```
Job `p6b4-span-recovery` đã COMPLETED (exit 0); thêm `--fresh` để dựng lại registry staging.
