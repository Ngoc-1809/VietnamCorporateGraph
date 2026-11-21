# Install the light local web runtime and a Drive-delivered SQLite snapshot.
param([Parameter(Mandatory=$true)][string]$Archive)
$archivePath = (Resolve-Path -LiteralPath $Archive -ErrorAction Stop).Path
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path.TrimEnd('\')
if (-not (Test-Path -LiteralPath $projectRoot)) { throw "Clone the repository at $projectRoot first" }
Set-Location -LiteralPath $projectRoot
. "$projectRoot\scripts\enter-project.ps1"
& "$projectRoot\scripts\verify-storage.ps1" -Bootstrap
if ($LASTEXITCODE -ne 0) { throw 'Project storage verification failed' }

if (-not (Test-Path -LiteralPath "$projectRoot\.venv\Scripts\python.exe")) {
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $launcher) { throw 'Python 3.11 with the Windows py launcher is required' }
    & py -3.11 -m venv "$projectRoot\.venv"
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python 3.11 virtual environment' }
}
. "$projectRoot\scripts\enter-project.ps1"
& "$projectRoot\scripts\verify-storage.ps1"
if ($LASTEXITCODE -ne 0) { throw 'Project storage verification failed after venv creation' }
$python = "$projectRoot\.venv\Scripts\python.exe"
& $python -c 'import sys; assert sys.version_info[:2] == (3, 11), "Python 3.11 is required"'
if ($LASTEXITCODE -ne 0) { throw 'The project venv is not Python 3.11' }
& $python -m pip install --disable-pip-version-check --no-input -r "$projectRoot\requirements-demo.txt"
if ($LASTEXITCODE -ne 0) { throw 'Could not install the demo dependencies' }
$env:PYTHONPATH = "$projectRoot\src"
& $python -m vckg.final_project.share install $archivePath
if ($LASTEXITCODE -ne 0) { throw 'Snapshot import or SHA-256 verification failed' }
Write-Host 'Installed. Run .\scripts\start-shared-demo.ps1, then open http://127.0.0.1:8765/'
