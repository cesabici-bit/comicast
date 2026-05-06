# One-shot launcher for the S34 dry-run on Invincible Vol 2 ch 1.
# Wraps env-var export + the comicast process invocation so it can run
# from a clean PowerShell session without copy/paste line-break hazards.
#
# Usage (from comicast/ directory):
#   .\scripts\run_dryrun.ps1
#
# If ExecutionPolicy blocks scripts, run instead:
#   powershell -ExecutionPolicy Bypass -File .\scripts\run_dryrun.ps1

$ErrorActionPreference = "Stop"

$env:POPPLER_PATH = "C:\Users\cesab\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"

Write-Host "POPPLER_PATH set to: $env:POPPLER_PATH"
Write-Host "Launching comicast process..."
Write-Host ""

& .\.venv\Scripts\comicast.exe process data\raw\invincible_vol2_ch1.cbz `
    --series invincible `
    --volume vol_2_ch1 `
    --work-dir data\work\dryrun_ch1
