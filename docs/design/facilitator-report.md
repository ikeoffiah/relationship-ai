# The facilitator report — print design

Owner: design (`local_81faf803`). Built by: engineer. Execution-plan **P0.3**.
Written 2026-08-03.

The **content** spec is `docs/specs/facilitator-report.md` and it is not
reopened here. This document is the typography, grid, page geometry and print
production of the same eight pages, plus the certificate in Appendix A.

Read `docs/specs/facilitator-report.md` §2 first. Everything below is subordinate
to the boundary rule; where a layout idea would put one partner's information
somewhere the other cannot see it, the layout idea loses.

---

## 1. What this document has to survive

Not a design review. A **counsellor in a parish office**, holding a printout,
deciding whether to hand it to twenty-five couples with their own name on it.

Three specific tests, and every decision below answers to at least one:

1. **The photocopier.** It will be duplicated in black and white on a machine
   bought in 2011. Nothing may depend on colour, tint, or a hairline.
2. **The eye of someone who has read Prepare/Enrich reports for fifteen years.**
   They will notice a document that looks like marketing collateral, and they
   will notice a claim we cannot support. Both end the evaluation.
3. **Sixty-two-year-olds in the room.** Our buyers are Catholic marriage-prep
   offices and evangelical premarital programmes across the US, UK, Canada and
   Australia. The couples are young; the facilitators frequently are not, and
   the parents sometimes read it too.

The house style for this document is one word: **quiet**. It should look like it
was set by an institution that had no need to impress anyone.

---

## 2. The typeface decision, and why it is not a serif

**Inter throughout. One family, four weights (400, 500, 600, 700). No serif, no
second face.**

This will be argued with, so the reasoning is on the record.

The convention says serif for printed body text and it is *convention*, not
evidence — controlled studies find serif "slightly more legible" in some tests
and no significant difference in others once x-height, weight and spacing are
matched. The one part of that literature that is **not** contested is that
sans-serif is better for low-vision, elderly and dyslexic readers. Given test 3
above, that is the part that applies to us.

Three further reasons:

- **It is the product's voice.** A couple who opens the app after the session
  should be reading the same letterforms. One of the two things this report
  uniquely offers over the incumbent is that it is the on-ramp to something the
  couple keeps; making the artefact and the app look like different companies
  throws that away on page one.
- **One embedded family is one thing that can fail.** WeasyPrint resolves fonts
  through the host system and `@font-face` needs a resolvable `base_url`; a
  second family doubles the surface for a substitution that silently reflows a
  page in production. Embed only the four weights used.
- **Credibility in print is carried by structure, restraint and methodology, not
  by serifs.** Page 8 is what convinces a clinician. Bookish body type on pages
  2–3 would not have.

What we give up by not having a serif/sans contrast is one axis of hierarchy.
§3 buys it back with rules, weight and space.

---

## 3. Type scale

A modular scale at ratio **1.25**, rounded to half-points. Sizes are in
**points**, because this is print; do not translate them to px.

| Role | Size / leading | Weight | Tracking | Case |
|---|---|---|---|---|
| Cover title (names) | 26 / 30 | 600 | −0.3 | Sentence |
| Page title | 18 / 22 | 600 | −0.2 | Sentence |
| Section head | 13 / 16 | 700 | 0 | Sentence |
| **Body** | **10.5 / 15** | **400** | **0** | Sentence |
| Body emphasis | 10.5 / 15 | 600 | 0 | Sentence |
| Eyebrow / column head | 8 / 10 | 700 | **+0.9** | UPPERCASE |
| Caption, provenance line | 8.5 / 12 | 400 | 0 | Sentence |
| Running footer | 7.5 / 10 | 400 | +0.4 | Sentence |

Body leading is **143%** — at the generous end of the 120–140% print
convention, deliberately. This text gets read aloud in a room, by someone
tracking a line with a finger while also looking up at a couple. Loose leading is
the cheapest thing you can give that person.

**Eyebrows are letterspaced uppercase bold, not small caps.** Small caps blur
first under repeated photocopying; 8pt bold uppercase at +0.9 tracking survives
two generations.

