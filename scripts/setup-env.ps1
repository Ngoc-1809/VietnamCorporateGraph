# Creates the project venv (Python 3.11 managed by uv, installed under T:) and syncs dependencies.
. "$PSScriptRoot\enter-project.ps1"
& "$PSScriptRoot\verify-storage.ps1" | Out-Null
if ($LASTEXITCODE -ne 0 -and -not (Test-Path "$env:VCKG_ROOT\.venv")) { Write-Host 'storage check (python not venv yet) - continuing' }
uv python install 3.11
uv sync --extra ml --python 3.11 --python-preference only-managed
