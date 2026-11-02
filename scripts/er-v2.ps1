# Entity Resolution v2 job control (detached, checkpointed). Output: data\entity_resolution\v2\
#   .\scripts\er-v2.ps1 start [-QwenBudget 1000] [-NoQwen] [-ForceStage org]    start or RESUME (finished stages are skipped)
#   .\scripts\er-v2.ps1 status | stop
param([Parameter(Mandatory)][ValidateSet('start','status','stop')][string]$Action, [int]$QwenBudget = 1000, [switch]$NoQwen, [string]$ForceStage, [string]$Snapshot = 'data\graph_preview\20261102-143350')
$root = 'T:\VietnamCorporateGraph'; $dir = "$root\data\entity_resolution\v2"; $st = "$dir\status.json"
switch ($Action) {
  'status' { if (Test-Path $st) { $j = Get-Content $st -Raw | ConvertFrom-Json; $alive = [bool](Get-Process -Id $j.pid -ErrorAction SilentlyContinue)
      "state=$($j.state) pid=$($j.pid) alive=$alive heartbeat=$($j.heartbeat_at) stage=$($j.stage) qwen=$($j.qwen_live_calls)/$($j.qwen_budget) err=$($j.last_error)"
      if ($j.state -eq 'RUNNING' -and -not $alive) { Write-Host 'DEAD: rerun start to resume' -ForegroundColor Yellow } } else { 'no status' } }
  'stop' { New-Item -ItemType Directory -Force $dir | Out-Null; Set-Content "$dir\STOP" "stop $(Get-Date -Format s)"; 'STOP requested (the job stops at the next check and keeps its checkpoint)' }
  'start' {
    New-Item -ItemType Directory -Force $dir | Out-Null; Remove-Item "$dir\STOP" -ErrorAction SilentlyContinue
    if (Test-Path $st) { $j = Get-Content $st -Raw | ConvertFrom-Json; if ($j.state -eq 'RUNNING' -and (Get-Process -Id $j.pid -ErrorAction SilentlyContinue)) { "already running (PID $($j.pid))"; exit 1 } }
    $a = "run --snapshot $Snapshot --qwen-budget $QwenBudget"; if ($NoQwen) { $a += ' --no-qwen' }; if ($ForceStage) { $a += " --force-stage $ForceStage" }
    & "$root\scripts\run-job.ps1" -Name 'er-v2' -Command ". .\scripts\enter-project.ps1; uv run python -m vckg.entity_resolution.v2 $a; exit `$LASTEXITCODE" -Force } }
