"""Renders one tsubu sentence to numbered PNG frames, one per video frame, in headless Chromium.

    python examples/capture-frames.py SENTENCE.json OUT_DIR [--fps 30] [--width 1280] [--height 720]
                                      [--theme media] [--motion appear] [--pad 0.5]

Every frame is drawn by apply(root, t) at that frame's time, on a fresh copy of the sentence, so
frames can be rendered in any order, or in parallel, and come out the same, pixel for pixel. It prints an ffmpeg command that joins the
frames and the audio into a video; it does not run it.

Needs Python 3.9+, Playwright and its Chromium (python -m pip install playwright, then
python -m playwright install chromium), and a Japanese font on the system. The sentence's times
come from you: tsubu estimates none.
"""

import argparse
import json
import math
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent.parent

PAGE = """<!doctype html><html lang="ja"><head><meta charset="utf-8">
<link rel="stylesheet" href="{css}">
<style>
  html, body {{ margin: 0; height: 100%; }}
  body {{ display: grid; place-items: end center; background: {background};
         font-family: "Hiragino Sans", "Noto Sans JP", "Noto Sans CJK JP", sans-serif; }}
  .frame {{ width: 86%; margin-bottom: 7%; }}
</style></head>
<body><div class="frame tsubu-fluid" id="frame"></div><script src="{js}"></script></body></html>"""


def frame_times(sentence, fps, pad):
    """The time of every frame, from `pad` seconds before the first segment to `pad` after the last."""
    times = [s[k] for s in sentence["segments"] for k in ("start", "end") if k in s]
    times += [sentence[k] for k in ("start", "end") if k in sentence]
    if not times:
        raise SystemExit("the sentence has no times: give it a start and end, or every segment its own")
    first, last = min(times) - pad, max(times) + pad
    # floor with a little room, so that 3.0000000000000004 s at 10 fps is 30 frame steps, not 31
    return [first + i / fps for i in range(math.floor((last - first) * fps + 1e-6) + 1)]


def render(sentence, out, *, fps=30, width=1280, height=720, theme="media", motion=None, pad=0.5, order=None, browser=None):
    """Writes frame_00000.png ... into `out` and returns their paths. `order` renders the frames in
    another order (a list of frame indexes), which must not change a single pixel. `browser` is a
    Playwright Chromium to use instead of launching one."""
    out.mkdir(parents=True, exist_ok=True)
    times = frame_times(sentence, fps, pad)
    page_file = out / "page.html"
    background = "linear-gradient(160deg, #fde68a, #f97316 45%, #1e3a8a)" if theme == "media" else "#ffffff" if theme == "light" else "#0f172a"
    page_file.write_text(PAGE.format(css=(HERE / "tsubu.css").as_uri(), js=(HERE / "tsubu.js").as_uri(), background=background),
                         encoding="utf-8")
    options = {"theme": theme, **({"motion": motion} if motion else {})}
    paths = [out / f"frame_{i:05d}.png" for i in range(len(times))]
    if browser is None:
        with sync_playwright() as playwright:
            launched = playwright.chromium.launch(headless=True)
            try:
                draw(launched, page_file, sentence, options, times, paths, order, width, height)
            finally:
                launched.close()
    else:
        draw(browser, page_file, sentence, options, times, paths, order, width, height)
    page_file.unlink()
    return paths


def draw(browser, page_file, sentence, options, times, paths, order, width, height):
    page = browser.new_page(viewport={"width": width, "height": height})
    try:
        page.goto(page_file.as_uri())
        page.evaluate("""([input, options]) => {
          window.S = Tsubu.sentence(input, options);
          document.getElementById("frame").innerHTML = S.html;
          return document.fonts.ready.then(() => true);
        }""", [sentence, options])
        for i in (order if order is not None else range(len(times))):
            # A fresh copy of the sentence for every frame: then Chromium paints the whole of it
            # anew. Reusing one and only applying t is the same state, but Chromium repaints only
            # what changed, and where a highlight's rounded corner lies over the translucent plate
            # a few edge pixels then depend on which frame came before.
            page.evaluate("""(t) => {
              const frame = document.getElementById("frame");
              frame.innerHTML = S.html;
              S.apply(frame.querySelector(".tsubu"), t);
            }""", times[i])
            page.screenshot(path=str(paths[i]))
    finally:
        page.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sentence", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--theme", default="media", choices=["light", "dark", "media"])
    parser.add_argument("--motion", default=None)
    parser.add_argument("--pad", type=float, default=0.5, help="seconds before the first and after the last segment")
    args = parser.parse_args()
    sentence = json.loads(args.sentence.read_text(encoding="utf-8"))
    paths = render(sentence, args.out, fps=args.fps, width=args.width, height=args.height, theme=args.theme,
                   motion=args.motion, pad=args.pad)
    print(f"{len(paths)} frames in {args.out}")
    print("Join them with your audio (which must start at the first frame's time):")
    print(f"  ffmpeg -framerate {args.fps} -i {args.out / 'frame_%05d.png'} -i AUDIO -c:v libx264 -pix_fmt yuv420p -shortest out.mp4")


if __name__ == "__main__":
    main()