**Nothing is set below 8pt, ever**, and nothing at 8pt carries meaning that is
not repeated elsewhere. There is no fine print in this document — a report whose
limitations are in 6pt at the foot has told you exactly how seriously it takes
them.

---

## 4. Colour — there is almost none, and that is the design

**The report is black on white with one accent, and it must lose nothing when
desaturated.**

| Use | Value |
|---|---|
| Body text | `#1A1A1A` — near-black, not `#000`. Pure black sets heavy on a laser printer. |
| Secondary text, captions | `#5A5651` |
| Rules and table borders | `#B8B2AA` at **1pt** |
| Section rule (under page titles) | `#1A1A1A` at 1.5pt |
| The one accent | `AppColors.warmCoral` `#FF9B8A` — hairline rules and the wordmark **only**. Never behind text, never as text. |
| Tints | **10% maximum.** See below. |

**Why 10% is a hard ceiling.** Black text on a 10% tint stays legible after
photocopying; at 20% comprehension drops measurably. Every panel in this
document is at 6–10% or it is a 1pt rule instead. If a panel needs to be
stronger than 10% to read as a panel, it needs a rule and some space, not more
ink.

**Hierarchy without colour**, in the order these devices survive a photocopier:

1. **Size** — the 1.25 scale does most of the work.
2. **Weight** — 400 / 600 / 700, and never 300.
3. **Whitespace** — space *before* a heading is the most robust device there is;
   a copier cannot degrade an absence.
4. **Rules** — 1pt minimum. 0.25pt hairlines do not reliably reproduce on a
   300–600dpi office laser, and 0.5pt is the floor for anything that must
   survive a copy. **There is no hairline in this document.**
5. **Indentation** — used once, for the reversibility examples on page 1.

**Acceptance:** print page 4 in greyscale, photocopy the photocopy, and confirm
every level of hierarchy is still distinguishable. If it is not, the fault is in
this table, not in the printer.

---

## 5. Page geometry — one layout, two paper sizes

A4 is 210×297mm. US Letter is 216×279mm. A4 is 18mm taller; Letter is 6mm wider.
The channel is US, UK, Canada, Australia and Nigeria, so both are guaranteed to
be used and **a report that reflows between them is a report a facilitator stops
handing out.**

**The rule: fixed margins, flexible width, Letter-constrained height.**

```
@page {
  size: A4;                       /* overridden per-render; see §8 */
  margin: 20mm 18mm 20mm 22mm;    /* top right bottom left */
}
```

- **Width flexes.** Content is 170mm on A4 and 176mm on Letter. A 3.5% change in
  measure is invisible and costs nothing. Do **not** fix the width — a fixed
  block centred on Letter throws the binding margin away.
- **The left margin is 22mm, not 18mm.** Punch holes sit ~6mm from the edge at
  ~6mm diameter; 22mm clears the hole plus a buffer. Every copy of this will be
  punched or stapled by someone.
- **Height does not flex. Every page is laid out to fit 239mm** — the Letter
  content height. On A4 that leaves 18mm of extra space at the foot, which reads
  as a slightly airier bottom margin and is invisible. The inverse — designing to
  A4 and letting Letter clip — loses the running footer on every page in North
  America, which is most of the channel.

### 5.1 The two-lane grid

The single most useful structural decision in this document.

```
|←22mm→|←──────── 112mm ────────→|←6mm→|←── 52mm ──→|←18mm→|
        THE COUPLE'S COLUMN              THE MARGIN
```

- **The column** is 112mm at 10.5pt, which lands at roughly **62–68 characters
  per line** — inside the 50–75 range and close to the 66 optimum. A full-width
  190mm column at this size would run to ~115 cpl, which is why one-column
  reports set at 11pt across a whole A4 page are tiring to read and look like
  internal memos.
- **The margin** carries: the facilitator's teaching cues (spec §6), the dated
  provenance line (spec, pages 2–3), and otherwise nothing. It is white space
  most of the time, and the white space is the point — it is where a facilitator
  writes, and it is why they keep paper.

**This does not create facilitator-only content and must never be allowed to.**
Per spec §2.1 there is exactly one document; the margin is printed in every copy
and the couple can read every word of it. It is a *reading lane*, not a
*privilege*. Two constraints make that hold:

