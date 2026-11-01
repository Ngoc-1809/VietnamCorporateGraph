# AGENTS.md - quy định cho mọi phiên OpenCode trên dự án VCKG

Ngôn ngữ: trao đổi/tài liệu tiếng Việt; code, tên hàm/class/biến/API tiếng Anh.

## 1. Lưu trữ (BẮT BUỘC)
- Mọi dữ liệu dự án nằm dưới `T:\VietnamCorporateGraph`: venv, cache pip/uv/HF/torch, model Ollama, DB, dữ liệu, log, checkpoint.
- LUÔN chạy `. .\scripts\enter-project.ps1` trước khi chạy python/uv/ollama, rồi `.\scripts\verify-storage.ps1`. Nếu có WARN trỏ về C: thì dừng và sửa.
- Ollama chạy từ `runtime\ollama\ollama.exe`, `OLLAMA_MODELS=T:\VietnamCorporateGraph\models\ollama`. Nếu có tiến trình ollama khác (cài ở C:) đang chạy, kiểm tra nó dùng đúng đường dẫn trước khi pull.
- Docker Desktop: chưa xác minh disk image nằm ở T: -> KHÔNG dùng Docker/Neo4j container cho tới khi xác minh.
- Không xóa/sửa môi trường cũ của người dùng (C:\Users\admin\.cache, miniconda...). Kiểm tra dung lượng T: trước mỗi lần tải lớn.
- Không commit: model weights, DB, bài báo thô, secrets, `.env`. Không xóa SQLite đã tạo (registry, staging, llm_cache); chạy trên bản sao khi cần.

## 2. Nguồn dữ liệu
- Graph chỉ xây từ BÀI BÁO (CafeF, Vietstock, VnEconomy, Báo Đầu tư, báo VN phù hợp). Cấm Wikipedia/Wikidata/bài báo khoa học làm đầu vào graph.
- Hồ sơ doanh nghiệp (cổng tài chính) chỉ để Entity Registry (tên/alias/ticker), ghi provenance riêng (`provider`, `source_url`, `fetched_at`, `identity_only=1`), KHÔNG sinh cạnh. Adapter hiện có: `VietstockSitemapProvider` (ticker + slug tên pháp nhân từ sitemap.xml công khai, ~2.270 công ty; điều khoản sử dụng CHƯA được rà soát nên chỉ dùng cho định danh, không lưu nội dung trang) và `HandwrittenSeedProvider` (19 mục viết tay, PROVISIONAL, không phải nguồn xác minh).
- Crawler: tuân thủ robots.txt, rate limit, backoff, không vượt login/paywall/anti-forgery (ví dụ không gọi AJAX có token chống giả mạo của Vietstock). Không production crawl khi chưa được phê duyệt. `crawl-targeted` chỉ dùng cho thí nghiệm nhỏ (<=15 bài/nguồn).

