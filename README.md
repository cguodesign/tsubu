<p align="center"><img src="assets/logo.svg" alt="tsubu" width="200"></p>

# tsubu

[English](README.md) · [简体中文](README.zh-CN.md) · [Website](https://chong.works/tsubu/) ·
[Guide](docs/guide.md) · [npm](https://www.npmjs.com/package/tsubu-js)

**tsubu** (粒, "grain", as in a grain of rice) is a tiny, dependency-free browser library that
renders exactly one Japanese sentence for read-along and language learning. The sentence arrives
already cut into segments (*bunsetsu*), and tsubu draws:

- a dotted underline under each segment;
- furigana that switch on and off **without moving any character**;
- a highlight on the segment being spoken, as a **pure function of time**: `apply(root, t)` has no
  timer, no `requestAnimationFrame` and no transition, so live playback and frame-by-frame video
  capture draw the same thing;
- themes whose contrast is measured, several lines broken by Japanese rules, vertical writing,
  motion presets, and WebVTT, ASS and SRT export.

It is one classic script (`tsubu.js`, about 21 KB unminified) and one stylesheet (`tsubu.css`),
and it loads from a `file://` page, from any web page, and from Node.

What tsubu does **not** do: split text into words, align audio to text, estimate times, play
audio, draw a speech bubble or lay out more than one sentence. Those belong to the caller.

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

From npm, where the package is named `tsubu-js` (npm refuses `tsubu` as too close to an
existing name), pinned to an exact version:

```sh
npm install --save-exact tsubu-js
```

The package holds the same files as this repository, with no build step: `tsubu.js` (the classic
script), `tsubu.css`, `tsubu-export.js`, an ES module for each script (`tsubu.mjs`,
`tsubu-export.mjs`, which only re-export the script's object) and TypeScript declarations.

```js
const Tsubu = require("tsubu-js");                     // Node, CommonJS
const TsubuExport = require("tsubu-js/export");
import Tsubu, { sentence } from "tsubu-js";            // ES modules and bundlers
import { toSRT } from "tsubu-js/export";
import "tsubu-js/tsubu.css";                           // with a bundler that handles CSS
```

From a CDN, with an exact version and [Subresource Integrity](https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity),
so the page runs only the file it was written against:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tsubu-js@0.1.0/tsubu.css"
      integrity="sha384-SlfIuFrZo0yor05+BcMvDiAP3WJ0dkZmH8a9JUHnmAUI9BGNU+oQ9dDy+5n1PKoG" crossorigin="anonymous">
<script src="https://cdn.jsdelivr.net/npm/tsubu-js@0.1.0/tsubu.js"
        integrity="sha384-KqOxfytJPFgoafKyYmfGSraqQPzpMAopz/++pPUH412E94z3r9qWDgy+b/aoryAE" crossorigin="anonymous"></script>
```

`https://unpkg.com/tsubu-js@0.1.0/tsubu.js` serves the same file. The hash of a file is
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

A segment's `parts` are pieces of text; a part with `ruby` is drawn as `<ruby>`. `kind: "punct"`
marks punctuation, which is never spoken and never timed. The times decide the sentence's
**timing**:

| `timing` | When | What lights up |
|---|---|---|
| `"segments"` | every non-punctuation segment has `start` and `end` | one segment at a time. The sentence's own span is `input.start`/`input.end` if given, otherwise from the first segment's start to the last one's end. |
| `"sentence"` | no segment has a time, the sentence has `start` and `end` | the whole sentence at once. The span is **not** divided among segments by length or by mora. |
| `"none"` | no times anywhere | nothing: the sentence can be drawn (a static preview), but `stateAt` and `apply` throw. |

tsubu never guesses: a partly timed sentence, overlapping or reversed times and malformed input
throw an `Error` whose message starts with `tsubu:`. The full contract is in the
[guide](docs/guide.md#input).

## Output

`Tsubu.sentence()` returns a frozen object with:

- `html`, the sentence as an HTML string, and `timing`;
- `stateAt(t)`, which segment is future, current or past at `t`;
- `apply(root, t)`, which writes that state onto the drawn sentence as attributes, never touching
  text or nodes; `htmlAt(t)`, the same frame as HTML, for servers and renderers;
- `span(i)` and `find(id)`, for click-to-seek.

`Tsubu` also has `setRuby`, `setRevealed`, `segmentOf`, `checkContrast`, `checkFit`, `contrast`
and the catalogues `THEMES`, `SPEAKERS`, `MOTIONS`, `CONTRAST` and `STATES`. Every name, option and
CSS custom property is in the [guide](docs/guide.md#output) and on the website's
[API page](https://chong.works/tsubu/api.html).

## What else it does

Each item links to its section of the guide:

- [**Themes and contrast**](docs/guide.md#themes-and-contrast): `light`, `dark` and `media`
  presets, colours per speaker, and `checkContrast`, which measures a drawn sentence against
  WCAG-based thresholds.
- [**Several lines**](docs/guide.md#several-lines): Japanese line-breaking rules, balanced lines, a
  size that follows the container, and paging by `t` beyond a maximum number of lines.
  `checkFit` tells whether a sentence fits where it is drawn.
- [**Vertical writing**](docs/guide.md#vertical-writing), with short half-width runs set upright.
- [**Motion and revealing**](docs/guide.md#motion-and-revealing): `appear`, `mask`, `blur` and
  `underline-draw`, each drawn from the state, and segments revealed on the caller's events.
- [**Recording video**](docs/guide.md#recording-video) frame by frame, and
  [**subtitles**](docs/guide.md#exporting-subtitles) (`tsubu-export.js`: WebVTT, ASS karaoke, SRT).
- [**Other tools**](docs/guide.md#using-tsubu-with-other-tools): frame engines such as Remotion and
  HyperFrames, video editors, PowerPoint.
- [**Accessibility**](docs/guide.md#accessibility): forced colours, and readings that screen
  readers can skip.

## For agents

tsubu takes input that is already segmented, with readings and real times.
[`docs/agents/segmenting.md`](docs/agents/segmenting.md) is a versioned guide for AI agents that
prepare it: bunsetsu from a morphological analyser, readings on the kanji, times from forced
alignment or a speech synthesiser, and the checks before use, with a dependency-free validator:

```sh
node docs/agents/validate.mjs input.json --text sentence.txt
```

## Guarantees and browser support

Every frame is a function of `t`; switching furigana, the highlight, the theme or the speaker moves
no character; lines break only between segments and by the line-breaking rules; nothing overflows
over a grid of widths and sentence lengths. Each of these is measured in a real browser, in
Chromium, Firefox and WebKit. All hold in Chromium; Firefox and WebKit do not balance lines in
every case. Details, and how each guarantee is tested, are in [docs/testing.md](docs/testing.md).

## Development

```sh
python -m pip install -r requirements-dev.txt
python -m playwright install chromium firefox webkit
npm ci
python -m pytest -q                    # add --engine firefox or --engine webkit
```

Requirements and options are in [docs/testing.md](docs/testing.md#running-the-tests). GitHub
Actions runs the suite on every push; a version tag publishes to npm with provenance and deploys
the site.

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
| `docs/guide.md` | the guide: input, output, CSS custom properties and every feature, in detail |
| `docs/testing.md` | the layout guarantees, how each is measured, browser support, running the tests |
| `assets/` | the logo |

## Licence

MIT; see [LICENSE](LICENSE). Planned work is in [ROADMAP.md](ROADMAP.md), changes in
[CHANGELOG.md](CHANGELOG.md).
