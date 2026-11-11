# Vietnam Corporate Knowledge Graph (VCKG)

VCKG là pipeline xây dựng knowledge graph về doanh nghiệp, ngân hàng, lãnh đạo và cơ quan quản lý Việt Nam từ **bài báo kinh tế – tài chính tiếng Việt**. Dự án ưu tiên provenance, bằng chứng theo span, trạng thái sự kiện và khả năng chạy lại có checkpoint; không tạo cạnh từ co-occurrence hoặc từ hồ sơ doanh nghiệp.

> Trạng thái nghiên cứu, chưa production. Chưa có tập gold hoàn chỉnh nên precision/recall/F1 vẫn là **NOT EVALUATED**. `QA_PASS` là kết quả qua rule/validator, không đồng nghĩa với gold hoặc sự thật đã được con người xác minh.

## Trạng thái hiện tại — 11/11/2026

Mass campaign đã được **chủ động dừng** sau khi thu đủ dữ liệu cho giai đoạn hiện tại. Toàn bộ checkpoint vẫn được giữ local để có thể resume sau này.

| Hạng mục | Kết quả |
|---|---:|
| Bài đã khám phá | 49.810 |
| Bài đã tải / parse | 30.380 / 30.000 |
| Bài đã chạy NLP | 12.017 |
| Mention | 491.172 |
| Candidate unique trước ER v2 | 21.961 |
| Qwen live calls | 25.869 |
| Loại quan hệ | 13 |

Đồ thị canonical sau Global Entity Resolution v2:

| Layer | Entity nodes | Edge-tier rows | Ghi chú |
|---|---:|---:|---|
| Validated | 1.868 | 1.516 | 44 `LEGACY_OFFICIAL` + 1.472 `QA_PASS` |
| Exploratory | 14.219 | 20.417 | Gồm thêm 18.901 `QUARANTINE`; không dùng để tuyên bố chất lượng |

ER v2 đã canonicalize 15.408 node gốc thành 14.219 node, gộp 1.189 node trong 479 cluster; giữ nguyên tập evidence, tier, hướng cạnh và không sinh self-loop mới. Mục tiêu 2.000 node / 5.000 quan hệ **chưa đạt trên validated layer**; exploratory layer không được dùng để thay thế KPI này.

Báo cáo tracked mới nhất: [`reports/campaign_final.md`](reports/campaign_final.md). Các DB, raw article corpus, model, cache, graph preview và output ER dung lượng lớn được giữ local; Git chỉ lưu mã nguồn, cấu hình, fixture và các báo cáo đã chọn.

## Pipeline hiện hành

```text
Discovery -> compliance gate -> crawl/parse queue
  -> Phase 6C worker theo chunk (GLiNER + registry/resolver)
  -> rule candidates + Qwen discovery
  -> hard validation + hybrid QA
  -> aggregate graph theo tier
  -> Neo4j QA_VALIDATED layer / CSV / GraphML / viewer
  -> Global Entity Resolution v2
```

Các thuộc tính quan trọng:

- Mỗi cạnh có một hoặc nhiều `EvidenceRecord`: article, URL, quote + offsets, thời gian, phương pháp trích xuất, model/prompt và trạng thái review/sự kiện.
- `FACT`, `HISTORICAL`, `ENDED` có thể vào tầng validated khi endpoint và verifier đạt chính sách; `PLANNED`, `ALLEGED`, `UNKNOWN` chỉ là candidate; `DENIED` không tạo cạnh.
- Entity chưa link chắc chắn được giữ `unresolved`/`ambiguous`; không merge chỉ vì tên giống nhau.
- Registry từ cổng tài chính chỉ phục vụ định danh (`identity_only=1`), không sinh cạnh.
- Quan hệ: `CHAIR_OF`, `CEO_OF`, `BOARD_MEMBER_OF`, `FOUNDED`, `OWNS_SHARES_IN`, `SUBSIDIARY_OF`, `ACQUIRED`, `LENDS_TO`, `ISSUED_BOND`, `JOINT_VENTURE_WITH`, `PARTNERS_WITH`, `SANCTIONED_BY`, `PROSECUTED_BY`.

## Nguồn và compliance

- Graph chỉ lấy bằng chứng từ bài báo phù hợp; không dùng Wikipedia/Wikidata hoặc bài báo khoa học làm đầu vào graph.
- Mass campaign hiện chỉ crawl các nguồn có `cleared: true` trong `config/crawl_compliance.yaml`: CafeF và Vietstock.
- VnEconomy và Báo Đầu tư bị loại khỏi mass crawl vì điều khoản yêu cầu đồng ý bằng văn bản.
- Crawler tuân thủ robots.txt, rate limit/backoff, không vượt login/paywall/anti-forgery.
- Mốc campaign hiện tại đã dừng chủ động; không tự chạy crawl khi clone repository.

