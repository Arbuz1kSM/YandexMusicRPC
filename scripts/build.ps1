param(
    [string]$DiscordApplicationId = "1539198053570060299",
    [string]$ActivityName = "Яндекс Музыка",
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher (py.exe) не найден. Установите Python 3.12 только на машине сборки."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
function Invoke-Python {
    & $Python @args
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code $LASTEXITCODE"
    }
}

Invoke-Python -m pip install --upgrade pip
Invoke-Python -m pip install -r requirements-dev.txt
Invoke-Python tools\configure_build.py --application-id $DiscordApplicationId --activity-name $ActivityName
Invoke-Python tools\make_icon.py
$env:PYTHONPATH = Join-Path $ProjectRoot "src"
Invoke-Python -m ruff check src tests tools
Invoke-Python -m ruff format --check src tests tools
Invoke-Python -m unittest discover -s tests -v
Invoke-Python -m PyInstaller --noconfirm --clean packaging\YandexMusicRPC.spec

if (-not $SkipInstaller) {
    $Candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe"
    )
    $Iscc = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($Iscc) {
        & $Iscc packaging\installer.iss
        if ($LASTEXITCODE -ne 0) {
            throw "Inno Setup failed with exit code $LASTEXITCODE"
        }
        Write-Host "Installer: installer-output\YandexMusicRPC-1.0.0-Setup.exe"
    } else {
        Write-Warning "Inno Setup не найден: portable-сборка готова, installer пропущен."
    }
}

Write-Host "Portable: dist\YandexMusicRPC\YandexMusicRPC.exe"
