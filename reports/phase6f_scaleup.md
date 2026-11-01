# Phase 6F - Scale-up có kiểm soát: 50 bài mới (20 + 20 + 10)

Staging only. Không đụng Neo4j, registry gốc, cạnh official, hard validation, prompt; không tải model; không tạo gold. **PASS không phải gold và không cho biết precision (NOT EVALUATED).**

## 0. CẢNH BÁO NGHIÊM TRỌNG: vi phạm rate limit trên vietstock.vn (phát hiện sau khi chiến dịch đã chạy xong)
- Bộ kiểm tra khoảng cách request ở Phase 6F nhóm theo `scheme://host`, và throttle cũng khóa theo `scheme://host`. Vietstock phục vụ bài qua `http://` rồi chuyển hướng 301 sang `https://`; hop chuyển hướng (và cả `robots.txt`) được gửi gần như ngay lập tức vì `https://vietstock.vn` bị coi là "host khác".
- Kiểm toán lại log request theo **tên host** (`reports/phase6f/http_spacing_audit.json`): trên 143 request có **53 vi phạm yêu cầu >= 2,5 s**, **toàn bộ ở vietstock.vn** (scale01 19/52, scale02 26/55, scale03 8/36 request của job), khoảng cách nhỏ nhất 0,024 s (hop `http -> https`). **CafeF: 0 vi phạm** (khoảng cách nhỏ nhất 2,49 s).
- Trạng thái `http_spacing_ok=True` trong `status.json` của các job là **sai (dương tính giả do lỗi nhóm khóa)**; tôi không sửa lịch sử, báo cáo này là bản đúng. Tải thực tế lên vietstock.vn vẫn thấp (mỗi bài: hai request sát nhau rồi nghỉ ~2,5 s) nhưng **điều kiện bắt buộc "tối thiểu 2 giây/host" đã không đạt đối với Vietstock**.
- Đã sửa mã (sau chiến dịch, không crawl thêm): throttle và checker khóa theo tên host (bỏ `www.`, gộp http/https), thêm 2 test hồi quy (285 passed). Pilot 6D (20 bài, không có log request) đi cùng đường mã nên nhiều khả năng bị cùng lỗi với Vietstock.
- **Cần bạn quyết định**: giữ hay loại dữ liệu Vietstock của scale01-03 (26 bài) và pilot6d (8 bài). Tôi không xóa gì (quy tắc không xóa dữ liệu). Nếu muốn loại cả job khỏi aggregate: `python -m vckg.graph.aggregate disable --source job:scale01` (cũng loại bài CafeF cùng job). Không crawl thêm cho đến khi bạn xác nhận.

## 1. Tuân thủ nguồn (chi tiết: `reports/phase6f/compliance.md`, `config/crawl_compliance.yaml`)
CafeF và Vietstock: robots.txt cho phép bài viết, không tìm thấy điều khoản hạn chế truy cập tự động (không có trang ToS nào được liên kết; rủi ro điều khoản không công bố vẫn còn). **VnEconomy và Báo Đầu tư không được crawl** (cần đồng ý bằng văn bản cho việc sử dụng/đăng lại nội dung). Pilot từ chối nguồn `cleared: false`. Hệ quả: chỉ 2 nguồn (CafeF 24 bài, Vietstock 26 bài); trần 60%/nguồn/job không phải nới lần nào (`cap_lifted` = 0).

## 2. Thực thi
| Job | Bài mới | Xử lý OK/lỗi | Ứng viên luật / Qwen thô | Cạnh candidate duy nhất | QA PASS / QUAR / REJ | Qwen live | Thời gian |
|---|---|---|---|---|---|---|---|
| scale01 | 20 | 20 / 0 | 15 / 44 | 40 | 3 / 37 / 0 | 51 | 14:08:30-14:11:52 (xử lý bài 112 s, Qwen 86 s) |
| scale02 | 20 | 20 / 0 | 6 / 40 | 31 | 1 / 29 / 1 | 51 | 14:11:53-14:18:44 (gồm gián đoạn, xử lý 109 s, Qwen 82 s) |
| scale03 | 10 | 10 / 0 | 3 / 11 | 12 | 2 / 9 / 1 | 28 | 14:18:44-14:20:22 (xử lý 35 s, Qwen 18 s) |
| **Tổng** | **50** | **50 / 0** | 24 / 95 | 83 | **6 / 75 / 2** | **130 / 160** | cache hit 0, lỗi Qwen 0 |
- 50 bài đều mới thật: 0 trùng với staging trước chiến dịch (294 -> 344 bài), hàng cũ không đổi (so hash), 0 trùng giữa các job; 0 thiếu hụt quota, 0 trùng URL/nội dung, 0 robots/loại chất lượng.
- **Gián đoạn**: lúc 14:13, giữa lúc crawl scale02 (14/20), tiến trình chiến dịch và Ollama bị tắt bởi sự kiện đóng cửa sổ console (`forrtl: error (200) ... window-CLOSE event`; nguyên nhân gốc chưa xác định). Bật lại Ollama rồi `-Resume`: kế hoạch crawl được dùng lại, không tải lại 14 bài, không xử lý lại bài DONE; một lần khởi động lại bị khóa nhầm do PID cũ chưa dọn xong, lần sau chạy bình thường. Không có lỗi dữ liệu.
- Chạy tuần tự trong một tiến trình, khóa GPU, mỗi job registry riêng, Qwen 130/160 (đã trừ ngân sách theo từng job). Chiến dịch COMPLETED (exit 0), aggregation chạy sau cùng. Wrapper cuối PID 15196, tiến trình chiến dịch PID 4212.

