# One-shot read-only campaign status (JSON files + SQLite; no AI call).   .\scripts\status-campaign.ps1 [-Json]
param([switch]$Json)
$root = 'T:\VietnamCorporateGraph'
$s = & "$root\.venv\Scripts\python.exe" -m vckg.campaign.supervisor status | ConvertFrom-Json
if ($Json) { $s | ConvertTo-Json -Depth 8; exit 0 }
$col = switch ($s.liveness) { 'RUNNING_OK' { 'Green' } 'FINISHED' { 'Cyan' } default { 'Yellow' } }
Write-Host ("== campaign: state={0} liveness={1} supervisor_pid={2} heartbeat_age={3}s uptime={4}h" -f $s.state, $s.liveness, $s.pid, $s.heartbeat_age_s, $s.uptime_h) -ForegroundColor $col
if ($s.liveness -eq 'DEAD' -or $s.liveness -eq 'STALE') { Write-Host "   supervisor not healthy: the watchdog (if installed) restarts it, or run .\scripts\start-campaign.ps1 -Resume" -ForegroundColor Yellow }
"   articles: discovered={0} downloaded={1} parsed={2} processed={3} deferred={4} failed={5} backlog={6}" -f $s.articles_discovered, $s.articles_downloaded, $s.articles_parsed, $s.articles_processed, $s.articles_deferred, $s.articles_failed, $s.articles_backlog
"   by publisher: $($s.by_publisher | ConvertTo-Json -Compress)   by topic: $($s.by_topic | ConvertTo-Json -Compress)"
"   acquire: state={0} pid={1} alive={2} acquired_new={3} spacing_ok={4}   process: state={5} pid={6} alive={7} chunk={8} stage={9}" -f $s.acquire.state, $s.acquire.pid, $s.acquire.alive, $s.acquire.acquired_new, $s.acquire.http_spacing_ok, $s.process.state, $s.process.pid, $s.process.alive, $s.process.chunk, $s.process.stage
"   speed={0} art/min  ETA={1} h  qwen_live={2}/{3}  chunks={4}  disk free={5} GB (campaign {6} GB)  ollama_up={7}" -f $s.articles_per_min, $s.eta_hours, $s.qwen_calls_live, $s.limits.max_qwen_live_calls, $s.chunks_finished, $s.disk.free_gb, $s.disk.campaign_gb, $s.ollama_up
"   candidates: rule={0} llm={1}  QA pass={2} quarantine={3} reject={4}  mentions={5}" -f $s.chunk_totals.rule_candidates, $s.chunk_totals.llm_candidates, $s.chunk_totals.qa_pass, $s.chunk_totals.qa_quarantine, $s.chunk_totals.qa_reject, $s.chunk_totals.mentions
if ($s.graph) { "   graph: nodes validated={0} all={1}  edges by tier={2}  relation types={3}  new edges/1000 art={4}" -f $s.graph.nodes_validated, $s.graph.nodes_all, ($s.graph.edges_by_tier | ConvertTo-Json -Compress), $s.graph.relation_types, ($s.new_edges_per_1000_articles | ConvertTo-Json -Compress)
  ("   components: {0}  collisions={1}" -f ($s.graph.components | ConvertTo-Json -Compress), $s.graph.identity_collisions) }
if ($s.neo4j_blocker) { Write-Host "   NEO4J BLOCKER: $($s.neo4j_blocker)" -ForegroundColor Yellow }
if ($s.last_error) { Write-Host "   last_error: $($s.last_error)" -ForegroundColor Yellow }
if ($s.incomplete_reasons) { Write-Host "   INCOMPLETE: $($s.incomplete_reasons -join '; ')" -ForegroundColor Yellow }
