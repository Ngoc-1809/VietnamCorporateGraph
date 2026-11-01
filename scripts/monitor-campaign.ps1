# Read-only monitor loop (no AI). Ctrl+C stops only the monitor.   .\scripts\monitor-campaign.ps1 [-IntervalSec 60] [-MaxMinutes 120] [-Once]
param([int]$IntervalSec = 60, [int]$MaxMinutes = 120, [switch]$Once)
$root = 'T:\VietnamCorporateGraph'; $t0 = Get-Date
while ($true) {
    $s = & "$root\.venv\Scripts\python.exe" -m vckg.campaign.supervisor status | ConvertFrom-Json
    "{0} [{1}/{2}] disc={3} dl={4} parsed={5} done={6} deferred={7} failed={8} backlog={9} {10}art/min eta={11}h qwen={12} nodes={13} edges={14} err={15}" -f (Get-Date).ToString('HH:mm:ss'), $s.state, $s.liveness, $s.articles_discovered, $s.articles_downloaded, $s.articles_parsed, $s.articles_processed, $s.articles_deferred, $s.articles_failed, $s.articles_backlog, $s.articles_per_min, $s.eta_hours, $s.qwen_calls_live, $s.graph.nodes_validated, ($s.graph.edges_by_tier | ConvertTo-Json -Compress), $s.last_error
    if ($s.liveness -eq 'FINISHED') { Write-Host "monitor end: $($s.state)"; break }
    if ($Once -or ((Get-Date) - $t0).TotalMinutes -ge $MaxMinutes) { break }
    Start-Sleep $IntervalSec
}
