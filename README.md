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

## Install

From npm, pinned to an exact version:

```sh
npm install --save-exact tsubu
```

The package holds the same files as this repository, with no build step: `tsubu.js` (the classic
script), `tsubu.css`, `tsubu-export.js`, an ES module for each script (`tsubu.mjs`,
`tsubu-export.mjs`, which only re-export the script's object) and TypeScript declarations.

```js
const Tsubu = require("tsubu");                     // Node, CommonJS
const TsubuExport = require("tsubu/export");
import Tsubu, { sentence } from "tsubu";            // ES modules and bundlers
import { toSRT } from "tsubu/export";
import "tsubu/tsubu.css";                           // with a bundler that handles CSS
```

From a CDN, with an exact version and [Subresource Integrity](https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity),
so the page runs only the file it was written against:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tsubu@0.1.0/tsubu.css"
      integrity="sha384-…" crossorigin="anonymous">
<script src="https://cdn.jsdelivr.net/npm/tsubu@0.1.0/tsubu.js"
        integrity="sha384-…" crossorigin="anonymous"></script>
```

`https://unpkg.com/tsubu@0.1.0/tsubu.js` serves the same file. The hash of a file is
`openssl dgst -sha384 -binary tsubu.js | openssl base64 -A`, taken from the package (`npm pack`)
or the CDN's copy; ask the CDN for the file itself, not a minified version, whose hash differs.
In a page without a bundler, `<script type="module">` can import `tsubu.mjs` from the same
places; the classic script then also defines the global `Tsubu`.

Or copy `tsubu.js` and `tsubu.css` next to your page: that is all a page needs, and it works from
`file://`.

**Versions.** tsubu follows [Semantic Versioning](https://semver.org/). Until 1.0, a change that
breaks callers raises the minor version (0.1 to 0.2) and anything else the patch version. Breaking
means a change to the input format or what it refuses, the HTML (elements, classes, `data-*` and
`aria-*` attributes), the names of the `--tsubu-*` properties, themes and motion presets, the
names and signatures on `Tsubu` and `TsubuExport`, the shape of what `stateAt`, `apply`,
`checkContrast` and `checkFit` return, or the text the exporters write. `Tsubu.version` is the
version of the script in hand; [CHANGELOG.md](CHANGELOG.md) lists every change.

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
  motion: "mask",              // motion presets from Tsubu.MOTIONS, a name, a list or an array
  writing: "vertical",         // "horizontal" (default) or "vertical"
  combineUpright: 2,           // in vertical text, runs of up to this many half-width characters stand upright (0-4)
}
```

- A **segment** is one unit of reading. Its `parts` are pieces of text; a part with `ruby` is drawn
  as `<ruby>text<rt>ruby</rt></ruby>`, so a word with a reading is never split.
- `kind: "punct"` marks punctuation: it has no underline, is never the segment being spoken and
  may not carry a time.
- Times are in seconds on the caller's clock, and `t` uses the same clock.
- A segment may carry an `id` (a non-empty string, unique in the sentence) and `tags` (lower-case
  names, such as `["new-word"]`). They are the caller's: tsubu writes them as `data-id` and
  `data-tags` and gives them no meaning. Style a tag with the same tokens as everything else, for
  example `.tsubu-seg[data-tags~="new-word"] { --tsubu-future-color: #be123c; }`;
  `checkContrast` measures whatever colours that gives. Keep tag styles to colours and lines, so
  that they move nothing.

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
  `options.announceRuby` that is not a boolean, an `options.theme` or `options.speaker` that is not a lower-case name
  (`a-z`, digits and `-`, starting with a letter), or an `options.motion` naming a preset that is
  not in `Tsubu.MOTIONS`;
- an empty or non-string `id`, an `id` used twice, or `tags` that are not an array of lower-case
  names.

## For agents

tsubu never segments, guesses readings or estimates times, so whoever calls it has to prepare
that input. [`docs/agents/segmenting.md`](docs/agents/segmenting.md) is a versioned guide for AI
agents that do this: how to cut a raw Japanese sentence into bunsetsu, take readings from a
morphological analyser and put them on the kanji, take times from forced alignment or from the
speech synthesiser, and check the result before it is drawn. Each tool it names was checked
against its own documentation on the date the guide gives, with links, and the guide has a
changelog, because the tools and models change. It comes with a dependency-free validator,
[`docs/agents/validate.mjs`](docs/agents/validate.mjs), and a hand-made worked example that the
tests check:

```sh
node docs/agents/validate.mjs input.json --text sentence.txt
```

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
- **`span(i)`**: segment `i`'s own time, `{ start, end }`, where to seek the caller's audio when it
  is tapped (with `Tsubu.segmentOf(event.target)` for `i`); `null` for punctuation and for a
  sentence without times for its segments, since nothing is estimated.
- **`find(id)`**: the index of the segment with that `id`, or `null`.
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
- **`htmlAt(t, { revealed })`**: the frame at `t` as an HTML string, without a page: `html` with
  the attributes `apply(root, t)` (and `setRevealed(root, revealed)`) would write. Use it on a server, in Node, or with a renderer that
  takes HTML (server-side rendering, HTML-to-image, a video renderer's frames). The tests check that
  it is the same element tree, text and attributes as a fresh `html` after `apply` in the browser,
  and in Chromium and WebKit even the same string (Firefox orders the attributes differently). It does not page (paging needs the layout), and like
  `stateAt` it refuses a sentence without times.
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
- **`Tsubu.setRevealed(root, which)`** reveals segments that a motion preset hides while they are
  unheard: `which` is an array of segment indexes, `"all"` or `"none"`, and replaces the previous
  set. It writes `data-revealed` and returns the indexes. See [Motion and revealing](#motion-and-revealing).
- **`Tsubu.segmentOf(node)`**: the index of the segment a node lies in (an event's target, say),
  or `null`; for click and tap handlers.
- **`Tsubu.MOTIONS`**: the catalogue of motion presets.
- **`Tsubu.checkContrast(root, options)`** measures a drawn sentence's colours in the browser;
  see [Themes and contrast](#themes-and-contrast).
- **`Tsubu.checkFit(root, options)`** measures whether a drawn sentence fits where it is drawn:
  in its container (`options.container`, else the root's parent element), at the size, font and
  width it has there. It works on a hidden copy with every segment shown and the furigana on, and
  checks a sentence paged by `t` page by page. It returns `{ ok, issues, lines, pages }`; each
  issue is `{ kind, segment, page, by, message }`, `by` in pixels:
  - `"overflow"`: a segment reaches past the container's padding box;
  - `"too-wide"`: segments that may not be parted are longer than a line (or column), so they can
    only overflow: shorten the segment or make the text smaller;
  - `"ruby-clipped"`: furigana reach past the container: raise `--tsubu-ruby-reserve` or give the
    container room;
  - `"too-many-lines"`: more lines than `--tsubu-max-lines` in a sentence that cannot be paged.

  The library's own guarantees are tested over a grid of widths (see below); `checkFit` is for the
  caller, or the agent working for it, to run on its own container, font and sentences.
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
| `--tsubu-underline-offset` | `0.02em` | distance below the em box of the text |
| `--tsubu-underline-inset` | `0.12em` | inset from each end, so neighbouring underlines stay apart |
| `--tsubu-current-spread` | `0.06em` | how far the highlight reaches past the em box of the text (a positioned layer, so it takes no room) |
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

The highlight covers the em box of the text, not the furigana above it, so the current segment's
furigana sit on the page: give them a colour that reads on the page, not on the highlight.

States, themes and speakers change colours and the background of one positioned layer only,
never weight, padding or size, so none of them can move a character.

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

**Fonts with a tall content area.** A segment's own box is the font's content area, and in many
web fonts (Noto Sans JP and the rest of the Noto and Source Han family, Shippori Mincho,
Zen Kaku Gothic) that is about 1.45em tall and reaches 0.28em above the em box of the text,
into the furigana, whose ink sits just above the base's em box. So the highlight and the underline
are not drawn from that box but from the em box: a band 1em tall, `--tsubu-current-spread` past
it, and a line `--tsubu-underline-offset` below it. CSS cannot read a font's ascent, so the em box
is placed within the content area by a fixed split of the extra height (62% above it and 38%
below; vertical text needs none, since each segment's line is centred on the em box), which is exact for Hiragino Sans, whose content area is its em box, and for the whole Noto family,
and within a few hundredths of an em for the rest. The current segment's furigana therefore sit
on the page in every font, and `checkContrast` measures the highlight where it is drawn.

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

## Vertical writing

```js
Tsubu.sentence(input, { writing: "vertical" })   // or data-tsubu-writing="vertical" on any ancestor
```

`options.writing` (`"horizontal"` or `"vertical"`) writes `data-tsubu-writing` on the root. The
attribute also works on an ancestor, as `data-tsubu-theme` does, and `"horizontal"` on the root
keeps a sentence horizontal inside a vertical ancestor. Vertical text is `writing-mode:
vertical-rl`: columns run from right to left, the furigana sit at the right of the characters, and
each segment's underline becomes a dotted **side line at its left**, inset at both ends. The ruby
reserve becomes room at the right of the first column. The highlight, its spread and the `media`
plate are the same boxes turned with the text; `underline-draw` draws the side line in from the
top. Each segment is an `inline-block` here, a line 2em across centred on the em box of its text,
and the highlight and the side line are drawn from its left edge: WebKit misplaces a box
positioned inside an inline in vertical text. Negative margins give the room back, so a column is
as wide as the line height and grows only for readings that would reach the characters of the
next; a segment's box takes in its reading. Without the ruby reserve the first column's readings
stick out of the sentence's box. The column length is the sentence's height, so give the container a height; without one, the
sentence is as tall as its content, up to the viewport.

**Digits and Latin letters.** A run of half-width characters (ASCII other than spaces and
brackets) of at most `options.combineUpright` characters (0 to 4, default 2) is set upright across
the column with `text-combine-upright` (10月, AI, !?). Longer runs lie on their side
(`text-orientation: mixed`), as in 2025年. Chromium squeezes any upright run into one em, so four
characters is the limit. The runs are wrapped in `<span class="tsubu-upright">` unless the
sentence is horizontal by its own option, since an ancestor can make it vertical after it is
drawn; the span has no effect in horizontal text (boxes measured the same to within 1/64 px).

**Punctuation, brackets and ー** take their vertical forms from the font's vertical alternates.
With Hiragino Sans or Noto Sans CJK, Chromium draws 、。 at the upper right, ー as a vertical
stroke, and brackets turned (measured from screenshots). A font without vertical alternates leaves
some marks in their horizontal form.

**Guarantees.** All the horizontal ones hold with columns in place of lines, tested in
`tests/test_vertical.py`: switching furigana, highlight, theme or speaker moves nothing; every
frame is a function of `t`; columns break only between units and by the line-breaking rules;
`checkContrast` measures across the column (the readings against the page, the side line inside
the highlight's spread); forced colours keep the highlight. **Paging** counts columns:
`--tsubu-max-lines` is the number of columns per page, counted from the right.

**Fluid size.** In vertical text the column runs along the container's height, so the height
drives the size: the `.tsubu-fluid` container becomes a size container (it must have a definite
height), the font size is its height divided by the characters per column, and the steps (480px,
960px) and their properties go by its height. This uses `:has()` and `cqh`.

## Motion and revealing

Motion presets change how a sentence shows what has and has not been heard. Each one is drawn by
`tsubu.css` from the state `apply` writes, so every frame is still a function of `t`; there is no
timer and no transition. Choose them with `options.motion` or `data-tsubu-motion` on any ancestor;
several can be combined. *Unheard* means neither current nor past: in the future, or in a sentence
that has not been applied (timing `"none"`).

| Preset | What it draws |
|---|---|
| `appear` | segments appear as they are spoken; nothing unheard is drawn, not even its underline |
| `mask` | unheard segments are blanks: no text and no reading, but the underline, so the length of what is to come shows; for listening and fill-in exercises |
| `blur` | unheard segments, readings included, are blurred (`--tsubu-blur`, `0.15em`) |
| `underline-draw` | the underline of the segment being spoken draws itself in over the segment's time; unheard segments have none yet |

**Revealing on the caller's events.** `Tsubu.setRevealed(root, [2, 3])` shows segments 2 and 3 as
if they had been heard, whatever `t` is: for a word the learner said right, a tap, a button.
tsubu handles no events itself. `Tsubu.segmentOf(event.target)` tells a click handler which segment
was hit. What is drawn is then a function of `t` and of the revealed set, and
`htmlAt(t, { revealed })` renders the same thing without a page.

```js
const s = Tsubu.sentence(input, { motion: "mask" });   // no times: every segment starts as a blank
let shown = [];
root.addEventListener("click", (event) => {
  const i = Tsubu.segmentOf(event.target);
  if (i !== null) shown = Tsubu.setRevealed(root, [...shown, i]);
});
recogniser.onCorrect = (i) => { shown = Tsubu.setRevealed(root, [...shown, i]); };  // your own speech check
```

`Tsubu.MOTIONS` is the same list as data: each preset's `name`, `purpose`, the timing it `needs`,
what it does `without` that timing, its `parameters` (custom property, default, range, meaning),
what it does under `prefers-reduced-motion: reduce`, and whether it is `revealable`. The tests
check that the catalogue and the stylesheet agree.

**Choosing motion (for agents and template authors).** Choose from the catalogue, do not invent
motion; and use motion only to show a change in what is being read, never to decorate.

- Plain read-along, subtitles: no preset. The highlight already shows what is being read.
- Teaching a sentence in a video, line by line: `appear`, or `underline-draw` when the whole
  sentence should stay readable.
- Listening and dictation: `mask` (the blanks show length) or `blur` (the shape shows), revealed
  by time or by the learner's answers.
- Do not combine `appear` with `mask` or `blur`: `appear` already hides everything they would.
  Nor `mask` with `underline-draw`, which leaves unheard segments without a line, so the blanks
  lose the line that shows their length.
- With timing `"sentence"` the presets act on the whole sentence at once; say so to the viewer,
  rather than adding motion that suggests segment timing that is not there.
- Do not dim what has been read with opacity: it would fall below the contrast thresholds. Use the
  past colour group, which the themes already set within them.

Not offered: a character-by-character wipe, which needs per-character times tsubu does not have.
Under `prefers-reduced-motion: reduce`, `underline-draw` draws the underline whole at once; the
others are changes of state, not movement. Text hidden by `mask` is still in the page, so screen
readers read it; for a test, keep the answer out of the page or use `appear`. `checkContrast`
reveals every segment in its copy, so every colour that can be drawn is checked, and it counts
opacity on a layer.

## Recording video

Because each frame depends on `t` alone, a video is a loop over frame times. Two examples, both run
by the tests (`tests/test_examples.py`), use `examples/sentence.json`:

- **`examples/capture-frames.py`** draws the sentence in headless Chromium (or `--engine firefox`
  or `webkit`) and saves one PNG per
  frame, calling `apply(root, t)` at each frame's time, then prints the ffmpeg command that joins
  the frames with your audio (it does not run it):

  ```sh
  python examples/capture-frames.py examples/sentence.json frames --fps 30 --theme media --motion appear
  ```

- **`examples/frames-from-node.mjs`** writes each frame as an HTML page with `htmlAt(t)`, with no
  browser, for renderers that take markup:

  ```sh
  node examples/frames-from-node.mjs examples/sentence.json frames 30
  ```

The test renders every frame forward and then backward and requires the PNGs to be identical, byte
for byte. One thing it found: calling `apply` on the same element frame after frame gives the same
state, but Chromium repaints only what changed, and where a highlight's rounded corner lies over
the translucent `media` plate, a few edge pixels then depend on the frame before. The example draws
each frame on a fresh copy of the sentence (`innerHTML = s.html`, then `apply`), which makes frames
identical in any order, and lets them be rendered in parallel. For engines with their own clock,
such as Remotion, see [Using tsubu with other tools](#using-tsubu-with-other-tools).

## Exporting subtitles

An optional script, `tsubu-export.js`, turns the same input into subtitles. Load it after
`tsubu.js` (it defines `TsubuExport`), or `require("./tsubu-export.js")` in Node. Input is checked
by `Tsubu.sentence()`, so it is refused with the same errors. A sentence without times cannot be
exported, and nothing is estimated.

- **`TsubuExport.toWebVTT(input, { ruby = true, offset = 0, id })`** returns a WebVTT file with
  one cue spanning the sentence. Each segment is a class span, `<c.tsubu-seg>`
  (`<c.tsubu-seg.punct>` for punctuation), and readings are `<ruby>雨<rt>あめ</rt></ruby>`. With
  timing `"segments"`, a cue timestamp marks each spoken segment's start, so `::cue(:past)` follows
  the reading. Timestamps are strictly increasing and inside the cue. `ruby: false` drops the
  readings, `offset` shifts all times in seconds, and `id` names the cue. `&`, `<` and `>` are
  escaped.
- **`TsubuExport.toASS(input, { ruby = "omit", offset = 0 })`** returns one ASS karaoke
  `Dialogue:` line with `\k` durations. A gap is an empty syllable, and punctuation joins the
  syllable before it. Boundaries are rounded to centiseconds before the durations are taken, so the
  durations always add up to the line's length. ASS has no ruby: `ruby: "inline"` writes
  `雨(あめ)`. ASS cannot escape `{`, `}` or `\`, so they are written as ｛ ｝ ＼.
  **`toASSScript`** wraps the line in a minimal script with one `Default` style.
- **`TsubuExport.toSRT(input, { mode = "sentence", ruby = "omit", offset = 0 })`** returns a
  SubRip (`.srt`) file of plain text. `mode: "sentence"` writes one cue for the sentence;
  `mode: "segments"` writes one numbered cue per spoken segment, from its start to its end, with
  punctuation joined to the segment before it. `"segments"` needs timing `"segments"` and is
  refused for a sentence timed as a whole. Times are `HH:MM:SS,mmm`. Each boundary is rounded on
  its own, so cues of segments that meet also meet. `ruby` is as for ASS. SRT has no standard
  karaoke, and players read tags in it inconsistently, so the file has no tags at all:
  `<`, `>`, `{`, `}` and `\` in the text are written as ＜ ＞ ｛ ｝ ＼. For a highlight that
  follows the reading, use ASS or WebVTT.

Times are rounded half up as written (to milliseconds or centiseconds), line breaks in text become
spaces, and negative times are refused. The tests (`tests/test_export.py`) check exact output in
Node, that the browser parses the WebVTT as one cue with its spans, ruby and timestamps, and, where
ffmpeg with libass is installed, that the ASS karaoke lights up at each syllable's start. Where
ffmpeg and ffprobe are installed, they read the SRT with the cues and times it was written with.

## Using tsubu with other tools

Every frame is a function of `t` alone, so any tool with its own clock can drive tsubu. Turn the
tool's time into seconds and render that frame. For a frame counter, `t = from + frame / fps`,
computed from the frame number each time rather than added up. Then either write
`s.htmlAt(t)` into an element, which needs no layout and leaves nothing behind from the previous
frame, or call `s.apply(root, t)` on a drawn sentence. `examples/tsubu-frames.js` holds that
arithmetic (`TsubuFrames.timeAt`, `frameCount`, `span` and `htmlAtFrame`), and the tests run it in
Node against `htmlAt`.

- **HTML frame engines.** [`examples/remotion/`](examples/remotion/) is a Remotion composition
  that renders `htmlAt` at `useCurrentFrame()` and `useVideoConfig().fps`.
  [`examples/hyperframes/`](examples/hyperframes/) is a HyperFrames composition that registers a
  frame source whose `render(sourceTime)` writes `htmlAt`. Both follow their engine's
  documentation, which each folder's README cites, but neither has been run against a live
  engine. The tests check that the Remotion files parse and that the HyperFrames page draws
  `htmlAt(t)` for any time, against a stand-in for the runtime.
- **Video editors.** Most editors import subtitle files: SRT nearly everywhere, ASS in tools built
  on libass (Aegisub, mpv, ffmpeg's `ass` filter), and WebVTT in web players. Only ASS and WebVTT
  carry the per-segment highlight. To burn the sentence into the picture with tsubu's own look,
  record frames as in [Recording video](#recording-video) and lay the video over your footage.
- **PowerPoint and other slide tools.** Slides cannot run tsubu's script. Record a video with
  `examples/capture-frames.py`, join the frames with the ffmpeg command it prints, and insert the
  video into the slide.

## Accessibility

- **Forced colours.** In forced-colours mode (Windows contrast themes and the like) browsers
  replace backgrounds, which would leave the segment being spoken looking like every other. tsubu keeps a highlight on that segment alone, in the user's own colours for
  selected text (`Highlight` and `HighlightText`); its furigana take `CanvasText`, since they sit
  on the page. Everything else is left to the browser.
- **Screen readers.** A reading is read after its base by default (Chromium exposes
  「雨 あめ が 降る」). With `options.announceRuby: false`, every `<rt>` gets `aria-hidden="true"`,
  so the sentence is read once; the readings are still drawn and still switch. Hidden furigana
  are never read, since they are `visibility: hidden`.
- The segment being spoken carries `aria-current="true"`, and segments on other pages are hidden
  from assistive technology along with the page (see [Paging by t](#paging-by-t)).

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
  - Balanced lines: WebKit does not apply `text-wrap: balance` to inline content that holds
    absolutely positioned boxes (each segment's highlight and underline), so lines break greedily.
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
    `inline-block` (see [Vertical writing](#vertical-writing)). WebKit also takes the font's whole
    content area into the line of a base that has a reading, whatever the line height, and sets
    the reading past it; the segment's line is 2em across to hold it, and the column grows only
    as far as the reading needs.
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

## Files

| File | What |
|---|---|
| `tsubu.js` | the library: a classic script that defines `Tsubu`, or `module.exports` in Node |
| `tsubu.css` | the styles; everything adjustable is a custom property |
| `tsubu-export.js` | optional: WebVTT, ASS karaoke and SRT subtitles from the same input |
| `tsubu.mjs`, `tsubu-export.mjs` | the same objects as ES modules, with no code of their own |
| `*.d.ts`, `*.d.mts` | TypeScript declarations, checked against the scripts by `tests/test_package.py` and `tests/types` |
| `package.json` | the npm package: its exports, the files it publishes, the pinned TypeScript |
| `docs/agents/` | the versioned guide for agents preparing tsubu's input, with its validator (also in the package) |
| `examples/` | recording video: PNG frames through Playwright, HTML frames from Node; `tsubu-frames.js`, the frame arithmetic, with Remotion and HyperFrames examples |
| `site/` | the project's website: a home page whose film is drawn from `t`, getting started, a guide, the API reference, a playground and a gallery, in English and 简体中文. The pages load the library from sibling files (symlinks in the checkout), so they open straight from disk |
| `demo/index.html` | a demo with a time slider, a furigana switch, a theme picker, a dialogue and a fluid, paged frame; accepts `?t=seconds&ruby=off&theme=dark&frame=320&lines=2` |
| `tests/` | the test suite (pytest; Node for the state, Playwright for the layout, in Chromium, Firefox or WebKit) |
| `.github/workflows/` | CI on every push; on a version tag, the tests, then `npm publish` with provenance, then the site on GitHub Pages |
| `assets/` | the logo |

## Licence

MIT; see [LICENSE](LICENSE). Planned work is in [ROADMAP.md](ROADMAP.md), changes in
[CHANGELOG.md](CHANGELOG.md).
