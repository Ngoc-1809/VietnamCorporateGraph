# Phase 6D - Pilot crawl tự động (staging only)

Phạm vi: crawl tối đa 20 bài MỚI bằng crawler Phase 5 rồi xử lý bằng worker Phase 6C. Không đổi NLP, model, prompt, hybrid QA, hard validation; không ghi Neo4j (không kết nối; cổng 7687 đóng), không sửa registry nguồn (mtime `registry_p5_new.sqlite` vẫn 30/10), không merge registry job, không bật official-sync. Không có gold: PASS/QUARANTINE là kết quả luật, không phải precision (NOT EVALUATED).

## 1. Kiến trúc
`jobs/pilot.py` (orchestrator riêng; không mở khóa `--crawl` của worker, vẫn bị từ chối). Một tiến trình, một thư mục job `data/pipeline/<job>/`, một `status.json`:
```
CRAWLING:  run_discovery (Phase 5: RSS/category page, robots.txt + >=2 s/host qua PoliteClient, bỏ URL/tiêu đề đã có) -> crawl_plan.json (checkpoint)
           -> fetch_one từng ứng viên (tách từ fetch_selected, hành vi cũ giữ nguyên) -> SQLite staging (dedup canonical URL + content hash)
           -> manifest.jsonl ghi lại sau MỖI bài
PROCESSING/FINALIZING: Worker Phase 6C không đổi (GLiNER, span recovery, grounding, Qwen discovery, fusion, hybrid QA, staging graph)
COMPLETED | FAILED | STOPPED
```
- Bài "mới" = chưa có trong `staging.sqlite` trước job (danh sách ID baseline lưu ở `baseline_article_ids.json`; bản sao DB `staging.sqlite.pre6d.bak`). Ứng viên trùng URL/nội dung KHÔNG được dùng để lấp quota; thiếu thì báo `crawl_shortfall`, không lấy bài cũ.
- Trần cứng 20 bài mới/job (tính cả bài thử: cùng JobId, `-Resume` dùng lại plan và bài đã tải). Retry fetch tối đa 2 lần/ứng viên (PoliteClient còn retry/backoff nội bộ). Một ứng viên lỗi/robots/bị loại không ảnh hưởng bài khác; lỗi cuối cùng không bị che.
- Khóa: `worker.lock` (một orchestrator/job), `_locks/gpu.lock` toàn cục (một worker NLP trên GPU; test chứng minh job thứ hai bị từ chối, exit 5), `start-pilot.ps1` từ chối khởi động khi job khác đang hoạt động. STOP file/tín hiệu được kiểm giữa các bài ở cả pha crawl lẫn pha NLP.
- Thay đổi code nhỏ: `crawlers/discovery.py` (`fetch_one`, tham số `targeted_share`, mặc định cũ), `jobs/pipeline_worker.py` (trạng thái ngoài/`external_status`, khóa GPU, trường status mới `candidates_unique`, `entities_in_candidates`, `qwen_failed`), script `start-pilot.ps1` mới; `status-pipeline.ps1`/`monitor-pipeline.ps1` được mở rộng (không viết lại). `stop-pipeline.ps1` dùng nguyên.
- Chọn bài: targeted 100% theo tín hiệu (appointment/board/shareholding/subsidiary/mna/credit/bond/jv/sanction/prosecution), nguồn CafeF/Vietstock/VnEconomy/BáoĐầuTư. Ranking chỉ để chọn bài, không phải bằng chứng.

## 2. Kết quả pilot `pilot6d`
Chạy: thử 3 bài -> kiểm tra -> mở rộng lên 20 (cùng job) -> rerun idempotent. Hai wrapper/worker: lần 20 bài PID worker **43000** (wrapper 26908), cửa sổ 13:39:35-13:43:01 (+07:00); lần thử PID 2424; các lần rerun (PID 14700, 3392) không làm gì thêm. Ollama chạy tách rời từ 6C.

