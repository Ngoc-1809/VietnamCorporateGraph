# Starts the Phase 6F controlled scale-up campaign (3 sequential jobs: scale01 20 + scale02 20 + scale03 10 NEW articles) FULLY DETACHED. STAGING only.
#   .\scripts\start-scaleup.ps1 [-CampaignId scale-campaign] [-Budget 160] [-MinDelay 2.5] [-Resume]
# Monitor: .\scripts\status-pipeline.ps1 -JobId scale-campaign (campaign) | scale01 | scale02 | scale03     .\scripts\monitor-pipeline.ps1 -JobId scale-campaign
# Stop (safe, keeps checkpoints): .\scripts\stop-pipeline.ps1 -JobId scale-campaign
param([string]$CampaignId = 'scale-campaign', [ValidateRange(1, 160)][int]$Budget = 160, [double]$MinDelay = 2.5, [switch]$Resume)
$root = 'T:\VietnamCorporateGraph'; $st = "$root\data\pipeline\$CampaignId\status.json"
if ($CampaignId -notmatch '^[A-Za-z0-9_.-]+$') { Write-Host "invalid CampaignId" -ForegroundColor Red; exit 2 }
if ($MinDelay -lt 2.0) { Write-Host "MinDelay must be >= 2.0 s/host" -ForegroundColor Red; exit 2 }
try { $null = Invoke-RestMethod http://127.0.0.1:11434/api/tags -TimeoutSec 5 } catch { Write-Host "Ollama is not reachable on 127.0.0.1:11434 - start it first: .\scripts\run-job.ps1 -Name ollama-serve -Command '. .\scripts\enter-project.ps1; & .\runtime\ollama\ollama.exe serve'" -ForegroundColor Red; exit 2 }
$busy = Get-ChildItem "$root\data\pipeline\*\status.json" -ErrorAction SilentlyContinue | ForEach-Object { Get-Content $_ -Raw | ConvertFrom-Json } |
    Where-Object { $_.state -in 'STARTING', 'CRAWLING', 'PROCESSING', 'FINALIZING', 'RUNNING' -and (Get-Process -Id $_.pid -ErrorAction SilentlyContinue) }
if ($busy) { Write-Host "another pipeline job/campaign is active: $($busy.job_id -join ', ') (PID $($busy.pid -join ', ')). Not starting a second one." -ForegroundColor Yellow; exit 1 }
if ((Test-Path $st) -and -not $Resume) { $j = Get-Content $st -Raw | ConvertFrom-Json; Write-Host "campaign $CampaignId exists (state $($j.state)). Use -Resume to continue it (COMPLETED jobs are skipped) or choose a new id." -ForegroundColor Yellow; exit 1 }
$cmd = ". .\scripts\enter-project.ps1; uv run python -m vckg.jobs.scaleup run --campaign-id $CampaignId --budget $Budget --min-delay $MinDelay; exit `$LASTEXITCODE"
& "$root\scripts\run-job.ps1" -Name "scaleup-$CampaignId" -Command $cmd -Force
Write-Host "status: .\scripts\status-pipeline.ps1 -JobId $CampaignId   monitor: .\scripts\monitor-pipeline.ps1 -JobId $CampaignId   stop: .\scripts\stop-pipeline.ps1 -JobId $CampaignId"
