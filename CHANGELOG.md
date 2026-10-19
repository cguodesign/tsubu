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

### Fixed

- A line could begin with punctuation or another mark that may not start a line: Chromium breaks
  at the underline's positioned box between two segments without applying its own rules.

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
