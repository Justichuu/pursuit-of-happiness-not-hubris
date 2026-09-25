# Comedy Gold

Comedy Gold is a private, local-first quote-curation pipeline. It turns material
the owner has deliberately imported into a small, accessible HTML collection
without silently rewriting quotations or leaking the private source archive.

This directory is only the foundation. It contains no chat transcript, mined
quote, credential, private address, or publishable book. Nothing in the private
workspace is approved merely because it was imported.

## Safety model

- Original UTF-8 bytes are copied once into a content-addressed file and are
  never edited by this program.
- Source, candidate, and approval ledgers are append-only and hash-chained.
- Quote selections are Unicode character offsets into the original. The program
  reconstructs the quote from those offsets; it never accepts a rewritten quote.
- A gap between selected ranges is always rendered as a visible ` … ` with an
  accessible explanation that quoted material was omitted.
- `Needs-context` is the default review state. `Exclude` and `Needs-context`
  records cannot be published.
- `Redact` records must cover every declared sensitive span. Redactions render as
  visible `[redacted: category]` markers.
- Obvious credential, email, phone, private-key, user-path, and long-token shapes
  are checked again after redaction. A match blocks the build.
- Publication requires a separate owner-approval record tied to the exact
  candidate digest. Revising the candidate invalidates that approval.
- The private source label, reviewer notes, source path, and source text never
  enter the public HTML.

This is an auditable workflow gate, not secret DRM and not proof of a person's
identity. Anyone with write access to the private workspace could alter the
program or rebuild its ledgers. Keep the workspace access-controlled, review the
generated artifact, and let the owner be the only person who runs the approval
step.

The detailed editorial rules are in [POLICY.md](POLICY.md).

## Miner (the shovel)

This is the only extra window. It finds public idea headings for the Comedy Gold
part of the book. It does not publish the book and it does not pay anyone.

```
Miner.exe
```

Run it in a folder. It creates `.mined` there and writes `.ore` files into one
folder per ore (gold, silver, copper, bronze, tin, dirt). Each `.ore` is the
raw extract plus the rule that graded it. The definition is `.mined/WORTH.txt`.
chuusmeltit is a different app. The miner only sends copies if `chuusmeltit`
is already next to it.

Piles land in `.mined\` (gold first, dirt last). Lead is not mined. Lead is the
final product: a buyer puts factory gold bars into the existing Novel Vault
(the lead safe already in this workshop). If we can mine gold, we cannot make
lead. `LeadSafe.bat` only seals one factory-refined bar from `.refined`. It will
not take a miner card or a smelter bar, and it does not open the vault. Pictures:
`Pictures.bat` or `diagrams\flows.html`. You still import a source and approve
an exact bite before a line is in the book.

## Quick start

Python 3.10 or newer is sufficient. There are no packages to install and no
network calls.

```powershell
Set-Location tools\comedy-gold   # from the repository root

# Creates private\ and its empty append-only ledgers.
python cli.py init private

# Run only when the owner intentionally chooses a source to import.
python cli.py import-source private C:\path\to\chosen-source.txt `
  --source-date 2026-08-27 --label "Private owner label"

# Copy candidate.template.json somewhere private, fill in source offsets, then:
python cli.py append-candidate private C:\path\to\candidate.json

# Validate everything and print the digest the owner must review.
python cli.py validate private
python cli.py fingerprint private CG-0001

# The owner runs this exact step only after reviewing the source and preview.
python cli.py approve private CG-0001 `
  --digest <digest-printed-above> `
  --approved-by owner `
  --declaration "I APPROVE THIS EXACT DIGEST"

# Produces deterministic index.html and build-manifest.json.
python cli.py build private private\preview
```

`private\` and `dist\` are ignored by Git. Keep the preview private until the
owner has inspected it with sight, keyboard-only navigation, a screen reader,
zoom, narrow viewport, and forced-colors/high-contrast mode. This project never
uploads or publishes an artifact.

## Candidate records

Candidate revisions are JSON objects. `candidate.template.json` is the canonical
shape. Important fields:

- `candidate_id`: stable editorial ID, such as `CG-0001`.
- `revision`: starts at 1 and increases by exactly one. Previous revisions stay
  in the ledger.
- `state`: `Include`, `Exclude`, `Redact`, or `Needs-context`.
- `ranges`: ordered `[start, end]` Unicode character offsets into the source;
  `end` is exclusive.
- `sensitive_spans`: selected source ranges that must not appear unchanged.
- `redactions`: selected source ranges replaced with visible redaction markers.
- `public_source`: attribution safe to show publicly. The private source label
  is never substituted for it.
- `public_context`: optional, reviewed context safe to show publicly.
- `reviewer_notes`: private and never rendered.

To revise a candidate, create a new record with the same `candidate_id` and the
next `revision`, then run `append-candidate` again. Do not edit an old ledger
line. Obtain a new fingerprint and approval after every revision.

## Deterministic validation

```powershell
python -m unittest discover -s tests -v
python cli.py validate private
```

For identical validated ledgers, originals, and approvals, `build` writes
byte-identical HTML and a manifest containing its SHA-256 hash. It deliberately
omits a build timestamp.

## Output roadmap

HTML is the sole implemented publication format because its semantics and
accessibility can be tested without adding a conversion dependency.

- EPUB: derive EPUB 3 navigation and XHTML from the same validated document
  model; validate with EPUBCheck and test reading order in multiple readers.
- PDF: use a renderer that preserves a tagged structure tree, language,
  headings, quotes, links, and reading order; verify with PAC or an equivalent
  accessibility checker. A browser printout is not automatically an accessible
  PDF.

Neither format should bypass the candidate digest, owner approval, safety scan,
or exact-quotation rules.

## Visual direction

The generated page uses an original five-color, blocky “happy bean” language:
solid shapes, thick outlines, generous type, and small smiles. It does not copy
Chowder characters, art, dialogue, layouts, lettering, or trade dress. The
phrase “Comedy Gold” is treated as this project's title, not as a license to
reproduce someone else's protected expression.