## Cài đặt

Dự án được thiết kế cho Windows/PowerShell và root cố định `T:\VietnamCorporateGraph`. Python, venv, model, cache và dữ liệu runtime phải nằm dưới root này.

Yêu cầu:

- Python 3.11 do `uv` quản lý.
- `uv` khả dụng trên PATH hoặc đặt portable tại `runtime\uv-bin`.
- GPU/CUDA chỉ cần cho GLiNER inference thật; unit test offline không yêu cầu GPU.
- Ollama portable + `qwen3.5:9b` chỉ cần cho các stage LLM/integration.

```powershell
cd T:\VietnamCorporateGraph
. .\scripts\enter-project.ps1
.\scripts\verify-storage.ps1
.\scripts\setup-env.ps1

uv run pytest
uv run ruff check
```

`enter-project.ps1` phải được dot-source trước mọi lệnh Python/uv/Ollama để cache và temp không rơi về ổ C:. Docker/Neo4j container không được dùng; Neo4j local nằm trong `runtime\neo4j`.

## Lệnh vận hành chính

### Campaign và worker

```powershell
.\scripts\status-campaign.ps1
.\scripts\monitor-campaign.ps1
.\scripts\start-campaign.ps1 -Resume   # chỉ dùng khi chủ động muốn chạy tiếp
.\scripts\stop-campaign.ps1

.\scripts\status-pipeline.ps1
.\scripts\monitor-pipeline.ps1
```

Campaign là luồng chính cho khối lượng lớn. Mỗi chunk dùng Phase 6C worker có checkpoint, cache versioned và registry riêng; aggregate được cập nhật idempotent theo source/tier.

### Aggregate, preview và ER v2

```powershell
.\scripts\aggregate-graph.ps1 -Verify
uv run python -m vckg.graph.preview build

.\scripts\er-v2.ps1 status
.\scripts\er-v2.ps1 start              # resume; stage đã DONE sẽ được bỏ qua
```

Output local chính:

- `data/aggregate/`: SQLite aggregate + CSV/GraphML.
- `data/graph_preview/<snapshot>/`: snapshot và viewer trước ER.
- `data/entity_resolution/v2/`: mapping canonical, graph V2, viewer và manual-review sample.
- `data/pipeline/`: checkpoint/artifact từng worker job.
- `data/campaign/mass/`: queue, raw pages nén, registry cumulative và campaign status.

ER v2 chỉ đọc snapshot và dựng mapping/graph mới ở staging; nó không sửa tier QA hay ghi ngược vào Neo4j.

### Neo4j

```powershell
.\scripts\start-neo4j.ps1
.\scripts\verify-neo4j.ps1
uv run python -m vckg.graph.neo4j_validated plan
uv run python -m vckg.graph.neo4j_validated sync
uv run python -m vckg.graph.neo4j_validated verify
.\scripts\stop-neo4j.ps1
```

Neo4j chỉ nhận validated layer sau cold backup và dry-run. `QUARANTINE`/`REJECT` không được sync vào lớp `V*`; legacy official graph phải giữ nguyên.

## Quality gates

Trạng thái kiểm thử tại commit hiện tại:

- `330 passed` offline; 7 integration test được tách khỏi lệnh mặc định.
- `ruff check` sạch.
- Integration test dùng GPU/Ollama/internet/Neo4j thật và phải báo `SKIPPED` nếu dịch vụ không có; mock không được báo như kết quả integration.
- Edge precision và NER P/R/F1 chỉ được công bố sau khi người dùng điền gold và chạy `python -m vckg.cli evaluate ...`.

```powershell
uv run pytest
uv run pytest -m integration -rs
uv run ruff check
```

## Cấu trúc repository

```text
src/vckg/
  campaign/            # discovery/acquire/process/supervisor khối lượng lớn
  jobs/                # worker checkpointed, pilot/scale-up orchestration
  entity_linking/      # registry SQLite, resolver, article grounding
  entity_resolution/   # Global Entity Resolution v2
  relation_extraction/ # rule candidates, modality, Qwen discovery/verifier
  validation/          # hard gate, evidence store, hybrid QA
  graph/               # aggregate, Neo4j sync, preview/projection
config/                # relation schema, NER labels, crawl compliance
scripts/               # PowerShell entrypoints
tests/                 # offline unit/regression + integration markers
reports/               # báo cáo đã chọn để lưu trong Git
```

Quy tắc kỹ thuật và provenance chi tiết nằm trong [`AGENTS.md`](AGENTS.md). Báo cáo theo giai đoạn được giữ để truy vết lịch sử; pipeline hiện hành là mass campaign + aggregate + ER v2.