| Mục | Kết quả |
|---|---|
| 1. Bài mới thực sự được crawl | **20** (cafef 12, vietstock 8), đều `inserted`; 0 trùng URL, 0 trùng nội dung, 0 robots_disallowed, 0 bị loại chất lượng, 0 lỗi tải. Staging 274 -> 294; 0 ID mới nằm trong baseline; hàng baseline không đổi (so hash) |
| Discovery | pool mới ~706 (cafef 264, vietstock 125, vneconomy 227, baodautu 90), 3 trùng tiêu đề với bài đã có; 54 ứng viên được lập kế hoạch (vietstock 26, cafef 25, baodautu 2, vneconomy 1); 34 chưa dùng. Chủ đề trong 20 bài: appointment 3, board 3, bond 3, credit 2, mna 2, prosecution 2, sanction 2, shareholding 2, subsidiary 1 |
| 2. Xử lý | **20 thành công / 0 thất bại**; 713 mention |
| 3. Candidate / entity | 11 ứng viên luật thô + 56 quan hệ Qwen hợp lệ thô -> **44 cạnh candidate duy nhất**, 50 evidence; 48 entity xuất hiện trong candidate; **6 domain entity trong cạnh validated** (5 ARTICLE_GROUNDED, 1 VERIFIED) |
| 4. QA | **4 PASS / 40 QUARANTINE / 0 REJECT**. Quarantine: HARD_BLOCK 20, INSUFFICIENT_EVIDENCE 11, SEMANTIC_ONLY_CLEAN 9 (không tự official). Theo phương pháp: BOTH 3 PASS + 3 QUARANTINE, RULE 0 PASS + 5 QUARANTINE, LLM-only 1 PASS + 32 QUARANTINE |
| Lý do chặn hàng đầu | IDENTITY_NOT_GROUNDED 21 (công ty chưa có định danh), PARTNERSHIP_CUE_MISSING 6, SPAN_BOUNDARY_SUSPECT 3, IDENTITY_SHORT_PERSON_NAME 3, ROLE_IN_CRIMINAL_CONTEXT 2, PARENT_CHILD_CUE_MISSING 2 |
| 5. Loại quan hệ | Tất cả candidate: OWNS_SHARES_IN 12, CEO_OF 8, PARTNERS_WITH 6, CHAIR_OF 4, BOARD_MEMBER_OF 4, SANCTIONED_BY 3, SUBSIDIARY_OF 3, FOUNDED 2, ACQUIRED 1, ISSUED_BOND 1 (**10 loại**). PASS: CHAIR_OF, BOARD_MEMBER_OF, OWNS_SHARES_IN, CEO_OF (**4 loại**) |
| 6. Qwen | **46 lần gọi live (cap 100), 0 lỗi, 0 cache hit** (bài mới nên không có cache); 46 cửa sổ; Qwen 131,5 s, 50.355 prompt token, 14.752 token sinh; NER: 20 live, 0 cache hit; tổng thời gian xử lý bài 176 s (gồm nạp GLiNER). Crawl ~25 s cho 17 bài sau khi đã có plan. Tổng cửa sổ 13:35:05-13:43:01 gồm cả quá trình thử và kiểm tra |
| Cạnh official | 0 (staging_edges.official có CHECK = 0) |

PASS (cả 4 đều cần người xem, không có gold): `Nguyễn Việt Cường CHAIR_OF Kosy Group`, `Nguyễn Thị Hằng BOARD_MEMBER_OF Kosy Group`, `Nguyễn Việt Cường OWNS_SHARES_IN KOS` (cùng một bài CafeF, BOTH) và `Trịnh Văn Tuệ CEO_OF Vimico` (LLM-only nhưng qua cùng cổng luật; bài nói ông bị khởi tố - kiểm tra thủ công trạng thái hiện/quá khứ là cần thiết, không tự coi là đúng).

### 7. Tỷ lệ cạnh PASS trên mỗi bài (chỉ mô tả, n nhỏ, cấu hình/bài chọn khác nhau)
| Tập | Bài | Cạnh PASS | PASS/bài | Bài có candidate |
|---|---|---|---|---|
| Pilot 6D (bài mới, targeted) | 20 | 4 | **0,20** | 13/20 (2 bài chứa toàn bộ PASS) |
| 6B.4 (60 bài, 40 targeted + 20 control, đã tinh chỉnh trên chúng) | 60 | 13 | 0,22 | 33/60 |
| 6C smoke (12 bài lấy từ 60 bài trên) | 12 | 4 | 0,33 | 6/12 |
Không kết luận có cải thiện/suy giảm: 20 bài, PASS tập trung ở 2 bài; hai tập cũ là bài đã dùng để chỉnh luật nên không phải đối chứng độc lập. Pilot là phép đo mới đầu tiên trên bài chưa từng thấy, nhưng vẫn không có nhãn người nên không tính được precision.

