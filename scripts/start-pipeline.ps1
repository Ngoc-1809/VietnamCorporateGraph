# Starts the Phase 6C end-to-end pipeline worker FULLY DETACHED (via run-job.ps1). STAGING mode only.
#   .\scripts\start-pipeline.ps1 -JobId smoke1 -Manifest data\pipeline\smoke_manifest.jsonl -MaxArticles 12 -MaxQwenCalls 60
#   .\scripts\start-pipeline.ps1 -JobId smoke1 -Manifest ... -Resume      (same JobId = resume from checkpoint; finished articles are skipped)
param([Parameter(Mandatory)][string]$JobId, [Parameter(Mandatory)][string]$Manifest, [int]$MaxArticles = 0, [int]$MaxQwenCalls = 60, [int]$MaxAttempts = 2,
      [switch]$NoLlm, [switch]$RetryFailed, [switch]$Resume)
$root = 'T:\VietnamCorporateGraph'; $dir = "$root\data\pipeline\$JobId"; $st = "$dir\status.json"
if ($JobId -notmatch '^[A-Za-z0-9_.-]+$') { Write-Host "invalid JobId" -ForegroundColor Red; exit 2 }
if (-not (Test-Path $Manifest)) { Write-Host "manifest not found: $Manifest" -ForegroundColor Red; exit 2 }
if (Test-Path $st) {
    $j = Get-Content $st -Raw | ConvertFrom-Json
    $alive = [bool](Get-Process -Id $j.pid -ErrorAction SilentlyContinue)
    if ($alive -and $j.state -in 'STARTING', 'RUNNING') { Write-Host "job $JobId already running (worker PID $($j.pid)); use status-pipeline.ps1" -ForegroundColor Yellow; exit 1 }
    if (-not $Resume -and $j.state -in 'COMPLETED', 'FAILED', 'STOPPED', 'INCOMPLETE') { Write-Host "job $JobId exists (state $($j.state)). Re-run with -Resume to continue (idempotent) or choose a new JobId." -ForegroundColor Yellow; exit 1 }
}
$mf = (Resolve-Path $Manifest).Path
$a = "run --job-id $JobId --manifest `"$mf`" --max-qwen-calls $MaxQwenCalls --max-attempts $MaxAttempts"
if ($MaxArticles -gt 0) { $a += " --max-articles $MaxArticles" }
if ($NoLlm) { $a += ' --no-llm' }
if ($RetryFailed) { $a += ' --retry-failed' }
$cmd = ". .\scripts\enter-project.ps1; uv run python -m vckg.jobs.pipeline_worker $a; exit `$LASTEXITCODE"
& "$root\scripts\run-job.ps1" -Name "pipeline-$JobId" -Command $cmd -Force
Write-Host "status: .\scripts\status-pipeline.ps1 -JobId $JobId   monitor: .\scripts\monitor-pipeline.ps1 -JobId $JobId   stop: .\scripts\stop-pipeline.ps1 -JobId $JobId"
