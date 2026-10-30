# Live monitor (refreshes status). Safe to close at any time; does not affect jobs.  .\scripts\monitor-phase5.ps1 [-Seconds 15] [-Once]
param([int]$Seconds = 15, [switch]$Once)
do { if (-not $Once) { Clear-Host }; & "$PSScriptRoot\status-phase5.ps1"; if (-not $Once) { Start-Sleep $Seconds } } while (-not $Once)
