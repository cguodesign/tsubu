<p align="center"><img src="assets/logo.svg" alt="tsubu" width="200"></p>

# tsubu

[English](README.md) · [简体中文](README.zh-CN.md)

**tsubu** (粒, "grain", as in a grain of rice) is a tiny, dependency-free browser library that
renders exactly one sentence for read-along and language-learning use:

- the sentence arrives already cut into segments (for Japanese, *bunsetsu*), one grain per segment;
- every segment gets its own dotted underline;
- optional furigana (`<ruby>`) can be switched on and off **without moving any character**;
- the segment being spoken, or the whole sentence, is highlighted from timestamps, as a **pure
  function of time**: `stateAt(t)` and `apply(root, t)`. There is no `requestAnimationFrame`, no
  timer and no CSS transition, so frame-by-frame video capture and live playback draw exactly the
  same thing;
- colours are tokens, one group per state, with presets for a light page, a dark page and text
  over an image or video, and colours per speaker for dialogue. Every preset's contrast is
  measured against WCAG-based thresholds that are part of the library;
- a sentence that takes several lines breaks only between segments and by Japanese line-breaking
  rules, keeps its lines close in length, can take its size from its container, and beyond a
  maximum number of lines is paged by `t`.

It is one classic script (`tsubu.js`, about 21 KB unminified) and one stylesheet (`tsubu.css`). It loads from
a `file://` page, from any web page, and from Node with `require()`.

What tsubu does **not** do: split text into words or segments, align audio to text, estimate
times, play audio, draw a speech bubble or lay out more than one sentence. Those belong to the
caller.

## 30-second example

```html
<link rel="stylesheet" href="tsubu.css">
<div id="line" style="font-size: 40px"></div>
<script src="tsubu.js"></script>
<script>
  const s = Tsubu.sentence({
    segments: [
      { parts: [{ text: "雨", ruby: "あめ" }, { text: "の" }, { text: "日", ruby: "ひ" }, { text: "は" }], start: 0.0, end: 0.7 },
      { parts: [{ text: "、" }], kind: "punct" },
      { parts: [{ text: "家", ruby: "いえ" }, { text: "で" }], start: 0.9, end: 1.3 },
      { parts: [{ text: "お" }, { text: "茶", ruby: "ちゃ" }, { text: "を" }], start: 1.3, end: 1.8 },
      { parts: [{ text: "飲", ruby: "の" }, { text: "みます" }], start: 1.85, end: 2.6 },
      { parts: [{ text: "。" }], kind: "punct" },
    ],
  });
  const line = document.getElementById("line");
  line.innerHTML = s.html;
  const root = line.querySelector(".tsubu");

  // Drive it from any clock: an <audio> element, a video timeline, a frame counter.
  const audio = document.querySelector("audio");
  audio?.addEventListener("timeupdate", () => s.apply(root, audio.currentTime));
  s.apply(root, 1.0);            // the frame at t = 1.0 s: 家で is highlighted

  Tsubu.setRuby(root, false);    // hide the furigana; nothing moves
</script>
```

Open [`demo/index.html`](demo/index.html) straight from disk for a page with a time slider and a
furigana switch.

## Input

```js
Tsubu.sentence(input, options)

input = {
  lang: "ja",                  // optional, default "ja"; written to the root's lang attribute
  start: 4.0, end: 6.0,        // optional: the whole sentence's start and end, in seconds
  segments: [                  // required, in reading order
    { parts: [{ text: "家", ruby: "いえ" }, { text: "で" }], start: 0.9, end: 1.3 },
    { parts: [{ text: "、" }], kind: "punct" },
    // ...
  ],
}
options = {                    // all optional
  ruby: true,                  // whether furigana start out shown (default true)
  announceRuby: true,          // whether screen readers read each reading (default true)
  theme: "light",              // a preset: "light", "dark", "media", or a name of your own
  speaker: "a",                // whose line this is, for colours per speaker: "a", "b" or your own
}
```

- A **segment** is one unit of reading. Its `parts` are pieces of text; a part with `ruby` is drawn
  as `<ruby>text<rt>ruby</rt></ruby>`, so a word with a reading is never split.
