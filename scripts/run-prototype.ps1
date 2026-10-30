# End-to-end prototype on hypothetical fixture sentences: offline tests, live integration tests, live GLiNER + Qwen run.
param([switch]$Crawl)
. "$PSScriptRoot\enter-project.ps1"
& "$PSScriptRoot\verify-storage.ps1"
if (-not (Get-Process ollama -ErrorAction SilentlyContinue)) {
    Start-Process -FilePath "$env:VCKG_ROOT\runtime\ollama\ollama.exe" -ArgumentList 'serve' -WindowStyle Hidden `
        -RedirectStandardOutput "$env:VCKG_ROOT\logs\ollama.out.log" -RedirectStandardError "$env:VCKG_ROOT\logs\ollama.err.log"
    Start-Sleep 6
}
uv run pytest -q
uv run pytest -m integration -rs -q
uv run python -m vckg.cli prototype
if ($Crawl) { uv run python -m vckg.cli crawl --limit 3 }
uv run ruff check
