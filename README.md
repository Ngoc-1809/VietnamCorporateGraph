# Vietnam Corporate Knowledge Graph (VCKG)

VCKG là pipeline xây dựng knowledge graph về doanh nghiệp, ngân hàng, lãnh đạo và cơ quan quản lý Việt Nam từ **bài báo kinh tế – tài chính tiếng Việt**. Dự án ưu tiên provenance, bằng chứng theo span, trạng thái sự kiện và khả năng chạy lại có checkpoint; không tạo cạnh từ co-occurrence hoặc từ hồ sơ doanh nghiệp.

> Trạng thái nghiên cứu, chưa production. Chưa có tập gold hoàn chỉnh nên precision/recall/F1 vẫn là **NOT EVALUATED**. `QA_PASS` là kết quả qua rule/validator, không đồng nghĩa với gold hoặc sự thật đã được con người xác minh.

## Trạng thái hiện tại — 20/11/2026

Chiến dịch đã xử lý **30.000/30.000 bài báo** qua NLP, không còn bài lỗi. Snapshot cuối kỳ `20261120-144636-gate-v2` được dựng từ Global ER v2 sau khi kiểm tra lại tier QA, trạng thái sự kiện và danh tính hai đầu cạnh.

| Tầng | Node thực thể | Cạnh | Loại quan hệ | Cách dùng |
|---|---:|---:|---:|---|
| Đồ thị ứng dụng đã lọc | 2.433 | 2.064 | 12 | Chân dung node, phân tích mạng, GraphRAG |
| ER v2 validated trước cổng ứng dụng | 2.804 | 2.453 dòng edge-tier | 13 | Đối chiếu và kiểm tra nguồn |
| ER v2 exploratory | 21.884 | 33.087 dòng edge-tier | 13 | Khảo sát lỗi; gồm `QUARANTINE`, không dùng để tuyên bố độ chính xác |

Cột 2.064 của ứng dụng là **dòng cạnh**; nếu gộp theo đúng bộ `(chủ thể, loại quan hệ, đối tượng)` thì có **1.978 quan hệ khác nhau**. Benchmark precision lấy ngẫu nhiên từ 1.978 bộ này.

Cổng ứng dụng loại 590 dòng chứng cứ có endpoint không đạt điều kiện sau ER, 6 dòng sai chứng cứ được soát từ bài gốc, cùng 6 dòng trạng thái `PLANNED`/`ALLEGED`. Mỗi cạnh hiển thị có URL và đoạn chứng cứ. Neo4j lưu 2.433 `FEntity` và 2.064 `F_RELATION` trong namespace riêng; lớp legacy và validated trước đó không đổi. Đồ thị toàn phần có 620 thành phần liên thông, thành phần lớn nhất 673 node; khoảng cách trung bình 7,540 và hệ số small-world 11,212 chỉ áp dụng trên thành phần lớn nhất. PageRank, Louvain và k-core đã được tính cho node.

Mốc **2.000 node và 10 loại quan hệ đã đạt**, mốc **5.000 cạnh chưa đạt**. Chất lượng trên 90% vẫn **NOT EVALUATED**: `QA_PASS` là kết quả kiểm tra tự động, không phải nhãn gold. Phiếu 300 mẫu trong `reports/final_project/quality_sample_20261120-144636.csv` được giữ local để tìm lỗi theo từng loại quan hệ. Mẫu này được cân bằng gần đều giữa các loại nên **không dùng để ước lượng precision toàn đồ thị**. Phiếu benchmark ngẫu nhiên riêng được xuất bằng lệnh dưới đây; cả hai file có trích đoạn báo nên không đưa lên Git.

Sản phẩm cuối kỳ: [báo cáo PDF](reports/final_project/topic17_final_report.pdf), [slide PDF](reports/final_project/topic17_final_slides.pdf), [giao diện chân dung node](src/vckg/final_project/static/index.html), [ghi chú audit](reports/final_project/assistant_audit_notes.md). DB, bài báo thô, model, cache, graph preview, output ER và phiếu kiểm định được giữ local trên ổ T:.

### Chạy và dựng lại ứng dụng cuối kỳ

```powershell
cd T:\VietnamCorporateGraph
. .\scripts\enter-project.ps1
.\scripts\verify-storage.ps1
.\scripts\start-final-project.ps1       # mở http://127.0.0.1:8765

# Dựng lại từ campaign đang có; không chạy crawler:
.\scripts\rebuild-final-project.ps1
```

`start-final-project.ps1` tự bật Neo4j local và nhập snapshot riêng; nếu Ollama `qwen3.5:9b` không chạy, ứng dụng vẫn trả đường đi và chứng cứ từ graph. Để bật phần diễn đạt GraphRAG bằng Qwen, chạy `runtime\ollama\ollama.exe serve` sau bước `enter-project.ps1`. Snapshot đang dùng được chỉ bởi `data/final_project/ACTIVE.txt`. Dữ liệu này không nằm trên GitHub, vì chứa nội dung báo; cần corpus local để dựng lại hoặc chạy demo đầy đủ.

### Kiểm định chất lượng

Xuất 200 bộ ba `(chủ thể, quan hệ, đối tượng)` ngẫu nhiên không trùng từ snapshot ứng dụng:

```powershell
uv run python -m vckg.final_project.quality_audit export-benchmark --out reports/final_project/benchmark_random.csv
```

Hai thành viên đọc bài gốc và điền `valid_relation` (gồm chiều cạnh), `valid_endpoints`, `valid_evidence`, `valid_status` bằng `YES`/`NO`, tên người duyệt và `review_mode=HUMAN_FULL_ARTICLE` cho **toàn bộ 200 dòng**. Sau đó chạy `uv run python -m vckg.final_project.quality_audit evaluate reports/final_project/benchmark_random.csv`. Chỉ mẫu ngẫu nhiên được duyệt đủ mới có ước lượng precision và khoảng Wilson 95%; mẫu cân bằng chỉ báo lỗi theo loại. Cần mẫu span gán nhãn riêng để đo NER recall/F1.

## Pipeline hiện hành

```text
Discovery -> compliance gate -> crawl/parse queue
  -> Phase 6C worker theo chunk (GLiNER + registry/resolver)
  -> rule candidates + Qwen discovery
  -> hard validation + hybrid QA
  -> aggregate graph theo tier
  -> Neo4j QA_VALIDATED layer / CSV / GraphML / viewer
  -> Global Entity Resolution v2
  -> cổng cạnh ứng dụng -> PageRank / Louvain / k-core / small-world
  -> Neo4j F* + giao diện chân dung node + hỏi đáp GraphRAG có trích dẫn
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
- Campaign hiện tại đã xử lý hết 30.000 bài được chọn; không tự chạy crawl khi clone repository.

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
- `data/final_project/`: snapshot SQLite/metrics cho ứng dụng cuối kỳ; `ACTIVE.txt` chọn bản đang dùng.

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

Trạng thái kiểm thử tại 20/11/2026:

- `347 passed` offline; 7 integration test được tách khỏi lệnh mặc định.
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
  final_project/       # snapshot, SNA, Neo4j F*, app GraphRAG, báo cáo/slide
config/                # relation schema, NER labels, crawl compliance
scripts/               # PowerShell entrypoints
tests/                 # offline unit/regression + integration markers
reports/               # báo cáo đã chọn để lưu trong Git
```

Quy tắc kỹ thuật và provenance chi tiết nằm trong [`AGENTS.md`](AGENTS.md). Báo cáo theo giai đoạn được giữ để truy vết lịch sử; sản phẩm cuối kỳ dùng snapshot được lọc từ mass campaign + aggregate + ER v2.
