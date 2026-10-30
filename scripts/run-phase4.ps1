# Re-runs the Phase 4 pipeline end to end (small, controlled; NOT a production crawl).
#   .\scripts\run-phase4.ps1            -> offline tests, identity load, process staged selection with GLiNER + Qwen
#   .\scripts\run-phase4.ps1 -Crawl     -> additionally runs the polite signal-targeted crawl first (<= 15 articles/source)
param([switch]$Crawl)
. "$PSScriptRoot\enter-project.ps1"
& "$PSScriptRoot\verify-storage.ps1"
if (-not (Get-Process ollama -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath "$env:VCKG_ROOT\runtime\ollama\ollama.exe" -ArgumentList 'serve' -WindowStyle Hidden `
        -RedirectStandardOutput "$env:VCKG_ROOT\logs\ollama.out.log" -RedirectStandardError "$env:VCKG_ROOT\logs\ollama.err.log"
    Start-Sleep 6
}
uv run pytest -q
uv run ruff check
# 1) identity-only registry from the public Vietstock Finance sitemap (idempotent; one request)
uv run python -m vckg.cli identity-load --provider vietstock
# 2) optional targeted crawl (robots.txt, 2 s/host delay, backoff). Selection list is written to the experiment folder.
if ($Crawl) { uv run python -m vckg.cli crawl-targeted --per-source 15 --min-score 2 }
# 3) work on a COPY of the registry so the provider base stays clean
Copy-Item data\registry\registry.sqlite data\registry\registry_phase4_run.sqlite -Force
uv run python -m vckg.cli process --selection data\outputs\experiment\selected_articles.jsonl `
    --registry data\registry\registry_phase4_run.sqlite --out data\outputs\experiment\phase4_run
# 4) review sample for humans (gold columns stay empty) + evaluator (prints NOT EVALUATED until gold is filled)
uv run python -m vckg.cli annotation-export --runs data\outputs\experiment\phase4_run --n 120 --out reports\phase4_annotation_sample.csv
uv run python -m vckg.cli evaluate reports\phase4_annotation_sample.csv
# live integration tests (GPU/Ollama/internet); unavailable services are reported SKIPPED
uv run pytest -m integration -rs -q
