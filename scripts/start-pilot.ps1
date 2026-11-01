# Starts the Phase 6D crawl+process pilot FULLY DETACHED (via run-job.ps1). STAGING only; hard ceiling 20 NEW articles per job.
#   .\scripts\start-pilot.ps1 -JobId pilot6d -TargetNew 3 -MaxQwenCalls 100        (trial)
#   .\scripts\start-pilot.ps1 -JobId pilot6d -TargetNew 20 -MaxQwenCalls 100 -Resume   (same JobId: reuses crawl plan + finished articles)
# Monitor/stop: .\scripts\status-pipeline.ps1 -JobId X | .\scripts\monitor-pipeline.ps1 -JobId X | .\scripts\stop-pipeline.ps1 -JobId X
param([Parameter(Mandatory)][string]$JobId, [Parameter(Mandatory)][ValidateRange(1, 20)][int]$TargetNew, [int]$MaxQwenCalls = 100, [string[]]$Only, [switch]$Resume)
$root = 'T:\VietnamCorporateGraph'; $dir = "$root\data\pipeline\$JobId"; $st = "$dir\status.json"
if ($JobId -notmatch '^[A-Za-z0-9_.-]+$') { Write-Host "invalid JobId" -ForegroundColor Red; exit 2 }
# only one NLP job on the GPU at a time (the worker also enforces a lock file)
$busy = Get-ChildItem "$root\data\pipeline\*\status.json" -ErrorAction SilentlyContinue | ForEach-Object { Get-Content $_ -Raw | ConvertFrom-Json } |
    Where-Object { $_.state -in 'STARTING', 'CRAWLING', 'PROCESSING', 'FINALIZING', 'RUNNING' -and (Get-Process -Id $_.pid -ErrorAction SilentlyContinue) }
if ($busy) { Write-Host "another pipeline job is active: $($busy.job_id -join ', ') (PID $($busy.pid -join ', ')). Not starting a second job." -ForegroundColor Yellow; exit 1 }
if ((Test-Path $st) -and -not $Resume) { $j = Get-Content $st -Raw | ConvertFrom-Json; Write-Host "job $JobId exists (state $($j.state)). Use -Resume to continue it or choose a new JobId." -ForegroundColor Yellow; exit 1 }
$a = "run --job-id $JobId --target-new $TargetNew --max-qwen-calls $MaxQwenCalls"
if ($Only) { $a += " --only " + ($Only -join ' ') }
$cmd = ". .\scripts\enter-project.ps1; uv run python -m vckg.jobs.pilot $a; exit `$LASTEXITCODE"
& "$root\scripts\run-job.ps1" -Name "pilot-$JobId" -Command $cmd -Force
Write-Host "status: .\scripts\status-pipeline.ps1 -JobId $JobId   monitor: .\scripts\monitor-pipeline.ps1 -JobId $JobId   stop: .\scripts\stop-pipeline.ps1 -JobId $JobId"
