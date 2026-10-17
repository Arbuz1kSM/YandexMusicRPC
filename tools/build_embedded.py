from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pefile


def validate_stdlib(path: Path) -> None:
    with ZipFile(path) as archive:
        damaged = archive.testzip()
        if damaged:
            raise ValueError(f"Damaged Python standard library entry: {damaged}")
        required = {"encodings/__init__.pyc", "encodings/utf_8.pyc", "codecs.pyc", "io.pyc"}
        missing = required.difference(archive.namelist())
        if missing:
            raise ValueError(f"Incomplete Python standard library: {', '.join(sorted(missing))}")


def validate_bundle(bundle: Path) -> None:
    required = (
        "YandexMusicRPC.exe",
        "app/embedded_main.py",
        "app/main.py",
        "runtime/pythonw.exe",
        "runtime/python312.dll",
        "runtime/python312._pth",
        "runtime/Lib/site-packages/PySide6/QtCore.pyd",
        "runtime/Lib/site-packages/PySide6/QtGui.pyd",
        "runtime/Lib/site-packages/PySide6/QtWidgets.pyd",
        "runtime/Lib/site-packages/PySide6/plugins/platforms/qwindows.dll",
    )
    for name in required:
        path = bundle / name
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Missing or empty application file: {name}")
    validate_stdlib(bundle / "runtime/python312.zip")


def extract_wheels(wheels: Path, site: Path) -> None:
    for wheel in sorted(wheels.glob("*.whl")):
        if wheel.name.lower().startswith(
            ("pyinstaller", "pyinstaller_hooks", "pefile-", "altgraph-", "setuptools-", "wheel-")
        ):
            continue
        with ZipFile(wheel) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                name = entry.filename
                if ".data/" in name:
                    _, tail = name.split(".data/", 1)
                    category, name = tail.split("/", 1)
                    if category not in {"purelib", "platlib"}:
                        continue
                destination = site / name
                if not destination.resolve().is_relative_to(site.resolve()):
                    raise ValueError("Unsafe wheel path")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(entry))


