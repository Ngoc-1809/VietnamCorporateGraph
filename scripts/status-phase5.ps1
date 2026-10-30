# One-shot status from REAL data: processes, jobs, latest outputs, Neo4j counts, errors. Read-only.
$root = 'T:\VietnamCorporateGraph'; $now = Get-Date
function Age($f) { if (Test-Path $f) { $s = [int]($now - (Get-Item $f).LastWriteTime).TotalSeconds; "{0}s ago ({1})" -f $s, (Get-Item $f).LastWriteTime.ToString('HH:mm:ss') } else { 'missing' } }
Write-Host "=== Phase 5 status @ $($now.ToString('yyyy-MM-dd HH:mm:ss')) ===" -ForegroundColor Cyan
Write-Host "-- services"
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'VietnamCorporateGraph' -and $_.Name -match 'java|ollama|python' } |
    ForEach-Object { "{0,-12} PID {1,-6} started {2:HH:mm:ss}  {3}" -f $_.Name, $_.ProcessId, $_.CreationDate, $_.CommandLine.Substring(0, [Math]::Min(90, $_.CommandLine.Length)) }
foreach ($p in 7687, 7474, 11434) { $c = Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue; "port {0}: {1}" -f $p, $(if ($c) { "listening on $($c[0].LocalAddress) (PID $($c[0].OwningProcess))" } else { 'closed' }) }
Write-Host "-- jobs (logs\jobs)"
$jobs = Get-ChildItem "$root\logs\jobs\*.json" -ErrorAction SilentlyContinue
if (-not $jobs) { Write-Host "no jobs registered" }
foreach ($f in $jobs) {
    $j = Get-Content $f -Raw | ConvertFrom-Json; $alive = [bool](Get-Process -Id $j.pid -ErrorAction SilentlyContinue)
    $state = $j.state; if ($state -eq 'RUNNING' -and -not $alive) { $state = 'DEAD (wrapper gone, no exit code) - rerun to resume' }
    "{0}: {1} pid={2} alive={3} heartbeat={4} exit={5}" -f $j.name, $state, $j.pid, $alive, (Age $f.FullName), $j.exit_code
    $err = "$root\logs\jobs\$($j.name).err.log"; if ((Test-Path $err) -and (Get-Item $err).Length -gt 0) { "   stderr tail:"; Get-Content $err -Tail 3 | ForEach-Object { "   $_" } }
    $out = "$root\logs\jobs\$($j.name).out.log"; if (Test-Path $out) { "   stdout updated {0}" -f (Age $out) }
}
Write-Host "-- latest pipeline outputs (data\outputs\phase5)"
foreach ($d in Get-ChildItem "$root\data\outputs\phase5" -Directory -ErrorAction SilentlyContinue) {
    $s = "$($d.FullName)\summary.json"
    if (Test-Path $s) { $j = Get-Content $s -Raw | ConvertFrom-Json; "{0,-12} articles={1} official_edges={2} candidate_only={3} llm_calls={4} cache_hits={5} updated {6}" -f $d.Name, $j.articles, $j.edges_official, $j.edges_candidate_only, $j.llm.llm_calls, $j.llm.cache_hits, (Age $s) }
}
Write-Host "-- Neo4j graph"
& "$root\.venv\Scripts\python.exe" -m vckg.graph.neo4j_sync stats 2>&1 | Out-String | ForEach-Object { $_.Trim() }
$ar = Get-ChildItem "$root\data\outputs\phase5\*\summary.json" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Write-Host "-- overall: " -NoNewline
$running = $jobs | ForEach-Object { Get-Content $_ -Raw | ConvertFrom-Json } | Where-Object { $_.state -eq 'RUNNING' }
if ($running) { Write-Host "RUNNING: $($running.name -join ', ')" -ForegroundColor Yellow } else { Write-Host "no job running (COMPLETED/FAILED states above)" -ForegroundColor Green }
