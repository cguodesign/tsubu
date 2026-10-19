# tsubu in HyperFrames

**Untested against a live HyperFrames runtime.** HyperFrames is not installed in this repository,
and the test suite does not run it. The code follows HyperFrames' documentation as cited below.
`tests/test_examples.py` loads `index.html` in Chromium with a stand-in for the one runtime call it
makes, `window.__hyperframes.registerFrameSource`. It checks that the page registers a frame source
on the right host, and that `render(sourceTime)` draws `htmlAt(t)` for any time, in any order.

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

Copy `index.html` and the three files it loads into a HyperFrames project; copy the files
themselves, not the links. Then:

```sh
npx hyperframes lint
npx hyperframes render --output tsubu.mp4
```

For an overlay on other footage, remove the white `background` from `#root` and render with
`--format webm` or `--format mov`, which keep transparency.

## Not confirmed

- **When `registerFrameSource` must be called.** The docs say "before runtime initialization
  completes". The script calls it synchronously at the end of `<body>`. Whether
  `window.__hyperframes` already exists at that point was not confirmed. If the runtime adds it
  later, the page draws a single static frame instead.
- **Attributes on the host.** The frame-sources page names `data-composition-id`, `data-start`,
  `data-duration`, `data-track-index` and `data-no-timeline`. `data-width` and `data-height` are
  added as in the docs' inline nested composition. Whether the host also needs `class="clip"` was
  not confirmed.
- **Fonts.** The docs say HyperFrames waits for fonts used by markup that exists when the page
  loads, but not for faces used only by text a script creates. The page requests its font with
  `document.fonts.load()` and passes that promise as `ready`. The docs show `ready` taking an
  initialisation promise, and this follows that pattern. For identical renders on every machine,
  the docs recommend `--docker`, which pins the font set.
- **Symlinks.** Whether the preview server and renderer follow them is unknown, so copy the files.

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