def trim_qt(site: Path) -> None:
    qt = site / "PySide6"

    modules = {"QtCore", "QtGui", "QtWidgets", "QtNetwork"}
    for pyd in qt.glob("*.pyd"):
        if pyd.stem not in modules:
            pyd.unlink()
    for pyi in qt.glob("Qt*.pyi"):
        if pyi.stem not in modules:
            pyi.unlink()
    for directory in (
        "qml",
        "resources",
        "metatypes",
        "include",
        "typesystems",
        "glue",
        "doc",
        "examples",
    ):
        shutil.rmtree(qt / directory, ignore_errors=True)
    for path in qt.glob("*.exe"):
        path.unlink()
    for path in qt.glob("*.lib"):
        path.unlink()
    plugin_groups = {
        "platforms",
        "styles",
        "imageformats",
        "iconengines",
        "tls",
        "networkinformation",
    }
    plugins = qt / "plugins"
    if plugins.exists():
        for path in plugins.iterdir():
            if path.is_dir() and path.name not in plugin_groups:
                shutil.rmtree(path)
        for path in (plugins / "platforms").glob("*.dll"):
            if path.name.lower() not in {"qwindows.dll", "qoffscreen.dll"}:
                path.unlink()
    translations = qt / "translations"
    if translations.exists():
        for path in translations.iterdir():
            if path.is_dir():
                shutil.rmtree(path)
            elif path.name not in {"qtbase_ru.qm", "qtbase_en.qm"}:
                path.unlink()

    dlls = {path.name.lower(): path for path in qt.glob("*.dll")}
    keep = {name for name in dlls if name.startswith(("pyside", "libpyside", "msvcp", "vcruntime"))}
    keep.update(name.lower() + ".dll" for name in ("Qt6Core", "Qt6Gui", "Qt6Widgets", "Qt6Network"))
    if "opengl32sw.dll" in dlls:
        keep.add("opengl32sw.dll")
    pending = (
        list(qt.glob("*.pyd")) + list(plugins.rglob("*.dll")) + [dlls[n] for n in keep if n in dlls]
    )
    visited = set()
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        with pefile.PE(str(path), fast_load=True) as pe:
            pe.parse_data_directories(directories=[1, 13])
            imports = getattr(pe, "DIRECTORY_ENTRY_IMPORT", []) + getattr(
                pe, "DIRECTORY_ENTRY_DELAY_IMPORT", []
            )
            for entry in imports:
                name = entry.dll.decode("ascii").lower()
                if name in dlls and name not in keep:
                    keep.add(name)
                    pending.append(dlls[name])
    for name, path in dlls.items():
        if name not in keep:
            path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Windows installer.")
    parser.add_argument("--python-zip", type=Path, required=True)
    parser.add_argument("--wheels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cc", default="x86_64-w64-mingw32-gcc")
    parser.add_argument("--windres", default="x86_64-w64-mingw32-windres")
    parser.add_argument("--makensis", default="makensis")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    version = re.search(
        r'APP_VERSION = "([^"]+)"', (root / "src/utils/version.py").read_text()
    ).group(1)
    output = args.output.resolve()
    bundle = output / "YandexMusicRPC"
    if bundle.exists():
        raise SystemExit(f"Refusing to overwrite an existing application folder: {bundle}")
    runtime = bundle / "runtime"
    runtime.mkdir(parents=True)
    with ZipFile(args.python_zip) as archive:
        archive.extractall(runtime)
    validate_stdlib(runtime / "python312.zip")
    site = runtime / "Lib/site-packages"
    extract_wheels(args.wheels, site)
    trim_qt(site)

    (runtime / "python312._pth").write_text(
        "python312.zip\n.\nLib/site-packages\n../app\n\nimport site\n"
    )
    shutil.copytree(
        root / "src", bundle / "app", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(root / name, bundle / name)
    build = {
        "app_version": version,
        "architecture": "Windows x64",
        "runtime": "CPython 3.12.10 embeddable",
        "installer": "NSIS",
        "python_zip_sha256": hashlib.sha256(args.python_zip.read_bytes()).hexdigest(),
        "stdlib_sha256": hashlib.sha256((runtime / "python312.zip").read_bytes()).hexdigest(),
        "wheels": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(args.wheels.glob("*.whl"))
        },
    }
    (bundle / "BUILD-INFO.json").write_text(json.dumps(build, indent=2) + "\n")
    resource = output / "launcher.rc"
    icon = (root / "packaging/app.ico").as_posix()
    number = version.replace(".", ",") + ",0"
    resource.write_text(f'''#include <windows.h>
1 ICON "{icon}"
1 VERSIONINFO
FILEVERSION {number}
PRODUCTVERSION {number}
FILEFLAGSMASK 0x3fL
FILEOS VOS_NT_WINDOWS32
FILETYPE VFT_APP
BEGIN
 BLOCK "StringFileInfo"
 BEGIN
  BLOCK "040904B0"
  BEGIN
   VALUE "ProductName", "Yandex Music RPC\\0"
   VALUE "FileDescription", "Yandex Music RPC\\0"
   VALUE "CompanyName", "Arbuz1k_SM\\0"
   VALUE "FileVersion", "{version}\\0"
   VALUE "ProductVersion", "{version}\\0"
   VALUE "OriginalFilename", "YandexMusicRPC.exe\\0"
  END
 END
 BLOCK "VarFileInfo"
 BEGIN
  VALUE "Translation", 0x409, 1200
 END
END
''')
    obj = output / "launcher-resource.o"
    subprocess.run([args.windres, str(resource), "-O", "coff", "-o", str(obj)], check=True)
    subprocess.run(
        [
            args.cc,
            "-municode",
            "-mwindows",
            "-Os",
            "-s",
            "-static",
            "-Wall",
            "-Wextra",
            str(root / "packaging/launcher.c"),
            str(obj),
            "-o",
            str(bundle / "YandexMusicRPC.exe"),
        ],
        check=True,
    )
    validate_bundle(bundle)
    exe = output / f"YandexMusicRPC-{version}-Setup.exe"
    subprocess.run(
        [
            args.makensis,
            "-V2",
            f"-DAPP_VERSION={version}",
            f"-DBUNDLE_DIR={bundle}",
            f"-DOUTPUT_FILE={exe}",
            str(root / "packaging/embedded-installer.nsi"),
        ],
        check=True,
    )
    print(exe)


if __name__ == "__main__":
    main()
