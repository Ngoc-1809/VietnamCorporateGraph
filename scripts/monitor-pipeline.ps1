# Read-only live monitor: polls status.json (+events tail). Never calls AI. Ctrl+C only stops the monitor, not the worker.
#   .\scripts\monitor-pipeline.ps1 -JobId smoke1 [-IntervalSec 10] [-MaxMinutes 60] [-Once]
param([Parameter(Mandatory)][string]$JobId, [int]$IntervalSec = 10, [int]$MaxMinutes = 60, [switch]$Once)
$root = 'T:\VietnamCorporateGraph'; $st = "$root\data\pipeline\$JobId\status.json"; $t0 = Get-Date
while ($true) {
    if (-not (Test-Path $st)) { Write-Host "no status.json yet for $JobId"; if ($Once) { exit 1 } }
    else {
        try { $s = Get-Content $st -Raw | ConvertFrom-Json } catch { Start-Sleep 1; continue }
        $alive = [bool](Get-Process -Id $s.pid -ErrorAction SilentlyContinue)
        $age = if ($s.heartbeat_at) { [int]((Get-Date) - [datetime]$s.heartbeat_at).TotalSeconds } else { -1 }
        $live = if ($s.state -in 'COMPLETED', 'FAILED', 'STOPPED') { 'FINISHED' } elseif (-not $alive) { 'DEAD' } elseif ($age -gt 60) { 'STALE' } else { 'RUNNING_OK' }
        "{0} [{18}] disc={19} fetched={20} {1}/{2} liveness={3} hb={4}s ok={5} fail={6} stage={7} art={8} cand(rule/llm)={9}/{10} QA(P/Q/R)={11}/{12}/{13} edges={14} ents={15} qwen={16} err={17}" -f (Get-Date).ToString('HH:mm:ss'), $s.processed_articles, $s.total_articles, $live, $age, $s.succeeded_articles, $s.failed_articles, $s.stage, $s.current_article, $s.rule_candidates, $s.llm_candidates, $s.qa_pass, $s.qa_quarantine, $s.qa_reject, $s.unique_staging_edges, $s.unique_staging_entities, $s.llm_calls, $s.last_error, $s.state, $s.discovered, $s.fetched_ok
        if ($live -in 'FINISHED', 'DEAD') { Write-Host "monitor end: $($s.state) / $live"; break }
        if ($live -eq 'STALE') { Write-Host "STALE heartbeat - not claiming the job is running" -ForegroundColor Yellow }
    }
    if ($Once -or ((Get-Date) - $t0).TotalMinutes -ge $MaxMinutes) { break }
    Start-Sleep $IntervalSec
}
