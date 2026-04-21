"""
Script de build: empaqueta main.py en un .exe con PyInstaller.

Uso:
    python build.py

Salida:
    desktop/dist/GVI-Admin.exe

Requisitos:
    pip install -r requirements.txt
"""

import pathlib
import sys

import PyInstaller.__main__


ROOT = pathlib.Path(__file__).parent.resolve()
ICON_PATH = ROOT / "assets" / "icon.ico"


def main():
    args = [
        str(ROOT / "main.py"),
        "--name=GVI-Admin",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        f"--distpath={ROOT / 'dist'}",
        f"--workpath={ROOT / 'build'}",
        f"--specpath={ROOT}",
    ]

    if ICON_PATH.exists():
        args.append(f"--icon={ICON_PATH}")

    print(f"[build] PyInstaller args: {args}", file=sys.stderr)
    PyInstaller.__main__.run(args)
    print(f"[build] OK -> {ROOT / 'dist' / 'GVI-Admin.exe'}")


if __name__ == "__main__":
    main()
