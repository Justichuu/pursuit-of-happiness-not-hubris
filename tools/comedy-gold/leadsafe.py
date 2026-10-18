"""Seal one refined bar into the existing Novel Vault.

This is the lead job. It only takes factory output under .refined.
It does not take miner piles or smelter bars. It never opens
master.rivault, reader.rivault, or inbox packets. Paths are derived.
Stdlib only. No network.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFINED = HERE / ".refined"
CARD_MARKS = ("- refined:", "- station: factory", "- bar-hash:")


def default_vault_dir() -> Path:
    return HERE.parent / "novel"


VAULT_DIR = default_vault_dir()
VAULT_EXE = VAULT_DIR / "Novel Vault.exe"


def refuse_if_not_refined(path: Path, refined: Path | None = None) -> Path:
    """Leadsafe may only hold factory-refined bars."""
    path = path.resolve()
    root = (refined or REFINED).resolve()
    blocked = {".mined", ".smelt", ".lead", "lead"}
    if any(part.lower() in blocked for part in path.parts):
        raise ValueError(
            "Leadsafe only takes .refined. Not the miner, not the smelter."
        )
    if not path.is_file():
        raise FileNotFoundError("Nothing to seal: %s" % path)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            "Leadsafe only takes a refined bar under .refined. "
            "This job cannot mine gold and cannot smelt."
        ) from exc
    if path.suffix.lower() not in {".md", ".markdown", ".txt"}:
        raise ValueError("Leadsafe only takes a refined bar.")
    text = path.read_text(encoding="utf-8", errors="replace")
    if any(mark not in text for mark in CARD_MARKS):
        raise ValueError("That file is not a factory-refined bar.")
    return path


def seal_refined(path: Path) -> dict:
    path = refuse_if_not_refined(path)
    if not VAULT_EXE.is_file():
        raise FileNotFoundError(
            "Novel Vault.exe is missing. The lead safe is the existing vault at %s"
            % VAULT_DIR
        )
    name = path.stem[:160] or "refined-bar"
    completed = subprocess.run(
        [
            str(VAULT_EXE),
            "--seal",
            "--note-name",
            name,
            "--content-file",
            str(path),
            "--source",
            "refined",
        ],
        cwd=str(VAULT_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if not stdout:
        raise RuntimeError(
            "Vault seal produced no receipt. Leadsafe does not open the vault.\n"
            + (stderr or "no stderr")
        )
    try:
        receipt = json.loads(stdout.splitlines()[-1] if stdout.startswith("{") else stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Vault seal did not return JSON.") from exc
    if receipt.get("status") == "error":
        raise RuntimeError(receipt.get("error") or "Vault seal failed.")
    if receipt.get("operation") != "seal":
        raise RuntimeError("Unexpected vault response.")
    if "content" in receipt or "notes" in receipt:
        raise RuntimeError("Seal receipt must not include vault contents.")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python leadsafe.py",
        description="Seal one refined bar into the existing Novel Vault.",
    )
    parser.add_argument("card", help="A file under .refined")
    parser.add_argument("--check", action="store_true", help="Check the bar only. Do not seal.")
    args = parser.parse_args(argv)
    try:
        path = refuse_if_not_refined(Path(args.card))
        if args.check:
            print("refined bar ok: %s" % path)
            return 0
        receipt = seal_refined(path)
        json.dump(receipt, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
