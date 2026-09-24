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
    "CONTRIBUTORS.md",
    "INCIDENT.md",
    "LICENSE.md",
    "PAYMENT.md",
    "PUBLICATION-BOUNDARY.md",
    "QUOTES.md",
    "README.md",
    "SECURITY.md",
    "VOICES.md",
    "validate.py",
}
CANONICAL_TITLE = "# The Pursuit of Happiness over Hubris"
STRICT_VOICES = "**Voices: separated.**"
FOUNDING_VOICES = ("Justichuu", "AI")
# A marker is "**Voice: <name>.**". The name is resolved against
# CONTRIBUTORS.md rather than against a list kept in here, so a person joins by
# opening a pull request and the validator learns about them from the same row
# a reader sees. An unregistered marker is a failure, not silently ignored
# prose: quietly dropping it is how somebody ends up signing as somebody else.
VOICE_MARKER = re.compile(r"^\*\*Voice: (?P<name>[A-Za-z0-9 .'-]{1,40})\.\*\*$")
CONTRIBUTOR_ROW = re.compile(
    r"^\|\s*(?P<name>[A-Za-z0-9 .'-]{1,40})\s*\|\s*"
    r"(?P<kind>writing voice|attribution)\s*\|"
)
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


SKIP_DIR_NAMES = {".git", "__pycache__", ".pytest_cache"}


def contributors() -> dict:
    """Read the register. Name to kind, from the table in CONTRIBUTORS.md."""
    path = ROOT / "CONTRIBUTORS.md"
    rows = {name: "writing voice" for name in FOUNDING_VOICES}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        found = CONTRIBUTOR_ROW.match(line.strip())
        if found:
            rows[found.group("name").strip()] = found.group("kind")
    return rows


def voice_of(line: str, register: dict) -> str:
    """Name a registered writing voice, or empty for anything else.

    An attribution row is deliberately not a voice. Somebody listed only to be
    credited has no passage to write, so a marker in their name is a mistake
    and gets reported as one.
    """
    found = VOICE_MARKER.match(line)
    if not found:
        return ""
    name = found.group("name").strip()
    if register.get(name) == "writing voice":
        return name
    return ""


def looks_like_marker(line: str) -> bool:
    """True for marker-shaped text, registered or not."""
    return VOICE_MARKER.match(line) is not None


def public_files() -> List[Path]:
    """Return every non-Git file that would be part of the public tree."""
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not any(
            part in SKIP_DIR_NAMES for part in path.relative_to(ROOT).parts
        )
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


def strip_fences(text: str) -> tuple:
    """Return kept lines and whether a fence was left open."""
    kept = []
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            kept.append(line)
    return kept, fenced


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


def voice_blocks(body: List[str], register: dict = None) -> tuple:
    """Return voiced blocks, unvoiced prose, and unregistered markers."""
    register = contributors() if register is None else register
    blocks = []
    orphans = []
    unregistered = []
    voice = None
    held: List[str] = []
    for raw in body:
        line = raw.strip()
        named = voice_of(line, register)
        if named:
            if voice is not None:
                blocks.append((voice, held))
            voice = named
            held = []
        elif looks_like_marker(line):
            # Marker shaped, but nobody by that name has a writing row. Report
            # it rather than letting it fall through and read as prose.
            unregistered.append(line)
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
    return blocks, orphans, unregistered


def prose_of(block: List[str]) -> List[str]:
    """Drop single-line HTML comments so only authored prose remains."""
    return [line for line in block if not line.startswith("<!--")]


def validate_voice_rules(relative: str, body: List[str],
                         failures: List[str]) -> None:
    """Require one named voice per passage and unwritable reserved slots."""
    blocks, orphans, unregistered = voice_blocks(body)
    if orphans:
        fail(relative, "voice-marker-missing", failures)
    if unregistered:
        fail(relative, "voice-not-in-contributors", failures)
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
    """Report whether a chapter declares separated voices anywhere."""
    return any(line.strip() == STRICT_VOICES for line in body)


def declaration_is_first(body: List[str]) -> bool:
    """Require the opt-in line to be the first non-empty chapter line."""
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
        lines, unclosed = strip_fences(path.read_text(encoding="utf-8"))
        if unclosed:
            found.append((name, None))
            continue
        for _, body in chapters(lines):
            if is_strict(body):
                found.append((name, body))
    return found


def validate_voices(failures: List[str]) -> None:
    """Apply the voice separation rules to every strict chapter."""
    for name, body in strict_chapters():
        if body is None:
            fail(name, "fence-unclosed", failures)
            continue
        if not declaration_is_first(body):
            fail(name, "voices-declaration-not-first", failures)
        validate_voice_rules(name, body, failures)


def voice_ledger() -> List[str]:
    """Return one report line per voice plus the reserved-slot count."""
    register = contributors()
    counts = {name: 0 for name, kind in register.items()
              if kind == "writing voice"}
    reserved = 0
    for _, body in strict_chapters():
        if body is None:
            continue
        for voice, block in voice_blocks(body, register)[0]:
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
