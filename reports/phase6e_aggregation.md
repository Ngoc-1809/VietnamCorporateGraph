# Phase 6E.1 - Tổng hợp graph staging xuyên batch

Phạm vi: aggregator độc lập, chỉ đọc dữ liệu nguồn. Không crawl, không chạy GLiNER/Qwen, không kết nối Neo4j, không sửa registry gốc, không đổi hard validation, không nâng QUARANTINE, không mở batch mới, không xóa/ghi đè output phase trước. Không có gold: **LEGACY_OFFICIAL (verifier-based, AUTO_ACCEPTED) và QA_PASS (kết quả luật) đều KHÔNG phải ground truth.**

## 1. Thiết kế
`src/vckg/graph/aggregate.py` (+ `scripts/aggregate-graph.ps1`, `tests/test_aggregate.py`). Đầu ra: `data/aggregate/` (gitignored, có câu bằng chứng): `staging_graph.sqlite`, `export/graph_validated.graphml`, `export/graph_all_tiers.graphml`, `nodes|edges|evidence|collisions.csv`, `summary.json`; bản tóm tắt không chứa câu bài báo ở `reports/phase6e/`.

**Nguồn** (đăng ký trong DB, mỗi nguồn có fingerprint nội dung):
- `baseline_legacy`: đúng dữ liệu đã nạp Neo4j baseline, dựng lại bằng `neo4j_sync.collect` (dev44 + holdout19 + new144, registry p5): 44 official, 31 candidate, 74 node; gộp người cùng tên + cùng tổ chức là luật có log sẵn (5 lần). Không kết nối Neo4j.
- `job:pilot6d`: bảng staging của `pipeline.sqlite` (quyết định QA từng cạnh + toàn bộ evidence/URL). Job `smoke1`, `smoke2`, `smoke-err` và các lần rerun **không** được tính: mặc định chỉ có pilot6d; `add-job` từ chối tên smoke/test/rerun/err/trial và job chưa COMPLETED (trừ khi cờ cố ý).

**Tầng chất lượng tách riêng, không bao giờ chuyển tầng**: LEGACY_OFFICIAL, QA_PASS, QUARANTINE (kèm lớp), REJECT, và LEGACY_CANDIDATE (thêm vào để giữ đủ 31 cạnh candidate của baseline). Mỗi dòng cạnh khóa bởi `(edge_id, tier)`; `edge_id = hash(subject_key, predicate, object_key, factual_status, valid_from, valid_to)`; evidence khóa `(edge, tier, article, span)`, giữ mọi `source_url`, nguồn đóng góp. Một triple có ở hai tầng thì nằm ở cả hai; evidence của dòng QUARANTINE không gắn sang cạnh PASS (có test).

**Định danh**: khóa entity = ID registry (merge đã ghi trong registry nguồn được tôn trọng). Không gộp thêm theo tên. Cùng ID nhưng khác kiểu/tên chuẩn hóa giữa hai nguồn = `ID_CONFLICT`, giữ riêng (`id@nguồn`). Trạng thái định danh của entity = **thận trọng nhất** giữa các nguồn (không bị nguồn khác nâng cấp).

**Idempotent**: nguồn chỉ nạp lại khi fingerprint đổi (khi đổi thì THAY toàn bộ dòng của nguồn, không cộng thêm); các bảng tổng hợp dựng lại xác định trong một transaction. Kiểm chứng: `verify` chạy hai lần cho cùng content hash; nạp cùng job hai lần, hai job trùng nội dung, hoặc khai báo lặp job không làm tăng cạnh/entity/evidence (test + dữ liệu thật: bản sao pilot6d dưới ID khác bị loại đủ 44 dòng cạnh trùng).

## 2. Kết quả (content hash `c22f294ec5911f26`, lặp lại bằng 3 lần chạy)
| Nguồn | Dòng cạnh | Evidence | Bài |
|---|---|---|---|
| baseline_legacy | 75 (44 official + 31 candidate) | 94 | 59 |
| job:pilot6d | 44 (4 PASS + 40 QUARANTINE) | 50 | 13 |

| Tầng | Cạnh duy nhất | Node | Loại quan hệ | Evidence | Bài |
|---|---|---|---|---|---|
| LEGACY_OFFICIAL | 44 | 74 | 8 | 60 | 39 |
| QA_PASS | 4 | 6 | 4 | 5 | 2 |
| QUARANTINE | 40 | 47 | 10 | 45 | 13 |
| REJECT | 0 | 0 | 0 | 0 | 0 |
| LEGACY_CANDIDATE | 31 | 60 | 9 | 34 | 26 |

