"""Command-line interface for the local Comedy Gold curation pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from miner import main as miner_main
from pipeline import (
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="comedygold",
        description="Private, exact-quote curation with digest-bound owner approval.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create an empty private workspace")
    init.add_argument("workspace", type=Path)

    imported = commands.add_parser("import-source", help="import one owner-chosen UTF-8 source")
    imported.add_argument("workspace", type=Path)
    imported.add_argument("source", type=Path)
    imported.add_argument("--source-date", required=True)
    imported.add_argument("--label", required=True, help="private label; never rendered")

    candidate = commands.add_parser("append-candidate", help="append one candidate revision JSON")
    candidate.add_argument("workspace", type=Path)
    candidate.add_argument("record", type=Path)

    digest = commands.add_parser("fingerprint", help="print the latest candidate digest")
    digest.add_argument("workspace", type=Path)
    digest.add_argument("candidate_id")

    approval = commands.add_parser("approve", help="append exact owner approval")
    approval.add_argument("workspace", type=Path)
    approval.add_argument("candidate_id")
    approval.add_argument("--digest", required=True)
    approval.add_argument("--approved-by", required=True)
    approval.add_argument("--declaration", required=True)

    validate = commands.add_parser("validate", help="verify originals, ledgers, candidates, approvals")
    validate.add_argument("workspace", type=Path)

    build = commands.add_parser("build", help="write private deterministic HTML preview")
    build.add_argument("workspace", type=Path)
    build.add_argument("output", type=Path)

    scan = commands.add_parser("scan", help="preview nearby ideas; write nothing")
    mine = commands.add_parser("mine", help="write .mined piles for the book")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "init":
            workspace = initialize(args.workspace)
            print(f"Initialized private workspace: {workspace.root}")
        elif args.command == "import-source":
            record = import_source(
                args.workspace,
                args.source,
                source_date=args.source_date,
                private_label=args.label,
            )
            print(record["source_id"])
        elif args.command == "append-candidate":
            with args.record.open("r", encoding="utf-8") as handle:
                candidate = json.load(handle)
            record = append_candidate(args.workspace, candidate)
            print(f"{record['candidate_id']} revision {record['revision']}")
            print(fingerprint(args.workspace, record["candidate_id"]))
        elif args.command == "fingerprint":
            print(fingerprint(args.workspace, args.candidate_id))
        elif args.command == "approve":
            approve(
                args.workspace,
                args.candidate_id,
                digest=args.digest,
                approved_by=args.approved_by,
                declaration=args.declaration,
            )
            print(f"Approved {args.candidate_id} for digest {args.digest}")
        elif args.command == "validate":
            print(json.dumps(validate_workspace(args.workspace), indent=2, sort_keys=True))
        elif args.command == "build":
            print(json.dumps(build_publication(args.workspace, args.output), indent=2, sort_keys=True))
        elif args.command == "scan":
            return miner_main(["scan"])
        elif args.command == "mine":
            return miner_main(["mine"])
    except (CurationError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if args.command == "approve":
            print(f'Required declaration: "{APPROVAL_DECLARATION}"', file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