## 3. Schema và quy tắc cạnh
- Node chính: Person, Organization, Bank (subtype), Regulator/Authority, BondIssue (khi cần). Article/Evidence KHÔNG tính vào số entity nodes. Hàng registry (VERIFIED identity-only hay PROVISIONAL) KHÔNG phải node đồ thị; chỉ thực thể nằm trong cạnh có bằng chứng mới tính vào KPI.
- Predicates: CHAIR_OF, CEO_OF, BOARD_MEMBER_OF, FOUNDED, OWNS_SHARES_IN, SUBSIDIARY_OF, ACQUIRED, LENDS_TO, ISSUED_BOND, JOINT_VENTURE_WITH, PARTNERS_WITH, SANCTIONED_BY, PROSECUTED_BY. Mẫu theo cấu trúc câu + chính sách trạng thái nằm trong `config/relations.yaml` (S = chủ thể theo hướng quan hệ, O = đối tượng; ví dụ SANCTIONED_BY: S = bên bị phạt, O = cơ quan). ISSUED_BOND chưa có mẫu (cần node BondIssue).
- Mỗi cạnh = (subject_id, predicate, object_id) duy nhất, nhiều EvidenceRecord (article_id, source_url, evidence_text + offsets, published_at, extraction_method, model, prompt_version, review_status, factual_status, valid_from/to).
- factual_status: FACT(=CONFIRMED), PLANNED, ALLEGED, DENIED(=NEGATED), HISTORICAL, ENDED, UNKNOWN. Chính sách (`status_policy` trong relations.yaml): FACT/HISTORICAL/ENDED có thể official; PLANNED/ALLEGED/UNKNOWN chỉ là candidate; DENIED không bao giờ tạo cạnh. "Khởi tố" = bị truy tố, KHÔNG phải bị kết tội.
- **Official** = verifier valid + không có lý do chặn + trạng thái official theo chính sách + endpoint đạt `endpoint_policy` (tổ chức: VERIFIED; người: cụm định danh trong bài có đủ họ tên, VERIFIED hoặc PROVISIONAL; cơ quan: VERIFIED/PROVISIONAL). Endpoint tổ chức PROVISIONAL -> `candidate_edge` (`ENDPOINT_NOT_VERIFIED`), chờ người duyệt, không tính vào đồ thị chính thức.
- LLM chỉ làm CHẶT thêm: không ghi đè phủ định/hướng suy ra từ cấu trúc/định danh endpoint/bằng chứng. HISTORICAL/ENDED của LLM chỉ được nhận khi tầng luật cũng có dấu hiệu từ vựng. Quote của LLM phải là chuỗi con hoặc dãy con có thứ tự của câu nguồn.
- Cấm co-occurrence làm cạnh. Entity chưa link chắc chắn -> `unresolved`/`ambiguous`, không tạo cạnh. Không merge theo tên giống nhau: người = `person:{tên}@art:{article_id}` (cụm trong một bài); chỉ gộp cụm khác bài khi cùng tên chuẩn hóa + chung tổ chức (`consolidate_persons`, có log, idempotent); công ty trùng tên chuẩn hóa nhưng khác ticker VERIFIED giữ thành 2 entity. Ticker chỉ liên kết khi có từ khóa ngữ cảnh ("cổ phiếu", "mã", "HOSE:"...) hoặc tên đầy đủ xuất hiện trong bài; không suy ticker từ chữ in hoa.
- Cạnh derived (person-person, company-company) phải có nhãn `derived=True` riêng.
- Điểm số tách riêng, null khi backend không có: `ner_score` (GLiNER), `linking_score` (chỉ khớp mờ), `relation_score` (hiện luôn null, `score_available=false`). KHÔNG lưu/diễn giải confidence tự khai của LLM như xác suất.

## 4. Quality gates
- Unit tests offline: `uv run pytest` phải xanh. Integration (GPU/Ollama/internet) đánh dấu `@pytest.mark.integration`, báo SKIPPED khi không có dịch vụ; cấm mock rồi báo PASS. FakeNER/AcceptAll trong `tests/helpers.py` chỉ cho unit test, không được dùng để báo chất lượng GLiNER/Qwen.
- Edge Precision/NER P-R-F1 chỉ được công bố dựa trên tập gán nhãn thật: `reports/phase4_annotation_sample.csv` (120 câu, cột gold TRỐNG - người dùng phải điền) rồi `uv run python -m vckg.cli evaluate <csv>`. Hiện: NOT EVALUATED. Không suy diễn chất lượng từ vài mẫu; không dùng số "linked PROVISIONAL" như độ chính xác.
- Mẫu quan hệ đã được chỉnh theo lỗi của 44 bài dev -> không còn là phép đo độc lập; hold-out chỉ 19 bài. Muốn đo mới phải dùng bài mới.
- Mục tiêu 11/11/2026: >=2.000 entity, >=5.000 quan hệ, >=10 loại quan hệ. Hiện (63 bài gốc + 144 bài mới, Phase 5): 44 cạnh official unique, 74 domain entity nodes, 8 loại predicate trong Neo4j (xem reports/phase5_report.md). Dài hạn ~10k nodes, 30-50k edges, precision >=90%.
- `ruff check` sạch trước khi kết thúc.

