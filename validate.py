"""Validate the exact files and publication rules allowed in this repository."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List


ROOT = Path(__file__).resolve().parent
EXPECTED = {
    ".gitignore",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/pylint.yml",
    "ACCESSIBILITY.md",
    "BOOK.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "INCIDENT.md",
    "LICENSE.md",
    "PAYMENT.md",
    "PUBLICATION-BOUNDARY.md",
    "README.md",
    "SECURITY.md",
    "validate.py",
}
TEXT_SUFFIXES = {".md", ".py", ".yml", ".gitignore"}
LONG_DASHES = {"\u2013", "\u2014"}
PRIVATE_PATH_SHAPES = (
    re.compile(r"(?i)\b[A-Z]:\\(?:[^\\\r\n]+\\)+"),
    re.compile(
        r"(?i)(?:^|[\\/])(?:users?|private|secrets?|vault|working)"
        r"(?:[\\/]|$)"
    ),
)
SECRET_SHAPES = (
    re.compile(r"-----BEGIN(?: [A-Z]+)? PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|github_pat|sk)-[A-Za-z0-9_]{16,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b(?:seed phrase|recovery phrase|private key|password|token)"
        r"\s*[:=]\s*(?!none\b|not\b|\[)[^\r\n]{8,}"
    ),
)


def public_files() -> List[Path]:
    """Return every non-Git file that would be part of the public tree."""
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(ROOT).parts
    )


def fail(path: str, rule: str, failures: List[str]) -> None:
    """Record one bounded validation failure without printing file contents."""
    failures.append(f"{path}: {rule}")


def validate_inventory(actual: set, failures: List[str]) -> None:
    """Require the allowlisted public file inventory and reject every extra."""
    for missing in sorted(EXPECTED - actual):
        fail(missing, "required-file-missing", failures)
    for unexpected in sorted(actual - EXPECTED):
        fail(unexpected, "unexpected-public-file", failures)


def validate_public_file(path: Path, failures: List[str]) -> None:
    """Check one public file without echoing possibly sensitive contents."""
    relative = path.relative_to(ROOT).as_posix()
    if path.is_symlink():
        fail(relative, "symlink-not-allowed", failures)
        return
    if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".gitignore":
        fail(relative, "non-text-file-not-allowed", failures)
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        fail(relative, "not-utf8", failures)
        return

    if any(mark in text for mark in LONG_DASHES):
        fail(relative, "long-dash-character", failures)

    if path.name == "validate.py":
        return
    if any(pattern.search(text) for pattern in PRIVATE_PATH_SHAPES):
        fail(relative, "private-path-marker", failures)
    if any(pattern.search(text) for pattern in SECRET_SHAPES):
        fail(relative, "secret-shaped-value", failures)


def validate_book(failures: List[str]) -> None:
    """Check the book's canonical title and required editorial section."""
    book = ROOT / "BOOK.md"
    if book.exists():
        book_text = book.read_text(encoding="utf-8")
        if not book_text.startswith("# The Pursuit of Happiness; Not Hubris"):
            fail("BOOK.md", "canonical-title-missing", failures)
        if "## Comedy Gold" not in book_text:
            fail("BOOK.md", "comedy-gold-section-missing", failures)


def validate_incident(failures: List[str]) -> None:
    """Refuse release while the recorded reopening gate remains blocked."""
    incident = ROOT / "INCIDENT.md"
    if incident.exists():
        incident_text = incident.read_text(encoding="utf-8")
        if "Status: BLOCKED." in incident_text:
            fail("INCIDENT.md", "reopening-gate-pending", failures)


def report(failures: List[str], file_count: int) -> int:
    """Print bounded rule names and return a process status code."""
    if failures:
        print("Public-tree validation failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print(f"Public-tree validation passed for {file_count} files.")
    return 0


def main() -> int:
    """Run the complete public-tree validation."""
    failures: List[str] = []
    files = public_files()
    actual = {path.relative_to(ROOT).as_posix() for path in files}
    validate_inventory(actual, failures)
    for path in files:
        validate_public_file(path, failures)
    validate_book(failures)
    validate_incident(failures)
    return report(failures, len(actual))


if __name__ == "__main__":
    sys.exit(main())
