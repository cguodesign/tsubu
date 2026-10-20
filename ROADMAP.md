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

## Later

- A character-by-character wipe within a segment, once the input can carry per-character times.
