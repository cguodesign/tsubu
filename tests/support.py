"""Shared pieces of the test suite: the example sentences and a way to run the library in Node.

The sentences are ordinary ones written for these tests. Their times are invented to exercise the
contract (gaps, boundaries, a second line), not measured from any recording.
"""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tsubu.js"
STYLES = ROOT / "tsubu.css"
DEMO = ROOT / "demo" / "index.html"

# How far two text boxes may reach into each other across the lines (or columns) before they
# overlap. Firefox rounds the ascent and the descent of a text box up to whole pixels (measured:
# 20px for Hiragino Sans at 18.18px, where Chromium gives 18px), and from Firefox 153 it sets a
# reading by the font's own metrics rather than on its base's rounded box. At a fractional font
# size a reading's box then reaches up to 1.4px into its base's (measured), with the glyphs as far
# apart as in Chromium.
def block_slack(engine):
    return 2 if engine == "firefox" else 1


def seg(*parts, start=None, end=None, punct=False):
    """A segment: each part is a plain string or a (text, ruby) pair."""
    made = {"parts": [{"text": p} if isinstance(p, str) else {"text": p[0], "ruby": p[1]} for p in parts]}
    if punct:
        made["kind"] = "punct"
    if start is not None:
        made["start"] = start
    if end is not None:
        made["end"] = end
    return made


# けさ、古い本屋で面白い地図を買いました。 ("This morning I bought an interesting map at an old
# bookshop.") Every segment is timed; there is a gap after the comma and another before 面白い.
TIMED = {"segments": [
    seg("けさ", start=0.0, end=0.5),
    seg("、", punct=True),
    seg(("古", "ふる"), "い", start=0.7, end=1.0),
    seg(("本屋", "ほんや"), "で", start=1.0, end=1.4),
    seg(("面白", "おもしろ"), "い", start=1.5, end=2.0),
    seg(("地図", "ちず"), "を", start=2.0, end=2.5),
    seg(("買", "か"), "いました", start=2.5, end=3.5),
    seg("。", punct=True),
]}

# 先週、東京で英語の授業を受けました。 ("Last week I took an English class in Tokyo.") Only the
# sentence as a whole is timed. Three readings (せんしゅう, とうきょう, じゅぎょう) are wider than
# their two kanji; えいご and う are not.
WHOLE = {"start": 4.0, "end": 6.0, "segments": [
    seg(("先週", "せんしゅう")),
    seg("、", punct=True),
    seg(("東京", "とうきょう"), "で"),
    seg(("英語", "えいご"), "の"),
    seg(("授業", "じゅぎょう"), "を"),
    seg(("受", "う"), "けました"),
    seg("。", punct=True),
]}

# 駅の前の小さな店では、毎朝六時から焼きたてのパンが売られています。 ("At the small shop in front
# of the station, fresh bread is sold from six every morning.") Long enough to take two lines in
# the layout tests, so that the second line has furigana too.
LONG = {"segments": [
    seg(("駅", "えき"), "の", start=0.0, end=0.4),
    seg(("前", "まえ"), "の", start=0.4, end=0.8),
    seg(("小", "ちい"), "さな", start=0.8, end=1.2),
    seg(("店", "みせ"), "では", start=1.2, end=1.7),
    seg("、", punct=True),
    seg(("毎朝", "まいあさ"), start=1.8, end=2.2),
    seg(("六時", "ろくじ"), "から", start=2.2, end=2.7),
    seg(("焼", "や"), "きたての", start=2.7, end=3.2),
    seg("パンが", start=3.2, end=3.5),
    seg(("売", "う"), "られて", start=3.5, end=4.0),
    seg("います", start=4.0, end=4.5),
    seg("。", punct=True),
]}


# The colour of the highlight's band behind a segment, which the stylesheet paints as a one-colour
# gradient on the segment's ::before; the band's background colour (none) when the segment is not
# current. A JavaScript function, to be put into a page's own script.
BAND_COLOUR = """((el) => { const s = getComputedStyle(el, "::before"), image = s.backgroundImage;
  return image === "none" ? s.backgroundColor : image.slice(image.indexOf("(") + 1, image.indexOf("),") + 1); })"""


NODE_RUNNER = r"""
const lib = require(process.argv[1]);
const job = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = { version: lib.version, keys: Object.keys(lib), frozen: Object.isFrozen(lib) };
try {
  const s = lib.sentence(job.input, job.options);
  out.html = s.html;
  out.timing = s.timing;
  out.states = job.times.map((t) => { try { return s.stateAt(t); } catch (e) { return { error: e.message }; } });
} catch (e) {
  out.error = e.message;
}
process.stdout.write(JSON.stringify(out));
"""


def run_library(sentence, times=(), options=None):
    """What the library makes of a sentence, and its state at each t, computed in Node."""
    node = shutil.which("node")
    assert node, "the state tests need Node on PATH"
    job = {"input": sentence, "options": options or {}, "times": list(times)}
    done = subprocess.run([node, "-e", NODE_RUNNER, str(SCRIPT)], input=json.dumps(job), capture_output=True,
                          text=True, encoding="utf-8", timeout=30, check=True)
    return json.loads(done.stdout)
