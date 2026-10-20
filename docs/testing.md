# tsubu: guarantees, browser support and tests

What tsubu promises about its layout, how each promise is measured, which hold in which
engine, and how to run the suite. The features themselves are in [guide.md](guide.md).

## Layout guarantees, and how they are tested

Each of these is checked by measuring the page in a headless browser (see `tests/test_layout.py`),
Chromium by default and Firefox or WebKit with `--engine`; [Browser support](#browser-support)
says which hold where:

- **Switching furigana moves nothing.** Hidden furigana get `visibility: hidden`, not
  `display: none`, so they keep their room: with `display: none` a word whose reading is wider than
  its base would narrow and everything after it would shift. The test records the box of every
  character, segment and reading, then switches the furigana and moves `t` back and forth, and
  requires every box to stay exactly where it was, on one line and on two.
- **Highlighting moves nothing.** Same test: boxes are compared across many values of `t`.
- **Romaji, and switching either side, move nothing** (`tests/test_romaji.py`). With romaji under
  the furigana, romaji over the furigana, romaji over the text alone and romaji under it alone, in
  horizontal and vertical text, on one line and on two (columns): the boxes of every character,
  segment and reading, and the sentence's own, stay where they are while `t` moves and the over
  and under sides are switched on and off, each and both; a sentence drawn with a side hidden is
  laid out as one with it shown. With furigana over and nothing under, the HTML is byte for byte
  that of the same sentence without romaji.
- **Each reading is on its side and clear of everything else** (`tests/test_romaji.py`): above or
  below its segment's text (at its right or left in vertical text), inside the sentence's box, its
  text clear of the underline (or side line), which runs between the text and the readings under
  it, and no reading overlapping another reading or a character, on its own line or the next. The
  same holds in a face with Noto Sans JP's metrics, measured by the em boxes of text and readings;
  in vertical text the highlight and the side line stay on the em box of the text whatever
  readings a segment has. Pages with readings under the text keep to their number of lines, and
  switching either side does not reflow them.
- **Changing the theme or the speaker moves nothing** (`tests/test_theme.py`): every preset and
  speaker, set on the root and on an ancestor, at several values of `t`, against the boxes of the
  unthemed sentence. The `media` plate is a positioned layer behind the sentence and takes no room.
- **Every preset meets the contrast thresholds** (`tests/test_theme.py`), in every state and for
  each speaker, measured by `checkContrast` on the library's own CSS. The tests also check that a
  colour below its threshold is reported, and that furigana above the highlight are measured
  against the page, not the highlight.
- **The highlight stays clear of the furigana whatever the font's metrics** (`tests/test_theme.py`).
  The system face is given Noto Sans JP's metrics with `ascent-override` and `descent-override`
  (a content area of 1.45em, 0.28em of it above the em box), and every preset still meets its
  thresholds in every state, horizontally and vertically. The highlight's band and the underline
  are measured against the baseline of the text, in that face and in the system's own, and a
  screenshot shows the text's ink inside the band and the reading's ink above it; nothing moves
  in that face either.
- **Furigana are not clipped and do not touch the line above.** `--tsubu-ruby-reserve` adds room
  above the first line, because browsers differ in whether the first line box grows to fit its
  ruby; with the reserve the reading stays inside the sentence's box (and so inside a container
  with `overflow: hidden`). The test checks that every reading lies inside the root and clears the
  characters and underlines of the line above. If you raise the furigana size or lower the line
  height, raise the reserve with them.
- **A reading wider than its base does not spread the base.** tsubu sets `ruby-align: center`; the
  default `space-around` would put space between the base characters. The test compares the ink
  width of the base with and without furigana in a screenshot, and checks that `space-around`
  would have been caught.
- **Every segment has its own underline.** The underline is the segment's own `::after`, inset at
  both ends, and segments have no `text-decoration`, so neighbouring underlines never join. The
  test checks the gap between neighbours on the same line.
- **Lines break only between segments and by Japanese line-breaking rules**
  (`tests/test_lines.py`), at many container widths, including a sentence cut on purpose so that
  segments begin with `っ` and `ー` next to brackets and commas.
- **Over a grid of container widths and sentence lengths** (`tests/test_lines.py`, 7 widths from
  200px to 1280px in a fluid container, 5 sentences from one line to many): nothing overflows the
  container, no two characters, rubies or readings overlap, no reading is clipped at the top, and
  switching the furigana moves no character.
- **Balanced lines**: wherever a greedy layout of up to six lines leaves a single segment on the
  last line, the balanced one does not, and its lines are closer in length.
