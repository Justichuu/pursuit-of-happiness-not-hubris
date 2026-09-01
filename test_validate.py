"""Tests for the draft-versus-product release gate."""

from __future__ import annotations

import unittest

import build_book
import validate


class ReleaseGateTests(unittest.TestCase):
    """The current tree is a living draft and must not ship as a product."""

    def test_edition_kind_is_draft(self) -> None:
        """BOOK.md still names itself a living public draft."""
        self.assertEqual(validate.book_edition_kind(), "draft")

    def test_product_version_absent(self) -> None:
        """No product version exists until the author sets one."""
        self.assertEqual(validate.product_version(), "")

    def test_reserved_slots_remain(self) -> None:
        """Empty human slots still block a product cut."""
        self.assertGreater(validate.reserved_slot_count(), 0)

    def test_product_release_fails_while_draft(self) -> None:
        """--release records both the status miss and the empty slots."""
        failures: list = []
        validate.validate_product_release(failures)
        rules = [item.split(": ", 1)[1] for item in failures]
        self.assertIn("product-status-missing", rules)
        self.assertIn("reserved-slots-block-product-release", rules)
        self.assertIn("unwritten-slot-blocks-product-release", rules)

    def test_ordinary_validate_still_passes(self) -> None:
        """A living draft may exist in public without being a product."""
        self.assertEqual(validate.main([]), 0)

    def test_release_mode_fails(self) -> None:
        """The product command exits nonzero until the author cuts."""
        self.assertEqual(validate.main(["--release"]), 1)

    def test_draft_pdf_is_not_a_product(self) -> None:
        """A layout PDF may be built now, and it must stay a draft file."""
        self.assertEqual(build_book.build([]), 0)
        path = build_book.OUTPUT_DIR / build_book.draft_filename()
        data = path.read_bytes()
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertIn(b"%%EOF", data[-32:])
        self.assertIn(b"DRAFT NOT A PRODUCT RELEASE", data)
        product = build_book.OUTPUT_DIR / build_book.product_filename("1.0.0")
        self.assertFalse(product.exists())

    def test_product_builder_refuses_empty_slots(self) -> None:
        """build_book --release must not write a product PDF yet."""
        self.assertEqual(build_book.build(["--release"]), 1)
        product = build_book.OUTPUT_DIR / build_book.product_filename("1.0.0")
        self.assertFalse(product.exists())


if __name__ == "__main__":
    unittest.main()
