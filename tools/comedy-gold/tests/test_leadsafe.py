from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import leadsafe  # noqa: E402


class LeadSafeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.refined = self.base / ".refined"
        self.mined = self.base / ".mined" / "gold"
        self.smelt = self.base / ".smelt"
        self.refined.mkdir()
        self.mined.mkdir(parents=True)
        self.smelt.mkdir()
        self.card = self.refined / "electrum-bar.md"
        self.card.write_text(
            "# Refined electrum\n\n"
            "- refined: yes\n"
            "- station: factory\n"
            "- from-smelt: `electrum-1.md`\n"
            "- alloy: electrum\n"
            "- bar-hash: `abc123def456`\n\n"
            "This factory does not pay.\n",
            encoding="utf-8",
        )
        self.mined_card = self.mined / "bean.md"
        self.mined_card.write_text(
            "# Bean\n\n- pile: gold\n- hash: `aaa`\n\nThis miner does not pay.\n",
            encoding="utf-8",
        )
        self.smelt_bar = self.smelt / "electrum-1.md"
        self.smelt_bar.write_text(
            "# electrum\n\n- alloy: electrum\n- metals: gold, silver\n- bar-hash: `abc`\n",
            encoding="utf-8",
        )
        leadsafe.REFINED = self.refined

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_accepts_refined_bar(self) -> None:
        self.assertEqual(
            leadsafe.refuse_if_not_refined(self.card, refined=self.refined),
            self.card.resolve(),
        )

    def test_refuses_mined_and_smelt(self) -> None:
        with self.assertRaises(ValueError):
            leadsafe.refuse_if_not_refined(self.mined_card, refined=self.refined)
        with self.assertRaises(ValueError):
            leadsafe.refuse_if_not_refined(self.smelt_bar, refined=self.refined)

    def test_check_does_not_need_the_vault(self) -> None:
        self.assertEqual(leadsafe.main([str(self.card), "--check"]), 0)
        self.assertEqual(leadsafe.main([str(self.mined_card), "--check"]), 2)

    def test_paths_are_derived(self) -> None:
        source = Path(leadsafe.__file__).read_text(encoding="utf-8")
        self.assertNotRegex(source, r"\b[A-Za-z]:[\\/]")   # no drive path of any kind
        self.assertEqual(leadsafe.VAULT_DIR.name, "novel")
        self.assertIn(leadsafe.HERE.name.lower(), {"comedy-gold", "comedygold", "poop", "chuuminer"})


if __name__ == "__main__":
    unittest.main()