- **The fluid size** is checked at and around every breakpoint, with defaults and with every step
  configured.
- **Paging**: with a maximum number of lines, every segment is on the page while it is spoken, no
  page has more lines than allowed, a page begins at the start of a line, the pages share no
  segment and together hold all of them, they turn only forward as `t` grows, a gap keeps the page
  of the segment just spoken, the same `t` always shows the same page, and switching the furigana
  does not reflow a page.
- **Forced colours and screen readers** (`tests/test_a11y.py`): under emulated forced colours the
  segment being spoken has the system highlight in every theme and timing, and nothing moves; with
  `announceRuby` off the accessibility tree holds no reading.
- **The `<rp>` parentheses show only where ruby cannot be drawn** (`tests/test_fallback.py`): every
  reading is wrapped in full-width `<rp>` parentheses, which take no room, move nothing and are not
  read in a browser that draws ruby, stay hidden where a page's own styles would show `rp`, are
  hidden with the reading when `announceRuby` is off, and read 雨（あめ） when tags are dropped or
  ruby is laid out inline.
- **Romaji in the checks, motion and accessibility** (`tests/test_romaji.py`): `checkContrast`
  measures them in every state and theme against the furigana's threshold, on the page rather than
  the highlight; `checkFit` reports romaji past the container; `appear`, `mask` and `blur` treat
  them as furigana and no preset moves them; under forced colours the spoken segment's romaji take
  `CanvasText`; with `announceRuby` off the accessibility tree holds none; `htmlAt` equals `apply`;
  without ruby layout they follow their segment in parentheses.
- **Motion presets** (`tests/test_motion.py`): each draws what it says for unheard segments only,
  a revealed segment is drawn as without the preset, nothing moves with any preset or reveal,
  frames are byte-identical screenshots whatever order `t` and reveals come in, every theme meets
  its thresholds with every preset, and the catalogue matches the stylesheet.
- **No motion.** Every element has `transition: none` and `animation: none`, and repeated
  `apply` calls produce the same attributes, text and node count.

The state logic (`tests/test_state.py`) runs `tsubu.js` itself in Node: half-open spans, gaps,
punctuation, progress, every refused input, and that `stateAt` depends on `t` alone.

## Browser support

