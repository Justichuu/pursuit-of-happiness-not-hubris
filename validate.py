from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPECTED = {
    ".gitignore",
    ".github/PULL_REQUEST_TEMPLATE.md",
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
TEXT_SUFFIXES = {".md", ".py", ".gitignore"}
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


def public_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(ROOT).parts
    )


def fail(path: str, rule: str, failures: list[str]) -> None:
    failures.append(f"{path}: {rule}")


def main() -> int:
    failures: list[str] = []
    actual = {path.relative_to(ROOT).as_posix() for path in public_files()}

    for missing in sorted(EXPECTED - actual):
        fail(missing, "required-file-missing", failures)
    for unexpected in sorted(actual - EXPECTED):
        fail(unexpected, "unexpected-public-file", failures)

    for path in public_files():
        relative = path.relative_to(ROOT).as_posix()
        if path.is_symlink():
            fail(relative, "symlink-not-allowed", failures)
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name != ".gitignore":
            fail(relative, "non-text-file-not-allowed", failures)
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            fail(relative, "not-utf8", failures)
            continue

        if any(mark in text for mark in LONG_DASHES):
            fail(relative, "long-dash-character", failures)

        if path.name != "validate.py":
            if any(pattern.search(text) for pattern in PRIVATE_PATH_SHAPES):
                fail(relative, "private-path-marker", failures)
            if any(pattern.search(text) for pattern in SECRET_SHAPES):
                fail(relative, "secret-shaped-value", failures)

    book = ROOT / "BOOK.md"
    if book.exists():
        book_text = book.read_text(encoding="utf-8")
        if not book_text.startswith("# The Pursuit of Happiness; Not Hubris"):
            fail("BOOK.md", "canonical-title-missing", failures)
        if "## Comedy Gold" not in book_text:
            fail("BOOK.md", "comedy-gold-section-missing", failures)

    incident = ROOT / "INCIDENT.md"
    if incident.exists():
        incident_text = incident.read_text(encoding="utf-8")
        if "Status: BLOCKED." in incident_text:
            fail("INCIDENT.md", "reopening-gate-pending", failures)

    if failures:
        print("Public-tree validation failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print(f"Public-tree validation passed for {len(actual)} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
