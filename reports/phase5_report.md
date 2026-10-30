# Phase 5 - Báo cáo (30/10/2026)

Số liệu chi tiết tự sinh: `phase5_benchmark.md/json` (`python -m vckg.phase5_report`), `phase5_false_negatives.md`, `phase5_baseline_kpis.json`.
**Không có gold nên Precision/Recall/F1 = NOT EVALUATED.** Mọi "đúng/sai" là đọc tay, không phải đánh giá.

## 1. Kết quả (cùng mã cuối, 207 bài)

| Nhóm | Bài | Official unique | Candidate unique | Official/bài | Loại official |
|---|---|---|---|---|---|
| dev44, Phase 4 | 44 | 4 | 9 | 0,09 | 3 |
| dev44, Phase 5 (đã dùng để chỉnh mẫu, không độc lập) | 44 | 15 | 7 | 0,34 | 7 |
| holdout19, Phase 4 | 19 | 0 | 5 | 0 | 0 |
| holdout19, Phase 5 (chỉ chạy lại, không chỉnh) | 19 | 5 | 4 | 0,26 | 4 |
| Bài mới, targeted (108) | 108 | 26-28* | 15 | ~0,25 | 7 |
| Bài mới, control ngẫu nhiên (36) | 36 | 0 | 5 | 0 | 0 |

*Bộ 144 bài chạy lại lần cuối cho 26 cạnh official (28 ở lần trước trước khi thêm cờ `SPAN_BOUNDARY_SUSPECT`); số chuẩn là của `phase5_benchmark.md`.
Tổng đồ thị Neo4j (3 nhóm gộp, gộp người liên-run theo tên + cùng tổ chức): **74 domain entity nodes, 44 cạnh official, 8 loại quan hệ, 31 cạnh candidate (namespace riêng)**.
Đã quan sát official: CHAIR_OF, CEO_OF, BOARD_MEMBER_OF, OWNS_SHARES_IN, ISSUED_BOND, SUBSIDIARY_OF, SANCTIONED_BY, PROSECUTED_BY. Candidate có thêm FOUNDED, PARTNERS_WITH, ACQUIRED. Chưa thấy: LENDS_TO, JOINT_VENTURE_WITH (official).
Control: 36 bài, 0 cạnh official -> yield trên báo chí phổ thông gần như 0; kết quả targeted KHÔNG ngoại suy cho toàn bộ báo chí. Bài targeted lệch nguồn (Vietstock 68/108, cho 25 cạnh), Báo Đầu tư/VnEconomy 0.

## 2. Việc đã làm
- A: commit Git local, snapshot bất biến `data/outputs/snapshots/phase4`, `metrics.py` (KPI chuẩn, cạnh unique, không đếm nguồn nhiều lần).
- B: `ARTICLE_GROUNDED` (`entity_linking/grounding.py`); thực thể grounded: 95 (dev), 60 (holdout), 362 (bài mới). Viettel, Ngân Lượng, China Railway có test và thành official khi tên đủ.
- C: phân tích false negative; mẫu mới (danh sách đối tượng, ngoặc, đồng thời, đại từ, đối tượng bị lược, nhiều chức vụ), BondIssue, gộp span bị tách, lan truyền mention lặp trong bài, mở rộng acronym trong bài; prompt Qwen v5 dựa trên lỗi quan sát.
- D: `crawlers/discovery.py` (10 chủ đề, ranking, nhóm trùng tiêu đề, targeted 75%/control 25%, manifest có subset/nguồn/ngày/chủ đề/điểm/lý do). 200 bài chọn, 199 tải được, 144 dùng (108 targeted + 36 control). Crawl theo robots.txt, 2 s/host.
- E: `review.py` (CLI + CSV, lịch sử append-only, idempotent, ACCEPT bị chặn khi định danh PROVISIONAL / thiếu bằng chứng / trạng thái không official). **Chưa có quyết định người duyệt nào** (0 cạnh HUMAN_VERIFIED).
- F: `evaluation.py` (NER P/R/F1 theo loại, linking accuracy/false merge, candidate recall, direction/status accuracy, official precision, recall chỉ trên bài `full_article`), `annotation-export-full`, cột `split`. NOT EVALUATED vì cột gold trống.
- G: Neo4j Community 2026.10.1 + JDK 21 trong `runtime\`, localhost, ràng buộc unique, import idempotent (chạy 2 lần: số nút/cạnh không đổi), candidate cách ly, truy vấn Cypher mẫu, export projection person-person / company-company (GraphML, CSV, nhãn derived).

## 3. Recall (cue coverage, KHÔNG phải recall)
Câu có từ khóa và >=1 mention có candidate: ROLE 20%, OWN 12%, SUBSID 11%, ACQUIRE 1%, LEND 1%, BOND 6%, PARTNER 14%, SANCTION 4%, PROSECUTE 16% (207 bài). Nguyên nhân câu không có candidate (heuristic): chủ ngữ ẩn/liên câu 234, thiếu cặp thực thể 174, generator chưa có mẫu 191, modality không phải FACT 195, span/loại sai 139, cue chung (lãi suất cho vay...) 39. Nhiều câu cue không chứa quan hệ thật; không thể tách nếu không có gold.

## 4. Chi phí
Qwen: lần chạy cuối hầu hết là cache hit (cache khóa theo prompt v5). Trung bình ~1,2-1,3 s/lần gọi khi chạy nguội, ~0,45 s/bài toàn pipeline. 144 bài nguội: 79 lần gọi live.

## 5. Khả năng đạt KPI 11/11/2026 (đánh giá thực tế)
Hiện 74 node, 44 cạnh official, 8 loại quan hệ (mục tiêu 2.000 / 5.000 / 10). Yield targeted ~0,25 cạnh/bài, control ~0. Để có 5.000 cạnh cần ~20.000 bài targeted, vượt xa thời gian còn lại (12 ngày) và giới hạn crawl lịch sự; **không đạt được với phương pháp hiện tại**. Không hạ chuẩn bằng cạnh co-occurrence hay nhận candidate hàng loạt. Đề xuất: giảm phạm vi mục tiêu (số cạnh có bằng chứng người duyệt, chất lượng đo bằng gold), hoặc nhắm vào loại bài có yield cao (tin bổ nhiệm/giao dịch cổ đông Vietstock) và tăng recall mẫu quan hệ trước khi mở rộng crawl.

## 6. Hạn chế
- Không có gold; Precision chưa biết. Cạnh official hiện dựa vào mẫu + Qwen; có ít nhất các rủi ro đã thấy khi đọc tay: người nhắc tới như thân nhân ("Bà Lương là vợ ông Đỗ Quý Hải, Chủ tịch HĐQT HPX" đúng, nhưng chỉ đúng với ông Hải), tên bị cắt, "Trương Mỹ Lan CHAIR_OF" là chức vụ cũ trong bài thi hành án (nên là HISTORICAL; Qwen và luật đã gán FACT).
- Một số "cạnh official" thực chất mô tả thời điểm quá khứ trong bài (ví dụ cựu Tổng giám đốc); cần review.
- Dung lượng ổ C: 10,55 GB trống (trước phiên này 34,4 GB). Mọi đường dẫn dự án nằm ở T:. Thư mục `%TEMP%` của C: tăng nhưng tôi chưa xác định tiến trình nào; không phải tiến trình dự án (TEMP của dự án đặt ở T:). Cần kiểm tra thủ công (Disk Cleanup); tôi không xóa gì.