- `kind: "punct"` marks punctuation: it has no underline, is never the segment being spoken and
  may not carry a time.
- Times are in seconds on the caller's clock, and `t` uses the same clock.

The times decide the sentence's **timing**:

| `timing` | When | What lights up |
|---|---|---|
| `"segments"` | every non-punctuation segment has `start` and `end` | one segment at a time. The sentence's own span is `input.start`/`input.end` if given, otherwise from the first segment's start to the last one's end. |
| `"sentence"` | no segment has a time, the sentence has `start` and `end` | the whole sentence at once. The span is **not** divided among segments by length or by mora. |
| `"none"` | no times anywhere | nothing: the sentence can be drawn (a static preview), but `stateAt` and `apply` throw. |

tsubu never guesses. These inputs throw an `Error` whose message starts with `tsubu:`:

- only some segments have times (completing them would be an estimate);
- segment times that overlap or are out of order, an `end` before its `start`, a time that is not
  a finite number, or only one of `start`/`end`;
- segment times outside the sentence's `start`/`end`;
- punctuation with a time, no segment that is not punctuation;
- an empty `segments`, `parts`, `text`, `ruby` or `lang`, an unknown `kind`, an `options.ruby` or
  `options.announceRuby` that is not a boolean, or an `options.theme` or `options.speaker` that is not a lower-case name
  (`a-z`, digits and `-`, starting with a letter).

## Output

`Tsubu.sentence()` returns a frozen object:

- **`html`**: an HTML string,

  ```html
  <span class="tsubu" lang="ja" data-timing="segments" data-ruby="on">
    <span class="tsubu-unit"><span class="tsubu-seg" data-index="0">…</span><span class="tsubu-seg" data-index="1" data-kind="punct">、</span></span>
    <wbr><span class="tsubu-unit"><span class="tsubu-seg" data-index="2">…</span></span>…
  </span>
  ```

  (without the whitespace). With `options.theme` the root also carries `data-tsubu-theme`, and
  with `options.speaker` it carries `data-speaker`. Punctuation segments carry `data-kind="punct"`.
  Segments are grouped in units, and a line breaks only between units (see
  [Several lines](#several-lines)): a segment is never split across lines, and a segment that may
  not begin a line (one that starts with a closing mark, `ー` or a small kana) shares a unit with
  the one before it, as does one that follows an opening bracket. All text is HTML-escaped. The
  fresh HTML has no state: `apply` adds it.
- **`timing`**: `"segments"`, `"sentence"` or `"none"`.
- **`stateAt(t)`**: a pure function of `t` that returns

  ```js
  { timing, state, progress, current, segments: [{ state, progress }] }
  ```

  - `state` is `"future"`, `"current"` or `"past"`. Every span is half-open, `[start, end)`:
    `t < start` is future, `start <= t < end` is current, `t >= end` is past. In a gap between two
    segments the one before is past, the one after is future, and none is current.
  - `progress` runs from 0 to 1 through the sentence or the segment. With timing `"sentence"` each
    segment's `progress` is `null` (unknown); punctuation's is always `null`.
  - `current` is the index of the segment being spoken, or `null`. It is always `null` with timing
    `"sentence"`.
  - With timing `"segments"`, punctuation becomes past together with the spoken segment before it;
    punctuation that opens the sentence becomes past when the first spoken segment begins. With
    timing `"sentence"` every segment, punctuation included, has the sentence's state.
- **`apply(root, t)`**: writes `stateAt(t)` onto the page and returns it. `root` must be the
  `.tsubu` element made from `html` (it throws if it is another element or the segment count does
  not match). It only sets attributes:
  - on the root: `data-state`, `--tsubu-progress`, and `aria-current="true"` while a sentence with
    timing `"sentence"` is being spoken;
  - on each segment: `data-state`, `--tsubu-progress` (timed segments only), and
    `aria-current="true"` on the segment being spoken;
  - with a maximum number of lines (see [Paging by t](#paging-by-t)): `data-page` and
    `data-pages` on the root, and `data-off-page` on the segments of other pages. The object it
    returns then also has `page` (from 0) and `pages`; both are `null` when the sentence is not
    paged.

  It never changes text and never adds or removes nodes.

Also on `Tsubu`:

- **`Tsubu.setRuby(root, on)`** shows or hides the furigana of a drawn sentence by setting the
  root's `data-ruby` to `"on"` or `"off"`.
- **`Tsubu.checkContrast(root, options)`** measures a drawn sentence's colours in the browser;
  see [Themes and contrast](#themes-and-contrast).
- **`Tsubu.contrast(foreground, background, backdrop)`**: the WCAG contrast ratio (1 to 21) of two
  colours (hex, `rgb()`, `rgba()`). A translucent foreground is painted over the background, and a
  translucent background over `backdrop` (default white). Works in Node too.
- **`Tsubu.CONTRAST`**: the thresholds, `{ text: 4.5, ruby: 4.5, underline: 3, highlight: 3 }`.
- **`Tsubu.THEMES`**: `["light", "dark", "media"]`; **`Tsubu.SPEAKERS`**: `["a", "b"]`.
- **`Tsubu.version`**: `"0.1.0"`.
- **`Tsubu.STATES`**: `["future", "current", "past"]`.

Because the frame for a given `t` never depends on which `t` came before, you can call
`apply(root, t)` from a video renderer's per-frame callback, from a headless browser that captures
frame by frame, or from a media element's time updates, and get the same picture. If you want a
fade or other easing, compute it from `progress` in your own CSS (`--tsubu-progress`) rather than
with a transition.

## CSS custom properties

Set them on `.tsubu` or on any ancestor (a bubble, a card, a theme's `:root`). Font family and
size are inherited from the page.

Layout and shape:

| Property | Default | Meaning |
|---|---|---|
| `--tsubu-line-height` | `1.75` | line height |
| `--tsubu-ruby-reserve` | `0.3em` | room above the first line for its furigana |
| `--tsubu-ruby-size` | `0.5em` | furigana size, relative to the text |
| `--tsubu-ruby-weight` | `400` | furigana weight |
| `--tsubu-underline-style` | `dotted` | underline style (any `border-style`) |
| `--tsubu-underline-width` | `0.06em` | underline thickness |
| `--tsubu-underline-offset` | `0.02em` | distance below the bottom of the segment's box |
| `--tsubu-underline-inset` | `0.12em` | inset from each end, so neighbouring underlines stay apart |
| `--tsubu-current-spread` | `0.06em` | how far the highlight reaches past the text (a `box-shadow`, so it takes no room) |
| `--tsubu-current-radius` | `0.18em` | highlight corner radius (0 with timing `"sentence"`, so the sentence reads as one band per line) |
| `--tsubu-plate-spread` | `0px` | how far the plate reaches past the sentence's box (it takes no room) |
| `--tsubu-plate-radius` | `0` | plate corner radius |
| `--tsubu-wrap` | `balance` | `text-wrap` of the sentence: `balance`, `pretty` or `wrap` |
| `--tsubu-max-lines` | `none` | more lines than this are paged by `t` |
| `--tsubu-progress` | written by `apply` | 0 to 1; read it in your own CSS, do not set it |

Colour tokens come in groups. The base group applies before the first `apply` and with timing
`"none"`; each state's group falls back to the base group, so setting only the base colours is
enough to recolour everything.

| Group | Text | Furigana | Underline | Background |
|---|---|---|---|---|
| base | `--tsubu-text-color` (inherited) | `--tsubu-ruby-color` (`#6b7280`) | `--tsubu-underline-color` (`#9ca3af`) | |
| future | `--tsubu-future-color` | `--tsubu-future-ruby-color` | `--tsubu-future-underline-color` | |
| current | `--tsubu-current-color` | `--tsubu-current-ruby-color` | `--tsubu-current-underline-color` | `--tsubu-current-bg` (`#e5e7eb`), the highlight |
| past | `--tsubu-past-color` | `--tsubu-past-ruby-color` | `--tsubu-past-underline-color` | |
| speaker *name* | `--tsubu-speaker-`*name*`-color` | `--tsubu-speaker-`*name*`-ruby-color` | `--tsubu-speaker-`*name*`-underline-color` | `--tsubu-speaker-`*name*`-bg` |
| plate | | | | `--tsubu-plate-bg` (transparent), behind the whole sentence |

A speaker's group replaces the current group in a sentence whose root has that `data-speaker`;
where the theme defines no colour for that speaker, the current group applies. `tsubu.css` maps
speakers `a` and `b`; for another name, copy its four-line `.tsubu[data-speaker="a"]` rule.
`--tsubu-backdrop` is not painted: it names the colours a theme is designed to sit on, for
`checkContrast`.

The highlight covers the line of text, not the furigana above it, so the current segment's
furigana sit on the page: give them a colour that reads on the page, not on the highlight.

States, themes and speakers change colours, a background and a `box-shadow` only, never weight,
padding or size, so none of them can move a character.

## Themes and contrast

Set a preset with `options.theme`, or with `data-tsubu-theme` on any ancestor (one attribute on
a page or a player themes every sentence in it):

| `data-tsubu-theme` | For | Checked against (`--tsubu-backdrop`) |
|---|---|---|
| `light` | dark text on a white or near-white page; a blue highlight with white text | `#ffffff` and `#f1f5f9` |
| `dark` | light text on a dark page; a light-blue highlight with dark text | `#0f172a` and `#1e293b` |
| `media` | text over an image or a video: a translucent black plate behind the sentence, a yellow highlight | anything: the plate is checked over pure black and pure white |

Each preset also has colours for speakers `a` (the preset's own highlight) and `b` (amber, or cyan
over media). To change one colour of a preset, set it on the `.tsubu` element itself, or set the
theme on an ancestor and the colour on anything inside it: a preset set on the root wins over
values it inherits.

The unthemed defaults are not a preset and are not checked: they inherit the page's text colour,
and their light-grey highlight and grey underline do not reach 3:1 on white. Use a preset, or check
your own colours, when contrast matters.

**The thresholds** are `Tsubu.CONTRAST`, after WCAG 2.2: 4.5:1 for text and for furigana (1.4.3,
normal-size text; furigana are small, and tsubu does not know your text size, so the large-text
allowance is never used), and 3:1 for the underline and for the highlight against what surrounds
it (1.4.11, graphics needed to follow the reading).

**`Tsubu.checkContrast(root, options)`** measures what the browser computes for a drawn sentence,
in every state: `"static"` (before any `apply`, and timing `"none"`), `"future"`, `"current"` and
`"past"`. For each segment it checks the text, the furigana and the underline against what is
behind them, painting translucent colours over what is beneath, and the highlight against the
plate and backdrop around it. A layer counts as on the highlight when the highlight covers its
middle, so the furigana above a highlighted segment are checked against the page. It works on a
hidden copy of the sentence and removes it again, so the page is left as it was.

```js
const result = Tsubu.checkContrast(root);
// { ok, checks: [{ state, layer, foreground, background, backdrop, ratio, minimum, ok }], failures }
Tsubu.checkContrast(root, { backdrop: "#fdf6e3", thresholds: { text: 7 } });  // your page, AAA text
```

The backdrop is `options.backdrop` (a colour, a list, or `"any"` for black and white), else the
theme's `--tsubu-backdrop`, else the background colours of the root's ancestors painted over white.
It does not see background images, `text-shadow` or anti-aliasing: over an image, use the `media`
plate or pass the image's lightest and darkest colours as backdrops.

## Several lines

### Line breaks

A line breaks only between segments, and never where Japanese line-breaking rules (*kinsoku*)
forbid it: no closing bracket or punctuation, long-vowel mark `ー`, small kana, iteration mark,
middle dot or colon at the start of a line, and no opening bracket at its end (the set of CSS
`line-break: strict`). tsubu applies these rules itself: segments that may not be parted share a
`white-space: nowrap` unit, and a `<wbr>` between units gives the line its place to break.

Why not leave it to the browser's `line-break`: Chromium treats an absolutely positioned box, such
as each segment's underline, as a place to break, and does not apply its line-breaking rules
there; a `<wbr>` likewise overrides them. Both were measured (Chromium 139). The rules work on the
first and last characters of segments as the caller cut them; tsubu does not look inside a
segment, which never breaks anyway. A segment wider than the line overflows it rather than being
split. Closing punctuation is not hung outside the line (`hanging-punctuation` is not supported in
Chromium), so a segment moves to the next line together with the comma after it.

### Balanced lines

The sentence has `text-wrap: balance` (change it with `--tsubu-wrap`), so the lines of a sentence
that takes several are kept close in length and the last line does not hold a lone segment.
Balancing is the browser's: Chromium balances a block of up to six lines and leaves a longer one
as it breaks greedily (measured in Chromium 139); per MDN, Firefox balances up to ten. Paging (below) keeps each page short enough.

### A size that follows the container

Inside an element with class `tsubu-fluid`, which becomes a query container named `tsubu`, the
sentence's font size is the container's width divided by a number of characters per line,
between a minimum and a maximum. Everything else in tsubu is in `em`, so spacing, furigana and
underlines follow. The width falls in one of three steps; the breakpoints are fixed, because a
container query cannot read a custom property, and every value in each step is configurable:

| Step | Container width | Characters per line | Maximum lines |
|---|---|---|---|
| narrow | under 480px | `--tsubu-narrow-chars` (`11`) | `--tsubu-narrow-max-lines` (else `--tsubu-max-lines`) |
| medium | 480px to 960px | `--tsubu-chars` (`15`) | `--tsubu-max-lines` |
| wide | 960px and over | `--tsubu-wide-chars` (`18`) | `--tsubu-wide-max-lines` (else `--tsubu-max-lines`) |

and `--tsubu-size-min` (`14px`) and `--tsubu-size-max` (`72px`) bound the size in every step. A
280px speech bubble on a phone gets about 25px text; a 1280px 16:9 frame gets 71px. The container
needs a width of its own: a query container does not take its width from its content, so a bubble
that shrinks to fit its text must be given a width or a `max-width` instead. Without
`tsubu-fluid` the size is inherited as before.

```html
<div class="tsubu-fluid" style="width: 100%; --tsubu-narrow-max-lines: 3; --tsubu-max-lines: 2">
  <!-- the .tsubu element made by Tsubu.sentence() -->
</div>
```

### Paging by t

With `--tsubu-max-lines` set (on the sentence or any ancestor, or per step), a sentence that takes
more lines is shown one page at a time, and `apply(root, t)` decides which:

- the page that holds the segment being spoken;
- between two segments, the page of the one just spoken; before the first, the first page;
  after the last, the last page.

The pages come from the layout: `apply` lays the sentence out whole and greedily, and every
`--tsubu-max-lines` lines make a page, so a page always begins at the start of a line; shown on its
own, it breaks into the same lines, which are then balanced among themselves. The page shown
depends on `t` and that layout alone, not on earlier calls: there is no scrolling and nothing is
estimated. Because it reads the layout, call `apply` after the fonts have loaded
(`document.fonts.ready`), and again after the container changes size.

A sentence without times for its segments (timing `"sentence"`) is never paged, since which part
of it is being read is not known: it is shown whole. Segments on other pages get `display: none`,
so they are also hidden from assistive technology until their page comes.

## Accessibility

- **Forced colours.** In forced-colours mode (Windows contrast themes and the like) browsers
  replace backgrounds and drop box-shadows, which would leave the segment being spoken looking
  like every other. tsubu keeps a highlight on that segment alone, in the user's own colours for
  selected text (`Highlight` and `HighlightText`); its furigana take `CanvasText`, since they sit
  on the page. Everything else is left to the browser.
- **Screen readers.** A reading is read after its base by default (Chromium exposes
  「雨 あめ が 降る」). With `options.announceRuby: false`, every `<rt>` gets `aria-hidden="true"`,
  so the sentence is read once; the readings are still drawn and still switch. Hidden furigana
  are never read, since they are `visibility: hidden`.
- The segment being spoken carries `aria-current="true"`, and segments on other pages are hidden
  from assistive technology along with the page (see [Paging by t](#paging-by-t)).

## Layout guarantees, and how they are tested

Each of these is checked by measuring the page in headless Chromium (see `tests/test_layout.py`):

- **Switching furigana moves nothing.** Hidden furigana get `visibility: hidden`, not
  `display: none`, so they keep their room: with `display: none` a word whose reading is wider than
  its base would narrow and everything after it would shift. The test records the box of every
  character, segment and reading, then switches the furigana and moves `t` back and forth, and
  requires every box to stay exactly where it was, on one line and on two.
- **Highlighting moves nothing.** Same test: boxes are compared across many values of `t`.
- **Changing the theme or the speaker moves nothing** (`tests/test_theme.py`): every preset and
  speaker, set on the root and on an ancestor, at several values of `t`, against the boxes of the
  unthemed sentence. The `media` plate is a positioned layer behind the sentence and takes no room.
- **Every preset meets the contrast thresholds** (`tests/test_theme.py`), in every state and for
  each speaker, measured by `checkContrast` on the library's own CSS. The tests also check that a
  colour below its threshold is reported, and that furigana above the highlight are measured
  against the page, not the highlight.
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
- **No motion.** Every element has `transition: none` and `animation: none`, and repeated
  `apply` calls produce the same attributes, text and node count.

The state logic (`tests/test_state.py`) runs `tsubu.js` itself in Node: half-open spans, gaps,
punctuation, progress, every refused input, and that `stateAt` depends on `t` alone.

## Browser support

Stated honestly:

- **Tested in Chromium only** so far (the build bundled with Playwright, Chromium 139 at the time
  of writing). Firefox and WebKit have not been run through the layout tests yet.
- `ruby-align` is needed for the "wide reading does not spread its base" guarantee. Per MDN it is
  supported from **Chrome 128** and **Safari 18.2**. In older browsers the furigana still switch
  without reflow, but a reading wider than its base spreads the base characters apart.
- Balanced lines use `text-wrap: balance` (Chrome 114, Firefox 121, Safari 17.5); without it,
  lines break greedily. The fluid size uses container queries and `cqi` units (Chrome 105,
  Firefox 110, Safari 16).
- The script uses ES2015+ syntax (`const`, arrow functions, template literals) and the `:scope`
  selector.
- No `<rp>` fallback parentheses are written yet, so a browser without ruby support shows the
  reading inline after its base.

Known limitation: when a reading is much wider than its base (いっしゅうかん over 一週間), the
ruby box takes the reading's width, so a visible gap appears around the base; browsers do not let
the reading overhang the neighbouring kana.

## Running the tests

Requirements:

- Node 18 or newer on `PATH` (tested with Node 22);
- Python 3.9 or newer (tested with 3.13) with `pytest` and `playwright`, and Playwright's Chromium:

  ```sh
  python -m pip install pytest playwright
  python -m playwright install chromium
  ```

Then, from the repository root, one command runs everything (state, layout and demo tests):

```sh
python -m pytest -q
```

The layout tests use a Japanese font from the system (Hiragino Sans, Noto Sans JP or Noto Sans CJK
JP); the measurements are relative, so another CJK font should give the same results.

## Files

| File | What |
|---|---|
| `tsubu.js` | the library: a classic script that defines `Tsubu`, or `module.exports` in Node |
| `tsubu.css` | the styles; everything adjustable is a custom property |
| `demo/index.html` | a demo with a time slider, a furigana switch, a theme picker, a dialogue and a fluid, paged frame; accepts `?t=seconds&ruby=off&theme=dark&frame=320&lines=2` |
| `tests/` | the test suite (pytest; Node for the state, Playwright Chromium for the layout) |
| `assets/` | the logo |

## Licence

MIT; see [LICENSE](LICENSE). Planned work is in [ROADMAP.md](ROADMAP.md), changes in
[CHANGELOG.md](CHANGELOG.md).
