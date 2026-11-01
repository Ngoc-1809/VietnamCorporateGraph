# Graceful stop of the whole campaign: writes data\campaign\mass\STOP; both workers finish their current unit, checkpoint, and the supervisor exits STOPPED.
# Does not touch Neo4j/Ollama.   .\scripts\stop-campaign.ps1 [-TimeoutSec 600]
param([int]$TimeoutSec = 600)
$root = 'T:\VietnamCorporateGraph'; $dir = "$root\data\campaign\mass"; $st = "$dir\status.json"
if (-not (Test-Path $st)) { Write-Host "no campaign"; exit 1 }
Set-Content "$dir\STOP" "stop requested $(Get-Date -Format s)"
Write-Host "STOP requested; waiting up to ${TimeoutSec}s ..."
$t0 = Get-Date
while (((Get-Date) - $t0).TotalSeconds -lt $TimeoutSec) {
    Start-Sleep 5; $s = Get-Content $st -Raw | ConvertFrom-Json
    if ($s.state -in 'COMPLETED', 'FAILED', 'STOPPED', 'INCOMPLETE') { Write-Host "campaign ended: $($s.state). Checkpoints kept. Resume: .\scripts\start-campaign.ps1 -Resume"; exit 0 }
    if (-not (Get-Process -Id $s.pid -ErrorAction SilentlyContinue)) { Write-Host "supervisor exited (state $($s.state))"; exit 0 }
}
Write-Host "still stopping (long Qwen call / chunk finalize); STOP file stays in place. Check status-campaign.ps1." -ForegroundColor Yellow; exit 3