## 5. Lệnh chính
```
. .\scripts\enter-project.ps1
.\scripts\verify-storage.ps1
uv run pytest
uv run pytest -m integration -rs      # cần GPU/Ollama/internet
.\scripts\run-prototype.ps1           # prototype trên câu giả định (GLiNER + Qwen thật)
.\scripts\run-phase4.ps1 [-Crawl]     # identity load + (crawl nhỏ) + xử lý + export gán nhãn + evaluate
uv run python -m vckg.cli {identity-load|crawl-targeted|process|annotation-export|evaluate|prototype}
uv run python -m vckg.diagnostics     # chẩn đoán baseline Phase 3 (reports/phase4_diagnostics.md)
```

## 6. Bản đồ mã (Phase 4)
- `entity_linking/store.py` RegistryStore (SQLite: entities, aliases, identity_sources, mentions, person_context, history, merge_rejections; add_entity/add_alias/find_candidates/merge_entities/reject_merge/get_resolution_history); `resolver.py` EntityResolver; `identity.py` IdentityProvider + adapters; `normalize.py` chuẩn hóa tên (bỏ dấu trước, rồi bỏ tiền tố/hậu tố pháp lý). `registry.py`/`dictionary.py`/`linker.py` là bản Phase 3 (giữ cho test cũ, pipeline mới không dùng).
- `relation_extraction/candidates.py` (che mention, khớp mẫu, hướng từ cấu trúc), `modality.py` (trạng thái theo cửa sổ quanh quan hệ), `qwen_verifier.py` (schema JSON ràng buộc, prompt_version, cache SQLite `data/staging/llm_cache.sqlite`, đếm token/độ trễ).
- `validation/evidence.py` EdgeStore (outcome official|candidate_edge|rejected + `reasons.py` mã lý do thống nhất, lọc trước LLM); `pipeline.py` (Counters funnel); `ner/merge.py` sửa ranh giới span; `ner/scope.py` lọc ngoài domain (heuristic, không phải ground truth).
- `annotation.py`, `evaluation.py`, `crawlers/targeted.py`, `diagnostics.py`, `cli.py`.

