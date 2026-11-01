# Phase 6C - Worker end-to-end độc lập (staging only)

Phạm vi: tích hợp các module đã có thành một worker chạy tách khỏi OpenCode, có checkpoint/resume/monitoring. Không đổi model, prompt, hard validation; không crawl; không tải model; không ghi Neo4j, registry nguồn hay cạnh official. Không có gold: số PASS/QUARANTINE dưới đây là kết quả luật, không phải precision/recall (NOT EVALUATED).

## 1. Kiến trúc thực tế
```
manifest(JSONL article_id) -> load (staging.sqlite, mở read-only)
  -> GLiNER NER theo câu (CachedNER: cache SQLite có version, nạp model lười, chỉ khi cache miss)
  -> pipeline.process_article (dictionary + merge + resolve trên registry RIÊNG của job, verifier=None => chỉ ứng viên luật + bond)
  -> span_recovery + article_grounding (đúng logic span_qa của 6B.4, từng bài)  => overlay (span gốc -> span/ID sửa)
  -> Qwen discovery (discover_article, cache có version, trần số lần gọi live)
  -> [mọi artifact của bài ghi MỘT transaction cùng trạng thái DONE]
finalize (mỗi N bài + cuối job + khi dừng): consolidate_persons (như Phase 5) -> apply_overlay + fuse -> hybrid QA (validator đóng băng)
  -> staging graph (staging_edges/evidence/entities, khóa PK) -> export JSONL + CSV kiểu Neo4j (thư mục job)
```
- Module mới: `jobs/pipeline_worker.py`, `jobs/stages.py`, 4 script `scripts/*-pipeline.ps1`, `tests/test_pipeline_worker.py` (16 test). Refactor tối thiểu: `discovery_benchmark.discover_article` (tách từ vòng lặp cũ, benchmark dùng lại nó), `hybrid_qa.run/build_fused` nhận `manifest/run_dir/staging_db/rule_rows/llm_chunks` (mặc định = hành vi cũ) và hàng kết quả có thêm `evidence_all`.
- Thứ tự stage: recovery+grounding chạy TRƯỚC discovery như yêu cầu; overlay được ÁP DỤNG lên ứng viên ở bước fusion (đúng cách đã kiểm chứng ở 6B.4), nên Qwen vẫn thấy mention gốc. Đây là lựa chọn có chủ ý để không đổi hành vi đã đo.
- Bảo toàn: provenance (evidence_all: bài, offset, URL, method), ID thực thể ổn định (registry riêng, ID dạng slug / `person:{tên}@art:`), trạng thái định danh và factual_status, tách official/candidate/quarantine (cột `official` có CHECK = 0; không có đường code nào tạo official), dedup theo khóa fusion (canon subject, predicate, canon object, status) + cửa sổ hiệu lực.
- Candidate chỉ Qwen tìm ra phải qua cùng hard + semantic gate; SEMANTIC_ONLY_CLEAN nằm ở quarantine (test: không vào file validated / CSV rels).

