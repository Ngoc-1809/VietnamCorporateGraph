# One-shot, READ-ONLY status of pipeline jobs (JSON + SQLite counts via a tiny python call; no AI/Ollama call).
#   .\scripts\status-pipeline.ps1 [-JobId smoke1] [-Json]
param([string]$JobId, [switch]$Json)
$root = 'T:\VietnamCorporateGraph'
$dirs = if ($JobId) { @(Get-Item "$root\data\pipeline\$JobId" -ErrorAction SilentlyContinue) } else { @(Get-ChildItem "$root\data\pipeline" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -notlike '_*' }) }
if (-not $dirs) { Write-Host "no pipeline jobs"; exit 0 }
foreach ($d in $dirs) {
    $s = & "$root\.venv\Scripts\python.exe" -m vckg.jobs.pipeline_worker status --job-id $d.Name | ConvertFrom-Json
    if ($Json) { $s | ConvertTo-Json -Depth 4; continue }
    $col = switch ($s.liveness) { 'RUNNING_OK' { 'Green' } 'FINISHED' { 'Cyan' } default { 'Yellow' } }
    Write-Host ("== {0}: state={1} liveness={2} pid={3} alive={4} heartbeat_age={5}s mode={6}" -f $s.job_id, $s.state, $s.liveness, $s.pid, $s.pid_alive, $s.heartbeat_age_s, $s.mode) -ForegroundColor $col
    if ($s.liveness -eq 'STALE') { Write-Host "   STALE: no heartbeat for >60s although PID is alive - do NOT assume it is working" -ForegroundColor Yellow }
    if ($s.liveness -eq 'DEAD') { Write-Host "   DEAD: worker is gone without a terminal state; checkpoint kept - re-run start-pipeline.ps1 -Resume" -ForegroundColor Yellow }
    if ($s.campaign) { "   CAMPAIGN: current_job={0} qwen_used={1}/{2} http_spacing_ok={3} min_gap={4}s" -f $s.current_job, $s.qwen_used, $s.qwen_budget, $s.http_spacing_ok, $s.http_min_gap_s; foreach ($p in $s.jobs.PSObject.Properties) { "     {0}: state={1} fetched={2} ok={3} failed={4} qwen={5} QA(P/Q/R)={6}" -f $p.Name, $p.Value.state, $p.Value.fetched_ok, $p.Value.succeeded, $p.Value.failed, $p.Value.llm_calls, ($p.Value.qa -join '/') } }
    if ($null -ne $s.target_new) { "   crawl: target_new={0} discovered={1} fetched_ok={2} fetch_failed={3} skipped(dup/robots/rejected)={4} still_planned={5} shortfall={6}" -f $s.target_new, $s.discovered, $s.fetched_ok, $s.fetch_failed, $s.fetch_skipped, $s.candidates_planned, $s.crawl_shortfall }
    "   articles: total={0} processed={1} ok={2} failed={3} current={4} stage={5}" -f $s.total_articles, $s.processed_articles, $s.succeeded_articles, $s.failed_articles, $s.current_article, $s.stage
    "   candidates: rule={0} llm={1}   QA: pass={2} quarantine={3} reject={4}   staging: edges={5} entities={6}   qwen_calls={7} (cache hits {8}, failures {9}) candidates_unique={10} entities_in_candidates={11}" -f $s.rule_candidates, $s.llm_candidates, $s.qa_pass, $s.qa_quarantine, $s.qa_reject, $s.unique_staging_edges, $s.unique_staging_entities, $s.llm_calls, $s.qwen_cache_hits, $s.qwen_failed, $s.candidates_unique, $s.entities_in_candidates
    "   started={0} finished={1}  last_error={2}" -f $s.started_at, $s.finished_at, $s.last_error
    $ev = "$($d.FullName)\events.jsonl"; if (Test-Path $ev) { "   last events:"; Get-Content $ev -Tail 3 | ForEach-Object { "     $_".Substring(0, [Math]::Min(170, "     $_".Length)) } }
    $err = "$root\logs\jobs\pilot-$($d.Name).err.log"; if (-not (Test-Path $err)) { $err = "$root\logs\jobs\pipeline-$($d.Name).err.log" }
    if ((Test-Path $err) -and (Get-Item $err).Length -gt 0) { "   stderr tail:"; Get-Content $err -Tail 3 | ForEach-Object { "     $_" } }
}
