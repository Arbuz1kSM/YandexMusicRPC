$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
}
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
& $Python -m pip install -r requirements.txt
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
& $Python src\main.py

