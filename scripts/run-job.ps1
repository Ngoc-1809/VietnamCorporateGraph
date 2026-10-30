# Launches a long job FULLY DETACHED from the calling shell/OpenCode (WMI Win32_Process.Create, not a child process).
#   .\scripts\run-job.ps1 -Name phase5-new144 -Command ". .\scripts\enter-project.ps1; uv run python -m vckg.cli process --selection ... --out ..."
# Files: logs\jobs\<Name>.json (state/pid/heartbeat via file mtime), .out.log, .err.log, .exitcode.
# Resume: re-run the same job; the pipeline is idempotent (LLM cache, registry upserts, article dedup), finished work is not repeated.
param([Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)][string]$Command, [switch]$Force)
$root = 'T:\VietnamCorporateGraph'; $st = "$root\logs\jobs\$Name.json"
New-Item -ItemType Directory -Force "$root\logs\jobs" | Out-Null
if ((Test-Path $st) -and -not $Force) {
    $j = Get-Content $st -Raw | ConvertFrom-Json
    if ($j.state -eq 'RUNNING' -and (Get-Process -Id $j.pid -ErrorAction SilentlyContinue)) { Write-Host "job $Name already running (PID $($j.pid))"; exit 1 }
}
Remove-Item "$root\logs\jobs\$Name.exitcode" -ErrorAction SilentlyContinue
$enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($Command))
$cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$root\scripts\job-wrapper.ps1`" -Name $Name -Command `"$($Command -replace '"','\"')`""
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $root }
if ($r.ReturnValue -ne 0) { Write-Host "launch failed ($($r.ReturnValue))" -ForegroundColor Red; exit 2 }
Write-Host "job $Name launched, wrapper PID $($r.ProcessId). Monitor: .\scripts\status-phase5.ps1"
