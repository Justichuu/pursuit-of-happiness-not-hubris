from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import miner  # noqa: E402


class MinerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.ideas = self.base / "ideas"
        self.novel = self.base / "novel"
        self.ideas.mkdir()
        self.novel.mkdir()
        (self.ideas / "funny.md").write_text(
            "# The bean laughs first\n\n"
            "A public joke for the book pile, told once and kept raw.\n",
            encoding="utf-8",
        )
        (self.ideas / "empty.md").write_text("no heading here at all\n", encoding="utf-8")
        (self.ideas / "README.md").write_text(
            "# Leftover pointer\n\n"
            "This heading lives in a leftover pointer file so it is silver.\n",
            encoding="utf-8",
        )
        (self.ideas / "setup.md").write_text(
            "# Wire the lamp\n\n"
            "- [ ] buy the bulb\n"
            "- [ ] screw it in\n"
            "- [ ] flip the switch\n",
            encoding="utf-8",
        )
        (self.ideas / "dump.txt").write_text(
            "# Scratch note\n\n"
            "Plain text dump with enough following characters to count as copper.\n",
            encoding="utf-8",
        )
        (self.novel / "secret.md").write_text(
            "# Vault leftover\n\nthis must never be mined\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_scan_skips_novel_and_sorts_headings(self) -> None:
        result = miner.scan([self.ideas, self.novel])
        titles = {n.title for n in result.nuggets}
        self.assertIn("The bean laughs first", titles)
        self.assertNotIn("Vault leftover", titles)
        self.assertGreaterEqual(result.skipped_not_ore, 1)

    def test_worth_rules_sort_raw_extracts(self) -> None:
        result = miner.scan([self.ideas, self.novel])
        by_title = {n.title: n for n in result.nuggets}
        self.assertEqual(by_title["The bean laughs first"].pile, "gold")
        self.assertEqual(by_title["The bean laughs first"].rule, "gold.vein")
        self.assertIn("told once and kept raw", by_title["The bean laughs first"].extract)
        self.assertEqual(by_title["Leftover pointer"].pile, "silver")
        self.assertEqual(by_title["Wire the lamp"].pile, "bronze")
        self.assertEqual(by_title["Scratch note"].pile, "copper")
        dirt = [n for n in result.nuggets if n.pile == "dirt"]
        self.assertTrue(dirt)
        self.assertIn("no heading here at all", dirt[0].extract)

    def test_mine_writes_ore_not_md(self) -> None:
        dest = self.base / ".mined"
        result = miner.scan([self.ideas, self.novel])
        report = miner.write_mined(result, dest)
        self.assertGreaterEqual(report["written"], 1)
        self.assertFalse((dest / "lead").exists())
        with self.assertRaises(RuntimeError):
            miner.write_mined(result, self.base / ".lead")
        gold = list((dest / "gold").glob("*.ore"))
        self.assertTrue(gold)
        self.assertFalse(list((dest / "gold").glob("*.md")))
        text = gold[0].read_text(encoding="utf-8")
        self.assertIn("ore: gold", text)
        self.assertIn("rule: gold.vein", text)
        self.assertIn("The bean laughs first", text)
        self.assertIn("told once and kept raw", text)
        self.assertNotIn("Vault leftover", text)
        worth = (dest / "WORTH.txt").read_text(encoding="utf-8")
        self.assertIn("gold.vein", worth)
        self.assertIn("silver.pointer", worth)
        self.assertFalse((dest.parent / ".smelt").exists())

    def test_send_needs_smelter_folder(self) -> None:
        with self.assertRaises(FileNotFoundError):
            miner.send_to_smelter(self.base / ".mined", root=self.base)

    def test_paths_are_derived(self) -> None:
        source = Path(miner.__file__).read_text(encoding="utf-8")
        self.assertNotRegex(source, r"\b[A-Za-z]:[\\/]")   # no drive path of any kind


if __name__ == "__main__":
    unittest.main()
