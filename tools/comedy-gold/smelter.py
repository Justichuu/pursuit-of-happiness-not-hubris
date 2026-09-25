"""Pour mined metal into one alloy bar. Same Comedy Gold folder, not a second app.

The miner window calls this. Lead is not an alloy. Paths are derived from this
file. Stdlib only. No network.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence

HOME = Path(__file__).resolve().parent
HERE = HOME
DEFAULT_MINED = HOME / "inbox"
DEFAULT_SMELT = HOME / ".smelt"

METALS = ("gold", "silver", "copper", "tin", "dirt")
ALLOYS = {
    "electrum": ("gold", "silver"),
    "bronze": ("copper", "tin"),
    "brass": ("copper", "gold"),
    "pewter": ("tin", "dirt"),
}

SLUG = re.compile(r"[^a-z0-9]+")


def _slug(name: str) -> str:
    raw = SLUG.sub("-", name.lower()).strip("-")
    return (raw or "alloy")[:60]


def metals_for(alloy: str, extra: Sequence[str] | None = None) -> List[str]:
    name = alloy.strip().lower()
    if name == "custom":
        chosen = [m for m in (extra or ()) if m in METALS]
        if len(chosen) < 2:
            raise ValueError("A custom alloy needs at least two metals.")
        return chosen
    if name not in ALLOYS:
        raise ValueError("Unknown alloy: %s" % alloy)
    return list(ALLOYS[name])


def list_cards(mined: Path, metals: Iterable[str]) -> List[Path]:
    mined = mined.resolve()
    if mined.name in {".lead", "lead"}:
        raise RuntimeError("If we can make lead, we cannot mine gold.")
    cards: List[Path] = []
    for metal in metals:
        if metal not in METALS:
            continue
        folder = mined / metal
        if not folder.is_dir():
            continue
        cards.extend(sorted(list(folder.glob("*.ore")) + list(folder.glob("*.md"))))
    return cards


def pour(
    alloy: str,
    *,
    mined: Path = DEFAULT_MINED,
    dest: Path = DEFAULT_SMELT,
    extra: Sequence[str] | None = None,
) -> dict:
    dest = dest.resolve()
    if dest.name in {".lead", "lead"}:
        raise RuntimeError("If we can smelt, we cannot make lead.")
    metals = metals_for(alloy, extra)
    cards = list_cards(mined, metals)
    if not cards:
        raise FileNotFoundError("No mined cards in %s. Mine first." % ", ".join(metals))
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    name = "%s-%s.md" % (_slug(alloy if alloy != "custom" else "+".join(metals)), stamp)
    lines = [
        "# %s" % (alloy if alloy != "custom" else " + ".join(metals)),
        "",
        "- alloy: %s" % alloy.strip().lower(),
        "- metals: %s" % ", ".join(metals),
        "- cards: %d" % len(cards),
        "",
        "Poured from mined piles. This is not the book and not the vault.",
        "",
    ]
    digest = hashlib.sha256()
    for card in cards:
        text = card.read_text(encoding="utf-8", errors="replace")
        digest.update(card.name.encode("utf-8"))
        digest.update(b"\n")
        lines.append("## %s" % card.stem)
        lines.append("")
        lines.append(text.strip())
        lines.append("")
    lines.append("- bar-hash: `%s`" % digest.hexdigest()[:12])
    lines.append("")
    path = dest / name
    path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "alloy": alloy.strip().lower(),
        "metals": metals,
        "cards": len(cards),
        "bar": str(path),
    }
