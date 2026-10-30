# Stops ONLY the project Neo4j JVM (identified by the project path in its command line).
$r = 'T:\VietnamCorporateGraph'
$procs = Get-CimInstance Win32_Process -Filter "Name='java.exe'" | Where-Object { $_.CommandLine -like "*$r\runtime\neo4j*" }
if (-not $procs) { Write-Host "[neo4j] project instance not running"; exit 0 }
foreach ($p in $procs) { Write-Host "[neo4j] stopping PID $($p.ProcessId)"; Stop-Process -Id $p.ProcessId }
Start-Sleep 4
if (Get-NetTCPConnection -State Listen -LocalPort 7687 -ErrorAction SilentlyContinue) { Write-Host "[neo4j] still listening" -ForegroundColor Yellow; exit 1 }
Write-Host "[neo4j] stopped"