### An toàn vận hành
- Một worker/job: `worker.lock` (O_EXCL; PID chết thì thu hồi, PID sống thì từ chối - exit 5). Mỗi job có registry copy riêng nên hai job không bao giờ ghi chung DB. Cache dùng chung là SQLite (timeout 30 s).
- Retry có giới hạn (`--max-attempts`, mặc định 2, backoff), lỗi cô lập từng bài, ghi `error/stage/attempts`. Lỗi không thể thử lại (ARTICLE_NOT_FOUND) không lặp lại. Cửa sổ Qwen lỗi => bài FAILED (không DONE âm thầm thiếu ứng viên LLM).
- Trần Qwen live theo job, cộng dồn qua các lần resume (ghi sau MỖI lần gọi, kể cả hỏng); hết trần => STOPPED (exit 3), bài dở trở lại PENDING không tính lần thử, cache giữ các cửa sổ đã gọi.
- Dừng: STOP file hoặc SIGINT/SIGTERM/SIGBREAK -> hết bài hiện tại, finalize, state=STOPPED (exit 0). Hard kill: lock/trạng thái bỏ lại, status đọc là DEAD, resume an toàn (hàng RUNNING mồ côi trở về PENDING, không tính là lỗi).
- Fingerprint cấu hình (phiên bản pipeline/NER/recovery/prompt/validator + hash relations.yaml + có/không LLM): đổi cấu hình thì bài cũ được xử lý lại; không đổi thì không bao giờ xử lý lại.
- `official-sync` bị từ chối; `--crawl` bị từ chối; trần 20 bài/lần (`VCKG_ALLOW_LARGE_BATCH` mới vượt được, chưa dùng).
- Neo4j: không khởi động, không kết nối trong 6C. Neo4j Community chỉ có một database nên không có DB test tách biệt; kiểm thử import lặp được làm trên staging graph (SQLite riêng của job): dựng lại 2 lần + khóa trùng không sinh thêm cạnh/evidence (test). Import production vẫn dùng `neo4j_sync` cũ, chưa bật.

## 2. Monitoring
`status.json` do chính worker ghi nguyên tử (heartbeat thread 5 s) với đủ trường yêu cầu (job_id, pid, state, started_at, heartbeat_at, finished_at, total/processed/succeeded/failed_articles, rule_candidates, llm_candidates, qa_pass/quarantine/reject, unique_staging_edges/entities, llm_calls, last_error) + stage, current_article, qwen_cache_hits, mode, stop_reason. Đọc: `liveness` = RUNNING_OK | STALE (PID sống, >60 s không heartbeat) | DEAD (PID chết, không trạng thái cuối) | FINISHED. Monitor/status chỉ đọc JSON/log/SQLite (không gọi AI/Ollama).

## 3. Smoke test (12 bài thật có sẵn từ 60 bài Phase 6, không crawl; GLiNER + Qwen3.5-9B local thật)
Bài: 8 targeted + 4 control (baodautu/cafef/vietstock), chọn xác định 2:1 từ manifest 6B.1 (`data/pipeline/smoke_manifest.jsonl`). Ollama chạy tách rời qua run-job.

| Bước | Kết quả |
|---|---|
| Khởi động độc lập | `start-pipeline.ps1` -> run-job (CIM, không phải tiến trình con); PID worker 18844 (khác PID wrapper 16300) |
| Dừng nhẹ giữa batch | `stop-pipeline.ps1`: STOPPED sau 4/12 bài, checkpoint giữ |
| Resume rồi hard kill | worker PID 5496 bị `Stop-Process` khi đang ở bài thứ 8 (stage qwen_discovery, 7/12 xong): status đọc **DEAD**, không báo RUNNING |
| Resume lần 3 (PID 44844) | chỉ xử lý 5 bài còn lại -> COMPLETED 12/12, exit 0 |
| Rerun idempotent (PID khác) | `pending n=0 skipped_done=12`, DB y hệt trước/sau: 12 DONE, 28 cạnh/28 khóa duy nhất, 29 evidence, 29 entity staging, registry 3.560 entity / 5.793 mention, 12 sự kiện article_done không trùng |
| Job chạy lại từ đầu (smoke2, thư mục job mới, cache ấm) | 12/12 trong ~4 s, 0 gọi Qwen live, 28 cache hit; QA y hệt smoke1 (4/23/1) -> tái lập xác định |
| Cô lập lỗi (smoke-err: 2 bài thật + 1 ID không tồn tại) | state **FAILED**, exit 4, ok=2 failed=1, last_error `ARTICLE_NOT_FOUND`; wrapper cũng ghi FAILED (exit 4); 2 bài tốt vẫn DONE |
| Đọc kết quả sau khi OpenCode kết thúc | worker/ollama là tiến trình tách rời; toàn bộ kết quả nằm ở `data/pipeline/<job>/` + bản sao nhỏ ở `reports/phase6c/` |

