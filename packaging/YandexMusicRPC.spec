from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path.cwd()
SRC = ROOT / "src"
ICON = ROOT / "packaging" / "app.ico"

hiddenimports = []
for package in (
    "keyring.backends",
    "pypresence",
    "pycaw",
    "comtypes",
    "yandex_music",
    "winrt",
):
    try:
        hiddenimports += collect_submodules(package)
    except Exception:
        pass

datas = [
    (str(SRC / "localization"), "localization"),
    (str(SRC / "resources"), "resources"),
    (str(ROOT / "LICENSE"), "."),
    (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
]

a = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt5", "PyQt6", "matplotlib"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YandexMusicRPC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.exists() else None,
    uac_admin=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="YandexMusicRPC",
)
