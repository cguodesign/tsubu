# Roadmap

This is a plan, not a promise: the order may change and items may be dropped. Version numbers
are left out on purpose.

## Principles every step keeps

- **Every frame is a function of `t`.** `stateAt(t)` stays pure and `apply(root, t)` draws only
  what it returns; the library has no `requestAnimationFrame`, no timers, no CSS transitions (a
  caller's own playback loop is the caller's). Live playback and frame-by-frame capture draw the
  same thing.
- **No segmentation, no estimated times.** Segments and times come from the caller; a partly timed
  sentence is refused.
- **Switching an annotation layer never moves a character**, and a test that measures the page in
  a real browser guards it.
- **No dependencies, and the script still loads from `file://`.**
- **One sentence.** Bubbles, cameras and the arrangement of several sentences stay with the caller.

## Done: loanword origins

- Loanwords' origins are drawn **over the text**, in the furigana's row, which a loanword in
  katakana leaves free, rather than under it as first planned: the source word, its language code
  and 和製 for a pseudo-loanword (*wasei-eigo*), switched on and off on their own without moving any
  character. A loanword written in kanji keeps its furigana and has no origin drawn. See
  [Loanword origins](docs/guide.md#loanword-origins) in the guide.
- **tsubu only draws them; the caller supplies the data**, and tsubu bundles no dictionary. One
  possible source is the `lsource` element of [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html);
  JMdict is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) by the
  Electronic Dictionary Research and Development Group, and **anyone who uses that data must give
  attribution** as the [EDRDG licence](https://www.edrdg.org/edrdg/licence.html) requires.
- Where the data has no entry, nothing is shown; the library never guesses an origin.

## Later

- A character-by-character wipe within a segment, once the input can carry per-character times.