Số liệu smoke1 (12 bài): 405 mention; 9 ứng viên luật thô, 41 quan hệ Qwen hợp lệ thô, 28 cạnh duy nhất sau fusion. QA hybrid: **4 PASS / 23 QUARANTINE / 1 REJECT**; theo phương pháp: BOTH 3 PASS + 2 QUARANTINE, RULE 1 PASS + 3 QUARANTINE, LLM-only 0 PASS + 18 QUARANTINE + 1 REJECT (Qwen-only không tự PASS). QUARANTINE: INSUFFICIENT_EVIDENCE 10, HARD_BLOCK 9, SEMANTIC_ONLY_CLEAN 3, NON_OFFICIAL_STATUS 1. Staging validated: 4 cạnh (CHAIR_OF 3, CEO_OF 1), 6 entity, 2 loại quan hệ. Cạnh official = 0.
Thời gian: tổng thời gian xử lý bài ~143 s (gồm nạp GLiNER lần đầu, 11 lượt NER live); Qwen: **28 lần gọi live, 28 cửa sổ** (+ tối đa 1 lần gọi đang dở khi bị kill, không được ghi nhận và không tạo cache; bộ đếm đã được sửa sau đó để ghi sau mỗi lần gọi). Tổng thời gian bốn lần chạy smoke1 ≈ 50 s + ~40 s + 64 s + 1 s.

### So với 6B.4 trên cùng 12 bài (không phải đo chất lượng)
Không giống hệt, và không được chỉnh để giống: 18/22 khóa trùng, 16/18 quyết định trùng; 6B.4: 6 PASS, worker: 4 PASS. Nguyên nhân quan sát được: (1) Qwen chạy lại trên danh sách mention mới nên ra tập quan hệ khác (41 so với 20 chấp nhận trên 28 cửa sổ như nhau); (2) hai ca khác về PASS do tái xử lý bài đã nằm trong registry đã hợp nhất người: `Đỗ Quý Hải -> HPX` bị SAME_NAME_CONFUSION vì resolver trả ngay ID chuẩn của bài khác (validator đóng băng coi đó là lỗi), và `Nguyễn Văn Thứ -> GCF` do NER chạy lại cho mention một từ "Thứ" (IDENTITY_SHORT_PERSON_NAME). Đây là đặc điểm của việc chạy lại bài đã xử lý trên registry đã hợp nhất, không phải lỗi worker; bài mới thật sự sẽ không gặp ca (2) kiểu này. Không sửa validator.

## 4. Kiểm thử
`uv run pytest`: **244 passed** (228 cũ + 16 mới), `ruff check` sạch. Test mới (đồ giả FakeNER/FakeLLM, chỉ chứng minh điều phối, không chứng minh chất lượng GLiNER/Qwen): hoàn tất + status đủ trường; rerun idempotent không xử lý lại/không trùng; một bài lỗi không hủy batch và job báo FAILED; bài không tồn tại cô lập; retry lỗi tạm thời; STOP file rồi resume không lặp; trần Qwen dừng sạch rồi resume; cửa sổ Qwen lỗi => bài FAILED; đổi cấu hình => xử lý lại; khóa chặn worker thứ hai/thu hồi khóa chết; liveness STALE/DEAD/FINISHED; official-sync và batch >20 bị từ chối; staging graph import lặp không trùng + SEMANTIC_ONLY_CLEAN không thành validated + CHECK official=0; cache NER có version; chọn bài xác định; kế toán Qwen ghi sau mỗi lần gọi.

