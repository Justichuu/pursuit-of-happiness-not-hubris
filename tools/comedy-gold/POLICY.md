# Editorial and publication policy

## 1. Originals are evidence, not copy drafts

Import only a source the owner deliberately selects. The importer stores its
exact UTF-8 bytes at `private/originals/<sha256>.utf8`. If a file already exists
at that hash but its bytes differ, the pipeline stops. Source records include a
private label, source date, capture time, byte length, and content hash.

Never edit an original or an existing JSONL ledger line. Corrections are new
records. The hash chain detects accidental edits, reordering, and deletion from
the middle. Removing only the final records cannot be detected without a trusted
copy of the last hash, so keep an owner-held backup or checkpoint. Neither the
chain nor a checkpoint substitutes for access control.

## 2. Quotations stay exact

A candidate points to one or more character ranges in an original. Text inside
each range is reproduced exactly, including spelling, capitalization, and
punctuation. HTML escaping changes markup representation, not visible text.

If more than one range is selected, each skipped interval is shown as a Unicode
ellipsis with spaces: ` … `. The HTML gives that mark the accessible label
“quoted material omitted.” An editor may not use an ellipsis to join words in a
way that reverses or materially changes the speaker's meaning. If the result
needs explanation, keep it `Needs-context` or add reviewed `public_context`.

Redactions are the only permitted replacement. A redaction is visibly rendered
as `[redacted: category]`; it is never disguised as the speaker's words.

## 3. Four review states

- `Include`: eligible only when it has no sensitive spans or redactions.
- `Exclude`: deliberately omitted from all public output.
- `Redact`: eligible only when every declared sensitive span is fully covered by
  a redaction and the post-redaction safety scan passes.
- `Needs-context`: the default; omitted until an editor resolves the concern in
  a new revision.

The generator does not treat silence, import, an AI suggestion, or a previous
revision's approval as consent to publish.

## 4. Private by default

Do not publish credentials, authentication material, private addresses, private
contact details, medical details, private information about another person,
actionable security logic, or unpublished defensible IP. Declare each sensitive
source span with one of these categories:

- `credential`
- `private-address`
- `private-contact`
- `medical`
- `third-party-private`
- `security-detail`
- `unpublished-ip`
- `other-private`

`Include` cannot carry any sensitive span. `Redact` must cover every one. The
automatic pattern scan is intentionally conservative and incomplete; passing it
does not establish that text is safe. Human review remains mandatory.

Reviewer notes, private source labels, filesystem paths, and the unselected text
surrounding a quotation never enter the output.

## 5. Owner approval is exact and revocable

Approval is a new append-only record containing:

- candidate ID;
- digest of the exact latest candidate and immutable source hash;
- approval time and approving owner label;
- the declaration `I APPROVE THIS EXACT DIGEST`.

The build accepts only an approval matching the latest candidate digest. A new
revision automatically makes the old approval stale. To withdraw an entry,
append an `Exclude` or `Needs-context` revision; do not erase history.

This approval mechanism deliberately contains no shared secret. Secrets leak,
and a secret would not prove good judgment. The meaningful controls are local
access, explicit review, a digest-bound act, artifact inspection, and a public
release performed separately by the owner.

## 6. Attribution and context

Use a speaker label and source attribution that are truthful and safe to make
public. Do not imply that an AI quote is the owner's quote, or that the owner's
quote came from an AI. A visible source date is optional, but if provided it must
be the source date recorded in the private ledger.

Cuts, redactions, and supplied context must not manufacture a claim or remove a
qualification essential to the joke's meaning. When uncertain, use
`Needs-context`.

## 7. Accessible publication bar

Before any release, verify at least:

- headings and landmarks expose a sensible reading order;
- every quote has an attribution;
- omission and redaction markers are understandable without color;
- keyboard focus is visible;
- text works at 200% zoom and a 320 CSS-pixel viewport without horizontal
  scrolling;
- forced-colors and reduced-motion preferences remain usable;
- decorative smiling shapes are hidden from assistive technology;
- contrast is checked, not guessed;
- HTML validates and a real screen-reader pass is recorded.

Automated checks are necessary evidence, never the entire accessibility claim.