## 3. Tăng trưởng aggregate (Phase 6E; hash `c22f294ec5911f26` -> `2c273cdfe5f5d770`)
| Chỉ số | Trước | Sau |
|---|---|---|
| Domain node tầng đã kiểm (LEGACY_OFFICIAL ∪ QA_PASS) | 80 | **90** (QA_PASS 6 -> 17 node; 1 node chung với legacy: Novaland `org:dau-tu-dia-oc-no-va`) |
| Node mọi tầng | 178 | 254 |
| Cạnh QA_PASS | 4 | **10** (+6) |
| Cạnh QUARANTINE | 40 | **115** (+75): HARD_BLOCK 54, INSUFFICIENT_EVIDENCE 35, SEMANTIC_ONLY_CLEAN 23, NON_OFFICIAL_STATUS 3 |
| Cạnh REJECT | 0 | 2 |
| LEGACY_OFFICIAL / LEGACY_CANDIDATE | 44 / 31 | 44 / 31 (không đổi) |
| Evidence duy nhất | 144 | 236 (+92, không có evidence bổ sung vào cạnh cũ: 0 cạnh trùng) |
| Bài có evidence | 72 | 94 (+22 trong 50 bài mới; 28 bài mới không sinh ứng viên nào) |
| Loại quan hệ | tầng đã kiểm 8, mọi tầng 11 | 8 / 12 (QA_PASS 4 -> 5: thêm ISSUED_BOND) |
| Connected components (hợp đã kiểm) | 35 (lớn nhất 4) | 39 (lớn nhất 4); mọi tầng 71/11 -> 84/14 |
| Identity collisions chưa giải quyết | 1 | 3 (cùng loại SAME_NAME_PERSONS_UNMERGED: "hà đức hiếu", "lý xuân tuyến", "trịnh văn tuệ"; không gộp) |
| Duplicate bị loại | 0 | 0 |
- Cạnh mới so với baseline: toàn bộ 83 cạnh scale là cạnh mới (không trùng edge_id với nguồn khác); PASS mới 6, không cạnh official nào.
- Triple xuất hiện ở nhiều tầng: 6 trường hợp (không hợp nhất, không nâng cấp), đáng chú ý: (a) `Tổng Công ty Đầu tư và Kinh doanh vốn nhà nước OWNS_SHARES_IN Tổng Công ty Thủy sản Việt Nam` vừa là QA_PASS (FACT, **LLM-only**) vừa là QUARANTINE (DENIED, cùng job) và LEGACY_CANDIDATE (PLANNED): **mâu thuẫn trạng thái, cần người xem**; (b) `Bùi Cao Nhật Quân CHAIR_OF Tập đoàn Đầu tư Địa ốc No Va`: LEGACY_OFFICIAL (FACT) với hai bản QUARANTINE (DENIED, FACT) ở scale02.
- Sáu cạnh QA_PASS mới (cần duyệt thủ công): Nguyễn Thanh Tùng CHAIR_OF Vietcombank; NVL ISSUED_BOND (trái phiếu 300 triệu USD, kỳ hạn 16/07/2028, 5,25%); SCIC OWNS_SHARES_IN Tổng công ty Thủy sản VN (xem cảnh báo); Dương Văn Bắc OWNS_SHARES_IN NVL; Đỗ Tiến Dũng CHAIR_OF CTCP Dịch vụ Ô tô Hàng Xanh; Đỗ Tuấn Anh CEO_OF KDI Holdings (HISTORICAL). Theo phương pháp: BOTH 3, RULE 2, LLM-only 1 (không có PASS nào chỉ do Qwen mà không qua luật cứng).