1. **Nothing in the margin is ever about this couple.** Margin cues are generic
   teaching notes selected by axis pattern, identical for every couple with that
   pattern. If a line could only have been written after seeing these two
   people's answers, it belongs in the column.
2. **Margin cues pass the reversibility test (spec §2.2) like everything else**,
   and are addressed to the room, not to one partner.

Set margin cues at 8.5/12, weight 500, colour `#5A5651`, with a 1pt coral rule
6mm long above each. They should read as marginalia — as if a previous reader
had annotated the document usefully — which is exactly the register a
facilitator wants and cannot get from a slide deck.

### 5.2 Vertical rhythm

Baseline grid of **5mm**. Every vertical measurement is a multiple:

| Between | mm |
|---|---|
| Body paragraphs | 5 |
| Body → section head | 15 |
| Section head → its body | 5 |
| Section → section | 20 |
| Page title → first content | 20 |

A 3:1 ratio between "space before a heading" and "space after it" is what makes
a heading belong to the text below rather than float between two blocks. It is
also the device that survives photocopying best (§4).

---

## 6. The pages

Page numbering below follows the content spec's 0–8.

### Page 0 — Cover

The hardest page, because the temptation is to design it.

```
                                          [ 40mm from top ]

   ADA & CHIDI                              26/30, weight 600
                                            
   ─────────────────────────────────        112mm coral rule, 1pt
   
   Relationship Preparation Report          13/16, weight 400, #5A5651

                                          [ vertical space ]

   ST BRIGID'S MARRIAGE PREPARATION         8/10, 700, +0.9, uppercase
   Prepared by Maria Okonkwo                10.5/15, 400
   4 March 2026                             10.5/15, 400, #5A5651

                                          [ foot of page ]
   Bliss                                    9pt, 600, #5A5651
```

- **Names at 26pt is the largest type in the document and it is 26pt.** A cover
  set in 60pt display type is a brochure. This is a document about two people
  and their names are the title.
