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
    "VOICES.md",
    "validate.py",
}
CANONICAL_TITLE = "# The Pursuit of Happiness; Not Hubris"
STRICT_VOICES = "**Voices: separated.**"
VOICE_MARKERS = {
    "**Voice: Justichuu.**": "Justichuu",
    "**Voice: AI.**": "AI",
}
UNWRITTEN_SLOT = "_Unwritten. Justichuu writes here._"
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
        if not book_text.startswith(CANONICAL_TITLE):
            fail("BOOK.md", "canonical-title-missing", failures)
        if "## Comedy Gold" not in book_text:
            fail("BOOK.md", "comedy-gold-section-missing", failures)


def strip_fences(text: str) -> List[str]:
    """Return text lines with fenced code blocks removed."""
    kept = []
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            kept.append(line)
    return kept


def chapters(lines: List[str]) -> List[tuple]:
    """Split Markdown lines into a list of second-level chapter bodies."""
    found = []
    body: List[str] = []
    title = None
    for line in lines:
        if line.startswith("## "):
            if title is not None:
                found.append((title, body))
            title = line[3:].strip()
            body = []
        elif title is not None:
            body.append(line)
    if title is not None:
        found.append((title, body))
    return found


def voice_blocks(body: List[str]) -> tuple:
    """Return voiced blocks and any prose that carries no voice marker."""
    blocks = []
    orphans = []
    voice = None
    held: List[str] = []
    for raw in body:
        line = raw.strip()
        if line in VOICE_MARKERS:
            if voice is not None:
                blocks.append((voice, held))
            voice = VOICE_MARKERS[line]
            held = []
        elif line.startswith("#"):
            if voice is not None:
                blocks.append((voice, held))
            voice = None
            held = []
        elif line and line != STRICT_VOICES:
            if voice is None:
                orphans.append(line)
            else:
                held.append(line)
    if voice is not None:
        blocks.append((voice, held))
    return blocks, orphans


def prose_of(block: List[str]) -> List[str]:
    """Drop single-line HTML comments so only authored prose remains."""
    return [line for line in block if not line.startswith("<!--")]


def validate_voice_rules(relative: str, body: List[str],
                         failures: List[str]) -> None:
    """Require one named voice per passage and unwritable reserved slots."""
    blocks, orphans = voice_blocks(body)
    if orphans:
        fail(relative, "voice-marker-missing", failures)
    for voice, block in blocks:
        prose = prose_of(block)
        if not prose:
            fail(relative, "empty-voice-block", failures)
            continue
        reserved = UNWRITTEN_SLOT in prose
        if reserved and voice != "Justichuu":
            fail(relative, "reserved-slot-outside-human-voice", failures)
        if reserved and len(prose) > 1:
            fail(relative, "reserved-slot-holds-other-text", failures)


def is_strict(body: List[str]) -> bool:
    """Report whether a chapter opens by declaring separated voices."""
    for line in body:
        if line.strip():
            return line.strip() == STRICT_VOICES
    return False


def strict_chapters() -> List[tuple]:
    """Return every chapter that opted into the voice separation rule."""
    found = []
    for name in sorted(EXPECTED):
        path = ROOT / name
        if path.suffix.lower() != ".md" or not path.exists():
            continue
        lines = strip_fences(path.read_text(encoding="utf-8"))
        for _, body in chapters(lines):
            if is_strict(body):
                found.append((name, body))
    return found


def validate_voices(failures: List[str]) -> None:
    """Apply the voice separation rules to every strict chapter."""
    for name, body in strict_chapters():
        validate_voice_rules(name, body, failures)


def voice_ledger() -> List[str]:
    """Return one report line per voice plus the reserved-slot count."""
    counts = {name: 0 for name in set(VOICE_MARKERS.values())}
    reserved = 0
    for _, body in strict_chapters():
        for voice, block in voice_blocks(body)[0]:
            prose = prose_of(block)
            if UNWRITTEN_SLOT in prose:
                reserved += 1
            else:
                counts[voice] += sum(len(line.split()) for line in prose)
    lines = [f"{voice}: {counts[voice]} words" for voice in sorted(counts)]
    lines.append(f"Reserved slots awaiting Justichuu: {reserved}")
    return lines


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


def main(argv: List[str]) -> int:
    """Run the complete public-tree validation."""
    if "--voices" in argv:
        for line in voice_ledger():
            print(line)
        return 0

    failures: List[str] = []
    files = public_files()
    actual = {path.relative_to(ROOT).as_posix() for path in files}
    validate_inventory(actual, failures)
    for path in files:
        validate_public_file(path, failures)
    validate_book(failures)
    validate_incident(failures)
    validate_voices(failures)
    return report(failures, len(actual))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
