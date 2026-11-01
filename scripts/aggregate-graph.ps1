# Re-run the cross-batch staging aggregation (no NLP, no crawl, no Neo4j). Usage:
#   .\scripts\aggregate-graph.ps1                      # ingest registered sources (unchanged ones are skipped), aggregate, export
#   .\scripts\aggregate-graph.ps1 -AddJob pilot6e      # register a COMPLETED pipeline job first (smoke/test/rerun jobs are refused)
#   .\scripts\aggregate-graph.ps1 -Verify              # idempotence check (two full runs must give the same content hash)
param([string]$AddJob, [switch]$Verify, [string]$Disable)
$py = 'T:\VietnamCorporateGraph\.venv\Scripts\python.exe'
if ($AddJob) { & $py -m vckg.graph.aggregate add-job --job-id $AddJob }
elseif ($Disable) { & $py -m vckg.graph.aggregate disable --source $Disable }
elseif ($Verify) { & $py -m vckg.graph.aggregate verify }
else { & $py -m vckg.graph.aggregate run }
