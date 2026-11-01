# Installs (or removes) a per-user Windows scheduled task that runs watchdog-campaign.ps1 every 5 minutes. The task DEFINITION lives in the Windows task store
# (outside T:); all campaign data stays on T:. The supervisor removes the task when the campaign finishes.   .\scripts\install-campaign-watchdog.ps1 [-Remove]
param([switch]$Remove)
$name = 'VCKG-campaign-watchdog'
if ($Remove) { schtasks /Delete /TN $name /F; exit $LASTEXITCODE }
$tr = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "T:\VietnamCorporateGraph\scripts\watchdog-campaign.ps1"'
schtasks /Create /SC MINUTE /MO 5 /TN $name /TR $tr /F
exit $LASTEXITCODE
