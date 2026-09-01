# Accessibility

Accessibility is part of authorship, not a later format conversion.

The day-one edition is text-first Markdown with semantic headings, descriptive
link text, short paragraphs, and no meaning that depends on color, animation,
audio, pointer precision, or an image. It should remain usable with keyboard,
screen reader, zoom, reflow, text extraction, and low-bandwidth access.

The Markdown in BOOK.md remains the accessible source. A generated PDF is a
paginated edition of that source. It must keep extractable text, a logical
heading order, and no meaning that exists only as a watermark or a page
decoration. A draft PDF is labeled as not a product and may include unfinished
chapters. A product PDF includes only completed chapters. See
[RELEASE.md](RELEASE.md).

Future HTML, EPUB, audio, video, or PDF editions must preserve:

- A logical heading and reading order
- Keyboard access and visible focus
- Reflow at narrow widths and high zoom
- Reduced-motion behavior
- Captions and transcripts for timed media
- Text alternatives for meaningful images
- Decorative art hidden from assistive technology
- No autoplay and no required drag, hover, speech, or fine pointer motion

Automated validation is evidence, not a claim that a disabled person has tested
the result. Human assistive-technology review must be named honestly when it
occurs.

Report an accessibility problem without including private information by using
the repository issue tracker or emailing `pseudonym@chuumind.com`.