- Alphabetical by first name (Appendix A's rule, applied here too) so nothing
  encodes precedence.
- **No score, no label, no archetype, no illustration, no photograph, no
  gradient, no coral field.** Spec is explicit and it is right: nobody learns
  their result from a cover sheet.
- The programme's name sits *above* ours and is set larger. The facilitator is
  handing out their own work; per marketing §11 item 3 that is most of what
  makes them keep doing it.
- If a programme logo is supplied, it goes at the foot beside the Bliss
  wordmark, max 18mm wide, greyscale. **Not at the top.** A logo at the top of a
  cover makes it collateral.

### Page 1 — How to read this

Four paragraphs, and per the spec the most important page in the document.

Set the **body one step up: 11.5/17, measure narrowed to 96mm.** It is the only
page in the report that is set differently, and the difference is what makes it
read as a preface rather than as content. Someone skimming will read this page
because it looks like it is addressing them.

The fourth paragraph — *"It can be wrong. You are the authority on you."* — gets
a 1pt rule above it and 15mm of space. It is the sentence that decides whether a
couple argues with the document or submits to it, and arguing is the better
outcome.

No margin cues on this page. Nobody needs coaching to read four paragraphs.

### Pages 2 and 3 — the portraits

One per partner, identical layout, **identical length**. If one portrait runs
shorter, pad the page rather than reflowing — two portraits of visibly different
length is read as one person having been assessed more thoroughly, or worse.

```
   ADA                                      18/22, 600
   ──────────────────────────────           1.5pt rule, full column

   THE STEADY ONE                           8/10, 700, +0.9, uppercase, coral
   [headline]                               13/16, 600

   [summary]                                10.5/15

   WHAT HELPS                               eyebrow
   [text]

   WHAT TRIPS YOU UP                        eyebrow
   [text]

   YOUR GROWTH EDGE                         eyebrow
   [text]

   WHERE FRICTION IS LIKELY                 eyebrow
   • [bullets, 10.5/15, 4mm hanging indent]

   ┌ 6% tint panel, 1pt rule top and bottom, no side rules ┐
   │ COMMUNICATION      [text]                             │
   │ CONTEXT            [text]                             │
   └───────────────────────────────────────────────────────┘
```

In the margin, at the foot: *"Based on 22 self-report items answered on
4 March 2026."* 8.5/12, `#5A5651`. Spec calls for it and the placement matters —
in the margin it reads as provenance, in the column it reads as a disclaimer.

**The archetype label is the eyebrow, not the headline.** It is set at 8pt above
the headline, not at 24pt across the page. An archetype rendered large becomes
the thing the couple remembers and repeats to each other, and it is the least
defensible element on the page.

### Page 4 — Where you meet

The page the facilitator teaches from. Four blocks, from spec §5:

1. `WHAT THIS LOOKS LIKE DAY TO DAY`
2. `THE STRENGTH IN IT`
3. `WHERE IT COSTS YOU`
4. `WHAT USUALLY HELPS`

Equal weight, equal type, equal space. **No block is tinted, boxed or coloured
differently from the others** — in particular "the strength in it" must not be
the pretty one and "where it costs you" must not be the warning-coloured one.
The moment those two are styled differently, the layout is telling the couple
which parts are good news, and the whole editorial position of the spec is that
neither is.

Margin cues on this page carry the facilitator's teaching notes.

#### 4a. There is no 2×2 diagram, and there will not be one

This will be requested — by a facilitator, by marketing, and by whoever designs
the next version. Refusing it in writing so the refusal outlives me.

Spec §5 says *"No numbers on this page. A printed number invites a couple to
compare scores, which is the compatibility-score failure mode arriving through
the back door."* A 2×2 with two dots on it **is a printed number**. It is two
numbers, rendered more memorably than digits, plus a third the couple will
invent immediately: the distance between the dots. A couple handed that diagram
four weeks before a wedding will measure that gap with their eyes and treat it
as a verdict, and no caption prevents it.

D3.4 refuses the compatibility score. This is the same object with better
graphic design.

**What is allowed, and only on page 8:** an unlabelled schematic of the
four-quadrant model with the two axes named and the four categories placed —
**with nobody plotted on it.** A diagram of the *instrument* is methodology. A
diagram with *your dot on it* is a score. The difference is whether the couple
appears in the picture.

### Page 5 — Four conversations

Four prompts. Per prompt:

```
   01                                        18/22, 600, coral
   [the question]                            13/16, 600, column
   [why this couple is being asked it]       10.5/15, column

   ── margin ──
   │ WHAT A GOOD ANSWER SOUNDS LIKE          8/10, 700, +0.9
   │ [the facilitator's cue]                 8.5/12, 500, #5A5651
```

The numeral is the only large coral element in the report and it exists to make
the page navigable by someone glancing down at it mid-sentence while talking.

Per D3.6, if the curriculum ships these become sessions 1–4. Design for that now:
the numeral is set as `01` rather than `1.` so it reads as a sequence rather than
a list, and the page needs no change if the word "Conversation" becomes
"Session".

### Page 6 — What you each said matters

The only two-column page. Two lanes of 82mm with a 6mm gutter and a **1pt
vertical rule between them**, running the height of the table.

At 82mm, drop body to **9.5/14** to hold ~55 cpl. This is the one place the
scale bends, and it bends because a 10.5pt two-column measure would fall to
~48 cpl and read as choppy.

```
   ─────────────────────────────────────────────────
   CULTURAL BACKGROUND     │ ADA        │ CHIDI
   ─────────────────────────────────────────────────
   [row]                   │ [answer]   │ [answer]
```

Where the two answers differ, per the spec: a **small open circle (◦) in the
left gutter, 2.5mm, 1pt stroke** — not a warning triangle, not a coloured dot,
not an exclamation. Below the table, once, in the margin: *"Worth talking
about — different is common and workable, unexamined is the problem."*

**The glyph is neutral by construction.** A triangle or an amber dot would mark
difference as a defect, on the page most likely to surface a mixed-faith or
mixed-culture couple, in a document going to a parish. The circle means "look
here", and the legend is what supplies the meaning — never the mark alone (§4,
and `accessibility.md` §5, which is the same discipline).

### Page 7 — Notes

Headed *"What we want to remember from this conversation."* 13/16, 600.

