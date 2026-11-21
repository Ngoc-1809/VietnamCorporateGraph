# Package only the frozen website databases and metrics for a private Drive transfer.
param([string]$Archive)
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path.TrimEnd('\')
Set-Location -LiteralPath $projectRoot
. "$projectRoot\scripts\enter-project.ps1"
& "$projectRoot\scripts\verify-storage.ps1"
if ($LASTEXITCODE -ne 0) { throw 'Project storage verification failed' }
$snapshot = (Get-Content -LiteralPath "$projectRoot\data\final_project\ACTIVE.txt" -Raw).Trim()
if (-not $Archive) { $Archive = "$projectRoot\dist\vckg-demo-$([IO.Path]::GetFileName($snapshot)).zip" }
$env:PYTHONPATH = "$projectRoot\src"
& "$projectRoot\.venv\Scripts\python.exe" -m vckg.final_project.share export $Archive
if ($LASTEXITCODE -ne 0) { throw 'Snapshot export failed' }
