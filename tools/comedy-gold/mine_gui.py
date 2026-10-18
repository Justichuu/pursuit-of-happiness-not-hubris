"""Drop-in miner window. Mines this folder. Sends to smelter if that app is here."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from tkinter import BOTH, END, LEFT, Button, Frame, Label, Text, Tk, X

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import miner  # noqa: E402


def _open_path(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.startfile(path)  # type: ignore[attr-defined]


class MineWindow:
    def __init__(self, root: Tk) -> None:
        self.root = root
        root.title("Idea miner")
        root.minsize(640, 420)
        root.configure(bg="#fff8ee")
        Label(
            root,
            text="Drop this app in a folder. It mines that folder.",
            font=("Georgia", 16),
            bg="#fff8ee",
        ).pack(anchor="w", padx=16, pady=(16, 4))
        Label(
            root,
            text="Piles go in .mined. chuusmeltit is a different app. Vault is later.",
            font=("Segoe UI", 11),
            bg="#fff8ee",
            wraplength=600,
            justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 12))
        bar = Frame(root, bg="#fff8ee")
        bar.pack(fill=X, padx=16)
        Button(bar, text="Scan", command=self.scan, width=12).pack(side=LEFT, padx=(0, 8))
        Button(bar, text="Mine", command=self.mine, width=12).pack(side=LEFT, padx=(0, 8))
        Button(bar, text="Send to chuusmeltit", command=self.send, width=18).pack(
            side=LEFT, padx=(0, 8)
        )
        Button(bar, text="Piles", command=self.open_piles, width=10).pack(side=LEFT)
        self.log = Text(root, height=18, wrap="word", font=("Consolas", 10))
        self.log.pack(fill=BOTH, expand=True, padx=16, pady=16)
        self.say("This folder: %s" % miner.run_dir())
        self.say("Piles: %s" % miner.mined_dir())

    def say(self, text: str) -> None:
        self.log.insert(END, text + "\n")
        self.log.see(END)

    def scan(self) -> None:
        try:
            result = miner.scan()
        except Exception:
            self.say(traceback.format_exc())
            return
        self.say("--- scan ---")
        self.say("files %d  ideas %d" % (result.scanned, len(result.nuggets)))
        for nugget in result.nuggets[:12]:
            self.say("  [%s] %s" % (nugget.pile, nugget.title))

    def mine(self) -> None:
        try:
            report = miner.write_mined(miner.scan())
        except Exception:
            self.say(traceback.format_exc())
            return
        self.say("--- mine ---")
        self.say("wrote %s ores into .mined (see WORTH.txt)" % report.get("written"))

    def send(self) -> None:
        try:
            copied = miner.send_to_smelter()
        except Exception as error:
            self.say(str(error))
            return
        self.say("--- send ---")
        self.say("copied %d cards into chuusmeltit/inbox" % copied)

    def open_piles(self) -> None:
        _open_path(miner.mined_dir())


def main() -> int:
    root = Tk()
    MineWindow(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
