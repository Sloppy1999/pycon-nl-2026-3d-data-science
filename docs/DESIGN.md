# Design: PyCon NL 2026 style

The talk is a personal presentation, so the deck uses the conference's palette and font, not a company master.
The only mention of the speaker's employer is the affiliation as plain text on slide 1 (from `deck/content.yaml`).
No company master, sidebar, wordmark, logo, claim, confidentiality field, company colour or company font appears
in the deck, its layouts, its theme or its metadata.

| What | Where |
|---|---|
| Slide master (11 layouts, one example slide per layout, notes master) | `deck/template/pycon_nl_2026_master.pptx` |
| Generator (deterministic: a rebuild is byte-identical) | `deck/template/make_master.py` |
| Every layout shape in EMU and inches, for the builder | `deck/template/pycon_nl_2026_master.geometry.json` |
| Palette, roles, fonts, sizes for the builder and helpers | `deck/lib/style.py` |
| Palette as data (single source for content and renders) | `deck/content.yaml` `meta.palette`, `meta.fonts`, `meta.render_palette` |
| QA fonts and private fontconfig | `deck/qa/fonts/`, `deck/qa/fonts.conf`, `deck/qa/setup_fonts.py` |

Rebuild: `uv run python deck/template/make_master.py`, then
`python3 ~/.claude/skills/pptx/scripts/office/validate.py deck/template/pycon_nl_2026_master.pptx` (passes).

## 1. Sources (pycon-nl.org, fetched 2026-10-03)

Saved copies (scratch, not part of the repo): `index.html`, `_app/immutable/assets/0.CrnuNnCX.css` (Tailwind
build), the other CSS bundles, and the pages `/speakers`, `/schedule`, `/practical-information`, `/history`,
`/sponsors`, `/call-for-sponsors`, `/members` with their JS and CSS bundles.

