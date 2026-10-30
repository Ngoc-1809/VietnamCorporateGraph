# Verifies the project Neo4j: java location, localhost binding, data on T:, auth, a trivial query.
. "$PSScriptRoot\enter-project.ps1"
$r = $env:VCKG_ROOT; $bad = 0
Write-Host "JDK: $(& "$r\runtime\jdk\jdk21\bin\java.exe" -version 2>&1 | Select-Object -First 1)"
foreach ($c in Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -in 7474, 7687 }) {
    $ok = $c.LocalAddress -in '127.0.0.1', '::1'
    Write-Host ("port {0} bound to {1} {2}" -f $c.LocalPort, $c.LocalAddress, $(if ($ok) { '[ OK ]' } else { '[WARN not localhost]' }))
    if (-not $ok) { $bad++ }
}
foreach ($d in 'data', 'logs', 'plugins', 'import') { if (-not (Test-Path "$r\runtime\neo4j\$d")) { Write-Host "[WARN] missing runtime\neo4j\$d"; $bad++ } }
$sz = (Get-ChildItem "$r\runtime\neo4j\data" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("database dir: {0}\runtime\neo4j\data ({1:N1} MB)" -f $r, $sz)
& "$r\.venv\Scripts\python.exe" -m vckg.graph.neo4j_sync ping
if ($LASTEXITCODE -ne 0) { $bad++ }
if ($bad) { Write-Host "verify-neo4j: $bad problem(s)" -ForegroundColor Red; exit 1 }
Write-Host "verify-neo4j: OK" -ForegroundColor Green