Ruled lines at **7.5mm**, 1pt, `#B8B2AA`, full column width **and through the
margin** — this is the one page where the two lanes merge, because a person
writing does not respect a text column. First rule 20mm below the heading; last
rule 20mm above the foot. That yields ~26 lines.

7.5mm sits between college rule (7.1mm) and wide rule (8.7mm). College rule is
the adult professional convention; wide rule is more forgiving. This page is
written on by couples in their twenties with a borrowed pen, in a room, on their
knee. Round up.

### Page 8 — How this was made

The credibility surface. Set as a single column at body size with numbered
sections and no tint panels anywhere. Plainness *is* the design; a methodology
page with pull-quotes is a methodology page nobody believes.

Two typographic decisions carry it:

- **The adaptation disclosure gets its own numbered section and its own rule**,
  not a parenthesis inside another paragraph. Spec §7 is right that volunteering
  it converts a discoverable weakness into demonstrated candour — but that only
  works if it is *findable*. Buried, it reads as having been hidden.
- **The final line — "Neither partner is ever shown a profile of the other…" —
  is the last thing on the last page**, set at 11.5/17 weight 600 with 20mm of
  space above it and a 1pt rule. Nothing follows it except the running footer.

That is the sentence that sells this to a clinician. It should be the last thing
in their hand.

The quadrant schematic (§4a) sits here, 60mm square, in the margin lane, at 1pt
strokes and no fill.

### Running footer, every page except 0

```
Ada & Chidi · Relationship Preparation Report · 4 March 2026        Page 4 of 8
```

7.5/10, `#5A5651`, 1pt rule above at column width. `page N of 8` matters: pages
get separated in a stack of twenty-five and a facilitator needs to reassemble
them.

**Not in the footer:** a URL, a QR code, a marketing line, or "Generated by
Bliss". The wordmark on the cover is sufficient and anything more turns the
artefact into an ad the facilitator is distributing on our behalf.

---

## 7. What the design refuses

Each of these will be asked for. The content spec has its own refusal list; this
is the visual one.

| Refused | Why |
|---|---|
| **The 2×2 with the couple plotted on it** | §4a. A score in graphic clothing. |
| **Any bar, gauge, dial, meter or progress ring** | Same object, less honest. There are no numbers in this report to visualise. |
| **Colour-coded results** | A green result and an amber result is a verdict, and it dies in the photocopier anyway. |
| **Stock photography of couples** | Every reader compares themselves to the models. Also the fastest way to look like collateral (test 2). |
| **Icons beside section headings** | Decoration that has to be photocopied. Weight and space are free. |
| **Rounded cards** | The app's card shell is a screen idiom. Rounded panels on paper read as a printed screenshot, which is precisely the "app company made a PDF" impression we cannot afford in this channel. Paper uses rules and space. |
| **Tints above 10%** | §4. Measured. |
| **A "your results at a glance" summary page** | The compressed version of a document whose whole design is that it resists compression. |
| **Full justification** | Ragged right. Justified text at 62–68 cpl opens rivers, and this text has many short lines. |

---

## 8. Production — WeasyPrint

```css
@page {
  size: A4;
  margin: 20mm 18mm 20mm 22mm;
  @bottom-left  { content: string(couple-footer); font-size: 7.5pt; color: #5A5651; }
  @bottom-right { content: "Page " counter(page) " of 8"; font-size: 7.5pt; color: #5A5651; }
}
@page letter { size: letter; }
@page :first { @bottom-left { content: none; } @bottom-right { content: none; } }

h1.page-title { string-set: none; }
.footer-key   { string-set: couple-footer content(); }

p { orphans: 3; widows: 3; }
.page { break-after: page; }
.block, .portrait-section, .conversation { break-inside: avoid; }
```

Notes, each of which is a known failure mode rather than a preference:

1. **Render both sizes at generation, not on demand.** Emit
   `report-{id}-a4.pdf` and `report-{id}-letter.pdf` by toggling the `letter`
   named page. A facilitator choosing a paper size at download time is a support
   email; two files is not.
2. **Embed only the four Inter weights used.** WeasyPrint resolves fonts through
   the host system and `@font-face` requires a resolvable `base_url`; a missing
   file substitutes silently and reflows the document. Add a build assertion that
   the rendered PDF's font list contains exactly the expected four faces —
   this is cheap and it catches the one production failure nobody notices until
   a facilitator does.