The browser tests run in Chromium, Firefox and WebKit (`--engine`, see
[Running the tests](#running-the-tests)). Measured with Playwright 1.54 on Chromium 139.0.7258.5,
Firefox 139.0 and WebKit 26.0 (the engine of Safari 26), and on Firefox 153.0. The suite passes in
all of them. Where an
engine cannot do something tsubu relies on, the test is marked as an expected failure in that
engine alone, with the reason (the `limitation` mark in `tests/conftest.py`); where the engine
only measures differently, the test checks the same guarantee in that engine's terms.

- **Chromium**: every guarantee holds.
- **Firefox**: every guarantee holds but balanced lines. Firefox does not apply
  `text-wrap: balance` when the only break opportunities are between nowrap units, which is how
  tsubu keeps the line-breaking rules, so lines and columns break greedily. Also measured: in
  Firefox 139 a column of upright text is as wide as the em box whatever the font's ascent and
  descent (Firefox 153 takes them, as Chromium does); Firefox rounds the ascent and the descent of
  a text box up to whole pixels, and Firefox 153 sets a reading by the font's own metrics, so at a
  fractional font size the reading's box reaches up to 1.4px into its base's, with the glyphs as
  far apart as in Chromium; without the ruby reserve the first column's readings stick out of the
  sentence's box by a few pixels (the reserve holds them, as intended); `htmlAt` gives the same
  element tree, with the style attribute in another place.
- **WebKit (Safari)**: every guarantee holds but balanced lines and columns, in horizontal and
  vertical text.
  - Balanced lines: Playwright's WebKit build 2182 does not apply `text-wrap: balance` to inline
    content that holds absolutely positioned boxes (each segment's highlight and underline), so
    lines break greedily. Build 2191 (Playwright 1.54's own, WebKit 26.0) does balance, and can
    put a sentence on one more line than greedy breaking needs (measured: 8, 3 and 7 characters
    where greedy breaking gives 8 and 10), which balancing should never do. Where that would put a
    page on more lines than `--tsubu-max-lines`, `apply` marks the root `data-greedy` and the page
    keeps its greedy lines.
  - Forced colours: WebKit has none of its own. With the media query emulated tsubu's rules apply
    and the segment being spoken gets the system highlight, but WebKit replaces no other colour.
  - `ascent-override` and `descent-override` are not supported, so the test that gives a face
    Noto Sans JP's metrics cannot run; with the system's Hiragino Sans every guarantee is measured,
    and the site's pages, set in web fonts with a tall content area, pass their contrast checks in
    vertical text too.
  - Fixed in tsubu: WebKit lets a reading wider than its base overhang the next kana but keeps
    the segment's box as long as before, so neighbouring underlines met; tsubu sets
    `ruby-overhang: none`. And WebKit reports the computed insets of a box positioned inside an
    inline against the block around it, so `checkContrast` measures the highlight and the
    underline on probes that take the same geometry instead of reading them back. In
    `vertical-rl` text WebKit places a box positioned inside an inline mirrored across the
    block's right edge, as far right of it as the segment lies left of it (measured), so each
    highlight and side line was drawn away from its segment: there each segment is an
    `inline-block` (see [Vertical writing](guide.md#vertical-writing)). WebKit also takes the font's whole
    content area into the line of a base that has a reading, whatever the line height, and sets
    the reading past it; the segment's line is 2em across to hold it, and the column grows only
    as far as the reading needs.
- **Romaji (nested ruby).** A segment with romaji is a ruby whose base holds the parts' own ruby.
  Chromium, Firefox and WebKit all draw it, with the readings on the side `ruby-position` says, in
  horizontal and vertical text (probed in each engine before relying on it). Measured in
  WebKit: a line of such segments, with readings on both sides, is laid out again with the
  segments wider than they are, and so on more lines, when a reading gets a filter, an opacity or
  a text shadow (the `blur` preset) or a positioned box is added to a segment; its first layout is
  right. The ruby is therefore drawn in an inline-block (`.tsubu-stack`), whose layout stays the
  same in every engine (tested with `blur` and an added box). WebKit also gives the side of a
  nested reading the room of the inner reading's line, so its lines with readings on both sides
  are further apart than Chromium's and Firefox's (in vertical text tsubu gives the inner ruby a
  line height of 1, which the other engines do not read there, so that the columns match); and it
  does not grow the last line for the readings under it, which `--tsubu-under-reserve` holds.
- `ruby-align` is needed for the "wide reading does not spread its base" guarantee. Per MDN it is
  supported from **Chrome 128** and **Safari 18.2**. In older browsers the furigana still switch
  without reflow, but a reading wider than its base spreads the base characters apart.
- Balanced lines use `text-wrap: balance` (Chrome 114, Firefox 121, Safari 17.5); without it,
  lines break greedily. The fluid size uses container queries and `cqi` units (Chrome 105,
  Firefox 110, Safari 16).
- `tsubu.js` needs ES2019 (`Array.prototype.flatMap`) and the `:scope` selector;
  `tsubu-export.js` ES2017 (`padStart`); `tsubu-import.js` ES2020 (`??`) with Unicode property
  escapes in regular expressions (ES2018).
- Where ruby cannot be drawn at all (a reader view, a feed reader, a text browser), the full-width
  `<rp>` parentheses show each reading after its base: 雨（あめ）.

Known limitation: when a reading is much wider than its base (いっしゅうかん over 一週間), the
ruby box takes the reading's width, so a visible gap appears around the base; Chromium and Firefox
do not let the reading overhang the neighbouring kana, and in WebKit tsubu turns it off (above).

## Running the tests

Requirements:

- Node 18 or newer on `PATH` (tested with Node 22);
- Python 3.9 or newer (tested with 3.13) with the versions of `pytest` and `playwright` pinned in
  `requirements-dev.txt`, and Playwright's Chromium (and its Firefox and WebKit, to run the tests
  there), the builds that Playwright version pins:

  ```sh
  python -m pip install -r requirements-dev.txt
  python -m playwright install chromium firefox webkit
  ```

Then, from the repository root, one command runs everything (state, layout and demo tests):

```sh
python -m pytest -q
```

The browser tests run in Chromium unless another engine is named; `--engine-executable PATH`
launches another build of that engine instead of Playwright's own:

```sh
python -m pytest -q --engine firefox
python -m pytest -q --engine webkit
```

`npm ci` installs the pinned TypeScript compiler, and the suite then also compiles
`tests/types` against the declarations (`npm run typecheck` does it alone). The same suite runs
on every push in GitHub Actions (`.github/workflows/ci.yml`), in all three engines.

The layout tests use a Japanese font from the system (Hiragino Sans, Noto Sans JP or Noto Sans CJK
JP); the measurements are relative, so another CJK font should give the same results.
