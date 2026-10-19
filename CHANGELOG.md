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
