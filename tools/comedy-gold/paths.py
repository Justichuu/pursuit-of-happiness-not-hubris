"""The folder the miner was started in."""

from __future__ import annotations

from pathlib import Path


def run_dir() -> Path:
    return Path.cwd().resolve()


def mined_dir() -> Path:
    return run_dir() / ".mined"