## 4. PASS trên mỗi bài (mô tả, mẫu nhỏ, không so sánh có ý nghĩa thống kê)
| Nhóm | Bài | PASS | PASS/bài | Bài có PASS |
|---|---|---|---|---|
| **Scale-up 6F (tổng)** | 50 | 6 | **0,12** | 6 (12%) |
| - CafeF | 24 | 3 | 0,125 | 3 |
| - Vietstock | 26 | 3 | 0,115 | 3 |
| - scale01 / scale02 / scale03 | 20 / 20 / 10 | 3 / 1 / 2 | 0,15 / 0,05 / 0,20 | |
| - có khớp định danh registry trong tiêu đề/slug (xếp hạng cộng điểm) | 13 | 0 | 0 | 0 (5 bài có ứng viên) |
| - không khớp | 37 | 6 | 0,16 | 6 |
| - theo chủ đề (số bài / PASS) | bond 12/3, mna 6/1, board 7/1, appointment 2/1, credit 7/0, prosecution 4/0, shareholding 2/0, sanction 2/0, subsidiary 2/0, none 6/0 | | | |
| Pilot 6D (20 bài) | 20 | 4 | 0,20 | 2 |
| 6B.4 (60 bài, đã tinh chỉnh trên chúng) | 60 | 13 | 0,22 | |
Nhận xét có giới hạn: PASS/bài của bài mới (0,12) thấp hơn pilot (0,20) và 6B.4, nhưng chênh lệch nằm trong dao động của mẫu 20-50 bài, bài khác chủ đề/nguồn, và các tập cũ đã dùng để chỉnh luật. Chiến lược ưu tiên "tổ chức có định danh registry" **không cải thiện** PASS (0/13): nguyên nhân phổ biến nhất của chặn vẫn là IDENTITY_NOT_GROUNDED (36 lượt trên 50 bài), tức công ty/người mới chưa được định danh trong bài. Hơn nửa số bài mới (28/50) không sinh ứng viên; ~58% bài scale03 không thuộc chủ đề nhắm tới (`none`).

## 5. Kiểm thử và phạm vi mã
`pytest`: **285 passed** (283 + 2 hồi quy sau khi sửa lỗi spacing; gồm 12 test chiến dịch, 5 test compliance/chọn bài, 6 test log HTTP), `ruff check` sạch. Mã mới: `jobs/scaleup.py`, `jobs/selection.py`, log request-start + kiểm khoảng cách (`crawlers/http.py`), `config/crawl_compliance.yaml`, `scripts/start-scaleup.ps1`. Thay đổi nhỏ: `jobs/pilot.py` (compliance, trần nguồn, danh tính, kiểm spacing), `status-pipeline.ps1`. Giới hạn 20 bài/job, 50 tổng, 160 Qwen được ép trong mã.

## 6. Việc cần xử lý trước khi mở batch lớn
1. **Quyết định về dữ liệu Vietstock** đã crawl dưới lỗi spacing (mục 0); xác nhận pháp lý cho CafeF/Vietstock vì ToS không công bố.
2. Chạy lại kiểm spacing theo tên host trước mỗi batch tương lai (đã tích hợp); cân nhắc dùng `https://` ngay từ URL Vietstock để tránh hop chuyển hướng.
3. Định danh vẫn là nút cổ chai; chưa có người duyệt, không có gold: 6 PASS mới cần duyệt, đặc biệt ca SCIC (PASS FACT vs QUARANTINE DENIED).
4. Chỉ có 2 nguồn hợp lệ; thiếu đa dạng nguồn. Ranking chủ đề chưa lọc tốt (scale03 nhiều bài `none`).
5. Chiến dịch dễ chết khi cửa sổ console bị đóng; resume hoạt động, nhưng nên xác định nguyên nhân (không rõ do môi trường).
6. Mốc 11/11 (2.000 entity/5.000 quan hệ) vẫn rất xa: 90 node, 54 cạnh trong tầng đã kiểm.

## 7. Lệnh
```powershell
.\scripts\start-scaleup.ps1 [-Budget 160] [-MinDelay 2.5] [-Resume]    # (không chạy lại khi chưa được phê duyệt)
.\scripts\status-pipeline.ps1 -JobId scale-campaign|scale01|scale02|scale03
.\scripts\monitor-pipeline.ps1 -JobId scale-campaign
.\scripts\stop-pipeline.ps1 -JobId scale-campaign
.\scripts\aggregate-graph.ps1 [-Verify] [-Disable job:scale01]
```
Phase 6F dừng tại đây; không chạy batch tiếp theo.