3. **`break-inside: avoid` interacts badly with named `@page` rules in some
   WeasyPrint versions.** Test the Letter render specifically, not just A4;
   there are tracked issues in this exact combination. If page 8 loses its
   footer on Letter, this is why.
4. `orphans` / `widows` at 3 are supported directly and are not optional — a
   single line of "Where it costs you" stranded at the top of page 5 changes
   what that sentence means.
5. **No screen units.** No `px`, no `rem`, no `vh`. `mm` and `pt` only.
6. **No `@media print` block.** There is no screen version of this document.
   Building one is how the two drift.

---

## 9. Acceptance criteria

Adds to the content spec's §10. All are checked against a **printed** artefact.

| # | Criterion |
|---|---|
| 9.1 | Renders on A4 and US Letter with **identical pagination** — page 4 is page 4 on both. |
| 9.2 | Desaturated to greyscale and photocopied twice, every level of hierarchy remains distinguishable and no information is lost. |
| 9.3 | No rule anywhere is below 1pt. No type anywhere is below 8pt. |
| 9.4 | No tint above 10%. |
| 9.5 | Three-hole-punched, no text is obscured on either paper size. |
| 9.6 | No page prints a number, a score, a percentage, a bar, a gauge, or a plotted position (§4a). |
| 9.7 | Both portraits occupy the same number of lines to within one. |
| 9.8 | The margin lane contains nothing specific to this couple (§5.1). Checked by generating two reports with different data and diffing the margin content: it must be identical for two couples sharing an axis pattern. |
| 9.9 | The PDF embeds exactly four font faces. |
| 9.10 | The final sentence of page 8 is the last content in the document. |
| 9.11 | Printed at 100% on a 600dpi office laser, body text is comfortably readable at arm's length by a reader who needs reading glasses. Tested by a person, not asserted. |

---

# Appendix A — the certificate

One page, landscape, per the content spec's Appendix A. It goes on a wall and it
gets photographed, so it is designed for **being seen at two metres and in a
phone photo**, not for being read.

```
   ┌──────────────────────────────────────────────────────────────┐
   │                                                              │
   │              CERTIFICATE OF COMPLETION                       │
   │              ──────────────────────────                      │
   │                                                              │
   │                  Ada Nwosu                                   │
   │                      and                                     │
   │                 Chidi Okafor                                 │
   │                                                              │
   │       completed the St Brigid's Marriage Preparation         │
   │              premarital preparation programme                │
   │                                                              │
   │                   4 March 2026                               │
   │                                                              │
   │                                                              │
   │      ______________________            [programme logo]      │
   │      Maria Okonkwo                                           │
   │      Facilitator                                  Bliss      │
   └──────────────────────────────────────────────────────────────┘
```

**Geometry.** A4 landscape 297×210 and Letter landscape 279×216. Same
intersection discipline: fixed 25mm margins, content laid out to the **279mm
width** so nothing is lost on Letter, with A4 gaining 18mm of side air.

**Type.** Names at 30pt weight 600 — the largest type anywhere in this product,
and appropriately so. "Certificate of Completion" at 12pt, 700, +1.4 tracking,
uppercase, above a 60mm rule. Programme line at 12/17, 400. Date at 11pt. All
Inter; a certificate in a script or blackletter face is a joke about
certificates.

**Both names at identical size, alphabetical by first name**, per the content
spec. The word "and" is set at 11pt weight 400 between them and is deliberately
small — equal billing means neither name is the subject of the sentence.

**The signature rule is 70mm, 1pt, with 12mm of clear space above it.** Nothing
is pre-printed on it. A facilitator signing by hand is what makes it theirs, and
12mm is what a fountain pen needs.

**Colour: one 1pt coral rule under the title, and nothing else.** No border, no
frame, no guilloche, no seal, no gold. This is a keepsake, not a diploma, and
ornament here reads as compensating.

**Refused:** QR code, verification URL, "scan to verify", certificate number,
holographic anything. Per the content spec — a broken link on a wall five years
from now is worse than no link. Also refused: any attachment style, archetype,
score or portrait text, asserted in test A.13. This document leaves the house.