## 6b. Phase 5 (đọc trước khi sửa)
- Định danh: `VERIFIED`(=EXTERNAL_VERIFIED) > `ARTICLE_GROUNDED` > `PROVISIONAL` > `AMBIGUOUS`. Quy tắc nâng cấp ở `entity_linking/grounding.py` (tổ chức: dạng pháp lý + tên riêng viết hoa, hoặc `<Tên> Group/Holdings/Bank`; người: họ tên đủ + có tổ chức cùng câu; cơ quan: tiền tố cơ quan + tên; acronym trần không bao giờ). Có xung đột định danh (ứng viên gần giống) thì KHÔNG nâng. `endpoint_policy` trong relations.yaml: ORG/PERSON/AUTHORITY/BOND = VERIFIED hoặc ARTICLE_GROUNDED mới official. Acronym chỉ mở rộng từ chữ cái đầu của tên đầy đủ TRONG CÙNG BÀI hoặc `(VAMC)` định nghĩa trong bài.
- Mẫu quan hệ: danh sách đối tượng, vai trò trong ngoặc (`raw: true`), `đồng thời là`, bị động, `sau khi ... , S`. Đại từ ông/bà và đối tượng bị lược (OWN) lấy từ câu trước: `direction_source=coref|elided_object` -> LUÔN candidate (`COREF_REVIEW`), bằng chứng là đoạn nhiều câu liền kề. Span tổ chức bị cắt (từ viết hoa liền sau) -> `SPAN_BOUNDARY_SUSPECT` (candidate). Mention ngoài scope (HĐQT, HĐTV, chỉ số) không phải đầu mối của mẫu.
- ISSUED_BOND: node `BondIssue` (`relation_extraction/bonds.py`): chỉ ARTICLE_GROUNDED khi bài nêu số tiền + (kỳ hạn|lãi suất|ngày) hoặc mã trái phiếu in trong bài; không tự tạo mã/ngày; không mã/ngày thì không gộp giữa các bài.
- Qwen prompt `v5` (cache key gồm prompt_version). `valid=true` kèm `rejection_reason!=NONE` được ghi `llm_inconsistent_rejection_reason` (quan sát thấy nhiều lần).
- KPI chuẩn: `metrics.py` (`graph_entity_nodes` chỉ đếm thực thể trong cạnh official; cạnh unique theo (s,p,o,cửa sổ hiệu lực); nhiều nguồn = 1 cạnh). Báo cáo nhóm: `phase5_report.py`.
- Chọn bài: `crawlers/discovery.py` + `cli discover` (targeted 75% / control ngẫu nhiên 25%, nhóm trùng tiêu đề, seed). Ranking chỉ để chọn bài, không phải bằng chứng.
- Review: `review.py` + `cli review-*` (SQLite `data/review/review.sqlite`, lịch sử append-only, ACCEPT bị từ chối nếu endpoint chưa VERIFIED/ARTICLE_GROUNDED hoặc status không official, HUMAN_VERIFIED không chứng minh sự kiện ngoài đời).
- Gold: `annotation-export`, `annotation-export-full`, `evaluate [--registry db] [--split development|blind_holdout]`; cột `split` suy từ hash article_id; blind_holdout KHÔNG dùng để chỉnh. Hiện NOT EVALUATED.
- Neo4j: `runtime\neo4j` (Community 2026.10.1, JDK 21 tại `runtime\jdk\jdk21`, chỉ 127.0.0.1, mật khẩu trong `.neo4j-auth` đã gitignore). `scripts\start-neo4j.ps1|stop-neo4j.ps1|verify-neo4j.ps1`; `python -m vckg.graph.neo4j_sync {ping|constraints|import|stats|queries|projections}`. Official = `(:Entity)`+kiểu quan hệ; candidate ở `(:CandEntity)-[:CANDIDATE]->`; import idempotent; gộp người liên-run chỉ khi cùng tên chuẩn hóa + cùng tổ chức (có log).
- Chạy lâu: `scripts\run-job.ps1` (tách hoàn toàn khỏi OpenCode, PID/log/exitcode ở `logs\jobs`), `scripts\status-phase5.ps1`, `scripts\monitor-phase5.ps1`.

## 6c. Phase 6C - worker end-to-end độc lập (staging only)
- `src/vckg/jobs/pipeline_worker.py` (điều phối, checkpoint, khóa, status, staging graph) + `jobs/stages.py` (stage từng bài, tái dùng module cũ). Job nằm ở `data/pipeline/<job_id>/` (gitignored): `pipeline.sqlite` (articles/artifacts/staging_*), `registry.sqlite` (BẢN SAO riêng của registry nguồn), `status.json` (heartbeat), `events.jsonl`, `STOP`, `worker.lock`, `qa/`, `export/`. Cache có version dùng chung: `data/pipeline/_cache/` (NER, Qwen).
- Lệnh: `scripts\start-pipeline.ps1|status-pipeline.ps1|monitor-pipeline.ps1|stop-pipeline.ps1`. `-Resume` = chạy tiếp cùng JobId (bài DONE cùng fingerprint không xử lý lại). Chỉ `status.json` là nguồn sự thật (wrapper run-job có thể ghi FAILED cho STOPPED/partial). Không có heartbeat > 60 s => STALE; PID chết không có trạng thái cuối => DEAD.
- Chế độ chỉ `staging` (xuất JSONL/CSV vào thư mục job; không đụng Neo4j). `official-sync` bị từ chối trong 6C. Trần 20 bài/lần; `--crawl` không bật. Bài lỗi => FAILED (exit 4), KHÔNG báo COMPLETED. SEMANTIC_ONLY_CLEAN = quarantine, không bao giờ official.