## 5. Lỗi/hạn chế còn tồn tại
- Wrapper `run-job` ghi FAILED với mọi exit != 0 (kể cả STOPPED do hết trần Qwen, exit 3) và `status.json` mới là nguồn sự thật; wrapper tự ghi FAILED cho cả STOPPED nếu exit != 0.
- Kill cứng làm mất kế toán của lần gọi Qwen đang dở (tối đa 1) trong smoke1; đã sửa cho các lần chạy sau, test đã có.
- Chưa có khóa liên-job cho GPU/Ollama: hai job cùng lúc sẽ tranh GPU (không hỏng dữ liệu vì mỗi job có DB riêng).
- Bài mới của batch sau không tự gộp ngược vào registry nguồn; registry của job là bản sao. Việc hợp nhất registry job -> registry chính (và official-sync) chưa làm, cần phê duyệt (Phase sau).
- Staging chỉ dựng lại toàn bộ từ artifact ở mỗi finalize (O(số bài)); đủ cho trăm bài, cần tối ưu khi batch lớn. `build_context` đọc toàn bộ staging.sqlite mỗi lần finalize.
- Chưa đo chất lượng (không gold); 12 bài là smoke, không đại diện. Neo4j Community không có DB test thứ hai; chưa kiểm chứng import lặp trên Neo4j thật (không được đụng DB production).
- Cảnh báo `sam2_video checkpoint` ở stderr khi nạp GLiNER là vô hại (đã có từ trước).
- Mốc 11/11/2026 (2.000 entity / 5.000 quan hệ) vẫn rất xa; smoke 12 bài cho 4 cạnh validated.

## 6. Lệnh
```powershell
cd T:\VietnamCorporateGraph
# (một lần, nếu Ollama chưa chạy)  .\scripts\run-job.ps1 -Name ollama-serve -Command ". .\scripts\enter-project.ps1; & .\runtime\ollama\ollama.exe serve"
.\.venv\Scripts\python.exe -m vckg.jobs.pipeline_worker select --from data\experiments\phase6b\manifest.jsonl --limit 12 --out data\pipeline\smoke_manifest.jsonl
.\scripts\start-pipeline.ps1 -JobId smoke1 -Manifest data\pipeline\smoke_manifest.jsonl -MaxArticles 12 -MaxQwenCalls 60   # thêm -Resume để chạy tiếp
.\scripts\status-pipeline.ps1 [-JobId smoke1] [-Json]
.\scripts\monitor-pipeline.ps1 -JobId smoke1 [-IntervalSec 10] [-Once]
.\scripts\stop-pipeline.ps1 -JobId smoke1 [-TimeoutSec 180] [-Force]      # -Force chỉ kill PID python của worker
.\.venv\Scripts\python.exe -m vckg.jobs.pipeline_worker finalize --job-id smoke1   # dựng lại QA/staging từ artifact, không suy luận
uv run pytest ; uv run ruff check
```

## 7. Chạy batch mới khi được phê duyệt
1. Chỉ bài ĐÃ lưu trong `data/staging/staging.sqlite` (crawl là bước riêng cần phê duyệt; `--crawl` đang bị từ chối). Tạo manifest JSONL mỗi dòng `{"article_id", "url", "source", "subset"}` (có thể dùng `cli discover` của Phase 5 hoặc `select`).
2. Bật Ollama (`run-job ... ollama serve`), `verify-storage.ps1`.
3. `start-pipeline.ps1 -JobId <mới> -Manifest <file> -MaxArticles <=20 -MaxQwenCalls <trần>`; theo dõi bằng status/monitor; dừng bằng stop; tiếp tục bằng `-Resume`.
4. Đọc kết quả ở `data/pipeline/<job>/` (`summary.json`, `qa_report/*.csv`, `export/staging_*.jsonl|csv`, `status.json`). Khi cần batch >20 bài phải đặt `VCKG_ALLOW_LARGE_BATCH=1` có chủ đích.
5. `official-sync` và hợp nhất registry vẫn bị khóa; cần phê duyệt riêng.

Phase 6C dừng tại đây; không chuyển sang 6D, không khởi chạy production.

