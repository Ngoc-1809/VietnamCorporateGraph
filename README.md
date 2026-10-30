# Vietnam Corporate Knowledge Graph (VCKG)

Knowledge Graph về lãnh đạo, tập đoàn, công ty và ngân hàng Việt Nam, trích xuất bằng NLP từ báo chí kinh tế – tài chính.

Pipeline: Crawl -> Preprocess -> GLiNER2.5 NER (+ từ điển registry) -> sửa ranh giới span -> Entity Resolver (registry SQLite) ->
mẫu quan hệ theo cấu trúc câu -> lọc trước LLM -> Qwen3.5 verification (JSON schema, cache) -> validator bằng chứng/trạng thái -> cạnh official / candidate.

## Bắt đầu (PowerShell)

```powershell
cd T:\VietnamCorporateGraph
. .\scripts\enter-project.ps1        # bắt buộc: đặt toàn bộ cache/temp về T:
.\scripts\verify-storage.ps1
uv sync --extra ml                   # tạo .venv trên T: (torch CUDA 12.8)
uv run pytest                        # unit tests offline (158)
uv run pytest -m integration -rs     # GPU + Ollama + internet (SKIPPED nếu thiếu)
.\scripts\run-phase4.ps1             # chạy lại Phase 4 (thêm -Crawl để crawl nhỏ có kiểm soát)
```

Ollama: `runtime\ollama\ollama.exe serve` (model `qwen3.5:9b` trong `models\ollama`).

## Phase 5 (30/10/2026)
```powershell
.\scripts\start-neo4j.ps1 ; .\scripts\verify-neo4j.ps1
uv run python -m vckg.graph.neo4j_sync import --runs data\outputs\phase5\dev44 data\outputs\phase5\holdout19 data\outputs\phase5\new144 --registry data\registry\registry_p5_dev.sqlite data\registry\registry_p5_holdout.sqlite data\registry\registry_p5_new.sqlite
uv run python -m vckg.graph.neo4j_sync queries        # Cypher mẫu
.\scripts\status-phase5.ps1   # trạng thái thật (monitor-phase5.ps1 để theo dõi liên tục)
```
Báo cáo: `reports/phase5_report.md`, `reports/phase5_benchmark.md`, `reports/phase5_false_negatives.md`.

## Trạng thái (30/10/2026)

- Phase 0-4 xong ở mức thí nghiệm; chưa production. Chi tiết: `reports/phase4_diagnostics.md` (vì sao 0 cạnh ở Phase 3 và cách sửa) và `reports/phase4_real_news_results.md` (63 bài thật).
- Registry: `data/registry/registry.sqlite` (2.267 định danh VERIFIED `identity_only` từ sitemap công khai của Vietstock Finance; các hàng này **không** phải node đồ thị) + thực thể PROVISIONAL tăng dần từ bài báo.
- Kết quả thí nghiệm: 4 cạnh official + 14 candidate (chờ duyệt người) trên 63 bài; Precision/Recall **NOT EVALUATED** (chưa có gold). Gán nhãn: `reports/phase4_annotation_sample.csv`, đánh giá: `uv run python -m vckg.cli evaluate <csv>`.
- Quy định cho các phiên sau: `AGENTS.md`.
