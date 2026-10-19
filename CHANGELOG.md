# Changelog

All notable changes to tsubu are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

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
- README in English and Simplified Chinese, and a roadmap.

### Notes

- The copyright holder in `LICENSE` is still a placeholder and must be filled in before the
  first public release.
