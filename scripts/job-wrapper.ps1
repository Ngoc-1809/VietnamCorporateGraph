# Internal: runs one job and records state. Do not call directly; use scripts\run-job.ps1.
param([Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][string]$Command)
. "$PSScriptRoot\enter-project.ps1" | Out-Null
$root = $env:VCKG_ROOT; $dir = "$root\logs\jobs"; $state = "$dir\$Name.json"
function Save($s, $extra = @{}) { (@{ name = $Name; state = $s; pid = $PID; command = $Command; started = $script:t0; updated = (Get-Date).ToString('s') } + $extra) | ConvertTo-Json | Set-Content $state -Encoding utf8 }
$script:t0 = (Get-Date).ToString('s'); Save 'RUNNING'
$hb = Start-Job -ScriptBlock { param($s, $n) while ($true) { Start-Sleep 20; if (Test-Path $s) { (Get-Item $s).LastWriteTime = Get-Date } } } -ArgumentList $state, $Name
try {
    & powershell -NoProfile -ExecutionPolicy Bypass -Command $Command > "$dir\$Name.out.log" 2> "$dir\$Name.err.log"
    $code = $LASTEXITCODE; if ($null -eq $code) { $code = 0 }
} catch { $code = 99; $_ | Out-String | Add-Content "$dir\$Name.err.log" }
Stop-Job $hb -ErrorAction SilentlyContinue; Remove-Job $hb -Force -ErrorAction SilentlyContinue
Set-Content "$dir\$Name.exitcode" $code
Save $(if ($code -eq 0) { 'COMPLETED' } else { 'FAILED' }) @{ exit_code = $code; finished = (Get-Date).ToString('s') }
