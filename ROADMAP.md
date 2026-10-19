# Roadmap

This is a plan, not a promise: the order may change and items may be dropped. Version numbers
are left out on purpose.

## Principles every step keeps

- **Every frame is a function of `t`.** `stateAt(t)` and `apply(root, t)` stay pure; no
  `requestAnimationFrame`, no timers, no CSS transitions. Live playback and frame-by-frame capture
  draw the same thing.
- **No segmentation, no estimated times.** Segments and times come from the caller; a partly timed
  sentence is refused.
- **Switching an annotation layer never moves a character**, and a test that measures the page in
  a real browser guards it.
- **No dependencies, and the script still loads from `file://`.**
- **One sentence.** Bubbles, cameras and the arrangement of several sentences stay with the caller.

## Theming presets and contrast checks

- Gather the colour properties into a named token set (text, past, current, future, underline,
  furigana, highlight background, highlight underline), one group per state.
- Ship a few presets: light background, dark background, and text over an image or video.
- Optional per-speaker colours for dialogue (speaker A, speaker B).
- An automatic contrast check: every preset and every state is measured against a WCAG-based
  threshold that is part of the library's configuration; a preset below it fails the tests.
- A changed colour never moves a character (tested).

## Multi-line layout and responsiveness

- Line breaks stay between segments; add Japanese line-breaking rules (small kana, the long-vowel
  mark and closing punctuation not at the start of a line), relying on the browser where it can and
  documenting where it cannot.
- **Balanced lines**: when a sentence takes several lines, keep their lengths close, so that the
  last line is not a single segment.
- **Responsive to the container**: container queries adjust size and spacing to the container's
  width, between a minimum and a maximum, with every step configurable. Targets include narrow
  speech bubbles on phone-sized layouts as well as wide 16:9 frames.
- **When it does not fit**: a maximum number of lines; beyond it the sentence is **paged by `t`**
  (the page that contains the current segment is shown). Still a pure function of `t`: no
  scrolling, no estimates.
- Tests over a grid of widths and sentence lengths: nothing overflows or overlaps, furigana are
  not clipped, switching furigana does not reflow.

## Vertical writing

- Segments, furigana (to the right of the characters), side lines in place of underlines, and the
  highlight under `writing-mode: vertical-rl`, for uses such as vertical title cards and signs.
- Digits and Latin letters: short runs upright with `text-combine-upright`, longer runs rotated.
- The shape and position of punctuation, brackets and the long-vowel mark in vertical text.
- The same guarantees as horizontal text: switching furigana does not reflow, every frame is a
  function of `t`. Chromium first; differences in Firefox and Safari recorded.

## Loanword-origin gloss layer

- An optional second annotation layer for loanwords: the source word, its language code and
  whether it is a pseudo-loanword coined in Japanese (*wasei-eigo*), drawn on the opposite side
  from the furigana (below in horizontal text, to the left in vertical text). It can be switched on
  and off on its own, again without moving any character.
- **tsubu only draws it; the caller supplies the data.** One possible source is the `lsource`
  element of [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html), which records a loanword's
  source language, source word and a *wasei* flag. JMdict is licensed under
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) by the Electronic Dictionary
  Research and Development Group: **anyone who uses that data must give attribution** as the
  [EDRDG licence](https://www.edrdg.org/edrdg/licence.html) requires, and share-alike terms apply to
  the data. tsubu will not bundle the dictionary.
- Where the data has no entry, nothing is shown; the library never guesses an origin.

## Animation presets and a guide for agents and templates

- A set of **named, deterministic presets**, each a pure function of `t` with configurable
  parameters. First candidates: segments appearing one by one, character-by-character progress
  within a segment (needs per-character times), the underline drawing itself in, masking or
  blurring what has not been heard yet, and dimming what has been read.
- A **machine-readable preset catalogue**: each preset's name, purpose, parameters and their
  ranges, which timing it needs (sentence, segment or character) and how it degrades without it.
  Templates and agents choose from the catalogue instead of inventing motion.
- A **guide for agents and template authors**: when to use which preset, and when not to. Motion
  should show a change in what is being read, not decorate.
- Every preset gets a determinism test (the same `t` twice gives the same frame) and a demo.

## Later

- An npm package with three forms: the classic script, an ES module and TypeScript declarations
  (`.d.ts`).
- The demo published on GitHub Pages.
- The layout tests run in Firefox and WebKit as well as Chromium.
- `<rp>` fallback parentheses in the output.
- Adapters that turn other formats into tsubu's input: kuroshiro's furigana output, Remotion
  caption data, and WebVTT cues with timestamps.
- Examples for video renderers that capture frame by frame.
