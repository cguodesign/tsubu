# Changelog

All notable changes to tsubu are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Colour tokens in groups, one per state (future, current, past), each with text, furigana and
  underline colours and falling back to a base group (`--tsubu-text-color`, `--tsubu-ruby-color`,
  `--tsubu-underline-color`); the current group also has the highlight background. The existing
  property names keep working.
- Theme presets `light`, `dark` and `media` (text over an image or a video, on a translucent
  plate), selected with `options.theme` or `data-tsubu-theme` on any ancestor. `Tsubu.THEMES`.
- Colours per speaker for dialogue: `options.speaker` writes `data-speaker`, and a speaker's
  group replaces the current group. Every preset defines speakers `a` and `b`. `Tsubu.SPEAKERS`.
- A plate behind the whole sentence (`--tsubu-plate-bg`, `--tsubu-plate-spread`,
  `--tsubu-plate-radius`), drawn as one positioned layer that takes no room.
- Contrast checking: the thresholds `Tsubu.CONTRAST` (after WCAG 2.2: 4.5 for text and furigana,
  3 for the underline and the highlight), `Tsubu.contrast()` for the ratio of two colours, and
  `Tsubu.checkContrast(root, options)`, which measures a drawn sentence in the browser in every
  state against the theme's `--tsubu-backdrop`, a given backdrop, or the page.
- Tests: every preset and speaker meets the thresholds in every state; a colour below its
  threshold is reported; changing the theme or the speaker moves no character.
- The demo has a theme picker, a dialogue with two speakers and each card's contrast result.
- Japanese line-breaking rules: segments that may not be parted at a line break (one that begins
  with a closing mark, the long-vowel mark or a small kana, or follows an opening bracket) share a
  nowrap `tsubu-unit`, and a line breaks only between units. The HTML gains that unit element.
- Balanced lines with `text-wrap: balance`, changeable with `--tsubu-wrap`.
- A size that follows the container: inside `.tsubu-fluid`, the font size is the container's width
  divided by a number of characters per line, between `--tsubu-size-min` and `--tsubu-size-max`,
  in three steps (narrow, medium, wide) whose values are all configurable.
- Paging by `t`: beyond `--tsubu-max-lines` (or a step's own maximum), `apply` shows only the page
  that holds the segment being spoken, and returns `page` and `pages`.
- Tests over a grid of container widths and sentence lengths: nothing overflows or overlaps,
  furigana are not clipped, switching them does not reflow, and the line-breaking rules hold;
  and tests of balancing, the fluid size and paging.
- The demo has a fluid frame with a width slider and a maximum number of lines.
- Forced colours: the segment being spoken keeps a highlight in the system colours `Highlight`
  and `HighlightText`, where it used to vanish with the background and box-shadow.
- `options.announceRuby: false` hides every reading from screen readers (`aria-hidden`), so the
  sentence is read once.
- `htmlAt(t)` on a sentence: the frame at `t` as HTML without a page, the same as `html` after
  `apply(root, t)`, for servers and renderers that take HTML.
- Motion presets `appear`, `mask`, `blur` and `underline-draw`, chosen with `options.motion` or
  `data-tsubu-motion`, each drawn from the state `apply` writes, and the catalogue
  `Tsubu.MOTIONS` (purpose, timing needed, behaviour without it, parameters, reduced motion), with
  a guide to choosing motion for agents and template authors.
- Revealing on the caller's events: `Tsubu.setRevealed(root, which)` shows segments a preset hides
  while unheard, whatever `t` is, `htmlAt(t, { revealed })` renders the same, and
  `Tsubu.segmentOf(node)` tells a click handler which segment was hit.
- `tsubu-export.js`: `TsubuExport.toWebVTT` (one cue with `<c.tsubu-seg>` class spans, `<ruby>`
  readings and strictly increasing cue timestamps), and `toASS` / `toASSScript` (`\k` karaoke with
  drift-free centisecond rounding, readings inline or omitted, and override braces and backslashes
  written in full-width). Input is checked by `Tsubu.sentence()`, and a sentence without times is
  refused.
- Examples for recording video: `examples/capture-frames.py` (PNG frames through Playwright, the
  same pixels in any frame order) and `examples/frames-from-node.mjs` (HTML frames with `htmlAt`).
- `TsubuExport.toSRT`: a SubRip file of plain text, one cue for the sentence (`mode: "sentence"`)
  or one per spoken segment with its punctuation (`mode: "segments"`), readings inline or omitted,
  each boundary rounded to milliseconds on its own, and no tags (angle brackets, braces and
  backslashes written in full-width). Tested with exact output, rounding, refusals, and, where
  installed, ffprobe and ffmpeg reading the file.
- Using tsubu with other tools: `examples/tsubu-frames.js` (`TsubuFrames.timeAt`, `frameCount`,
  `span`, `htmlAtFrame`: frame number to `t` to `htmlAt`, tested in Node), a Remotion example and a
  HyperFrames example, each citing the engine's documentation and not yet run against a live
  engine, and a README section on frame engines, video editors and PowerPoint.
- Vertical writing: `options.writing: "horizontal" | "vertical"` (`data-tsubu-writing`, also on
  an ancestor). Columns run right to left, furigana sit at the right, each segment has a side line
  at its left, and the ruby reserve sits at the right of the first column. `underline-draw` draws
  the side line from the top, and `htmlAt` marks the same upright runs.
- Short runs of half-width digits and letters are set upright with `text-combine-upright`
  (`options.combineUpright`, 0–4, default 2); longer runs are rotated.
- Paging by `t` counts columns in vertical text; `checkContrast` measures across the column.
- Fluid vertical text is sized by the container's height (`container-type: size`, `cqh`, steps by
  height).
