# Builds a standalone Windows game: dist\ShadowRoad\ShadowRoad.exe
# Usage (from the project folder):   powershell -ExecutionPolicy Bypass -File build_exe.ps1
# Needs: pip install pyinstaller pygame-ce
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Running tests first..."
python -m unittest discover tests
if ($LASTEXITCODE -ne 0) { throw "Tests failed - not building." }

# Only the art and balance settings ship with the game (not the 90 MB source pack or the AI tools).
python -m PyInstaller --noconfirm --clean --windowed --name ShadowRoad `
    --add-data "assets\art;assets\art" `
    --add-data "assets\balance.json;assets" `
    --exclude-module numpy --exclude-module PIL --exclude-module tkinter `
    main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

Write-Host ""
Write-Host "Built dist\ShadowRoad\ShadowRoad.exe - zip the whole dist\ShadowRoad folder to share it."
