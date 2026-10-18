"""Smelter window. Lives in its own folder. Writes .smelt here."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from tkinter import BOTH, END, LEFT, Button, Frame, Label, OptionMenu, StringVar, Text, Tk, X

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import smelter  # noqa: E402


class SmeltWindow:
    def __init__(self, root: Tk) -> None:
        self.root = root
        root.title("Smelter")
        root.minsize(640, 400)
        root.configure(bg="#fff8ee")
        Label(
            root,
            text="Separate tool. Reads inbox in this folder. Writes .smelt here.",
            font=("Segoe UI", 11),
            bg="#fff8ee",
            wraplength=600,
            justify="left",
        ).pack(anchor="w", padx=16, pady=16)
        bar = Frame(root, bg="#fff8ee")
        bar.pack(fill=X, padx=16)
        self.alloy = StringVar(value="electrum")
        OptionMenu(bar, self.alloy, "electrum", "bronze", "brass", "pewter").pack(side=LEFT)
        Button(bar, text="Smelt", command=self.smelt, width=12).pack(side=LEFT, padx=8)
        self.log = Text(root, height=16, wrap="word", font=("Consolas", 10))
        self.log.pack(fill=BOTH, expand=True, padx=16, pady=16)
        self.log.insert(END, "inbox %s\n.smelt %s\n" % (smelter.DEFAULT_MINED, smelter.DEFAULT_SMELT))

    def smelt(self) -> None:
        try:
            poured = smelter.pour(self.alloy.get())
        except Exception:
            self.log.insert(END, traceback.format_exc() + "\n")
            return
        self.log.insert(END, "bar %s\n" % poured["bar"])


def main() -> int:
    root = Tk()
    SmeltWindow(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
