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

- A character-by-character wipe within a segment, once the input can carry per-character times.
