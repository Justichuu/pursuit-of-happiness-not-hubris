"""Private, provenance-preserving curation pipeline for Comedy Gold.

The module uses only the Python standard library and performs no network I/O.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = 1
STATES = {"Include", "Exclude", "Redact", "Needs-context"}
SENSITIVE_CATEGORIES = {
    "credential",
    "private-address",
    "private-contact",
    "medical",
    "third-party-private",
    "security-detail",
    "unpublished-ip",
    "other-private",
}
APPROVAL_DECLARATION = "I APPROVE THIS EXACT DIGEST"
ZERO_HASH = "0" * 64


class CurationError(ValueError):
    """Raised when provenance, review, or publication rules fail."""


@dataclass(frozen=True)
class Workspace:
    root: Path

    @property
    def originals(self) -> Path:
        return self.root / "originals"

    @property
    def sources(self) -> Path:
        return self.root / "sources.jsonl"

    @property
    def candidates(self) -> Path:
        return self.root / "candidates.jsonl"

    @property
    def approvals(self) -> Path:
        return self.root / "approvals.jsonl"


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _require_keys(record: Mapping[str, Any], keys: Iterable[str], kind: str) -> None:
    missing = sorted(set(keys) - set(record))
    if missing:
        raise CurationError(f"{kind} record is missing: {', '.join(missing)}")


def _validate_date(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise CurationError(f"{field} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise CurationError(f"{field} must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise CurationError(f"{field} must be YYYY-MM-DD")
    return value


def _validate_timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CurationError(f"{field} must be an RFC 3339 UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise CurationError(f"{field} is not a valid timestamp") from exc
    return value


def initialize(root: Path | str) -> Workspace:
    workspace = Workspace(Path(root))
    workspace.originals.mkdir(parents=True, exist_ok=True)
    for ledger in (workspace.sources, workspace.candidates, workspace.approvals):
        ledger.touch(exist_ok=True)
    return workspace


def _without_chain(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.items()
        if key not in {"previous_record_hash", "record_hash"}
    }


def _load_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    expected_previous = ZERO_HASH
    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.endswith("\n"):
                raise CurationError(f"{path.name}:{line_number} is not newline-terminated")
            if not line.strip():
                raise CurationError(f"{path.name}:{line_number} is blank")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CurationError(f"{path.name}:{line_number} is invalid JSON") from exc
            if not isinstance(record, dict):
                raise CurationError(f"{path.name}:{line_number} must be an object")
            previous = record.get("previous_record_hash")
            recorded_hash = record.get("record_hash")
            if previous != expected_previous:
                raise CurationError(f"{path.name}:{line_number} breaks the hash chain")
            if not isinstance(recorded_hash, str) or len(recorded_hash) != 64:
                raise CurationError(f"{path.name}:{line_number} has no valid record hash")
            expected_hash = _sha256(_canonical({k: v for k, v in record.items() if k != "record_hash"}))
            if recorded_hash != expected_hash:
                raise CurationError(f"{path.name}:{line_number} record hash does not match")
            expected_previous = recorded_hash
            records.append(record)
    return records


def _append_ledger(path: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    records = _load_ledger(path)
    previous = records[-1]["record_hash"] if records else ZERO_HASH
    record = dict(payload)
    if "record_hash" in record or "previous_record_hash" in record:
        raise CurationError("callers may not supply ledger chain fields")
    record["previous_record_hash"] = previous
    record["record_hash"] = _sha256(_canonical(record))
    encoded = _canonical(record).decode("utf-8") + "\n"
    with path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return record


def _source_records(workspace: Workspace) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for record in _load_ledger(workspace.sources):
        _validate_source_record(record)
        source_id = record["source_id"]
        if source_id in records:
            raise CurationError(f"duplicate source_id: {source_id}")
        records[source_id] = record
    return records


def _validate_source_record(record: Mapping[str, Any]) -> None:
    _require_keys(
        record,
        {
            "schema_version",
            "record_type",
            "source_id",
            "source_date",
            "captured_at",
            "private_label",
            "content_sha256",
            "byte_length",
            "stored_as",
        },
        "source",
    )
    if record["schema_version"] != SCHEMA_VERSION or record["record_type"] != "source":
        raise CurationError("unsupported source record schema")
    if not re.fullmatch(r"src-[0-9a-f]{16}", str(record["source_id"])):
        raise CurationError("source_id must be content-derived")
    _validate_date(record["source_date"], "source_date")
    _validate_timestamp(record["captured_at"], "captured_at")
    digest = str(record["content_sha256"])
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise CurationError("content_sha256 must be lowercase SHA-256")
    if record["stored_as"] != f"originals/{digest}.utf8":
        raise CurationError("stored_as must be the content-addressed original path")
    if not isinstance(record["byte_length"], int) or record["byte_length"] < 0:
        raise CurationError("byte_length must be a non-negative integer")
    if not isinstance(record["private_label"], str) or not record["private_label"].strip():
        raise CurationError("private_label is required")


def import_source(
    root: Path | str,
    source_path: Path | str,
    *,
    source_date: str,
    private_label: str,
    captured_at: str | None = None,
) -> dict[str, Any]:
    workspace = initialize(root)
    _validate_date(source_date, "source_date")
    captured_at = captured_at or _utc_now()
    _validate_timestamp(captured_at, "captured_at")
    if not private_label.strip():
        raise CurationError("private_label is required")

    raw = Path(source_path).read_bytes()
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CurationError("sources must be valid UTF-8 so offsets stay exact") from exc
    digest = _sha256(raw)
    source_id = f"src-{digest[:16]}"
    destination = workspace.originals / f"{digest}.utf8"

    if destination.exists():
        if destination.read_bytes() != raw:
            raise CurationError("content-addressed original has unexpected bytes")
    else:
        with destination.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())

    existing = _source_records(workspace)
    if source_id in existing:
        if existing[source_id]["content_sha256"] != digest:
            raise CurationError("source ID collision")
        return existing[source_id]

    payload = {
        "schema_version": SCHEMA_VERSION,
        "record_type": "source",
        "source_id": source_id,
        "source_date": source_date,
        "captured_at": captured_at,
        "private_label": private_label,
        "content_sha256": digest,
        "byte_length": len(raw),
        "stored_as": f"originals/{digest}.utf8",
    }
    return _append_ledger(workspace.sources, payload)


def _read_original(workspace: Workspace, source: Mapping[str, Any]) -> str:
    path = workspace.root / str(source["stored_as"])
    if not path.is_file() or path.parent.resolve() != workspace.originals.resolve():
        raise CurationError(f"missing or unsafe original path for {source['source_id']}")
    raw = path.read_bytes()
    if len(raw) != source["byte_length"] or _sha256(raw) != source["content_sha256"]:
        raise CurationError(f"immutable original failed verification: {source['source_id']}")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CurationError("stored original is no longer valid UTF-8") from exc


def _normal_range(value: Any, field: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) for item in value)
    ):
        raise CurationError(f"{field} must be [start, end] integers")
    start, end = value
    if start < 0 or end <= start:
        raise CurationError(f"{field} must satisfy 0 <= start < end")
    return start, end


def _span_with_category(value: Any, field: str) -> tuple[int, int, str]:
    if not isinstance(value, dict):
        raise CurationError(f"{field} must be an object")
    _require_keys(value, {"start", "end", "category"}, field)
    start, end = _normal_range([value["start"], value["end"]], field)
    category = value["category"]
    if category not in SENSITIVE_CATEGORIES:
        raise CurationError(f"{field} has unsupported category: {category}")
    return start, end, category


def _within_selection(start: int, end: int, ranges: Sequence[tuple[int, int]]) -> bool:
    return any(selected_start <= start and end <= selected_end for selected_start, selected_end in ranges)


def _candidate_records(workspace: Workspace) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    sources = _source_records(workspace)
    all_records: list[dict[str, Any]] = []
    latest: dict[str, dict[str, Any]] = {}
    revisions: dict[str, int] = {}
    for record in _load_ledger(workspace.candidates):
        source = sources.get(str(record.get("source_id")))
        if source is None:
            raise CurationError(f"candidate refers to unknown source: {record.get('source_id')}")
        source_text = _read_original(workspace, source)
        validate_candidate(record, source_text, source)
        candidate_id = record["candidate_id"]
        expected_revision = revisions.get(candidate_id, 0) + 1
        if record["revision"] != expected_revision:
            raise CurationError(
                f"{candidate_id} revision must be {expected_revision}, got {record['revision']}"
            )
        revisions[candidate_id] = expected_revision
        all_records.append(record)
        latest[candidate_id] = record
    return all_records, latest


def validate_candidate(
    record: Mapping[str, Any], source_text: str, source: Mapping[str, Any]
) -> None:
    _require_keys(
        record,
        {
            "schema_version",
            "candidate_id",
            "revision",
            "recorded_at",
            "source_id",
            "speaker",
            "state",
            "ranges",
            "sensitive_spans",
            "redactions",
            "public_source",
            "public_source_date",
            "public_context",
            "reviewer_notes",
        },
        "candidate",
    )
    if record["schema_version"] != SCHEMA_VERSION:
        raise CurationError("unsupported candidate schema")
    if not re.fullmatch(r"CG-[0-9]{4,}", str(record["candidate_id"])):
        raise CurationError("candidate_id must look like CG-0001")
    if not isinstance(record["revision"], int) or record["revision"] < 1:
        raise CurationError("revision must be a positive integer")
    _validate_timestamp(record["recorded_at"], "recorded_at")
    if record["source_id"] != source["source_id"]:
        raise CurationError("candidate source does not match source record")
    if not isinstance(record["speaker"], str) or not record["speaker"].strip():
        raise CurationError("speaker is required")
    if record["state"] not in STATES:
        raise CurationError(f"state must be one of: {', '.join(sorted(STATES))}")
    for field in ("public_source", "public_context", "reviewer_notes"):
        if not isinstance(record[field], str):
            raise CurationError(f"{field} must be a string")
    if not record["public_source"].strip():
        raise CurationError("public_source is required and must be deliberately public-safe")
    if record["public_source_date"] != source["source_date"]:
        raise CurationError("public_source_date must exactly match the private source date")

    if not isinstance(record["ranges"], list) or not record["ranges"]:
        raise CurationError("ranges must contain at least one selection")
    ranges = [_normal_range(value, f"ranges[{index}]") for index, value in enumerate(record["ranges"])]
    previous_end = -1
    for index, (start, end) in enumerate(ranges):
        if end > len(source_text):
            raise CurationError(f"ranges[{index}] extends beyond the source")
        if start <= previous_end:
            raise CurationError("ranges must be ordered, non-overlapping, and separated by a real cut")
        previous_end = end

    if not isinstance(record["sensitive_spans"], list):
        raise CurationError("sensitive_spans must be a list")
    sensitive = [
        _span_with_category(value, f"sensitive_spans[{index}]")
        for index, value in enumerate(record["sensitive_spans"])
    ]
    if not isinstance(record["redactions"], list):
        raise CurationError("redactions must be a list")
    redactions = [
        _span_with_category(value, f"redactions[{index}]")
        for index, value in enumerate(record["redactions"])
    ]
    for field, spans in (("sensitive_spans", sensitive), ("redactions", redactions)):
        previous_end = -1
        for index, (start, end, _category) in enumerate(spans):
            if not _within_selection(start, end, ranges):
                raise CurationError(f"{field}[{index}] is outside the selected quotation")
            if start < previous_end:
                raise CurationError(f"{field} must be ordered and non-overlapping")
            previous_end = end

    if record["state"] == "Include" and (sensitive or redactions):
        raise CurationError("Include cannot contain sensitive spans or redactions; use Redact")
    if record["state"] == "Redact":
        if not redactions:
            raise CurationError("Redact requires at least one visible redaction")
        for start, end, category in sensitive:
            if not any(
                redaction_start <= start
                and end <= redaction_end
                and redaction_category == category
                for redaction_start, redaction_end, redaction_category in redactions
            ):
                raise CurationError(
                    f"sensitive {category} span {start}:{end} is not fully covered"
                )


def append_candidate(root: Path | str, candidate: Mapping[str, Any]) -> dict[str, Any]:
    workspace = initialize(root)
    supplied = _without_chain(candidate)
    if "record_type" in supplied and supplied["record_type"] != "candidate":
        raise CurationError("record_type must be candidate")
    supplied["record_type"] = "candidate"
    _all, latest = _candidate_records(workspace)
    sources = _source_records(workspace)
    source = sources.get(str(supplied.get("source_id")))
    if source is None:
        raise CurationError(f"candidate refers to unknown source: {supplied.get('source_id')}")
    validate_candidate(supplied, _read_original(workspace, source), source)
    existing = latest.get(str(supplied["candidate_id"]))
    expected = int(existing["revision"]) + 1 if existing else 1
    if supplied["revision"] != expected:
        raise CurationError(f"revision must be {expected}")
    return _append_ledger(workspace.candidates, supplied)


def _candidate_digest(candidate: Mapping[str, Any], source: Mapping[str, Any]) -> str:
    meaningful = {
        key: value
        for key, value in _without_chain(candidate).items()
        if key not in {"record_type", "recorded_at"}
    }
    meaningful["source_content_sha256"] = source["content_sha256"]
    return _sha256(_canonical(meaningful))


def fingerprint(root: Path | str, candidate_id: str) -> str:
    workspace = initialize(root)
    _all, latest = _candidate_records(workspace)
    candidate = latest.get(candidate_id)
    if candidate is None:
        raise CurationError(f"unknown candidate: {candidate_id}")
    source = _source_records(workspace)[candidate["source_id"]]
    return _candidate_digest(candidate, source)


def _approval_records(workspace: Workspace) -> list[dict[str, Any]]:
    records = _load_ledger(workspace.approvals)
    for record in records:
        _require_keys(
            record,
            {
                "schema_version",
                "record_type",
                "candidate_id",
                "candidate_digest",
                "approved_at",
                "approved_by",
                "declaration",
            },
            "approval",
        )
        if record["schema_version"] != SCHEMA_VERSION or record["record_type"] != "approval":
            raise CurationError("unsupported approval schema")
        if not re.fullmatch(r"CG-[0-9]{4,}", str(record["candidate_id"])):
            raise CurationError("approval has invalid candidate_id")
        if not re.fullmatch(r"[0-9a-f]{64}", str(record["candidate_digest"])):
            raise CurationError("approval has invalid candidate digest")
        _validate_timestamp(record["approved_at"], "approved_at")
        if not isinstance(record["approved_by"], str) or not record["approved_by"].strip():
            raise CurationError("approved_by is required")
        if record["declaration"] != APPROVAL_DECLARATION:
            raise CurationError("approval declaration is not exact")
    return records


def approve(
    root: Path | str,
    candidate_id: str,
    *,
    digest: str,
    approved_by: str,
    declaration: str,
    approved_at: str | None = None,
) -> dict[str, Any]:
    workspace = initialize(root)
    if declaration != APPROVAL_DECLARATION:
        raise CurationError(f'declaration must be exactly "{APPROVAL_DECLARATION}"')
    current = fingerprint(workspace.root, candidate_id)
    if digest != current:
        raise CurationError("digest does not match the latest candidate revision")
    _all, latest = _candidate_records(workspace)
    candidate = latest[candidate_id]
    if candidate["state"] not in {"Include", "Redact"}:
        raise CurationError("only Include or Redact candidates can receive publication approval")
    source = _source_records(workspace)[candidate["source_id"]]
    parts = _quote_parts(candidate, _read_original(workspace, source))
    findings = safety_findings(_plain_quote(parts))
    if findings:
        raise CurationError("candidate failed the safety scan: " + ", ".join(findings))
    if not approved_by.strip():
        raise CurationError("approved_by is required")
    approved_at = approved_at or _utc_now()
    _validate_timestamp(approved_at, "approved_at")
    _approval_records(workspace)
    return _append_ledger(
        workspace.approvals,
        {
            "schema_version": SCHEMA_VERSION,
            "record_type": "approval",
            "candidate_id": candidate_id,
            "candidate_digest": digest,
            "approved_at": approved_at,
            "approved_by": approved_by,
            "declaration": declaration,
        },
    )


SAFETY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "credential assignment",
        re.compile(r"(?i)\b(?:api[_ -]?key|secret|password|access[_ -]?token)\s*[:=]\s*\S+"),
    ),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("email address", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)),
    (
        "phone number",
        re.compile(r"(?<!\d)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)"),
    ),
    ("private user path", re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\\s]+")),
    ("long token-like value", re.compile(r"\b[A-Za-z0-9_-]{40,}\b")),
)


def _redactions_for_range(
    selected_start: int,
    selected_end: int,
    redactions: Sequence[tuple[int, int, str]],
) -> list[tuple[int, int, str]]:
    return [
        span
        for span in redactions
        if selected_start <= span[0] and span[1] <= selected_end
    ]


def _quote_parts(candidate: Mapping[str, Any], source_text: str) -> list[tuple[str, str]]:
    ranges = [_normal_range(value, "range") for value in candidate["ranges"]]
    redactions = [_span_with_category(value, "redaction") for value in candidate["redactions"]]
    parts: list[tuple[str, str]] = []
    for range_index, (selected_start, selected_end) in enumerate(ranges):
        if range_index:
            parts.append(("omission", " … "))
        cursor = selected_start
        for start, end, category in _redactions_for_range(selected_start, selected_end, redactions):
            if cursor < start:
                parts.append(("text", source_text[cursor:start]))
            parts.append(("redaction", f"[redacted: {category}]"))
            cursor = end
        if cursor < selected_end:
            parts.append(("text", source_text[cursor:selected_end]))
    return parts


def _plain_quote(parts: Sequence[tuple[str, str]]) -> str:
    return "".join(value for _kind, value in parts)


def safety_findings(text: str) -> list[str]:
    return [label for label, pattern in SAFETY_PATTERNS if pattern.search(text)]


def _render_quote_parts(parts: Sequence[tuple[str, str]]) -> str:
    rendered: list[str] = []
    for kind, value in parts:
        escaped = html.escape(value)
        if kind == "omission":
            rendered.append(
                '<span class="omission" aria-label="quoted material omitted"> … </span>'
            )
        elif kind == "redaction":
            rendered.append(f'<span class="redaction">{escaped}</span>')
        else:
            rendered.append(escaped)
    return "".join(rendered)


def validate_workspace(root: Path | str) -> dict[str, Any]:
    workspace = initialize(root)
    sources = _source_records(workspace)
    for source in sources.values():
        _read_original(workspace, source)
    all_candidates, latest = _candidate_records(workspace)
    approvals = _approval_records(workspace)
    approved_pairs = {
        (record["candidate_id"], record["candidate_digest"]) for record in approvals
    }
    eligible = 0
    blocked: dict[str, str] = {}
    for candidate_id, candidate in latest.items():
        if candidate["state"] not in {"Include", "Redact"}:
            blocked[candidate_id] = f"state is {candidate['state']}"
            continue
        source = sources[candidate["source_id"]]
        digest = _candidate_digest(candidate, source)
        if (candidate_id, digest) not in approved_pairs:
            blocked[candidate_id] = "latest digest has no owner approval"
            continue
        parts = _quote_parts(candidate, _read_original(workspace, source))
        findings = safety_findings(_plain_quote(parts))
        if findings:
            blocked[candidate_id] = "post-redaction safety scan: " + ", ".join(findings)
            continue
        eligible += 1
    return {
        "sources": len(sources),
        "candidate_records": len(all_candidates),
        "latest_candidates": len(latest),
        "approval_records": len(approvals),
        "eligible": eligible,
        "blocked": blocked,
    }


def _page(entries: Sequence[dict[str, str]]) -> str:
    cards = []
    for entry in entries:
        context = ""
        if entry["context"]:
            context = f'<p class="context">{html.escape(entry["context"])}</p>'
        cards.append(
            "\n".join(
                [
                    f'<article class="quote-card" id="{html.escape(entry["id"])}" '
                    f'aria-labelledby="{html.escape(entry["id"])}-heading">',
                    '  <div class="bean" aria-hidden="true"><span></span></div>',
                    f'  <h3 class="visually-hidden" id="{html.escape(entry["id"])}-heading">'
                    f'Quotation from {html.escape(entry["speaker"])}</h3>',
                    "  <figure>",
                    f'    <blockquote><p>{entry["quote_html"]}</p></blockquote>',
                    "    <figcaption>",
                    f'      <span class="speaker">— {html.escape(entry["speaker"])}</span>',
                    f'      <span class="source">{html.escape(entry["source"])}, '
                    f'<time datetime="{entry["date"]}">{entry["date"]}</time></span>',
                    "    </figcaption>",
                    f"    {context}" if context else "",
                    "  </figure>",
                    "</article>",
                ]
            )
        )
    card_html = "\n".join(cards)
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <meta name="description" content="A carefully reviewed collection of exact, attributed funny moments.">
  <title>Comedy Gold</title>
  <style>
    :root {{
      --paper: #fff8e7;
      --ink: #201338;
      --purple: #713595;
      --teal: #52d6c7;
      --gold: #ffbf3f;
      color-scheme: light;
      font-family: ui-rounded, "Arial Rounded MT Bold", system-ui, sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    html {{ background: var(--paper); color: var(--ink); }}
    body {{ margin: 0; min-width: 0; line-height: 1.55; }}
    .skip-link {{
      position: absolute; left: 0.75rem; top: 0.75rem; z-index: 10;
      padding: 0.75rem 1rem; background: var(--gold); color: var(--ink);
      border: 0.2rem solid var(--ink); transform: translateY(-180%);
    }}
    .skip-link:focus {{ transform: translateY(0); }}
    :focus-visible {{ outline: 0.25rem solid var(--ink); outline-offset: 0.2rem; }}
    .visually-hidden {{
      position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
      overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
    }}
    header {{
      padding: clamp(2.5rem, 8vw, 6rem) 1rem 3rem;
      background: var(--purple); color: var(--paper); text-align: center;
      border-bottom: 0.35rem solid var(--ink);
    }}
    .mark {{
      display: inline-grid; place-items: center; width: 5.5rem; aspect-ratio: 1;
      margin-bottom: 1rem; border: 0.3rem solid var(--ink); border-radius: 42% 58% 48% 52%;
      background: var(--gold); color: var(--ink); font-size: 2rem; transform: rotate(-3deg);
    }}
    h1 {{ margin: 0; font-size: clamp(2.5rem, 11vw, 6rem); line-height: 0.95; }}
    header p {{ max-width: 42rem; margin: 1.25rem auto 0; font-size: clamp(1rem, 3vw, 1.3rem); }}
    main {{ width: min(100% - 2rem, 54rem); margin: clamp(2rem, 6vw, 5rem) auto; }}
    .intro {{ max-width: 44rem; margin-bottom: 2rem; font-size: 1.08rem; }}
    .quote-list {{ display: grid; gap: 1.25rem; }}
    .quote-card {{
      position: relative; padding: clamp(1.25rem, 5vw, 2.5rem);
      border: 0.28rem solid var(--ink); background: var(--paper);
      box-shadow: 0.5rem 0.5rem 0 var(--teal); overflow-wrap: anywhere;
    }}
    .bean {{
      position: absolute; right: 0.8rem; top: 0.8rem; width: 2.5rem; height: 2rem;
      border: 0.18rem solid var(--ink); border-radius: 50% 45% 48% 52%; background: var(--gold);
    }}
    .bean::before, .bean::after {{
      content: ""; position: absolute; top: 0.55rem; width: 0.2rem; height: 0.2rem;
      border-radius: 50%; background: var(--ink);
    }}
    .bean::before {{ left: 0.65rem; }}
    .bean::after {{ right: 0.65rem; }}
    .bean span {{
      position: absolute; left: 0.85rem; bottom: 0.35rem; width: 0.55rem; height: 0.3rem;
      border-bottom: 0.15rem solid var(--ink); border-radius: 50%;
    }}
    figure, blockquote {{ margin: 0; }}
    blockquote {{ padding-right: 2.5rem; font-family: Georgia, serif; }}
    blockquote p {{ margin: 0; font-size: clamp(1.35rem, 5vw, 2.1rem); line-height: 1.35; }}
    figcaption {{ margin-top: 1.25rem; display: grid; gap: 0.2rem; }}
    .speaker {{ font-weight: 800; }}
    .source {{ font-size: 0.93rem; }}
    .context {{ margin: 1.25rem 0 0; padding: 0.9rem; border-left: 0.35rem solid var(--purple); }}
    .omission {{ font-weight: 800; }}
    .redaction {{ padding: 0.05em 0.25em; background: var(--ink); color: var(--paper); }}
    footer {{ padding: 2rem 1rem; border-top: 0.28rem solid var(--ink); text-align: center; }}
    @media (max-width: 24rem) {{
      main {{ width: min(100% - 1rem, 54rem); }}
      .quote-card {{ box-shadow: 0.3rem 0.3rem 0 var(--teal); }}
    }}
    @media (prefers-reduced-motion: reduce) {{ *, *::before, *::after {{ scroll-behavior: auto !important; }} }}
    @media (forced-colors: active) {{
      .mark, .quote-card, .bean, .redaction {{ forced-color-adjust: auto; }}
      .quote-card {{ box-shadow: none; }}
    }}
    @media print {{
      header {{ background: none; color: var(--ink); }}
      .quote-card {{ break-inside: avoid; box-shadow: none; }}
      .skip-link, .bean {{ display: none; }}
    }}
  </style>
</head>
<body>
  <a class="skip-link" href="#main">Skip to the quotes</a>
  <header>
    <div class="mark" aria-hidden="true">:)</div>
    <h1>Comedy Gold</h1>
    <p>Exact words, visible cuts, honest attribution. The funny part does not need a fake memory.</p>
  </header>
  <main id="main">
    <section class="intro" aria-labelledby="about-heading">
      <h2 id="about-heading">A tiny, reviewed collection</h2>
      <p>Every entry has been checked against its source and approved for this exact edition.</p>
    </section>
    <section class="quote-list" aria-label="Approved quotations">
{card_html}
    </section>
  </main>
  <footer><p>Made with context, not confidence tricks.</p></footer>
</body>
</html>
'''


def build_publication(root: Path | str, output: Path | str) -> dict[str, Any]:
    workspace = initialize(root)
    report = validate_workspace(workspace.root)
    sources = _source_records(workspace)
    _all, latest = _candidate_records(workspace)
    approvals = {
        (record["candidate_id"], record["candidate_digest"])
        for record in _approval_records(workspace)
    }
    entries: list[dict[str, str]] = []
    approved_digests: list[str] = []
    for candidate_id in sorted(latest):
        candidate = latest[candidate_id]
        if candidate["state"] not in {"Include", "Redact"}:
            continue
        source = sources[candidate["source_id"]]
        digest = _candidate_digest(candidate, source)
        if (candidate_id, digest) not in approvals:
            continue
        source_text = _read_original(workspace, source)
        parts = _quote_parts(candidate, source_text)
        findings = safety_findings(_plain_quote(parts))
        if findings:
            raise CurationError(
                f"{candidate_id} failed post-redaction safety scan: {', '.join(findings)}"
            )
        entries.append(
            {
                "id": candidate_id,
                "quote_html": _render_quote_parts(parts),
                "speaker": candidate["speaker"],
                "source": candidate["public_source"],
                "date": candidate["public_source_date"],
                "context": candidate["public_context"],
            }
        )
        approved_digests.append(digest)
    if not entries:
        reasons = "; ".join(f"{key}: {value}" for key, value in sorted(report["blocked"].items()))
        raise CurationError("no approved, publication-safe entries" + (f" ({reasons})" if reasons else ""))

    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    page = _page(entries).encode("utf-8")
    (output_path / "index.html").write_bytes(page)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "entry_count": len(entries),
        "candidate_digests": approved_digests,
        "index_sha256": _sha256(page),
    }
    (output_path / "build-manifest.json").write_bytes(_canonical(manifest) + b"\n")
    return manifest
