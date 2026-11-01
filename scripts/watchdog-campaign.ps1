# Watchdog (run by a Windows scheduled task every 5 min, or by hand): if the campaign supervisor died without a terminal state, restart it with -Resume.
# Idempotent and silent when everything is fine or the campaign is finished.   Logs to logs\campaign-watchdog.log
$root = 'T:\VietnamCorporateGraph'; $st = "$root\data\campaign\mass\status.json"; $log = "$root\logs\campaign-watchdog.log"
function Log($m) { Add-Content $log "$(Get-Date -Format s) $m" }
if (-not (Test-Path $st)) { exit 0 }
$j = Get-Content $st -Raw | ConvertFrom-Json
if ($j.state -in 'COMPLETED', 'FAILED', 'STOPPED', 'INCOMPLETE') { exit 0 }
if (Test-Path "$root\data\campaign\mass\STOP") { exit 0 }
$alive = [bool](Get-Process -Id $j.pid -ErrorAction SilentlyContinue)
$age = if ($j.heartbeat_at) { ((Get-Date) - [datetime]$j.heartbeat_at).TotalSeconds } else { 9999 }
if ($alive -and $age -lt 300) { exit 0 }
if ($alive -and $age -ge 300) { Log "supervisor PID $($j.pid) alive but heartbeat ${age}s old (not restarting a second one)"; exit 0 }
Log "supervisor PID $($j.pid) is dead (last state $($j.state)); restarting with -Resume"
& "$root\scripts\start-campaign.ps1" -Resume | Out-Null
