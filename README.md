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
  same thing.

It is one classic script (`tsubu.js`, about 10 KB) and one stylesheet (`tsubu.css`). It loads from
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
options = { ruby: true }       // optional; whether furigana start out shown (default true)
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
- an empty `segments`, `parts`, `text`, `ruby` or `lang`, an unknown `kind`, or an `options.ruby`
  that is not a boolean.

## Output

`Tsubu.sentence()` returns a frozen object:

- **`html`**: an HTML string,

  ```html
  <span class="tsubu" lang="ja" data-timing="segments" data-ruby="on">
    <span class="tsubu-seg" data-index="0">…</span><wbr><span class="tsubu-seg" data-index="1">…</span>…
  </span>
  ```

  (without the whitespace). Punctuation segments carry `data-kind="punct"`. Every segment is
  `white-space: nowrap`, so a segment is never split across lines; a `<wbr>` before each segment
  lets the line break between segments, and there is none before punctuation, so punctuation never
  starts a line. All text is HTML-escaped. The fresh HTML has no state: `apply` adds it.
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
    `aria-current="true"` on the segment being spoken.

  It never changes text and never adds or removes nodes.

Also on `Tsubu`:

- **`Tsubu.setRuby(root, on)`** shows or hides the furigana of a drawn sentence by setting the
  root's `data-ruby` to `"on"` or `"off"`.
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

| Property | Default | Meaning |
|---|---|---|
| `--tsubu-line-height` | `1.75` | line height |
| `--tsubu-ruby-reserve` | `0.3em` | room above the first line for its furigana |
| `--tsubu-ruby-size` | `0.5em` | furigana size, relative to the text |
| `--tsubu-ruby-color` | `#6b7280` | furigana colour |
| `--tsubu-ruby-weight` | `400` | furigana weight |
| `--tsubu-underline-color` | `#9ca3af` | underline colour |
| `--tsubu-underline-style` | `dotted` | underline style (any `border-style`) |
| `--tsubu-underline-width` | `0.06em` | underline thickness |
| `--tsubu-underline-offset` | `0.02em` | distance below the bottom of the segment's box |
| `--tsubu-underline-inset` | `0.12em` | inset from each end, so neighbouring underlines stay apart |
| `--tsubu-future-color` | inherited | text colour of segments not yet spoken |
| `--tsubu-past-color` | inherited | text colour of segments already spoken |
| `--tsubu-current-color` | inherited | text colour of the segment being spoken |
| `--tsubu-current-bg` | `#e5e7eb` | highlight colour |
| `--tsubu-current-spread` | `0.06em` | how far the highlight reaches past the text (a `box-shadow`, so it takes no room) |
| `--tsubu-current-radius` | `0.18em` | highlight corner radius (0 with timing `"sentence"`, so the sentence reads as one band per line) |
| `--tsubu-current-underline-color` | the underline colour | underline colour of the segment being spoken |
| `--tsubu-progress` | written by `apply` | 0 to 1; read it in your own CSS, do not set it |

States change colours, a background and a `box-shadow` only, never weight, padding or size, so a
change of state cannot move a character.

## Layout guarantees, and how they are tested

Each of these is checked by measuring the page in headless Chromium (see `tests/test_layout.py`):

- **Switching furigana moves nothing.** Hidden furigana get `visibility: hidden`, not
  `display: none`, so they keep their room: with `display: none` a word whose reading is wider than
  its base would narrow and everything after it would shift. The test records the box of every
  character, segment and reading, then switches the furigana and moves `t` back and forth, and
  requires every box to stay exactly where it was, on one line and on two.
- **Highlighting moves nothing.** Same test: boxes are compared across many values of `t`.
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
- **Lines break only between segments, never before punctuation**, at several container widths.
- **No motion.** Every element has `transition: none` and `animation: none`, and repeated
  `apply` calls produce the same attributes, text and node count.

The state logic (`tests/test_state.py`) runs `tsubu.js` itself in Node: half-open spans, gaps,
punctuation, progress, every refused input, and that `stateAt` depends on `t` alone.

## Browser support

Stated honestly:

- **Tested in Chromium only** so far (the build bundled with Playwright, Chromium 138 at the time
  of writing). Firefox and WebKit have not been run through the layout tests yet.
- `ruby-align` is needed for the "wide reading does not spread its base" guarantee. Per MDN it is
  supported from **Chrome 128** and **Safari 18.2**. In older browsers the furigana still switch
  without reflow, but a reading wider than its base spreads the base characters apart.
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
| `demo/index.html` | a demo with a time slider and a furigana switch; accepts `?t=seconds&ruby=off` |
| `tests/` | the test suite (pytest; Node for the state, Playwright Chromium for the layout) |
| `assets/` | the logo |

## Licence

MIT; see [LICENSE](LICENSE). Planned work is in [ROADMAP.md](ROADMAP.md), changes in
[CHANGELOG.md](CHANGELOG.md).
