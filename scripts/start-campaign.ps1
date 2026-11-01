# Starts (or resumes) the autonomous mass campaign supervisor FULLY DETACHED via run-job.ps1.  STAGING + validated-layer Neo4j sync only.
#   .\scripts\start-campaign.ps1 [-MaxArticles 30000] [-QwenBudget 90000] [-ChunkSize 200] [-MinDelay 2.5] [-NoNeo4j] [-Resume]
# Status: .\scripts\status-campaign.ps1   Monitor: .\scripts\monitor-campaign.ps1   Stop (graceful, checkpointed): .\scripts\stop-campaign.ps1
param([ValidateRange(1, 30000)][int]$MaxArticles = 30000, [ValidateRange(1, 90000)][int]$QwenBudget = 90000, [ValidateRange(1, 500)][int]$ChunkSize = 200,
      [double]$MinDelay = 2.5, [switch]$NoNeo4j, [switch]$Resume)
$root = 'T:\VietnamCorporateGraph'; $dir = "$root\data\campaign\mass"; $st = "$dir\status.json"
if ($MinDelay -lt 2.0) { Write-Host "MinDelay must be >= 2.0 s/host" -ForegroundColor Red; exit 2 }
New-Item -ItemType Directory -Force $dir | Out-Null
if (Test-Path $st) {
    $j = Get-Content $st -Raw | ConvertFrom-Json
    if ((Get-Process -Id $j.pid -ErrorAction SilentlyContinue) -and $j.state -notin 'COMPLETED', 'FAILED', 'STOPPED', 'INCOMPLETE') { Write-Host "campaign supervisor already running (PID $($j.pid), state $($j.state))" -ForegroundColor Yellow; exit 1 }
    if (-not $Resume -and $j.state -in 'COMPLETED', 'INCOMPLETE') { Write-Host "campaign finished ($($j.state)); see reports\campaign_final.md. Use -Resume to run again (finished work is never repeated)." -ForegroundColor Yellow; exit 1 }
}
try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 5 } catch {
    Write-Host "starting Ollama (project runtime)"; & "$root\scripts\run-job.ps1" -Name ollama-serve -Command ". .\scripts\enter-project.ps1; & .\runtime\ollama\ollama.exe serve" -Force | Out-Null; Start-Sleep 15 }
Remove-Item "$dir\STOP", "$dir\acquire.STOP", "$dir\process.STOP" -ErrorAction SilentlyContinue
$a = "--max-articles $MaxArticles --qwen-budget $QwenBudget --chunk-size $ChunkSize --min-delay $MinDelay"; if ($NoNeo4j) { $a += ' --no-neo4j' }
$cmd = ". .\scripts\enter-project.ps1; uv run python -m vckg.campaign.supervisor run $a; exit `$LASTEXITCODE"
& "$root\scripts\run-job.ps1" -Name "campaign-mass" -Command $cmd -Force
Write-Host "status: .\scripts\status-campaign.ps1   monitor: .\scripts\monitor-campaign.ps1   stop: .\scripts\stop-campaign.ps1   resume: .\scripts\start-campaign.ps1 -Resume"