- **Unique domain nodes**: **80** trong tầng đã kiểm (LEGACY_OFFICIAL ∪ QA_PASS = 74 + 6; hai tập rời nhau), 178 nếu tính cả quarantine/legacy candidate. Entity đã kiểm theo trạng thái: ARTICLE_GROUNDED 58, VERIFIED 22; theo kiểu: PERSON 35, ORGANIZATION 37, BANK 3, BOND_ISSUE 3, REGULATOR 1, GOVERNMENT_AGENCY 1.
- **Cạnh**: 119 dòng (cạnh, tầng); 48 cạnh trong tầng đã kiểm (44 + 4). **Loại quan hệ**: 8 trong tầng đã kiểm (QA_PASS không thêm loại mới: chỉ BOARD_MEMBER_OF, CEO_OF, CHAIR_OF, OWNS_SHARES_IN), 11 tính mọi tầng.
- **Evidence** 144 dòng duy nhất, **72 bài** đóng góp (41 bài ở tầng đã kiểm); 144/144 có source URL.
- **Duplicate bị loại**: 0 dòng cạnh, 0 dòng evidence giữa baseline và pilot6d (không có cạnh/bài chung nào); khi thử thêm bản sao pilot6d: 44 dòng cạnh bị loại (test). Gộp người in-source theo luật có log của baseline: 5.
- **Triple xuất hiện ở nhiều tầng**: 1: `Trịnh Văn Tuệ CEO_OF Tổng Công ty Vimico` là QA_PASS với trạng thái ENDED và QUARANTINE (HARD_BLOCK) với trạng thái FACT; hai cạnh khác trạng thái nên là hai cạnh riêng, không hợp nhất, không nâng cấp.
- **Connected components** (đồ thị vô hướng): LEGACY_OFFICIAL 74 node / 33 thành phần (lớn nhất 4); QA_PASS 6 node / 2 (lớn nhất 4); hợp đã kiểm 80 node / **35 thành phần** (lớn nhất 4); mọi tầng 178 node / 71 (lớn nhất 11). Đồ thị rất phân mảnh: hai batch không có node chung nên tổng hợp chưa tạo cạnh nối giữa chúng.

### Identity collisions chưa giải quyết: 1 (chỉ báo cáo, không hợp nhất)
- `SAME_NAME_PERSONS_UNMERGED`: "trịnh văn tuệ" có hai khóa người theo bài (`person:trinh-van-tue@art:7dda...`, `...@art:bb7c...`), không có tổ chức chung được xác nhận -> giữ riêng. Không có ID_CONFLICT, không có cặp công ty tên giống nhau (ngưỡng 92 trên tên chuẩn hóa).
- Quan sát không tự gộp: bài Kosy có cả "Kosy Group" và "ctcp kosy" (mã KOS) là hai ID khác nhau; cần người/nguồn định danh quyết định (cùng tên rút gọn không phải bằng chứng).
- PROVISIONAL xuyên bài: chỉ được báo cáo khi trùng tên chuẩn hóa với entity khác; hiện không có ca nào (không có gì bị gộp).

## 3. Giới hạn
- Hai nguồn hiện rời nhau nên cơ chế dedup liên-batch mới được kiểm bằng test tổng hợp/bản sao, chưa bằng chồng lấn tự nhiên; kết quả "0 duplicate" là sự thật của dữ liệu, không phải bằng chứng dedup đúng.
- Khóa cạnh dùng khoảng hiệu lực rỗng cho staging (job chưa điền `valid_from/to`); nếu job tương lai điền, hai nhiệm kỳ sẽ là hai cạnh.
- Ngưỡng tương đồng tên (92) chỉ là gợi ý duyệt; chưa đo độ nhạy. Người cùng tên khác bài không được gộp -> số node người có thể bị đếm dư (thận trọng có chủ ý).
- Tầng LEGACY_OFFICIAL do verifier (Qwen) + luật cũ chấp nhận, QA_PASS do hybrid QA mới: hai chuẩn khác nhau, cộng lại chỉ để thống kê, không đồng nhất chất lượng. Không có người duyệt -> không có gold.
- Chưa có projection người-người/công ty-công ty (module `projection.py` đòi mô hình `Edge`, giữ nguyên cho official baseline); chưa import vào Neo4j (không được phép trong phase này).
- Aggregator đọc `pipeline.sqlite` của job; job chưa COMPLETED bị từ chối nên một lần chạy dở dang chưa đóng góp.

## 4. Kiểm thử
`pytest`: **267 passed** (253 + 14 test mới trong `tests/test_aggregate.py`), `ruff check` sạch. Test: tầng tách riêng; nạp lại cùng job/khai báo lặp không tăng; hai job trùng nội dung loại trùng và đếm; job đổi nội dung thì thay thế; cùng triple ở PASS và QUARANTINE giữ cả hai tầng, evidence không lẫn; cùng cạnh từ hai job hợp evidence và giữ URL; cùng tên người/công ty tương tự chỉ báo cáo; ID_CONFLICT giữ riêng và tách thành phần liên thông; trạng thái định danh thận trọng nhất; từ chối smoke/rerun/chưa COMPLETED; disable nguồn; thành phần liên thông và file xuất (GraphML validated không chứa QUARANTINE); quyết định QA lạ báo lỗi; dữ liệu thật pilot6d idempotent + bản sao trùng 44 dòng.

## 5. Lệnh
```powershell
cd T:\VietnamCorporateGraph
.\.venv\Scripts\python.exe -m vckg.graph.aggregate run                       # nạp nguồn đã đăng ký (nguồn không đổi bị bỏ qua), tổng hợp, xuất, báo cáo summary.json
.\.venv\Scripts\python.exe -m vckg.graph.aggregate add-job --job-id <job>    # đăng ký job COMPLETED mới rồi chạy lại (từ chối smoke/test/rerun)
.\.venv\Scripts\python.exe -m vckg.graph.aggregate disable --source job:<job>
.\.venv\Scripts\python.exe -m vckg.graph.aggregate list | verify
.\scripts\aggregate-graph.ps1 [-AddJob <job>] [-Verify] [-Disable job:<job>]
```
Không gọi Qwen, GLiNER hay crawler; sau mỗi batch tương lai chỉ cần `add-job` (hoặc `run`). Phase 6E.1 dừng tại đây.