## 3. Kiểm thử và bằng chứng vận hành
- `pytest`: **253 passed** (244 + 9 test mới trong `tests/test_pilot.py`), `ruff check` sạch. Test dùng MockTransport sau PoliteClient thật + FakeNER/FakeLLM (chứng minh điều phối, không chứng minh chất lượng): chỉ tải bài mới đến đủ quota; rerun không tải/không xử lý lại; thử rồi mở rộng quota dùng lại bài đã tải; bài cũ/trùng nội dung/503 không lấp quota và thiếu thì báo shortfall; robots disallow được tôn trọng; trần 20 và target sai bị từ chối; STOP trong crawl rồi resume; khóa GPU; một job không chạy hai lần.
- Thử 3 bài thật: manifest đúng, 3/3 xử lý (14 candidate, 0 PASS), rerun cùng target không tải thêm, không gọi Qwen thêm, DB y hệt (hash cạnh trùng). Mở rộng lên 20 chỉ tải 17 bài, 40 lần gọi Qwen thêm. Rerun cuối: 20 DONE, 44 cạnh/44 khóa, 120 artifact, 20 sự kiện `article_done` không trùng, Qwen vẫn 46.
- STOP/kill giữa chừng cho pha NLP đã kiểm thật ở 6C; ở 6D STOP của pha crawl chỉ được kiểm bằng test (không dừng live trong pilot).

## 4. Trạng thái worker và lệnh theo dõi
Trạng thái cuối: COMPLETED, 20/20, exit 0; wrapper `pilot-pilot6d` ghi COMPLETED. `status.json` hiện thuộc lần rerun idempotent (PID 3392); bản chạy chính PID 43000 có trong `events.jsonl`/`summary.json` (bản sao ở `reports/phase6d/`).
```powershell
.\scripts\start-pilot.ps1 -JobId <id> -TargetNew <=20 -MaxQwenCalls 100 [-Only cafef vietstock] [-Resume]
.\scripts\status-pipeline.ps1 -JobId <id>        # hiện crawl: discovered/fetched/failed/skipped + liveness (STALE/DEAD)
.\scripts\monitor-pipeline.ps1 -JobId <id> -Once  # chỉ đọc JSON, không gọi AI
.\scripts\stop-pipeline.ps1 -JobId <id>           # STOP an toàn, giữ checkpoint
```
Dữ liệu: `data/pipeline/pilot6d/` (pipeline.sqlite, crawl_plan.json, manifest.jsonl, qa/, qa_report/, export/, summary.json); bản sao nhỏ ở `reports/phase6d/`.

## 5. Giới hạn cần giải quyết trước khi mở batch lớn
1. **Bằng chứng rate limit chưa đầy đủ**: throttle của PoliteClient đo từ lúc bắt đầu request (>=2 s/host theo thiết kế và test), nhưng log chỉ ghi thời điểm hoàn tất ở độ phân giải giây (khoảng cách quan sát tối thiểu 1 s giữa hai lần hoàn tất, không phải giữa hai lần bắt đầu), và `robots.txt` mỗi host được tải một lần không qua throttle. Cần log thời điểm bắt đầu request trước khi crawl lớn.
2. **Điều khoản sử dụng chưa được rà soát** (chỉ có robots.txt đã kiểm 2026-10-30); phải rà trước khi mở rộng.
3. **Cân bằng nguồn kém**: ranking chọn gần như chỉ CafeF/Vietstock (VnEconomy 1, Báo Đầu tư 2 ứng viên trên 54 dù pool lớn); cần ngưỡng/quota nguồn nếu muốn đa dạng.
4. **Định danh là nút cổ chai**: 21/44 candidate bị IDENTITY_NOT_GROUNDED vì công ty mới chưa có trong registry; PASS phụ thuộc bài có tổ chức/người có định danh bài-grounded. Registry job là bản sao, chưa merge về registry chính (cần quy trình duyệt).
5. **Chất lượng chưa đo**: không có gold; 4 PASS cần người xem (đặc biệt Vimico: bài về khởi tố, rủi ro hiện/quá khứ). Kết quả Qwen-only không tự PASS nhưng 1 PASS LLM-only vẫn đi qua luật.
6. Kết quả khác nhau giữa các lần Qwen chạy trên cùng mention (đã thấy ở 6C) -> cache Qwen/NER có version là bắt buộc khi so sánh.
7. Mỗi finalize dựng lại toàn bộ QA/staging (O(số bài)); `build_context` đọc toàn bộ staging.sqlite; chưa tối ưu cho hàng trăm bài. Khóa GPU chỉ giữa các job của dự án (không chặn Ollama dùng bởi tiến trình ngoài).
8. Staging chung `staging.sqlite` đã được ghi thêm 20 hàng bởi pilot (đúng thiết kế "Article Staging"); bản sao trước pilot là `data/staging/staging.sqlite.pre6d.bak` (gitignored). Mốc 11/11 (2.000 entity/5.000 quan hệ) vẫn rất xa: pilot cho 4 cạnh validated / 20 bài.

Đề xuất (chưa làm, cần phê duyệt): log thời điểm bắt đầu request + rà điều khoản; quota nguồn; người duyệt 4 PASS và các SEMANTIC_ONLY_CLEAN; sau đó mới cân nhắc batch 50-100 bài. Phase 6D dừng tại đây.
