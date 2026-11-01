# Graceful stop: writes data\pipeline\<JobId>\STOP; the worker finishes the current article, writes the checkpoint + QA/staging and exits as STOPPED.
# -Force (only after -TimeoutSec): terminates ONLY the worker python PID (checkpoint stays valid; an unfinished article is simply redone). Never touches Neo4j/Ollama.
#   .\scripts\stop-pipeline.ps1 -JobId smoke1 [-TimeoutSec 180] [-Force]
param([Parameter(Mandatory)][string]$JobId, [int]$TimeoutSec = 180, [switch]$Force)
$root = 'T:\VietnamCorporateGraph'; $dir = "$root\data\pipeline\$JobId"; $st = "$dir\status.json"
if (-not (Test-Path $st)) { Write-Host "no such job: $JobId" -ForegroundColor Red; exit 1 }
$s = Get-Content $st -Raw | ConvertFrom-Json
if ($s.state -in 'COMPLETED', 'FAILED', 'STOPPED', 'INCOMPLETE') { Write-Host "job already finished: $($s.state)"; exit 0 }
if (-not (Get-Process -Id $s.pid -ErrorAction SilentlyContinue)) { Write-Host "worker PID $($s.pid) is not running (state $($s.state)); nothing to stop. Resume with start-pipeline.ps1 -Resume." -ForegroundColor Yellow; exit 0 }
Set-Content "$dir\STOP" "stop requested $(Get-Date -Format s)"
Write-Host "STOP requested for $JobId (worker PID $($s.pid)); waiting up to ${TimeoutSec}s for the current article to finish..."
$t0 = Get-Date
while (((Get-Date) - $t0).TotalSeconds -lt $TimeoutSec) {
    Start-Sleep 3
    $s = Get-Content $st -Raw | ConvertFrom-Json
    if ($s.state -in 'COMPLETED', 'FAILED', 'STOPPED', 'INCOMPLETE') { Write-Host "worker ended: state=$($s.state) processed=$($s.processed_articles)/$($s.total_articles) ok=$($s.succeeded_articles) failed=$($s.failed_articles). Checkpoint kept."; exit 0 }
    if (-not (Get-Process -Id $s.pid -ErrorAction SilentlyContinue)) { Write-Host "worker exited (state $($s.state))"; exit 0 }
}
if ($Force) {
    $p = Get-Process -Id $s.pid -ErrorAction SilentlyContinue
    if ($p -and $p.ProcessName -match 'python') { Stop-Process -Id $s.pid -Force; Write-Host "FORCED: worker PID $($s.pid) terminated (checkpoint intact; resume with -Resume)" -ForegroundColor Yellow }
    else { Write-Host "refusing to kill PID $($s.pid): not a python worker" -ForegroundColor Red; exit 2 }
} else { Write-Host "timeout: worker still finishing (e.g. a long Qwen call). STOP file remains; re-check status, or use -Force." -ForegroundColor Yellow; exit 3 }
