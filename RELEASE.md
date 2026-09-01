# Product release

Completed chapters are a product release.

The living draft is the whole BOOK.md. It may contain reserved slots. It
may grow tomorrow.

A product is the subset that is done: every chapter that holds no
`_Unwritten. Justichuu writes here._` placeholder, paginated as a
six-by-nine trade PDF. Unfinished chapters stay in the draft. They are
not in the product.

## What determines a product release

A chapter is complete when it has no reserved unwritten slot. Completing
the chapter is the cut. The machine cannot complete a chapter by drafting
his words.

`python validate.py --release` passes when the public tree is clean and
at least one chapter is complete. It does not wait for every slot in the
book. It does not require the whole book to change its status line.

`python build_book.py --release` then writes only those completed
chapters. The filename uses the version already on the BOOK.md status
line.

If he later sets `Status: product release, version X.Y.Z`, that claims
the whole book is the product. That claim fails while any chapter is
still unfinished.

## What does not determine a product release

- Shipping an unfinished chapter because the rest of the book is ready
- Filling a reserved slot by drafting words for him to check as his
- A calendar, a word count, or an AI saying the essay seems done
- Revenue, a store listing, or a file that merely looks like a book

## Final version

The tooling has no final version. A product of completed chapters can
ship while the book is still a living draft. Another chapter can be
completed later and another PDF can follow. Whether the book should ever
end is a sentence for Justichuu, not a status the machine may invent.

## Commands

```text
python validate.py
python validate.py --voices
python validate.py --release
python build_book.py --draft
python build_book.py --release
```

`--draft` builds the whole living book and marks it as not a product.
`--release` builds only completed chapters.
