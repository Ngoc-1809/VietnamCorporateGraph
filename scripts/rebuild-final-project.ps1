# Rebuild the final-project read model from the existing campaign data. No crawler is started.
param([switch]$NoNeo4j, [switch]$NoPdf)
$ErrorActionPreference = 'Stop'
$projectRoot = 'T:\VietnamCorporateGraph'
Set-Location -LiteralPath $projectRoot
. .\scripts\enter-project.ps1
.\scripts\verify-storage.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$erDir = Join-Path $projectRoot "data\entity_resolution\final_$stamp"
$appDir = Join-Path $projectRoot "data\final_project\rebuild_$stamp"
$sample = Join-Path $projectRoot "reports\final_project\quality_sample_$stamp.csv"
$benchmarkSample = Join-Path $projectRoot "reports\final_project\benchmark_random_$stamp.csv"

uv run python -m vckg.graph.preview build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$snapshotId = (Get-Content 'data\graph_preview\LATEST.txt' -Raw).Trim()
$previewDir = Join-Path $projectRoot "data\graph_preview\$snapshotId"

uv run python -m vckg.entity_resolution.v2 run --snapshot $previewDir --out $erDir --qwen-budget 1000
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run python -m vckg.final_project.build --er $erDir --out $appDir --random-trials 20
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run python -m vckg.final_project.quality_audit export --er $erDir --out $sample
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run python -m vckg.final_project.quality_audit export-benchmark --out $benchmarkSample
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $NoNeo4j) {
    .\scripts\start-neo4j.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    uv run python -m vckg.final_project.neo4j_sync
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$pdfArgs = @()
if (-not $NoPdf) { $pdfArgs = @('--pdf') }
uv run python -m vckg.final_project.report @pdfArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run python -m vckg.final_project.slides @pdfArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Final-project snapshot: $((Get-Content 'data\final_project\ACTIVE.txt' -Raw).Trim())"
Write-Host "Review sheet: $sample"
Write-Host "Random precision benchmark: $benchmarkSample"
