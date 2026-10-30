# Starts the PROJECT Neo4j (Community, user-level console process, localhost only). Never touches other Neo4j instances.
. "$PSScriptRoot\enter-project.ps1"
$r = $env:VCKG_ROOT
$env:JAVA_HOME = "$r\runtime\jdk\jdk21"; $env:NEO4J_HOME = "$r\runtime\neo4j\app"; $env:NEO4J_CONF = "$r\runtime\neo4j\conf"
$busy = Get-NetTCPConnection -State Listen -LocalPort 7687 -ErrorAction SilentlyContinue
if ($busy) {
    $p = Get-CimInstance Win32_Process -Filter "ProcessId=$($busy[0].OwningProcess)"
    if ($p.CommandLine -like "*$r\runtime\neo4j*") { Write-Host "[neo4j] already running (PID $($p.ProcessId))"; exit 0 }
    Write-Host "[neo4j] port 7687 is used by another process (PID $($p.ProcessId)); not touching it. Aborting." -ForegroundColor Red; exit 2
}
Start-Process -FilePath "$r\runtime\neo4j\app\bin\neo4j.bat" -ArgumentList 'console' -WindowStyle Hidden `
    -RedirectStandardOutput "$r\logs\neo4j.console.out.log" -RedirectStandardError "$r\logs\neo4j.console.err.log"
for ($i = 0; $i -lt 60; $i++) { Start-Sleep 2; if (Get-NetTCPConnection -State Listen -LocalPort 7687 -ErrorAction SilentlyContinue) { Write-Host "[neo4j] bolt up on 127.0.0.1:7687"; exit 0 } }
Write-Host "[neo4j] did not open 7687 in 120 s; see logs\neo4j.console.err.log and runtime\neo4j\logs" -ForegroundColor Red; exit 1
