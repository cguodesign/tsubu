# tsubu in HyperFrames

**Rendered with HyperFrames 0.8.181 on 2026-10-20** (macOS, arm64), as described under
[Checked against HyperFrames](#checked-against-hyperframes). HyperFrames is not installed in this
repository, and the test suite does not run it: `tests/test_examples.py` loads `index.html` in
Chromium with a stand-in for the one runtime call it makes,
`window.__hyperframes.registerFrameSource`. It checks that the page registers a frame source on the
right host, and that `render(sourceTime)` draws `htmlAt(t)` for any time, in any order.

## The idea

HyperFrames renders an HTML composition frame by frame in headless Chrome. Code that is already a
function of time can register as a *frame source*: HyperFrames calls its `render(sourceTime)` with
the time in seconds since the host element's start, for every frame and in any order, and waits
for `ready` before the first capture. tsubu's frames depend on time alone, so `render` writes
`s.htmlAt(from + sourceTime)` whole into the host. No GSAP timeline is needed.

| File | What |
|---|---|
| `index.html` | the composition: a 1920 x 1080 root at 30 fps, one host element and the script that registers it |
| `tsubu.js`, `tsubu.css`, `tsubu-frames.js` | links to the repository's files (symlinks, as in `site/`) |

The root's `data-duration` (3.6 s) is the sentence's span (2.6 s) plus 0.5 s before and after.
HyperFrames reads it before any script runs, so it is written into the HTML rather than computed.
`TsubuFrames.frameCount(sentence, fps, 0.5)` gives the same length in frames. The root and the host
carry `data-no-timeline`, because neither registers a GSAP timeline.

Opened straight from disk, outside HyperFrames, the page shows one frame: `index.html?t=1.4`
shows the frame 1.4 s into the video.

## Using it

Copy `index.html` and the three files it loads into a HyperFrames project (or render this folder
as it is: the links are followed). Then:

```sh
npx hyperframes lint
npx hyperframes render --output tsubu.mp4
```

For an overlay on other footage, remove the white `background` from `#root` and render with
`--format webm` or `--format mov`, which keep transparency.

## Checked against HyperFrames

With HyperFrames 0.8.181, `npx hyperframes lint` and `npx hyperframes render` were run on this
folder, rendering MP4 and PNG frames, with the GPU and without it (`--no-browser-gpu`):

- **The frame source is registered.** `window.__hyperframes` exists when the script at the end of
  `<body>` runs, and the renderer reports the registered frame source. The MP4 is 1920 x 1080 at
  30 fps, 108 frames, 3.6 s, as `data-duration` and `data-fps` say.
- **Every frame is the right one.** Each of the 108 PNG frames was compared with `htmlAt(t)` for
  its own time, drawn in the same Chrome build: each is closest to its own time, gaps between
  segments included. The pixels are not identical: glyph edges are anti-aliased differently in
  HyperFrames' capture, with the GPU or without, while every character and highlight is in the
  same place.
- **The host needs no `class="clip"`**, and the font requested through `ready` is drawn from the
  first frame.
- **Symlinks are followed.** Rendering this folder with its links gives the same frames as
  rendering copies of the files.
- **Lint** reports two `negative_z_index` warnings and no errors. They are about the highlight's
  band and the plate, which `tsubu.css` puts at `z-index: -1` inside `.tsubu`, and `.tsubu` sets
  `isolation: isolate`, the fix the warning suggests; the renders show the highlight.

Two things about the CLI itself: it sends anonymous usage telemetry unless `HYPERFRAMES_NO_TELEMETRY=1`
or `DO_NOT_TRACK=1` is set, and it downloads its own `chrome-headless-shell` unless
`HYPERFRAMES_BROWSER_PATH` names one already installed (the one Playwright installs works). For
identical renders on every machine, HyperFrames recommends `--docker`, which pins the fonts and the
browser.

## Sources

Each was read on 2026-10-19:

- The repository (what HyperFrames is, the CLI, the licence): https://github.com/heygen-com/hyperframes
- HeyGen's overview: https://developers.heygen.com/hyperframes-overview
- Frame sources (`window.__hyperframes.registerFrameSource`, `element`, `ready`, `render(sourceTime, signal)`, `dispose`, `data-no-timeline`): https://hyperframes.heygen.com/guides/frame-sources
- Compositions (the root, inline nested compositions, scoped styles, asset paths): https://hyperframes.heygen.com/concepts/compositions
- HTML schema reference (a minimal composition, the root's attributes, `data-duration` read before scripts run): https://hyperframes.heygen.com/reference/html-schema
- Deterministic rendering (`time = floor(frame) / fps`, no wall clock, frames in any order): https://hyperframes.heygen.com/concepts/determinism
- Frame adapters (the lifecycle the renderer follows): https://hyperframes.heygen.com/concepts/frame-adapters
- Fonts for script-created text (`document.fonts.load()`): https://hyperframes.heygen.com/guides/gsap-animation
- Rendering (`data-fps`, `npx hyperframes render`, formats, transparency, Docker): https://hyperframes.heygen.com/guides/rendering
