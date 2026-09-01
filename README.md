# The Pursuit of Happiness over Hubris

This is the day-one public draft of a living open book by Justichuu.

[Read the book](BOOK.md)

## The short version

Success cannot require another person to repeat one exact life. A useful path
should help a person gain agency, make things, recover from mistakes, and decide
what a good life means for them.

The book is being built in public so the work can be read, checked, preserved,
and improved. Public does not mean careless. Only deliberately released text
belongs here.

## What is public

- The title, thesis, and selected writing that the author intentionally releases
- The Comedy Gold, Dramedy, and Andromedy sections, with exact attribution for
  every quoted fragment
- The publication boundary, [voice separation rule](VOICES.md), and contribution
  rules
- The name-free [publication incident record](INCIDENT.md)
- The validator used before publication
- The Git history showing how the public draft changes

## What is not public

- Private conversations or bulk chat exports
- Passwords, keys, recovery material, addresses, or identifying family details
- Unreleased inventions, security mechanisms, or patent-sensitive work
- A quote from any person who did not knowingly release it
- Claims of credentials, revenue, results, or approval that do not exist

See [PUBLICATION-BOUNDARY.md](PUBLICATION-BOUNDARY.md) for the complete rule.

## Verify this checkout

The validator has no third-party dependencies:

```text
python validate.py
```

It checks the required public files, text encoding, publication boundaries,
secret-shaped values, voice separation, and the project's no-long-dash rule. It
reports only the file and failed rule, never the suspected value.

To see how many words belong to each voice:

```text
python validate.py --voices
```

## License and contributions

Released original text is offered under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), subject to the
details in [LICENSE.md](LICENSE.md). The license permits commercial reuse and
does not force reusers to pay royalties.

Pull-request proposals are open. Opening a pull request does not guarantee a
merge or payment. Paid terms must be explicit and accepted before paid work is
merged. Read [CONTRIBUTING.md](CONTRIBUTING.md), [PAYMENT.md](PAYMENT.md), and
the pull-request template before offering substantial work.

## Two authors, never blended

Justichuu writes the book. An AI assistant contributes labeled passages. In any
chapter that declares separated voices, every paragraph names its speaker, and
neither author writes inside the other's blocks. Slots reserved for Justichuu
stay visibly unwritten until he writes them, because a ghostwritten passage
under his name would be the exact failure this book is about.

The full rule is in [VOICES.md](VOICES.md), and the validator enforces it.

## Current evidence

- Public draft version: 0.1.2
- Publication history: rebuilding after a disclosed privacy mistake
- Revenue attributed to this book: $0
- Paid contributors: none
- Human-authored foundation: title, thesis language, and the first selected
  Comedy Gold fragment
- AI assistance: editing, repository structure, validation, labeled editorial
  lines, and labeled passages in the ego chapter
- Voice accounting: run `python validate.py --voices` for the current word count
  of each voice and the number of slots still awaiting Justichuu

No degree, award, sale, investor return, or universal outcome is claimed.
