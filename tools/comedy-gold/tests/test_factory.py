from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import factory  # noqa: E402


class FactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.smelt = self.base / ".smelt"
        self.refined = self.base / ".refined"
        self.smelt.mkdir()
        self.bar = self.smelt / "electrum-1.md"
        self.bar.write_text(
            "# electrum\n\n"
            "- alloy: electrum\n"
            "- metals: gold, silver\n"
            "- cards: 2\n\n"
            "- bar-hash: `abc123def456`\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_refine_writes_refined_marks(self) -> None:
        report = factory.refine_bar(self.bar, dest=self.refined, smelt=self.smelt)
        out = Path(report["refined"])
        self.assertTrue(out.is_file())
        self.assertEqual(out.parent, self.refined.resolve())
        text = out.read_text(encoding="utf-8")
        self.assertIn("- refined: yes", text)
        self.assertIn("- station: factory", text)
        self.assertIn("- bar-hash:", text)

    def test_refuses_mined_path(self) -> None:
        mined = self.base / ".mined" / "gold"
        mined.mkdir(parents=True)
        fake = mined / "nope.md"
        fake.write_text("x", encoding="utf-8")
        with self.assertRaises(ValueError):
            factory.refuse_if_not_smelt(fake, smelt=self.smelt)

    def test_paths_are_derived(self) -> None:
        source = Path(factory.__file__).read_text(encoding="utf-8")
        self.assertNotRegex(source, r"\b[A-Za-z]:[\\/]")   # no drive path of any kind
        self.assertEqual(factory.default_refined().name, ".refined")


if __name__ == "__main__":
    unittest.main()
