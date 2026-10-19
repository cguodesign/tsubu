"""The examples run, and show that a frame depends on t alone: frames rendered in reverse order are
the same, pixel for pixel, as frames rendered in order."""

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess

import pytest

from support import ROOT

EXAMPLES = ROOT / "examples"
SENTENCE = json.loads((EXAMPLES / "sentence.json").read_text(encoding="utf-8"))


def load_capture():
    spec = importlib.util.spec_from_file_location("capture_frames", EXAMPLES / "capture-frames.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_captured_frames_are_the_same_in_any_order(tmp_path, browser):
    capture = load_capture()
    times = capture.frame_times(SENTENCE, 10, 0.2)
    assert len(times) == 31 and times[0] == pytest.approx(-0.2) and times[-1] == pytest.approx(2.8)
    shot = dict(fps=10, width=640, height=360, pad=0.2, motion="underline-draw", browser=browser)
    forward = capture.render(SENTENCE, tmp_path / "forward", **shot)
    backward = capture.render(SENTENCE, tmp_path / "backward", order=list(reversed(range(len(times)))), **shot)
    assert [digest(p) for p in forward] == [digest(p) for p in backward]
    assert not (tmp_path / "forward" / "page.html").exists()
    # and the highlight really moves: the frames are not all alike
    assert len({digest(p) for p in forward}) > 10


def test_html_frames_from_node_match_html_at(tmp_path):
    node = shutil.which("node")
    assert node
    done = subprocess.run([node, str(EXAMPLES / "frames-from-node.mjs"), str(EXAMPLES / "sentence.json"), str(tmp_path), "10"],
                          capture_output=True, text=True, encoding="utf-8", timeout=60, check=True)
    files = sorted(tmp_path.glob("frame_*.html"))
    assert len(files) == 27 and done.stdout.strip().startswith("27 frames")  # 0.0 to 2.6 s at 10 fps
    assert 'data-index="2" data-state="current"' in files[10].read_text(encoding="utf-8")  # t = 1.0: 家で
    assert "aria-current" not in files[-1].read_text(encoding="utf-8").split("<body>")[1]  # the end: nothing is current


# --- frame engines: the shared arithmetic, and the Remotion and HyperFrames examples ------------

FRAMES = EXAMPLES / "tsubu-frames.js"

FRAMES_RUNNER = r"""
const [lib, tsubu] = process.argv.slice(1).map((p) => require(p));
const jobs = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = { keys: Object.keys(lib), frozen: Object.isFrozen(lib) };
out.results = jobs.map(([name, ...args]) => {
  try {
    if (name === "htmlAt") return { value: tsubu.sentence(...args[0]).htmlAt(args[1]) };
    if (name === "htmlAtFrame" && args[0]) args[0] = tsubu.sentence(...args[0]);
    return { value: lib[name](...args) };
  } catch (e) { return { error: e.message }; }
});
process.stdout.write(JSON.stringify(out));
"""


def run_frames(*jobs):
    """Runs each (function name, *arguments) of tsubu-frames.js in Node. For htmlAtFrame the first argument is
    [input, options] for Tsubu.sentence(); ("htmlAt", [input, options], t) asks tsubu itself."""
    node = shutil.which("node")
    assert node
    done = subprocess.run([node, "-e", FRAMES_RUNNER, str(FRAMES), str(ROOT / "tsubu.js")], input=json.dumps([list(j) for j in jobs]),
                          capture_output=True, text=True, encoding="utf-8", timeout=30, check=True)
    return json.loads(done.stdout)


def frames_value(*job):
    found = run_frames(job)["results"][0]
    assert "error" not in found, found
    return found["value"]


def test_frame_n_is_from_plus_n_over_fps_without_drift():
    found = run_frames(("timeAt", 0, 30), ("timeAt", 45, 30, -0.5), ("timeAt", 108000, 30), ("timeAt", 7, 29.97, 4))
    assert found["frozen"] and sorted(found["keys"]) == ["frameCount", "htmlAtFrame", "span", "timeAt"]
    assert [r["value"] for r in found["results"]] == [0, 1.0, 3600, 4 + 7 / 29.97]
    # computed from n each time: an hour in, frame 108000 at 30 fps is exactly 3600 s


def test_a_sentence_s_span_and_its_frame_count():
    assert frames_value("span", SENTENCE) == {"start": 0, "end": 2.6}
    assert frames_value("span", {"start": 4, "end": 6, "segments": [{"parts": [{"text": "本"}]}]}) == {"start": 4, "end": 6}
    # the same count frames-from-node.mjs writes: 0.0 to 2.6 s at 10 fps, both ends included
    assert frames_value("frameCount", SENTENCE, 10) == 27
    # with half a second before and after at 30 fps: 3.6 s, so frames 0 to 108
    assert frames_value("frameCount", SENTENCE, 30, 0.5) == 109


def test_html_at_frame_is_html_at_the_frame_s_time():
    jobs = []
    for frame, fps, start in [(0, 10, 0), (10, 10, 0), (26, 10, 0), (42, 30, -0.5), (108, 30, -0.5)]:
        t = start + frame / fps
        jobs += [("htmlAtFrame", [SENTENCE], frame, fps, start), ("htmlAt", [SENTENCE], t)]
    results = [r["value"] for r in run_frames(*jobs)["results"]]
    for by_frame, by_time in zip(results[::2], results[1::2]):
        assert by_frame == by_time
    assert 'data-index="2" data-state="current"' in results[2]  # frame 10 at 10 fps, t = 1.0: 家で


def test_html_at_frame_matches_the_frames_from_node_example(tmp_path):
    node = shutil.which("node")
    subprocess.run([node, str(EXAMPLES / "frames-from-node.mjs"), str(EXAMPLES / "sentence.json"), str(tmp_path), "10"],
                   capture_output=True, text=True, encoding="utf-8", timeout=60, check=True)
    files = sorted(tmp_path.glob("frame_*.html"))
    assert len(files) == frames_value("frameCount", SENTENCE, 10)
    found = run_frames(*[("htmlAtFrame", [SENTENCE, {"theme": "light"}], i, 10) for i in range(len(files))])["results"]
    for path, html in zip(files, (r["value"] for r in found)):
        assert path.read_text(encoding="utf-8").split("<body>")[1].split("</body>")[0] == html


@pytest.mark.parametrize("job, message", [
    (("timeAt", -1, 30), "frame must be a whole number"),
    (("timeAt", 1.5, 30), "frame must be a whole number"),
    (("timeAt", 1, 0), "fps must be more than 0"),
    (("timeAt", 1, "30"), "fps must be a finite number"),
    (("timeAt", 1, 30, "0"), "from must be a finite number"),
    (("frameCount", SENTENCE, 30, -1), "pad cannot be negative"),
    (("span", {"segments": [{"parts": [{"text": "本"}]}]}), "has no times"),
    (("span", None), "must be an object"),
    (("htmlAtFrame", None, 0, 30), "Tsubu.sentence"),
])
def test_frame_arithmetic_refuses_what_it_cannot_use(job, message):
    found = run_frames(job)["results"][0]
    assert found.get("error", "").startswith("tsubu-frames: ") and message in found["error"], found


REMOTION = EXAMPLES / "remotion" / "src"

PARSE_TS = r"""
const { stripTypeScriptTypes } = require("node:module");
const { writeFileSync } = require("node:fs");
const [source, target] = process.argv.slice(1);
writeFileSync(target, stripTypeScriptTypes(require("node:fs").readFileSync(source, "utf8")));
"""


def test_the_remotion_example_parses_and_renders_html_at_the_frame_s_time(tmp_path):
    files = sorted(REMOTION.glob("*.ts"))
    assert [f.name for f in files] == ["Root.ts", "TsubuSentence.ts", "index.ts", "load-font.ts"]
    node = shutil.which("node")
    strip = subprocess.run([node, "-e", "process.exit(typeof require('node:module').stripTypeScriptTypes === 'function' ? 0 : 1)"])
    for source in files:
        text = source.read_text(encoding="utf-8")
        assert "<" + "/" not in text  # no JSX: Node's type stripping cannot read it
        if strip.returncode == 0:
            target = tmp_path / (source.stem + ".mjs")
            subprocess.run([node, "-e", PARSE_TS, str(source), str(target)], capture_output=True, text=True, timeout=30, check=True)
            done = subprocess.run([node, "--check", str(target)], capture_output=True, text=True, timeout=30)
            assert done.returncode == 0, (source.name, done.stderr)
    component = (REMOTION / "TsubuSentence.ts").read_text(encoding="utf-8")
    # the frame from Remotion's clock, the time from the frame, and the frame's HTML from tsubu
    assert "const frame = useCurrentFrame();" in component and "const { fps } = useVideoConfig();" in component
    assert "TsubuFrames.htmlAtFrame(s, frame, fps, from)" in component
    assert "dangerouslySetInnerHTML: { __html: html }" in component
    # every relative import names a file that exists
    for source in files:
        for spec in re.findall(r'^import [^"]*"(\.[^"]+)";$', source.read_text(encoding="utf-8"), re.M):
            found = (source.parent / spec)
            assert found.exists() or found.with_suffix(".ts").exists(), (source.name, spec)
    if strip.returncode != 0:
        pytest.skip("this Node has no built-in type stripping, so the files were checked for their references only")


HYPERFRAMES = EXAMPLES / "hyperframes"

# A stand-in for the one HyperFrames call the page makes: it keeps the frame source the page
# registers, so that the test can call render() as the runtime would.
FAKE_RUNTIME = """window.__hyperframes = { registerFrameSource(source) { window.__registered = source; return () => {}; } };"""


def test_the_hyperframes_example_registers_a_frame_source_that_draws_html_at_t(browser):
    html = (HYPERFRAMES / "index.html").read_text(encoding="utf-8")
    for name in ("tsubu.js", "tsubu.css", "tsubu-frames.js"):
        assert (HYPERFRAMES / name).resolve().read_bytes() == (EXAMPLES / name if name == "tsubu-frames.js" else ROOT / name).read_bytes()
    # the inline sentence is examples/sentence.json, and the root lasts its span plus PAD each side
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.add_init_script(FAKE_RUNTIME)
        page.goto((HYPERFRAMES / "index.html").as_uri())
        assert page.evaluate("() => SENTENCE") == SENTENCE
        pad = page.evaluate("() => PAD")
        span = frames_value("span", SENTENCE)
        root = page.evaluate("() => Object.assign({}, document.getElementById('root').dataset)")
        assert float(root["duration"]) == pytest.approx(span["end"] - span["start"] + 2 * pad)
        assert frames_value("frameCount", SENTENCE, int(root["fps"]), pad) == round(float(root["duration"]) * int(root["fps"])) + 1
        assert "noTimeline" in root
        registered = page.evaluate("""async () => { const s = window.__registered; await s.ready;
          return { host: s.element.id, typeOfRender: typeof s.render, hostData: Object.assign({}, s.element.dataset) }; }""")
        assert registered["host"] == "sentence" and registered["typeOfRender"] == "function"
        assert "noTimeline" in registered["hostData"] and registered["hostData"]["duration"] == root["duration"]
        # render(sourceTime) draws htmlAt(from + sourceTime), in any order
        times = [0, 0.5, 1.5, 2.0, 2.6, 3.6, 1.5, 0]
        drawn = page.evaluate("""(times) => times.map((t) => { window.__registered.render(t);
          return document.getElementById('sentence').innerHTML; })""", times)
        expected = run_frames(*[("htmlAt", [SENTENCE, {"theme": "light"}], span["start"] - pad + t) for t in times])["results"]
        parsed = page.evaluate("""(htmls) => htmls.map((h) => { const d = document.createElement('div'); d.innerHTML = h; return d.innerHTML; })""",
                               [r["value"] for r in expected])
        assert drawn == parsed
        assert drawn[2] == drawn[6] and drawn[0] == drawn[7] and len(set(drawn)) == 6
        assert 'data-index="2" data-state="current"' in drawn[2]  # 1.5 s in is t = 1.0: 家で
        assert errors == []
    finally:
        page.close()
