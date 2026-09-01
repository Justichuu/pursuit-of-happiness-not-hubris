# Product release

A living public draft and a product release are not the same object.

The draft is BOOK.md in this repository. It may contain reserved slots. It
may grow tomorrow. It is the public book.

A product release is a numbered cut of that book: a paginated PDF in trade
book pages, generated from the current BOOK.md, allowed to call itself a
product only after Justichuu has done the human work the machine cannot do.

## What determines a product release

All of these must be true at once:

1. Every reserved Justichuu slot in a voice-separated chapter is filled by
   him. The placeholder `_Unwritten. Justichuu writes here._` is gone.
2. He changed the BOOK.md status line to exactly:

   `Status: product release, version X.Y.Z`

   He chooses the number. A tool does not.
3. `python validate.py` passes on the public tree.
4. `python validate.py --release` passes. That command adds the product
   rules on top of the ordinary checks.
5. `python build_book.py --release` then writes the product PDF under
   `release/`. The builder calls the release validator and refuses to write
   a product file if the gate fails.

No contributor merge, CI pass, or generated paragraph can stand in for
steps 1 and 2. A draft PDF may be built for layout while slots are empty.
It is marked `DRAFT` and `NOT A PRODUCT RELEASE`. It is not a product.

## What does not determine a product release

- A calendar, a word count, or an AI saying the essay seems done
- Filling a reserved slot by drafting words for him to check as his
- Tagging a Git commit without the status line and the filled slots
- Revenue, a store listing, or a file that merely looks like a book

## Final version

The tooling has no final version. A product is a snapshot. The living draft
can continue after a cut, and another cut can follow. Whether the book
should ever end is a sentence for Justichuu, not a status the machine may
invent.

## Commands

```text
python validate.py
python validate.py --voices
python validate.py --release
python build_book.py --draft
python build_book.py --release
```

`--release` is expected to fail until he writes the slots and changes the
status line. That failure is the gate working.
