# Publication boundary

This repository is an allowlist, not a mirror of the author's computer or
conversations.

## Included in version 0.1.0

- The author-selected title and thesis
- One exact author-selected conversation fragment
- One clearly labeled AI editorial line
- Public licensing, accessibility, contribution, payment, and security rules
- A validator that reports rule failures without printing suspected secrets

## Always excluded unless deliberately reviewed and released

- Bulk conversation exports and private source archives
- Passwords, authentication material, wallet recovery material, and keys
- Addresses, private contact details, family identities, and private medical or
  financial information
- Unreleased inventions, defenses, challenge mechanisms, and patent-sensitive
  implementation details
- Paid product contents and private repositories
- Third-party words or likenesses without rights and informed consent

## Release gate

1. A human selects the exact public text.
2. Attribution, context, consent, and rights are checked.
3. The public tree is scanned for boundary and secret-shaped material.
4. The exact change is reviewed and committed.
5. Only that repository is pushed.

## Product release

A living public draft may contain reserved slots. A product release is the
completed chapters only.

A product PDF is a paginated edition of those finished chapters, not a paid
secret file and not a final edition declared by a tool. A chapter that still
holds `_Unwritten. Justichuu writes here._` stays out of the product. The
commands are in [RELEASE.md](RELEASE.md).

A draft PDF may be built for layout while the book is still a draft. It must
be marked as not a product. Generated PDFs live under `release/` and are not
part of the public source tree.

No tool may automatically mine private conversations into this public project.
No human signature, legal approval, sale, or credential may be inferred from a
generated file.
