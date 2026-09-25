"""Turn smelt bars into refined bars. Not the mine. Not the vault.

A refined bar is coherent and helpful or novel enough to send later.
Paths are derived from this file. Stdlib only. No network.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List

HOME = Path(__file__).resolve().parent
HERE = HOME
DEFAULT_SMELT = HOME / ".smelt"
DEFAULT_REFINED = HOME / ".refined"

SMELT_MARKS = ("- alloy:", "- metals:", "- bar-hash:")


def default_refined() -> Path:
    return DEFAULT_REFINED


def refuse_if_not_smelt(path: Path, smelt: Path = DEFAULT_SMELT) -> Path:
    path = path.resolve()
    if any(part.lower() in {".mined", ".lead", "lead"} for part in path.parts):
        raise ValueError("Factory only takes a smelt bar, not a mine pile or lead.")
    try:
        path.relative_to(smelt.resolve())
    except ValueError as exc:
        raise ValueError("Factory only takes a bar under .smelt.") from exc
    if not path.is_file():
        raise FileNotFoundError("Nothing to refine: %s" % path)
    text = path.read_text(encoding="utf-8", errors="replace")
    if any(mark not in text for mark in SMELT_MARKS):
        raise ValueError("That file is not a smelt bar.")
    return path


def refine_bar(path: Path, dest: Path = DEFAULT_REFINED, smelt: Path = DEFAULT_SMELT) -> dict:
    path = refuse_if_not_smelt(path, smelt)
    dest = dest.resolve()
    if dest.name in {".lead", "lead", ".mined", ".smelt"}:
        raise RuntimeError("Refined bars land in .refined, not the mine or the vault.")
    dest.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8", errors="replace")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = dest / ("%s-%s.md" % (path.stem, stamp))
    body = (
        "# Refined %s\n\n"
        "- refined: yes\n"
        "- station: factory\n"
        "- from-smelt: `%s`\n"
        "%s\n"
        "Factory wrote this bar. Leadsafe may send only .refined to the vault.\n"
        "This factory does not pay.\n"
        % (path.stem, path.name, text.strip())
    )
    out.write_text(body, encoding="utf-8")
    return {"refined": str(out), "from": str(path)}


def refine_all(smelt: Path = DEFAULT_SMELT, dest: Path = DEFAULT_REFINED) -> List[dict]:
    smelt = smelt.resolve()
    if not smelt.is_dir():
        raise FileNotFoundError("No .smelt folder. Smelt first.")
    bars = sorted(smelt.glob("*.md"))
    if not bars:
        raise FileNotFoundError("No smelt bars. Smelt first.")
    return [refine_bar(bar, dest=dest, smelt=smelt) for bar in bars]
