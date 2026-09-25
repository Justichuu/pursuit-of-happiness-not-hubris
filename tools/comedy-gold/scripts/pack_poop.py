"""Write a drop-in miner plus a separate chuusmeltit folder. Does not write code_v2."""

from __future__ import annotations

import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def sandbox_poop() -> Path:
    for folder in HERE.parents:
        if (folder / "_workstation").is_dir() or folder.name.lower() == "code":
            return folder / "_workstation" / "sandbox" / "poop"
    return HERE.parent.parent.parent / "_workstation" / "sandbox" / "poop"


def main() -> int:
    dest = sandbox_poop()
    dest.mkdir(parents=True, exist_ok=True)
    for child in list(dest.iterdir()):
        if child.name in {".mined", ".ideamine"}:
            continue
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            try:
                child.unlink()
            except OSError:
                pass
    for name in (
        "paths.py",
        "miner.py",
        "mine_gui.py",
        "Mine.bat",
        "Build Miner.bat",
    ):
        shutil.copy2(HERE / name, dest / name)
    exe = HERE / "Miner.exe"
    if exe.is_file():
        shutil.copy2(exe, dest / "Miner.exe")
    smelter = dest / "chuusmeltit"
    smelter.mkdir()
    shutil.copy2(HERE / "smelter.py", smelter / "smelter.py")
    shutil.copy2(HERE / "smelt_gui.py", smelter / "smelt_gui.py")
    shutil.copy2(HERE / "Smelter.bat", smelter / "Smelter.bat")
    for leftover in (
        "smelter.py",
        "smelt_gui.py",
        "Smelter.bat",
        "factory.py",
        "leadsafe.py",
        "ideamine.md",
    ):
        junk = dest / leftover
        if junk.is_file():
            junk.unlink()
    old = dest / "smelter"
    if old.is_dir():
        shutil.rmtree(old, ignore_errors=True)
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
