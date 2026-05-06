# S34 post-patch rerun launcher.
# Skips review (already complete) and voice_assign (all 37 cast have voice_id post-patch).
# Stages that will run: learn -> direction -> tts -> stitch -> m4b.
#
# Usage (from comicast/ directory):
#   .\scripts\rerun_dryrun_post_patch.ps1
#
# If ExecutionPolicy blocks scripts:
#   powershell -ExecutionPolicy Bypass -File .\scripts\rerun_dryrun_post_patch.ps1

$ErrorActionPreference = "Stop"

$env:POPPLER_PATH = "C:\Users\cesab\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"

Write-Host "POPPLER_PATH set."
Write-Host "Launching comicast process with --skip-review..."
Write-Host ""

& .\.venv\Scripts\comicast.exe process data\raw\invincible_vol2_ch1.cbz --series invincible --volume vol_2_ch1 --work-dir data\work\dryrun_ch1 --skip-review
