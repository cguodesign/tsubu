# tsubu in Remotion

**Untested against a live Remotion.** No Remotion package is installed in this repository, and
the test suite does not run Remotion. The code follows Remotion's documentation as cited below.
The tests check two things: that each file here parses as TypeScript, using Node's built-in type
stripping, and that the frame arithmetic in `../tsubu-frames.js` gives the same frames as
`htmlAt` (`tests/test_examples.py`).

## The idea

A Remotion component reads the current frame with `useCurrentFrame()` and the frame rate with
`useVideoConfig()`. tsubu's frame is a function of time alone, so the component computes
`t = from + frame / fps` and writes `s.htmlAt(t)` into a `<div>`. Frames do not depend on each
other, so Remotion can render them in any order or in parallel.

| File | What |
|---|---|
| `src/index.ts` | the entry point: `registerRoot(RemotionRoot)` |
| `src/Root.ts` | one `<Composition>`, 1920 x 1080 at 30 fps, as long as the sentence plus 0.5 s before and after |
| `src/TsubuSentence.ts` | the component: `TsubuFrames.htmlAtFrame(s, useCurrentFrame(), fps, from)` inside an `<AbsoluteFill>` |
| `src/load-font.ts` | holds the render until a Japanese font has loaded |

The components are written with `createElement` instead of JSX, so that the tests can parse them
without a JSX compiler. In a `.tsx` file they work the same as JSX.

## Using it

1. Set up Remotion as its docs describe. For an existing project, the brownfield page installs
   it with `npm i --save-exact remotion@<version> @remotion/cli@<version>`. Remotion renders React,
   so the project also needs `react` and `react-dom`.
2. The imports point into this repository (`../../../tsubu.js`, `../../../tsubu.css`,
   `../../tsubu-frames.js`, `../../sentence.json`). In your own project, copy those four files
   into `src/` and change the imports to `./`.
3. Put a Japanese font at `public/NotoSansJP-Regular.woff2`. To use the system's fonts instead,
   delete `src/load-font.ts` and its import.
4. Open the Studio or render a file:

   ```sh
   npx remotion studio examples/remotion/src/index.ts
   npx remotion render examples/remotion/src/index.ts TsubuSentence out.mp4
   ```

`tsubu.js` and `tsubu-frames.js` are plain scripts. Remotion's bundler reads their
`module.exports`, so `import Tsubu from ".../tsubu.js"` works, and TypeScript takes its types from
`tsubu.d.ts` beside it. `tsubu-frames.js` has no type declarations, which is why its import
carries `// @ts-ignore`. Importing `sentence.json` from TypeScript needs `resolveJsonModule` in
`tsconfig.json`.

## Not confirmed

- Whether the components type-check under a particular Remotion and React version. Their syntax is
  checked; their types are not.
- That `dangerouslySetInnerHTML` replaces the markup on every frame whose HTML differs. This is
  React's behaviour, not something Remotion documents.
- The exact Remotion version: the brownfield page names one, and this example uses only APIs that
  its pages document without a version note (`registerRoot`, `Composition`, `useCurrentFrame`,
  `useVideoConfig`, `AbsoluteFill`, `staticFile`, `delayRender`, `continueRender`).

## Sources

Each was read on 2026-10-19:

- `useCurrentFrame()` (frames are 0-indexed): https://www.remotion.dev/docs/use-current-frame
- `useVideoConfig()` (`fps`, `width`, `height`, `durationInFrames`): https://www.remotion.dev/docs/use-video-config
- `registerRoot()` and `<Composition>` (entry file, root, composition props): https://www.remotion.dev/docs/register-root
- `<AbsoluteFill>`: https://www.remotion.dev/docs/absolute-fill
- Importing a `.css` file, the `public/` folder and `staticFile()`: https://www.remotion.dev/docs/assets
- Loading fonts (`FontFace` with `delayRender()` and `continueRender()`): https://www.remotion.dev/docs/fonts
- Installing into an existing project, and the `studio` and `render` commands: https://www.remotion.dev/docs/brownfield
