from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "src" / "resources" / "app_icon.png"
    icon = source.with_suffix(".ico")
    sizes = [(size, size) for size in (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)]
    with Image.open(source) as image:
        image.convert("RGBA").save(icon, format="ICO", sizes=sizes)
    target = root / "packaging" / "app.ico"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(icon, target)


if __name__ == "__main__":
    main()
