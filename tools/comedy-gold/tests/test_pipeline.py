from __future__ import annotations

import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline import (  # noqa: E402
    APPROVAL_DECLARATION,
    CurationError,
    append_candidate,
    approve,
    build_publication,
    fingerprint,
    import_source,
    initialize,
    validate_workspace,
)


class TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.ids: set[str] = set()
        self.aria_labels: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(str(values["id"]))
        if values.get("aria-label"):
            self.aria_labels.add(str(values["aria-label"]))

    def handle_data(self, data: str) -> None:
        self.text.append(data)


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.workspace = self.base / "private"
        self.source_file = self.base / "source.txt"
        self.source_text = "Beans laugh loudly. Secrets stay private."
        self.source_file.write_text(self.source_text, encoding="utf-8", newline="")
        initialize(self.workspace)
        self.source = import_source(
            self.workspace,
            self.source_file,
            source_date="2026-08-27",
            private_label="PRIVATE LABEL MUST NOT LEAK",
            captured_at="2026-08-27T12:00:00Z",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def candidate(self, **changes: object) -> dict[str, object]:
        second_start = self.source_text.index("Secrets")
        record: dict[str, object] = {
            "schema_version": 1,
            "candidate_id": "CG-0001",
            "revision": 1,
            "recorded_at": "2026-08-27T12:01:00Z",
            "source_id": self.source["source_id"],
            "speaker": "Synthetic bean",
            "state": "Include",
            "ranges": [[0, len("Beans laugh")], [second_start, len(self.source_text)]],
            "sensitive_spans": [],
            "redactions": [],
            "public_source": "Synthetic test fixture",
            "public_source_date": "2026-08-27",
            "public_context": "Invented text used only for a deterministic test.",
            "reviewer_notes": "This must stay private.",
        }
        record.update(changes)
        return record

    def approve_latest(self, candidate_id: str = "CG-0001") -> str:
        digest = fingerprint(self.workspace, candidate_id)
        approve(
            self.workspace,
            candidate_id,
            digest=digest,
            approved_by="test owner",
            declaration=APPROVAL_DECLARATION,
            approved_at="2026-08-27T12:02:00Z",
        )
        return digest

    def test_exact_ranges_visible_ellipsis_accessible_html_and_no_private_metadata(self) -> None:
        append_candidate(self.workspace, self.candidate())
        digest = self.approve_latest()
        first = self.base / "first"
        second = self.base / "second"
        manifest = build_publication(self.workspace, first)
        build_publication(self.workspace, second)

        page = (first / "index.html").read_text(encoding="utf-8")
        self.assertEqual((first / "index.html").read_bytes(), (second / "index.html").read_bytes())
        self.assertEqual(manifest["candidate_digests"], [digest])
        self.assertIn("Beans laugh", page)
        self.assertIn("Secrets stay private.", page)
        self.assertIn("quoted material omitted", page)
        self.assertNotIn("PRIVATE LABEL MUST NOT LEAK", page)
        self.assertNotIn("This must stay private", page)

        parsed = TextCollector()
        parsed.feed(page)
        visible = "".join(parsed.text)
        self.assertIn("Beans laugh … Secrets stay private.", visible)
        self.assertIn("main", parsed.ids)
        self.assertIn("Approved quotations", parsed.aria_labels)

    def test_unapproved_candidate_cannot_build(self) -> None:
        append_candidate(self.workspace, self.candidate())
        report = validate_workspace(self.workspace)
        self.assertEqual(report["eligible"], 0)
        self.assertIn("no owner approval", report["blocked"]["CG-0001"])
        with self.assertRaisesRegex(CurationError, "no approved"):
            build_publication(self.workspace, self.base / "output")

    def test_new_revision_invalidates_old_approval(self) -> None:
        append_candidate(self.workspace, self.candidate())
        self.approve_latest()
        append_candidate(
            self.workspace,
            self.candidate(
                revision=2,
                recorded_at="2026-08-27T12:03:00Z",
                public_context="New context requires a new approval.",
            ),
        )
        report = validate_workspace(self.workspace)
        self.assertEqual(report["eligible"], 0)
        self.assertIn("no owner approval", report["blocked"]["CG-0001"])

    def test_redaction_must_cover_declared_sensitive_span(self) -> None:
        start = self.source_text.index("Secrets")
        end = start + len("Secrets")
        unsafe = self.candidate(
            state="Redact",
            ranges=[[0, len(self.source_text)]],
            sensitive_spans=[{"start": start, "end": end, "category": "security-detail"}],
            redactions=[{"start": start + 1, "end": end, "category": "security-detail"}],
        )
        with self.assertRaisesRegex(CurationError, "not fully covered"):
            append_candidate(self.workspace, unsafe)

        safe = self.candidate(
            state="Redact",
            ranges=[[0, len(self.source_text)]],
            sensitive_spans=[{"start": start, "end": end, "category": "security-detail"}],
            redactions=[{"start": start, "end": end, "category": "security-detail"}],
        )
        append_candidate(self.workspace, safe)
        self.approve_latest()
        build_publication(self.workspace, self.base / "redacted")
        page = (self.base / "redacted" / "index.html").read_text(encoding="utf-8")
        self.assertIn("[redacted: security-detail]", page)
        self.assertNotIn("Secrets stay private.", page)

    def test_automatic_safety_scan_blocks_obvious_unredacted_secret(self) -> None:
        credential_source = self.base / "credential.txt"
        credential_text = "api_key=abcdefghijklmnopqrstuvwxyz123456"
        credential_source.write_text(credential_text, encoding="utf-8", newline="")
        source = import_source(
            self.workspace,
            credential_source,
            source_date="2026-08-27",
            private_label="credential fixture",
            captured_at="2026-08-27T12:04:00Z",
        )
        candidate = self.candidate(
            candidate_id="CG-0002",
            source_id=source["source_id"],
            ranges=[[0, len(credential_text)]],
            public_source="Synthetic credential fixture",
        )
        append_candidate(self.workspace, candidate)
        with self.assertRaisesRegex(CurationError, "safety scan"):
            self.approve_latest("CG-0002")
        report = validate_workspace(self.workspace)
        self.assertIn("no owner approval", report["blocked"]["CG-0002"])
        with self.assertRaisesRegex(CurationError, "no approved"):
            build_publication(self.workspace, self.base / "unsafe")

    def test_needs_context_cannot_receive_publication_approval(self) -> None:
        append_candidate(self.workspace, self.candidate(state="Needs-context"))
        with self.assertRaisesRegex(CurationError, "only Include or Redact"):
            self.approve_latest()

    def test_duplicate_import_does_not_duplicate_source_ledger(self) -> None:
        again = import_source(
            self.workspace,
            self.source_file,
            source_date="2026-08-27",
            private_label="A changed private label is not a new source",
            captured_at="2026-08-27T13:00:00Z",
        )
        self.assertEqual(again["source_id"], self.source["source_id"])
        self.assertEqual(len((self.workspace / "sources.jsonl").read_text(encoding="utf-8").splitlines()), 1)

    def test_hash_chain_detects_ledger_edit(self) -> None:
        append_candidate(self.workspace, self.candidate())
        ledger = self.workspace / "candidates.jsonl"
        record = json.loads(ledger.read_text(encoding="utf-8"))
        record["speaker"] = "Tampered speaker"
        ledger.write_text(json.dumps(record) + "\n", encoding="utf-8", newline="")
        with self.assertRaisesRegex(CurationError, "record hash does not match"):
            validate_workspace(self.workspace)


if __name__ == "__main__":
    unittest.main()
