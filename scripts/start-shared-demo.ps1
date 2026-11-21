# Serve the installed SQLite snapshot without requiring Neo4j, Ollama, GPU or the crawler.
param([int]$Port = 8765)
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path.TrimEnd('\')
Set-Location -LiteralPath $projectRoot
. "$projectRoot\scripts\enter-project.ps1"
& "$projectRoot\scripts\verify-storage.ps1"
if ($LASTEXITCODE -ne 0) { throw 'Project storage verification failed' }
$active = "$projectRoot\data\final_project\ACTIVE.txt"
if (-not (Test-Path -LiteralPath $active)) { throw 'Install a snapshot with install-shared-demo.ps1 first' }
$snapshot = (Get-Content -LiteralPath $active -Raw).Trim()
foreach ($name in 'profile.sqlite','quarantine.sqlite','metrics.json','quarantine_metrics.json') {
    if (-not (Test-Path -LiteralPath (Join-Path $snapshot $name))) { throw "Snapshot is missing $name" }
}
$env:PYTHONPATH = "$projectRoot\src"
$env:VCKG_FINAL_SNAPSHOT = $snapshot
$env:VCKG_DISABLE_NEO4J = '1'
$env:VCKG_DISABLE_OLLAMA = '1'
Write-Host "Snapshot: $snapshot"
Write-Host "Open http://127.0.0.1:$Port/ (Ctrl+C to stop)"
& "$projectRoot\.venv\Scripts\python.exe" -m uvicorn vckg.final_project.app:app --host 127.0.0.1 --port $Port