## 6d. Chiến dịch khối lượng lớn (mass campaign, staging + Neo4j validated layer)
- `src/vckg/campaign/`: `queue.py` (SQLite bền: discovery/crawl/parse/nlp tách trạng thái; raw HTML zlib ở `raw_pages.sqlite`), `discover.py` (sitemap/RSS/category, chấm điểm slug), `acquire.py` (1 thread/nhà xuất bản, >=2,5 s/host, trần cứng 30.000 bài MỚI), `process.py` (1 worker GPU, chunk 200 bài, ngân sách Qwen toàn chiến dịch 90.000, hết ngân sách => DEFERRED không phải DONE), `supervisor.py` (giữ worker/Ollama sống, KPI, tóm tắt mỗi 1.000 bài, báo cáo cuối, Neo4j sync định kỳ). Dữ liệu: `data/campaign/mass/` (gitignored); chunk: `data/pipeline/camp-cNNNNN/`.
- Lệnh: `scripts\start-campaign.ps1 [-Resume]`, `status-campaign.ps1`, `monitor-campaign.ps1`, `stop-campaign.ps1`, `install-campaign-watchdog.ps1 [-Remove]` (task định kỳ 5 phút; supervisor tự gỡ khi xong). Trạng thái cuối: COMPLETED chỉ khi không còn bài pending/deferred/failed; ngược lại INCOMPLETE kèm lý do.
- Chỉ crawl nguồn `cleared: true` trong `config/crawl_compliance.yaml` (CafeF, Vietstock). VnEconomy/Báo Đầu tư bị loại (điều khoản yêu cầu đồng ý bằng văn bản). Throttle theo TÊN host (http/https dùng chung); log thời điểm bắt đầu từng request; audit mỗi 100 bài, vi phạm => acquire FAILED, không tự thử lại.
- Registry chuỗi: `registry_cumulative.sqlite` (bản sao tích lũy từ registry p5, KHÔNG ghi registry gốc). Aggregator (`graph/aggregate.py`) gộp người liên-nguồn CHỈ khi cùng họ tên đầy đủ + chung tổ chức trong cạnh đã kiểm (LEGACY_OFFICIAL/QA_PASS) + định danh >= ARTICLE_GROUNDED; có log `person_merges`.
- Neo4j: `graph/neo4j_validated.py` chỉ ghi lớp `V*` (VEntity, VEvidence, VArticle; layer=QA_VALIDATED, official=false, gold=false) từ tầng QA_PASS, sau backup nguội có xác minh hash (`data/campaign/neo4j_backup/`), dry-run, MERGE idempotent; legacy (74 node/44 cạnh official) phải không đổi sau mỗi lần sync. QUARANTINE/REJECT không bao giờ vào Neo4j. Không backup được => bỏ qua Neo4j, vẫn tích lũy SQLite/GraphML/CSV.
- Subprocess gọi script PowerShell phải ghi ra FILE, không dùng pipe (JVM/worker con giữ pipe làm treo).

## 7. Hạn chế đã biết / việc dở
- Neo4j đã có (Phase 5); `graph/neo4j_export.py` (CSV) là bản cũ chưa cập nhật. Chưa chạy chỉ số small-world (đã có export projection GraphML/CSV).
- Đa số công ty chưa niêm yết không có trong nguồn định danh -> cạnh chỉ là candidate. Cần quy trình duyệt người (`HUMAN_VERIFIED`) hoặc thêm nguồn định danh hợp lệ.
- GLiNER chia nhỏ/gán nhầm loại một số tên; NER cấp câu mặc định (+85% mention, chưa chứng minh tốt hơn cả bài - dùng `--doc-ner` để so sánh).
- Qwen có thể từ chối nhầm hoặc gán HISTORICAL cho câu hiện tại; chưa đo bằng gold.
- Báo Đầu tư: chỉ khám phá qua trang chuyên mục công khai; RSS/sitemap tin tức không dùng được (2026-10-30).