- `tsubu.css` uses logical properties for the ruby reserve and the underline (no change in
  horizontal text).
- A vertical card in the demo, and `tests/test_vertical.py`.
- Segment `id` and `tags`, written as `data-id` and `data-tags` for the caller to find and style
  segments by, and `span(i)` and `find(id)` on a sentence, for click-to-seek.
- `Tsubu.checkFit(root, options)`: whether a drawn sentence fits its container, measured where
  it is drawn: overflow, units longer than a line, clipped furigana, and too many lines for a
  sentence that cannot be paged; paged sentences page by page.
- `checkContrast` counts opacity on a layer, and checks every segment revealed and with its
  furigana on, so every colour that can be drawn is measured.
- The website in `site/`: a home page with a film drawn frame by frame from `t` and a furigana
  loupe, getting started, a guide with a live example per section, the API reference (checked
  against the README and the library by a test), a playground with `checkContrast` live, and a
  gallery of every theme, motion preset and writing mode, in English and 简体中文. Every page is
  tested for errors, horizontal scroll at phone width and colour contrast.
- The browser tests run in Firefox and WebKit as well as Chromium: `--engine firefox|webkit`
  (default `chromium`) and `--engine-executable` for another build; `capture-frames.py` takes
  `--engine` too. Each limitation of an engine is an expected failure there alone, with its
  reason; the README's Browser support says what holds where. Measured in Firefox 139 and 153
  (the `engine_version` fixture gives a test the browser's major version).
- A versioned guide for agents, `docs/agents/segmenting.md` (guide 1.0.0, verified 2026-10-19):
  bunsetsu from GiNZA or KNP/KWJA (or merged from SudachiPy, MeCab with UniDic, kuromoji.js),
  readings from the analyser on the kanji only, times from WhisperX, the Montreal Forced Aligner
  or a speech synthesiser's timing, never estimated, and the checks before use. With a
  dependency-free validator, `docs/agents/validate.mjs`, a hand-made worked example in
  `docs/agents/example/`, and `tests/test_agent_guide.py`.

### Changed

- The highlight and the underline are drawn from the em box of the text, not from the segment's
  box, which is the font's content area: the highlight is a positioned layer behind each segment
  (its `::before`), a band 1em tall plus `--tsubu-current-spread`, and the underline sits
  `--tsubu-underline-offset` below the em box. With Hiragino Sans, whose content area is its em
  box, both are drawn where they were. `checkContrast` measures the layer.
- In vertical text each segment is an `inline-block`, a line 2em across centred on the em box of
  its text, and its highlight and side line are drawn from its left edge; negative margins give
  the room back. In Chromium and Firefox every character, reading, highlight and side line is
  where it was (measured). A segment's box now takes in its reading; `apply` finds the columns
  by the segments' left edges, `checkFit` measures a vertical segment by its text, and the `blur`
  preset blurs a vertical segment's furigana once, with the segment. Without the ruby reserve,
  Chromium's first column no longer grows to hold its readings: they stick out of the sentence's
  box, as they already did in Firefox.

### Fixed

- With Noto Sans JP and other web fonts whose content area is about 1.45em (Shippori Mincho B1,
  Zen Kaku Gothic New, the rest of the Noto family), the highlight reached 0.28em above the em
  box and covered the lower half of the furigana, which `checkContrast` reported. A test draws
  every preset in a face given those metrics, horizontally and vertically.
- A line could begin with punctuation or another mark that may not start a line: Chromium breaks
  at the underline's positioned box between two segments without applying its own rules.
- In WebKit a reading wider than its base overhung the next kana while the segment's box kept its
  length, so the underlines of neighbouring segments met: `ruby-overhang: none`.
- In WebKit `checkContrast` read the highlight and the underline from computed insets that WebKit
  gives against the wrong box; it now measures them on probes that take the same geometry, and it
  checks the text against the page where the highlight does not cover it.
- Vertical text in WebKit: each segment's highlight and side line were drawn mirrored across the
  block's right edge, away from the segment, because WebKit misplaces a box positioned inside an
  inline in `vertical-rl` text. And in a font whose content area is taller than its em box
  (Shippori Mincho B1), WebKit widened every column that holds readings by the content area and
  the readings; a column now grows only for readings that would reach the characters of the next. Vertical text holds every guarantee in WebKit but balanced
  columns.

## [0.1.0] - unreleased

First version.

### Added

- `Tsubu.sentence(input, options)` renders one sentence that the caller has already cut into
  segments: each segment is an unbreakable span with its own dotted underline, a `<wbr>` lets
  lines break between segments (never before punctuation), and parts with a reading are drawn
  as `<ruby>`.
- Strict timing contract: every spoken segment timed (`"segments"`), only the whole sentence
  timed (`"sentence"`) or no times (`"none"`). Partly timed sentences, overlapping or reversed
  times, timed punctuation and malformed input are refused with an error; nothing is estimated.
- `stateAt(t)`, a pure function of `t`, and `apply(root, t)`, which writes that state as
  `data-state`, `aria-current` and `--tsubu-progress` without touching text or nodes.
- `Tsubu.setRuby(root, on)` shows or hides furigana without moving any character.
- `tsubu.css` with `--tsubu-*` custom properties for line height, furigana, underline and
  highlight; no transitions or animations.
- `Tsubu.version` and `Tsubu.STATES`.
- A demo page (`demo/index.html`) that works from `file://`.
- Tests: the state in Node, the layout measured in headless Chromium through Playwright.
- A hygiene test: no tracked file and no commit message may contain an absolute local path, or a
  term from an optional, untracked `.leakcheck.local` list.
- README in English and Simplified Chinese, and a roadmap.

### Notes

- The copyright holder in `LICENSE` is still a placeholder and must be filled in before the
  first public release.
