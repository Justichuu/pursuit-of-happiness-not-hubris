"""Tests for completed-chapter product releases."""

from __future__ import annotations

import unittest

import build_book
import validate


class ReleaseGateTests(unittest.TestCase):
    """Completed chapters may ship; unfinished chapters may not."""

    def test_edition_kind_is_draft(self) -> None:
        """The whole book may stay a living public draft."""
        self.assertEqual(validate.book_edition_kind(), "draft")

    def test_edition_version_follows_draft_status(self) -> None:
        """A completed-chapter cut uses the draft version number."""
        self.assertEqual(validate.edition_version(), "0.1.1")
        self.assertEqual(validate.product_version(), "")

    def test_reserved_slots_remain_in_unfinished_chapters(self) -> None:
        """Empty human slots can remain in the living draft."""
        self.assertGreater(validate.reserved_slot_count(), 0)
        self.assertIn("The ego", validate.incomplete_chapter_titles())
        self.assertIn("The irony mark", validate.incomplete_chapter_titles())
        self.assertIn(
            "A cut is not an ending",
            validate.incomplete_chapter_titles(),
        )

    def test_some_chapters_are_already_complete(self) -> None:
        """Chapters without reserved slots are already a product unit."""
        complete = validate.complete_chapter_titles()
        self.assertIn("The thesis", complete)
        self.assertIn("Comedy Gold", complete)
        self.assertNotIn("The ego", complete)

    def test_product_release_allows_completed_chapters(self) -> None:
        """--release does not wait for every slot in the book."""
        failures: list = []
        validate.validate_product_release(failures)
        self.assertEqual(failures, [])

    def test_ordinary_validate_still_passes(self) -> None:
        """A living draft may exist in public with unfinished chapters."""
        self.assertEqual(validate.main([]), 0)

    def test_release_mode_passes(self) -> None:
        """The product command may cut completed chapters now."""
        self.assertEqual(validate.main(["--release"]), 0)

    def test_draft_pdf_is_not_a_product(self) -> None:
        """The full-book layout PDF stays marked as a draft."""
        self.assertEqual(build_book.build([]), 0)
        path = build_book.OUTPUT_DIR / build_book.draft_filename()
        data = path.read_bytes()
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertIn(b"%%EOF", data[-32:])
        self.assertIn(b"DRAFT NOT A PRODUCT RELEASE", data)
        self.assertIn(b"The irony mark", data)

    def test_product_pdf_contains_only_completed_chapters(self) -> None:
        """The product file ships finished chapters and omits empty slots."""
        self.assertEqual(build_book.build(["--release"]), 0)
        path = build_book.OUTPUT_DIR / build_book.product_filename("0.1.1")
        data = path.read_bytes()
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertIn(b"Completed chapters. The living draft continues.", data)
        self.assertIn(b"The thesis", data)
        self.assertIn(b"Comedy Gold", data)
        self.assertNotIn(b"Unwritten. Justichuu writes here.", data)
        self.assertNotIn(b"DRAFT NOT A PRODUCT RELEASE", data)
        self.assertNotIn(b"The irony mark", data)
        self.assertNotIn(b"The ego", data)


if __name__ == "__main__":
    unittest.main()