- **Brand colours** are custom Tailwind colours in `0.CrnuNnCX.css`:
  `.bg-north{background-color:rgb(28 50 91)}`, `.fill-north{fill:#1c325b}`, `.fill-north2{fill:#2b6797}`,
  `.fill-north3{fill:#b1cac5}` (aliases `north-300` = navy, `north-200` = blue, `north-50` = sage).
  Use on the pages: `bg-north3` 59, `bg-north2` 51, `fill-north3` 45, `bg-north` 35, `fill-north2` 23,
  `fill-north` 14 times. `north4` (#4C1D95, purple) appears only in one sponsor-page illustration and is not used.
  `ordina` (#FF8133) and `soprasteria` are sponsor colours, `fountain` (#61BFC3) is unused on the pages; none
  of them is used.
- **Neutrals**: the inline SVG illustrations on the home page (Freepik illustrations recoloured in the brand
  colours) use `#263238` (315 fills), `#E0E0E0` (168), `#455A64` (103), `#FAFAFA` (59) besides
  `#B1CAC5` (63) and `#2B6797` (25). `#9CA3AF` is the Tailwind gray-400 the CSS uses for input placeholders.
  The site's own dark text class is `text-shark` (#1A1D1F); the deck uses `#263238` (ink) for body text, as set
  in `content.yaml`. The warm illustration fills (#EB996E, #FF9A6C, #FFBF9D: skin tones) are not brand colours.
- **Fonts**: every page loads Google Fonts `Fira Sans` (all weights, roman and italic) and `Caveat Brush`; the CSS
  sets `body{font-family:Fira Sans,sans-serif}`. Caveat Brush is used in exactly one place: `.initials`
  (`text-transform:uppercase; font-family:Caveat Brush`) in `12.hnByEAV9.css`, the speaker initials on the
  "delfts-blauw" (Delft blue tile) speaker cards of `/speakers`. The deck does not use Caveat Brush: it would
  carry no meaning on a slide, and no Dutch motif is needed.
- **Third-party logos (slide 4, 2027-11-12)**: the ecosystem wall shows other projects' and companies' logos in their
  own colours, unaltered, on white (light grey for companies) tiles. An approved exception to the palette; terms and
  policies per file in deck/assets/logos/SOURCES.md, open points in OPEN_ITEMS k1.
- **Logo**: the site logo is `/logo-sopra4.svg` (a square 375 x 375 viewBox with embedded rasters). It is not in
  the deck: no file and no permission yet, so slides 1 and 25 keep a labelled placeholder in the logo zone.
  Its colours (approximate, read from the embedded raster to plan the logo zone): navy about #203060, mid blue
  about #4070A0, pale blue about #B0D0E0. Its navy parts would disappear on the navy title and closing slides,
  so when the file arrives it needs a light version or a white tile the size of the logo zone.
- **Code font**: the site has none (Tailwind's default `ui-monospace` stack). The deck uses Fira Mono, from the
  same family as Fira Sans and under the same licence.

## 2. Palette

Nine values from the site, eight of them in the deck (`content.yaml` `meta.palette`, `deck/lib/style.py`
`PALETTE`). The theme colour scheme of the master is named "PyCon NL 2026".

| Name | Hex | Theme slot | Source | Role in the deck |
|---|---|---|---|---|
| navy | `#1C325B` | dk2 (tx2), accent3 | CSS `north`, `.fill-north` | dark backgrounds (slides 1, 20, 25), titles on white |
| blue | `#2B6797` | accent1, hlink, folHlink | CSS `north2`, `.fill-north2` | the highlight on white: highlighted series, key-line edge, accent bar, links |
| sage | `#B1CAC5` | accent2 | CSS `north3`, `.fill-north3` | the highlight on navy; small print and footer on navy; code joke on slide 1 |
| white | `#FFFFFF` | lt1 (bg1) | CSS `bg-white`, `text-white` | content slide background; text on navy; QR tile |
| ink | `#263238` | dk1 (tx1) | inline SVG fills (315) | body text on white |
| slate | `#455A64` | accent4 | inline SVG fills (103) | small print, source lines, conditions, footer, slide number, code comments on white |
| grey | `#9CA3AF` | accent5 | CSS placeholder colour (Tailwind gray-400) | muted marks only: greyed chart series, outlines, rules; never text on white |
| light | `#E0E0E0` | lt2 (bg2), accent6 | inline SVG fills (168) | tiles, code key-line bar, thin rules |
| (paper) | `#FAFAFA` | not used | inline SVG fills (59) | not used (not in `content.yaml`) |

There is no warm accent in the conference palette. Highlights use blue on white and sage on navy; "muted" is grey.

### Render palette (inside renders and on render label chips only)

From `content.yaml` `meta.render_palette` (read by `pipeline/render.py` and by `deck/lib/style.py` `RENDER`):
background navy `#1C325B`, ground `#4A5F69` (slate lifted 5 levels per channel), buildings `#6FA0CC` (light tint
of the blue), vegetation sage `#B1CAC5`, street furniture white, unlabelled `#34486B`; height ramp blue, sage,
white; clusters blue, sage, grey, light; noise `#2A3F66`. The four classes have distinct gray levels, and the
deck labels them directly (chips), so no information depends on colour alone.

## 3. Contrast (WCAG 2.x relative luminance)

Every text/background pair the deck uses, plus the forbidden ones for reference. AA needs 4.5:1 for normal text
and 3:1 for large text (18 pt and up, or 14 pt bold); AAA needs 7:1.

| Text | Background | Ratio | Use |
|---|---|---|---|
| ink `#263238` | white | 13.16 | body text, chart labels |
| navy `#1C325B` | white | 12.68 | titles, keywords in code |
| slate `#455A64` | white | 7.24 | 12 pt small print, footer, slide number, code comments |
| blue `#2B6797` | white | 6.02 | highlighted words, strings in code, links |
| ink | light `#E0E0E0` | 9.97 | text on tiles and on the code key-line bar |
| navy | light | 9.60 | titles or keywords on tiles |
| slate | light | 5.49 | small text on tiles (AA) |
| blue | light | 4.56 | highlight on tiles (AA, keep at 20 pt or more) |
| white | navy | 12.68 | titles and body on navy |
| sage `#B1CAC5` | navy | 7.32 | small print, footer, highlight and code on navy |
| light | navy | 9.60 | secondary text on navy |
| grey `#9CA3AF` | navy | 4.99 | code comments on navy (slide 1), at 18 pt or more |
| white | blue | 6.02 | text on blue shapes (theme default for new shapes) |
| navy | sage | 7.32 | text on sage chips or tiles |
| ink | sage | 7.60 | text on sage chips or tiles |
| white | slate | 7.24 | text on slate chips |
| navy | buildings `#6FA0CC` | 4.57 | text on a buildings-coloured chip (AA) |
| ink | buildings | 4.75 | text on a buildings-coloured chip (AA) |
| **grey** | **white** | **2.54** | **not allowed for text** (marks only) |
| **blue** | **navy** | **2.11** | **not allowed** (use sage on navy) |
| **white** | **sage** | **1.73** | **not allowed** |

Non-text marks: grey bars on white are 2.54:1, blue bars on white 6.02:1, so the highlighted series always
stands out from the greyed ones, and data labels carry the values in text.

## 4. Fonts and licences

| Family name in PowerPoint | File (deck/qa/fonts/) | Weight | Use |
|---|---|---|---|
| Fira Sans | FiraSans-Regular.ttf, -Italic.ttf, -Bold.ttf (b="1") | 400, 700 | body, labels, small print (theme major and minor font) |
| Fira Sans Medium | FiraSans-Medium.ttf | 500 | optional emphasis (labels, column headings) |
| Fira Sans SemiBold | FiraSans-SemiBold.ttf | 600 | titles and hero numbers (master title style) |
| Fira Mono | FiraMono-Regular.ttf, FiraMono-Bold.ttf (b="1") | 400, 700 | code, at 18 pt or more |
| Fira Mono Medium | FiraMono-Medium.ttf | 500 | optional (key line) |

- Fira Sans 4.203 (Copyright 2012-2015 The Mozilla Foundation and Telefonica S.A.) and Fira Mono 3.206
  (Copyright 2012-2013 The Mozilla Corporation and Telefonica S.A.), both SIL Open Font License 1.1
  (`deck/qa/fonts/OFL-FiraSans.txt`, `OFL-FiraMono.txt`), downloaded from github.com/google/fonts (`ofl/firasans`,
  `ofl/firamono`) by `deck/qa/setup_fonts.py`. OS/2 `fsType` is 0 (installable embedding).
- PowerPoint addresses weights other than Regular and Bold by their own family name (name ID 1 of the static
  TTFs), so the master's title style names `Fira Sans SemiBold` explicitly; the theme font scheme is
  major = minor = `Fira Sans`. Title runs must not set a typeface: `+mj-lt` is Fira Sans Regular.
- Metrics for layout estimates: line height 1.2 em at 100 % spacing (ascender 935, descender 265, no line gap,
  units per em 1000), cap height 0.689 em. Fira Mono advance 0.600 em: 35 characters at 18 pt are 5.25 in,
  70 characters 10.5 in. Fira Sans SemiBold at 32 pt averages about 0.20 in per character of English text.
- **Presenting laptop**: Fira Sans (Regular, Italic, Medium, SemiBold, Bold) and Fira Mono (Regular, Medium,
  Bold) must be installed (fonts.google.com/specimen/Fira+Sans, /Fira+Mono, or the files in `deck/qa/fonts/`),
  or the fonts embedded in the file: PowerPoint, File > Options > Save > "Embed fonts in the file", "Embed all
  characters". The OFL permits embedding. The master sets `embedTrueTypeFonts="1"` in `presentation.xml`, so
  that option is already ticked when the deck is saved from PowerPoint on a machine with the fonts. Without the
  fonts, PowerPoint substitutes and every text fit in this deck becomes wrong; check on the presenting laptop.
- QA renders use exactly these files through a private fontconfig (`deck/qa/fonts.conf`, used by
  `deck/qa/render.py` via `FONTCONFIG_FILE`); no alias or substitution is configured. `pdffonts` on the master's
  render lists only FiraSans-Regular, FiraSans-SemiBold and FiraMono-Regular.

## 5. Master and layouts

Slide size 13.333 x 7.5 in (12 192 000 x 6 858 000 EMU). One slide master, theme "PyCon NL 2026", 11 layouts
with English names, numbered as `content.yaml` uses them. Language en-GB on every text style and run.

### Grid (inches)

- Outer margin 0.600 on all sides; content right edge 12.733; content width 12.133; column gap 0.500.
- Accent bar 0.550 x 0.070 at y 0.600 on content layouts (blue on white, sage on navy), left-aligned with the
  title. It marks where the title starts, so slide 9 to 15 Morph frames keep a fixed anchor.
- Title top y 0.800 on every content layout (L2, L4, L5, L7, L8, L9, L10) and on L11. Title boxes are
  top-anchored, so the first line never moves when a title wraps. Title style: 32 pt Fira Sans SemiBold, navy,
  100 % line spacing (one line 0.533 in, two lines 1.067 in).
- Content area: from y 1.700 (below a one-line title) or 2.150 (below a two-line title, L7 and L8) to y 6.800.
- Footer (12 pt, slate on white, sage on navy): "3D Data Science with Python | PyCon NL 2026", box x 0.600,
  y 6.950, 8.000 x 0.250, bottom-anchored (text bottom at 7.200). Slide number: box x 11.733, y 6.950,
  1.000 x 0.250, right-aligned. On every layout except L1 and L11. No date placeholder anywhere.
- All text placeholders have zero insets, so text starts exactly on the 0.600 margin. Builder text boxes should
  also use zero left and right insets to align with titles.
- Media frame (L7, L8): exactly 1588:1792 (397:448): 5 023 638 x 5 668 992 EMU = 5.494 x 6.200 in, top 0.600,
  bottom 6.800, flush with the right margin on L7 (x 7.239) and the left margin on L8 (x 0.600). A 1588 x 1792
  render inserted into it gets zero crop. The text column beside it is 6.139 in wide.

### Body text styles (master)

Level 1: 24 pt ink, no bullet, 6 pt after. Level 2: 20 pt ink, blue bullet, 0.3125 in hanging indent. Level 3 and
below: 20 pt, grey bullet. L7, L8 and L10 bodies default to 20 pt. L2 numbers its items in blue.

### Layout geometry (inches: x, y, width, height)

`idx` is the placeholder index (`p:ph idx`); the title is idx 0 (no idx attribute). Text colours are theme
references: bg1 = white, tx1 = ink, tx2 = navy, accent2 = sage, accent4 = slate.

**L1 Title** (navy, no footer)

| idx | type | name | x | y | w | h | anchor | text |
|---|---|---|---|---|---|---|---|---|
| static | bar | Accent bar | 0.600 | 1.750 | 0.550 | 0.070 | | sage |
| 0 | ctrTitle | Title | 0.600 | 1.950 | 12.133 | 1.000 | t | 54 pt SemiBold white |
| 1 | subTitle | Subtitle | 0.600 | 3.200 | 10.500 | 0.950 | t | 24 pt Fira Mono sage (two lines: 0.80 in) |
| 13 | body | Presenter | 0.600 | 5.700 | 8.933 | 1.200 | b | 24 pt white (two lines fit) |
| 16 | pic | Logo zone | 9.833 | 5.600 | 2.900 | 1.300 | | labelled placeholder; bottom right, bottom edge 6.900 |

**L2 Agenda** (white; filler)

| idx | type | name | x | y | w | h | anchor | text |
|---|---|---|---|---|---|---|---|---|
| static | bar | Accent bar | 0.600 | 0.600 | 0.550 | 0.070 | | blue |
| 0 | title | Title | 0.600 | 0.800 | 12.133 | 0.600 | t | master |
| 1 | obj | Agenda list | 0.600 | 1.700 | 12.133 | 5.100 | t | 24 pt, blue numbers |
| 11 | ftr | Footer | 0.600 | 6.950 | 8.000 | 0.250 | b | 12 pt slate |
| 12 | sldNum | Slide number | 11.733 | 6.950 | 1.000 | 0.250 | b | 12 pt slate, right |

**L3 Section** (navy; filler)

| idx | type | name | x | y | w | h | anchor | text |
|---|---|---|---|---|---|---|---|---|
| static | bar | Accent bar | 0.600 | 2.600 | 0.550 | 0.070 | | sage |
| 0 | title | Title | 0.600 | 2.800 | 12.133 | 1.000 | t | 44 pt SemiBold white |
| 1 | body | Section line | 0.600 | 3.950 | 12.133 | 0.900 | t | 24 pt sage |
| 11 | ftr | Footer | 0.600 | 6.950 | 8.000 | 0.250 | b | 12 pt sage |
| 12 | sldNum | Slide number | 11.733 | 6.950 | 1.000 | 0.250 | b | 12 pt sage, right |

**L4 Title and content** (white)

| idx | type | name | x | y | w | h | anchor | text |
|---|---|---|---|---|---|---|---|---|
| static | bar | Accent bar | 0.600 | 0.600 | 0.550 | 0.070 | | blue |
| 0 | title | Title | 0.600 | 0.800 | 12.133 | 0.600 | t | master (one line) |
| 1 | obj | Content | 0.600 | 1.700 | 12.133 | 5.100 | t | master body |
| 11 | ftr | Footer | 0.600 | 6.950 | 8.000 | 0.250 | b | 12 pt slate |
| 12 | sldNum | Slide number | 11.733 | 6.950 | 1.000 | 0.250 | b | 12 pt slate, right |

**L5 Two columns** (white)

| idx | type | name | x | y | w | h | anchor | text |
|---|---|---|---|---|---|---|---|---|
| static | bar | Accent bar | 0.600 | 0.600 | 0.550 | 0.070 | | blue |
| 0 | title | Title | 0.600 | 0.800 | 12.133 | 0.600 | t | master (one line) |
| 1 | obj | Left column | 0.600 | 1.700 | 5.817 | 5.100 | t | master body |
| 2 | obj | Right column | 6.917 | 1.700 | 5.817 | 5.100 | t | master body |
| 11 | ftr | Footer | 0.600 | 6.950 | 8.000 | 0.250 | b | 12 pt slate |
| 12 | sldNum | Slide number | 11.733 | 6.950 | 1.000 | 0.250 | b | 12 pt slate, right |

**L6 Statement** (navy)

| idx | type | name | x | y | w | h | anchor | text |
|---|---|---|---|---|---|---|---|---|
| static | bar | Accent bar | 0.600 | 2.050 | 0.550 | 0.070 | | sage |
| 0 | title | Statement | 0.600 | 2.250 | 11.000 | 1.700 | t | 48 pt SemiBold white (two lines fit) |
| 1 | body | Support | 0.600 | 4.150 | 11.000 | 1.400 | t | 28 pt sage |
| 11 | ftr | Footer | 0.600 | 6.950 | 8.000 | 0.250 | b | 12 pt sage |
| 12 | sldNum | Slide number | 11.733 | 6.950 | 1.000 | 0.250 | b | 12 pt sage, right |

**L7 Text left, media right** (white; slides 9 to 15 and 18)

| idx | type | name | x | y | w | h | anchor | text |
|---|---|---|---|---|---|---|---|---|
| static | bar | Accent bar | 0.600 | 0.600 | 0.550 | 0.070 | | blue |
| 0 | title | Title | 0.600 | 0.800 | 6.139 | 1.100 | t | master (two lines fit) |
| 14 | obj | Text column | 0.600 | 2.150 | 6.139 | 4.650 | t | 20 pt |
| 18 | pic | Media | 7.239 | 0.600 | 5.494 | 6.200 | | exact 1588:1792 |
| 11 | ftr | Footer | 0.600 | 6.950 | 8.000 | 0.250 | b | 12 pt slate |
| 12 | sldNum | Slide number | 11.733 | 6.950 | 1.000 | 0.250 | b | 12 pt slate, right |

**L8 Media left, text right** (white; mirror of L7)

| idx | type | name | x | y | w | h | anchor | text |
|---|---|---|---|---|---|---|---|---|
| static | bar | Accent bar | 6.594 | 0.600 | 0.550 | 0.070 | | blue |
| 0 | title | Title | 6.594 | 0.800 | 6.139 | 1.100 | t | master (two lines fit) |
| 14 | obj | Text column | 6.594 | 2.150 | 6.139 | 4.650 | t | 20 pt |
| 18 | pic | Media | 0.600 | 0.600 | 5.494 | 6.200 | | exact 1588:1792 |
| 11 | ftr | Footer | 0.600 | 6.950 | 8.000 | 0.250 | b | 12 pt slate |
| 12 | sldNum | Slide number | 11.733 | 6.950 | 1.000 | 0.250 | b | 12 pt slate, right |

**L9 Large media** (white; filler)

| idx | type | name | x | y | w | h | anchor | text |
|---|---|---|---|---|---|---|---|---|
| static | bar | Accent bar | 0.600 | 0.600 | 0.550 | 0.070 | | blue |
| 0 | title | Title | 0.600 | 0.800 | 12.133 | 0.600 | t | master (one line) |
| 18 | pic | Media | 0.600 | 1.700 | 12.133 | 5.100 | | picture, chart or diagram |
| 11 | ftr | Footer | 0.600 | 6.950 | 8.000 | 0.250 | b | 12 pt slate |
| 12 | sldNum | Slide number | 11.733 | 6.950 | 1.000 | 0.250 | b | 12 pt slate, right |

**L10 Title left, content right** (white)

| idx | type | name | x | y | w | h | anchor | text |
|---|---|---|---|---|---|---|---|---|
| static | bar | Accent bar | 0.600 | 0.600 | 0.550 | 0.070 | | blue |
| 0 | title | Title | 0.600 | 0.800 | 3.900 | 2.600 | t | master; about 16 to 19 characters per line ("These [N] gotchas" is 3.57 in) |
| 1 | obj | Content | 5.000 | 0.800 | 7.733 | 6.000 | t | 20 pt |
| 11 | ftr | Footer | 0.600 | 6.950 | 8.000 | 0.250 | b | 12 pt slate |
| 12 | sldNum | Slide number | 11.733 | 6.950 | 1.000 | 0.250 | b | 12 pt slate, right |

**L11 Closing** (navy, no footer)

| idx | type | name | x | y | w | h | anchor | text |
|---|---|---|---|---|---|---|---|---|
| static | bar | Accent bar | 0.600 | 0.600 | 0.550 | 0.070 | | sage |
| static | tile | QR tile | 9.833 | 3.100 | 2.900 | 2.900 | | white, rounded |
| 0 | title | Title | 0.600 | 0.800 | 8.933 | 1.100 | t | 60 pt SemiBold white |
| 15 | body | Contact | 0.600 | 2.300 | 8.933 | 3.700 | b | 24 pt white, 4 pt after; bottom edge 6.000 = QR tile bottom |
| 19 | body | Small print | 0.600 | 6.200 | 12.133 | 0.700 | b | 12 pt sage |
| 16 | pic | Logo zone | 9.833 | 0.600 | 2.900 | 1.300 | | labelled placeholder, top right |
| 17 | pic | QR code | 10.033 | 3.300 | 2.500 | 2.500 | | inside the white tile (0.200 in quiet zone) |

Example slides 1 to 12 (one per layout, in a section "Layout examples") carry sample text, the footer and the
slide-number field; their picture placeholders are left empty, so python-pptx `insert_picture` works on the
duplicates. `deck/lib/structure.py` maps them by their layout relationship and rebuilds the sections from the
plan. The notes master uses the same theme (Fira Sans 12 pt notes).

### Changes the builder must know (old master to new master)

| Old (removed) | New |
|---|---|
| presenter idx 11 on L1 | idx 13 |
| contact idx 12 on L11 | idx 15 |
| date idx 100, confidentiality idx 101 | gone; footer is `ftr` idx 11, slide number `sldNum` idx 12 (on example slides already) |
| logo, QR and small print drawn freely | zones: logo idx 16 (L1, L11), QR idx 17 (L11), small print idx 19 (L11) |
| sidebar, filename slot, claim, `layouts.py` | nothing to fill: the footer text is already in the master |
| text inset 0.1 in, X0 1.155 | zero insets, margin 0.600 |
| title 30 pt, `font="major"` on title runs | 32 pt Fira Sans SemiBold inherited from the master: set no typeface on title runs |
| media 5.512 x 6.22 at 7.219 / 1.155 | 5.494 x 6.200 at 7.239 (L7) / 0.600 (L8), y 0.600 |
| `TITLE_PT` {1: 50, 6: 50, 11: 70} | `style.LAYOUT_TITLE_PT` {1: 54, 3: 44, 6: 48, 11: 60}, else 32 |

## 6. Rules

- **One highlight per slide.** On white: blue `#2B6797`. On navy: sage `#B1CAC5`. Never blue on navy (2.1:1).
- **Muted** elements (greyed chart series, "not in this pipeline" outlines, rules) use grey `#9CA3AF`; muted
  *text* on white uses slate `#455A64`, never grey.
- **Text colours.** On white: titles navy, body ink, small print slate. On navy: titles and body white, small
  print and footer sage.
- **Sizes.** Titles 32 pt (dark layouts as above), body 20 to 24 pt, code 18 pt or more (Fira Mono), source lines
  and footer 12 pt, appendix at least 14 pt. Hero numbers in Fira Sans SemiBold.
- **Code on white**: default ink, keywords navy (bold allowed), strings blue, comments slate (italic allowed),
  key line on a light `#E0E0E0` bar with a blue left edge. **Code on navy** (slide 1): default white, strings and
  highlights sage, comments grey or sage.
- **Charts**: highlighted series blue, other series grey, data labels and category labels ink (20 pt), axis titles
  slate, no gridlines, no legend where a direct label works; reference bars (RAM) navy.
- **Label chips on renders**: navy chip with white text, or a class swatch from the render palette next to the
  label; the label text carries the class, not the colour.
- **Decoration**: the accent bar is the only decorative element; it is marked decorative for screen readers.
  No sidebar, no logo on content slides, no Dutch motifs (none needed).
- **Language**: en-GB on every run; no en or em dashes in on-screen text.
