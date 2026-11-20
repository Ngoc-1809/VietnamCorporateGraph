# Run the local final-project demo on 127.0.0.1:8765. Uses data/final_project/ACTIVE.txt.
param([switch]$NoNeo4j)
$projectRoot = 'T:\VietnamCorporateGraph'
Set-Location -LiteralPath $projectRoot
. "$projectRoot\scripts\enter-project.ps1"
& "$projectRoot\scripts\verify-storage.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not $NoNeo4j) {
    & "$projectRoot\scripts\start-neo4j.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    uv run python -m vckg.final_project.neo4j_sync
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
try {
    $models = (Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3).models
    if (-not ($models.name -contains 'qwen3.5:9b')) { Write-Warning 'Ollama is up but qwen3.5:9b is absent; answers will use cited graph paths.' }
} catch {
    Write-Warning 'Ollama is not running; answers will use cited graph paths. Start runtime\ollama\ollama.exe serve after enter-project.ps1 to enable Qwen.'
}
Write-Host 'Open http://127.0.0.1:8765'
uv run uvicorn vckg.final_project.app:app --host 127.0.0.1 --port 8765
