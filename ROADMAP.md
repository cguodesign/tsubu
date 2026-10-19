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

## Later

- An npm package with three forms: the classic script, an ES module and TypeScript declarations
  (`.d.ts`).
- The demo published on GitHub Pages.
- The layout tests run in Firefox and WebKit as well as Chromium.
- `<rp>` fallback parentheses in the output.
- Adapters that turn other formats into tsubu's input: kuroshiro's furigana output, Remotion
  caption data, and WebVTT cues with timestamps.
- A character-by-character wipe within a segment, once the input can carry per-character times.
