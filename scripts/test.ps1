$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
$Python = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "py" }
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
if ($Python -eq "py") {
    & py -3.12 -m unittest discover -s tests -v
} else {
    & $Python -m unittest discover -s tests -v
}

