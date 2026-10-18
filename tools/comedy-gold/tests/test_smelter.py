from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import smelter  # noqa: E402


class SmelterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.mined = self.base / ".mined"
        self.smelt = self.base / ".smelt"
        (self.mined / "gold").mkdir(parents=True)
        (self.mined / "silver").mkdir(parents=True)
        (self.mined / "gold" / "bean.md").write_text(
            "# Bean\n\n- pile: gold\n- hash: `aaa`\n\nThis miner does not pay.\n",
            encoding="utf-8",
        )
        (self.mined / "silver" / "leftover.md").write_text(
            "# Leftover\n\n- pile: silver\n- hash: `bbb`\n\nThis miner does not pay.\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_electrum_pours_gold_and_silver(self) -> None:
        report = smelter.pour(
            "electrum",
            mined=self.mined,
            dest=self.smelt,
        )
        self.assertEqual(report["cards"], 2)
        bar = Path(report["bar"])
        self.assertTrue(bar.is_file())
        self.assertEqual(bar.parent, self.smelt.resolve())
        text = bar.read_text(encoding="utf-8")
        self.assertIn("gold", text)
        self.assertIn("silver", text)
        self.assertNotIn("Vault leftover", text)

    def test_refuses_lead_dest(self) -> None:
        with self.assertRaises(RuntimeError):
            smelter.pour("electrum", mined=self.mined, dest=self.base / ".lead")

    def test_custom_needs_two_metals(self) -> None:
        with self.assertRaises(ValueError):
            smelter.pour("custom", mined=self.mined, dest=self.smelt, extra=["gold"])

    def test_paths_are_derived(self) -> None:
        source = Path(smelter.__file__).read_text(encoding="utf-8")
        self.assertNotRegex(source, r"\b[A-Za-z]:[\\/]")   # no drive path of any kind
        self.assertTrue(smelter.HERE.is_dir())


if __name__ == "__main__":
    unittest.main()
