"""Find nearby idea notes and sort them into .mined piles for Comedy Gold.

This is the shovel, not the book, not the pay box, and not the lead safe.
Lead is the final product. The mine cannot make it. If we can mine gold, we
cannot make lead. Paths come from the folder the miner was started in.
Stdlib only. No network.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from paths import mined_dir, run_dir

HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*#*$", re.M)
SLUG = re.compile(r"[^a-z0-9]+")
LISTISH = re.compile(r"(?m)^[ \t]*([-*+]|\d+\.)[ \t]+")
HOWTO = re.compile(
    r"(?im)^[ \t]*(todo|install|usage|how to|pip install|npm install|yarn add)\b"
)

MIN_BODY = 40
ORES = ("gold", "silver", "copper", "bronze", "tin", "dirt")

SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "private",
    ".mined",
    ".ideamine",
    ".smelt",
    ".refined",
    "chuusmeltit",
    "dist",
    ".pytest_cache",
}

# These trees are other products or sealed by existing ledger rules.
SKIP_TREE_NAMES = {"novel", "skye", "veskara", "veskara-gguf-work"}

BORING = {
    "overview",
    "usage",
    "install",
    "installation",
    "notes",
    "todo",
    "changelog",
    "license",
    "readme",
    "summary",
    "index",
    "contents",
}

LEFTOVER_STEMS = {
    "readme",
    "changelog",
    "contributing",
    "license",
    "index",
    "contents",
    "ideamine",
}

# First match wins. Lead is not a pile.
WORTH = (
    ("not_ore.tree", "skip: other product or sealed tree name"),
    ("not_ore.sealed", "skip: ledger policy marked sealed"),
    ("not_ore.uncleanable", "skip: ledger policy could not clean the file"),
    ("dirt.raw", "no usable heading; the whole file is the extract"),
    ("tin.cleaned", "extract exists only after ledger cleanup"),
    (
        "silver.pointer",
        "leftover pointer file, or following text shorter than %d characters"
        % MIN_BODY,
    ),
    ("bronze.steps", "heading plus install, todo, or list steps"),
    (
        "copper.dump",
        "heading plus at least %d characters from a .txt dump" % MIN_BODY,
    ),
    (
        "gold.vein",
        "heading plus at least %d characters from a markdown file, "
        "not a leftover pointer, not steps" % MIN_BODY,
    ),
)

WORTH_TEXT = "\n".join(
    [
        "Worth is subjective. This mine uses the first matching rule.",
        "Lead is not a pile. If we can mine gold, we cannot make lead.",
        "",
        *[("%s\t%s" % (rule, reason)) for rule, reason in WORTH],
        "",
    ]
)


@dataclass
class Nugget:
    title: str
    pile: str
    rule: str
    reason: str
    sha256: str
    source: str
    extract: str
    skipped: bool = False

    def ore(self) -> str:
        lines = [
            "ore: %s" % self.pile,
            "rule: %s" % self.rule,
            "worth: %s" % self.reason,
            "from: %s" % self.source.replace("\\", "/"),
            "hash: %s" % self.sha256,
            "chars: %d" % len(self.extract),
            "",
        ]
        return "\n".join(lines) + self.extract.rstrip() + "\n"


@dataclass
class Sweep:
    nuggets: List[Nugget] = field(default_factory=list)
    skipped_not_ore: int = 0
    scanned: int = 0
    errors: List[str] = field(default_factory=list)
    by_pile: Counter = field(default_factory=Counter)

    @property
    def skipped_lead(self) -> int:
        """Old name. Lead is not a skip pile. This is sealed / not-ore."""
        return self.skipped_not_ore


def _policy():
    try:
        from ledger import policy  # type: ignore
    except Exception:
        return None
    return policy


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return path.name


def _slug(title: str) -> str:
    raw = SLUG.sub("-", title.lower()).strip("-")
    return (raw or "idea")[:60]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _leftover(path: Path) -> bool:
    return path.stem.lower() in LEFTOVER_STEMS


def _is_steps(body: str) -> bool:
    if HOWTO.search(body):
        return True
    return len(LISTISH.findall(body)) >= 3


def _blocks(text: str) -> List[Tuple[str, str, str]]:
    """Return (title, body, raw extract including the heading)."""
    matches = list(HEADING.finditer(text))
    if not matches:
        return []
    out: List[Tuple[str, str, str]] = []
    for i, match in enumerate(matches):
        title = match.group(2).strip()
        if not title or title.lower() in BORING or len(title) > 120:
            continue
        if title.startswith("!") or title.startswith("<"):
            continue
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        extract = text[start:end].rstrip() + "\n"
        out.append((title, body, extract))
    return out[:20]


def _reason(rule: str) -> str:
    for name, text in WORTH:
        if name == rule:
            return text
    return rule


def grade_extract(
    path: Path,
    title: str,
    body: str,
    *,
    findings: bool = False,
) -> Tuple[str, str]:
    """Return (pile, rule). First match in WORTH order after file-level skips."""
    if not title:
        return "dirt", "dirt.raw"
    if findings:
        return "tin", "tin.cleaned"
    if _leftover(path) or len(body) < MIN_BODY:
        return "silver", "silver.pointer"
    if _is_steps(body):
        return "bronze", "bronze.steps"
    if path.suffix.lower() == ".txt":
        return "copper", "copper.dump"
    return "gold", "gold.vein"


def iter_docs(roots: List[Path]) -> Iterator[Tuple[Path, Path]]:
    for root in roots:
        if not root.exists():
            continue
        root = root.resolve()
        for dirpath, dirnames, filenames in os.walk(root):
            here = Path(dirpath)
            nested = here.relative_to(root).parts if here != root else ()
            if any(part.lower() in SKIP_TREE_NAMES for part in nested):
                dirnames[:] = []
                continue
            dirnames[:] = [
                d
                for d in dirnames
                if d.lower() not in SKIP_DIRS and not d.startswith(".")
            ]
            for name in filenames:
                if Path(name).suffix.lower() not in {".md", ".markdown", ".txt"}:
                    continue
                if name.upper() == "POLICY.MD":
                    continue
                yield root, here / name


def _file_skip(rel: str, text: str, policy, path: Path) -> Optional[Tuple[str, str]]:
    if any(part.lower() in SKIP_TREE_NAMES for part in path.parts):
        return "not_ore", "not_ore.tree"
    low = rel.lower().replace("/", "\\")
    if "novel" in low.split("\\") or ".env" in low or "secret" in low:
        return "not_ore", "not_ore.tree"
    if policy is None:
        return None
    verdict = policy.classify_content(rel, text)
    if verdict.tier.value == "sealed":
        return "not_ore", "not_ore.sealed"
    cleaned, _findings = policy.redact(text)
    if policy.verify_redacted(cleaned):
        return "not_ore", "not_ore.uncleanable"
    return None


def default_roots() -> List[Path]:
    return [run_dir()]


def scan(roots: Optional[List[Path]] = None) -> Sweep:
    policy = _policy()
    result = Sweep()
    seen: set = set()
    here = run_dir()
    for root, path in iter_docs(roots or default_roots()):
        base = here if here == path or here in path.parents else root
        rel = _rel(path, base)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            result.errors.append("%s: %s" % (rel, exc))
            continue
        result.scanned += 1
        skip = _file_skip(rel, text, policy, path)
        if skip:
            result.skipped_not_ore += 1
            result.by_pile["not_ore"] += 1
            continue
        findings = False
        work = text
        if policy is not None:
            work, found = policy.redact(text)
            findings = bool(found)
        blocks = _blocks(work)
        if not blocks:
            title = path.stem.replace("_", " ").replace("-", " ")
            extract = work if work.endswith("\n") else work + "\n"
            pile, rule = grade_extract(path, "", work, findings=findings)
            key = (pile, title.lower(), _hash(extract)[:8])
            if key in seen:
                continue
            seen.add(key)
            nugget = Nugget(
                title=title,
                pile=pile,
                rule=rule,
                reason=_reason(rule),
                sha256=_hash(extract),
                source=rel,
                extract=extract,
            )
            result.nuggets.append(nugget)
            result.by_pile[pile] += 1
            continue
        for title, body, extract in blocks:
            pile, rule = grade_extract(path, title, body, findings=findings)
            key = (pile, title.lower())
            if key in seen:
                continue
            seen.add(key)
            nugget = Nugget(
                title=title,
                pile=pile,
                rule=rule,
                reason=_reason(rule),
                sha256=_hash(extract),
                source=rel,
                extract=extract,
            )
            result.nuggets.append(nugget)
            result.by_pile[pile] += 1
    return result


def write_mined(result: Sweep, dest: Path | None = None) -> dict:
    dest = (dest or mined_dir()).resolve()
    if dest.name in {".lead", "lead"}:
        raise RuntimeError("If we can mine gold, we cannot make lead.")
    written = 0
    for nugget in result.nuggets:
        if nugget.pile in {"lead", "not_ore"}:
            continue
        folder = dest / nugget.pile
        folder.mkdir(parents=True, exist_ok=True)
        name = "%s-%s.ore" % (_slug(nugget.title), nugget.sha256[:8])
        (folder / name).write_text(nugget.ore(), encoding="utf-8")
        written += 1
    report = {
        "when": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "scanned": result.scanned,
        "written": written,
        "skipped_not_ore": result.skipped_not_ore,
        "by_pile": dict(result.by_pile),
        "errors": result.errors[:10],
    }
    policy = _policy()
    blob = json.dumps(report, indent=2)
    if policy is not None:
        blob, _ = policy.redact(blob)
        leaks = policy.verify_redacted(blob)
        if leaks:
            raise RuntimeError("mined sweep leaked: %s" % leaks)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "WORTH.txt").write_text(WORTH_TEXT, encoding="utf-8")
    (dest / "SWEEP.json").write_text(blob + "\n", encoding="utf-8")
    return report


def send_to_smelter(mined: Path | None = None, root: Path | None = None) -> int:
    """Copy ores into chuusmeltit/inbox only if that app folder is already here."""
    mined = (mined or mined_dir()).resolve()
    root = (root or run_dir()).resolve()
    smelter = root / "chuusmeltit"
    if not smelter.is_dir():
        raise FileNotFoundError(
            "chuusmeltit is a separate app. Put its folder next to this miner, then send."
        )
    inbox = smelter / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    copied = 0
    if mined.is_dir():
        for card in mined.glob("*/*.ore"):
            shutil.copy2(card, inbox / card.name)
            copied += 1
    return copied


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="python miner.py")
    parser.add_argument("cmd", choices=("scan", "mine"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = scan()
    report = {
        "scanned": result.scanned,
        "ideas": len(result.nuggets),
        "skipped_not_ore": result.skipped_not_ore,
        "by_pile": dict(result.by_pile),
    }
    if args.cmd == "mine":
        report = write_mined(result)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("scanned %d files" % result.scanned)
        print("  ideas      : %d" % len(result.nuggets))
        print("  not ore    : %d" % result.skipped_not_ore)
        for pile in ORES + ("not_ore",):
            if result.by_pile.get(pile):
                print("    %-8s %d" % (pile, result.by_pile[pile]))
        if args.cmd == "mine":
            print("wrote %s" % mined_dir())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
