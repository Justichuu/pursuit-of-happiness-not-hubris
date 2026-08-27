# Publication incident record

Date: August 27, 2026

Status: READY FOR REOPENING. The old remote is verifiably deleted. The sanitized
replacement is not public at the time of this record.

## Verified events

The first public history briefly included a family name in a dedication. The
author ordered the repository closed. The AI-assisted publisher then:

1. Changed the exact GitHub repository from public to private.
2. Removed the name from every file in the local public tree.
3. Ran the public-tree validator and a direct family-name scan with no matches.
4. Permanently removed the local Git history that contained the name.
5. Opened a narrowly scoped GitHub permission for deletion.
6. Deleted the exact private remote repository.
7. Confirmed through GitHub's authenticated API that the old repository returns
   HTTP 404.
8. Removed the temporary deletion permission and confirmed it is absent from
   the active CLI scopes.

The sanitized replacement has not been reopened publicly at the time of this
entry. Reopening requires a new root commit, another full-tree validation, and a
separate visibility check.

## Why this record will remain

Deleting an ordinary public Git repository cannot guarantee that every cache,
clone, notification, or automated index has forgotten earlier bytes. A clean
new history must not pretend otherwise. This record names the category of the
mistake without repeating the exposed identity.

The incident is a privacy and publication-control failure. It is not evidence
that an account credential was compromised. The released tree's validator did
not detect a key, token, private email, recovery phrase, or password-shaped
value.

## Control changes

- A real person's name or relationship requires exact human confirmation at the
  final public manifest.
- Uncertain spelling is a stop condition, not permission to choose a spelling.
- The release scan reports the file and rule without printing a suspected
  private value.
- Private conversations are never mined directly into the public tree.
- Publication and later removal are both recorded as consequences, not treated
  as proof that the internet forgot.
- Every temporary permission has a narrow purpose, a close step, and a verified
  closed state.
- Every human-facing gate has an exit. A process that only sends a person back
  to the same gate fails review.

## Reopening gate

The deletion half of this gate is complete. After reopening, this record must be
updated with the clean root commit and verified public state. Generated text is
not evidence that an external action occurred.
