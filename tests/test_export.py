"""The exporters in tsubu-export.js: WebVTT and ASS karaoke.

The exact output is computed by running tsubu-export.js in Node. Chromium then parses the WebVTT
as a <track>, and, when ffmpeg is installed, libass renders the ASS script.
"""

import base64
import json
import re
import shutil
import subprocess

import pytest

from support import ROOT, SCRIPT, TIMED, WHOLE, seg

EXPORT = ROOT / "tsubu-export.js"

NODE_RUNNER = r"""
const lib = require(process.argv[1]);
const jobs = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = { keys: Object.keys(lib), frozen: Object.isFrozen(lib) };
out.results = jobs.map(([name, input, options]) => {
  try { return { value: lib[name](input, options) }; } catch (e) { return { error: e.message }; }
});
process.stdout.write(JSON.stringify(out));
"""


def run_export(*jobs):
    """Runs each (function name, input, options) in Node and returns its value or error."""
    node = shutil.which("node")
    assert node, "the export tests need Node on PATH"
    done = subprocess.run([node, "-e", NODE_RUNNER, str(EXPORT)], input=json.dumps([list(j) for j in jobs]),
                          capture_output=True, text=True, encoding="utf-8", timeout=30, check=True)
    return json.loads(done.stdout)


def value(name, sentence, options=None):
    found = run_export((name, sentence, options))["results"][0]
    assert "error" not in found, found
    return found["value"]


def error(name, sentence, options=None):
    found = run_export((name, sentence, options))["results"][0]
    assert found.get("error", "").startswith("tsubu: "), found
    return found["error"]


TIMED_CUE = ("<c.tsubu-seg>けさ</c><c.tsubu-seg.punct>、</c>"
             "<00:00:00.700><c.tsubu-seg><ruby>古<rt>ふる</rt></ruby>い</c>"
             "<00:00:01.000><c.tsubu-seg><ruby>本屋<rt>ほんや</rt></ruby>で</c>"
             "<00:00:01.500><c.tsubu-seg><ruby>面白<rt>おもしろ</rt></ruby>い</c>"
             "<00:00:02.000><c.tsubu-seg><ruby>地図<rt>ちず</rt></ruby>を</c>"
             "<00:00:02.500><c.tsubu-seg><ruby>買<rt>か</rt></ruby>いました</c><c.tsubu-seg.punct>。</c>")

WHOLE_CUE = ("<c.tsubu-seg><ruby>先週<rt>せんしゅう</rt></ruby></c><c.tsubu-seg.punct>、</c>"
             "<c.tsubu-seg><ruby>東京<rt>とうきょう</rt></ruby>で</c><c.tsubu-seg><ruby>英語<rt>えいご</rt></ruby>の</c>"
             "<c.tsubu-seg><ruby>授業<rt>じゅぎょう</rt></ruby>を</c><c.tsubu-seg><ruby>受<rt>う</rt></ruby>けました</c>"
             "<c.tsubu-seg.punct>。</c>")

TIMED_KARAOKE = "{\\k50}けさ、{\\k20}{\\k30}古い{\\k40}本屋で{\\k10}{\\k50}面白い{\\k50}地図を{\\k100}買いました。"

STAMP = re.compile(r"<(\d{2,}):([0-5]\d):([0-5]\d)\.(\d{3})>")
VTT_TIME = r"(\d{2,}):([0-5]\d):([0-5]\d)\.(\d{3})"


def ms(match):
    h, m, s, t = (int(g) for g in match)
    return ((h * 60 + m) * 60 + s) * 1000 + t


def cue_of(vtt):
    """The cue's start and end in milliseconds, and its timestamps, from a one-cue WebVTT file."""
    timing = re.search(rf"^{VTT_TIME} --> {VTT_TIME}$", vtt, re.M)
    stamps = [ms(m.groups()) for m in STAMP.finditer(vtt)]
    return ms(timing.groups()[:4]), ms(timing.groups()[4:]), stamps


# --- WebVTT -------------------------------------------------------------------------------------

def test_a_timed_sentence_becomes_one_cue_with_a_timestamp_at_each_segment_s_start():
    assert value("toWebVTT", TIMED) == f"WEBVTT\n\n00:00:00.000 --> 00:00:03.500\n{TIMED_CUE}\n"


def test_a_sentence_timed_as_a_whole_becomes_one_cue_without_timestamps():
    assert value("toWebVTT", WHOLE) == f"WEBVTT\n\n00:00:04.000 --> 00:00:06.000\n{WHOLE_CUE}\n"


def test_webvtt_options_drop_the_readings_shift_the_times_and_name_the_cue():
    plain = value("toWebVTT", TIMED, {"ruby": False})
    assert "<ruby>" not in plain and "<rt>" not in plain and "<c.tsubu-seg>古い</c>" in plain
    without = re.sub(r"<ruby>(.*?)<rt>.*?</rt></ruby>", r"\1", TIMED_CUE)
    assert plain == f"WEBVTT\n\n00:00:00.000 --> 00:00:03.500\n{without}\n"
    shifted = value("toWebVTT", TIMED, {"offset": 3600 + 61.25, "id": "line 7"})
    assert shifted.startswith("WEBVTT\n\nline 7\n01:01:01.250 --> 01:01:04.750\n")
    assert cue_of(shifted)[2] == [s + 3661250 for s in cue_of(value("toWebVTT", TIMED))[2]]
    back = value("toWebVTT", WHOLE, {"offset": -4})
    assert "\n00:00:00.000 --> 00:00:02.000\n" in back


def test_the_cue_spans_the_sentence_s_own_start_and_end_when_it_has_them():
    padded = dict(TIMED, start=-0.5, end=4.0)
    vtt = value("toWebVTT", padded, {"offset": 1})
    start, end, stamps = cue_of(vtt)
    assert (start, end) == (500, 5000)
    # text before the first timestamp counts as spoken from the cue's start, so a first segment
    # that begins later gets a timestamp of its own
    assert stamps == [1000, 1700, 2000, 2500, 3000, 3500]
    assert vtt.split("\n")[3].startswith("<00:00:01.000><c.tsubu-seg>けさ</c>")


def test_punctuation_that_opens_the_sentence_waits_for_the_first_segment():
    quoted = {"start": 0.0, "end": 3.0, "segments": [seg("「", punct=True), seg("はい", start=1.0, end=2.0), seg("」", punct=True)]}
    assert value("toWebVTT", quoted).endswith(
        "\n<00:00:01.000><c.tsubu-seg.punct>「</c><c.tsubu-seg>はい</c><c.tsubu-seg.punct>」</c>\n")
    assert value("toASS", quoted).endswith(",,{\\k100}{\\k100}「はい」{\\k100}")


AWKWARD = {"segments": [
    seg("あ", start=0.0005, end=0.3334),
    seg("い", start=0.3334, end=0.6667),
    seg("う", start=0.6667, end=1.0001),
    seg("え", start=1.0001, end=1.0004),   # shorter than a millisecond, and than a centisecond
    seg("お", start=1.0004, end=1.285),
    seg("か", start=1.2851, end=2.675),
]}


def test_timestamps_are_strictly_increasing_and_inside_the_cue():
    for sentence, offset in [(TIMED, 0), (AWKWARD, 0), (AWKWARD, 0.1), (dict(TIMED, start=-1, end=9), 1)]:
        start, end, stamps = cue_of(value("toWebVTT", sentence, {"offset": offset}))
        assert start < end
        assert all(a < b for a, b in zip([start] + stamps, stamps + [end])), (start, stamps, end)
    vtt = value("toWebVTT", AWKWARD)
    # times are rounded half up as written: 0.0005 s is 1 ms, 0.3334 s is 333 ms
    assert cue_of(vtt) == (1, 2675, [333, 667, 1000, 1285])
    # お begins in the same millisecond as え, so the text before it already turns at that time
    assert "<00:00:01.000><c.tsubu-seg>え</c><c.tsubu-seg>お</c><00:00:01.285><c.tsubu-seg>か</c>" in vtt


def test_a_segment_that_begins_as_the_cue_ends_is_refused_rather_than_moved():
    last = {"segments": [seg("本", start=0, end=1), seg("を", start=1, end=1)]}
    assert "must lie inside the cue" in error("toWebVTT", last)


def test_webvtt_text_is_escaped_and_kept_on_one_line():
    tricky = {"start": 0, "end": 1, "segments": [seg("a<b>&c", ("x-->y", "<i>&")), seg("one\ntwo\r\n\r\nthree")]}
    vtt = value("toWebVTT", tricky)
    assert vtt == ("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n"
                   "<c.tsubu-seg>a&lt;b&gt;&amp;c<ruby>x--&gt;y<rt>&lt;i&gt;&amp;</rt></ruby></c>"
                   "<c.tsubu-seg>one two  three</c>\n")
    assert vtt.count("-->") == 1


# --- ASS ----------------------------------------------------------------------------------------

def test_a_timed_sentence_becomes_one_karaoke_line_with_empty_syllables_for_the_gaps():
    assert value("toASS", TIMED) == f"Dialogue: 0,0:00:00.00,0:00:03.50,Default,,0,0,0,,{TIMED_KARAOKE}"


def test_readings_can_be_written_inline_after_their_base():
    line = value("toASS", TIMED, {"ruby": "inline"})
    assert line.endswith(",,{\\k50}けさ、{\\k20}{\\k30}古(ふる)い{\\k40}本屋(ほんや)で{\\k10}"
                         "{\\k50}面白(おもしろ)い{\\k50}地図(ちず)を{\\k100}買(か)いました。")
    assert value("toASS", TIMED, {"ruby": "omit"}) == value("toASS", TIMED)


def test_a_sentence_timed_as_a_whole_is_one_syllable():
    assert value("toASS", WHOLE) == "Dialogue: 0,0:00:04.00,0:00:06.00,Default,,0,0,0,,{\\k200}先週、東京で英語の授業を受けました。"


def karaoke(line):
    start, end = re.match(r"Dialogue: 0,(\d+:\d\d:\d\d\.\d\d),(\d+:\d\d:\d\d\.\d\d),", line).groups()
    cs = lambda t: (lambda h, m, s: round((int(h) * 3600 + int(m) * 60 + float(s)) * 100))(*t.split(":"))
    return cs(start), cs(end), [int(k) for k in re.findall(r"\{\\k(\d+)\}", line)]


def test_ass_durations_add_up_to_the_rounded_span_without_drift():
    line = value("toASS", AWKWARD)
    assert line == ("Dialogue: 0,0:00:00.00,0:00:02.68,Default,,0,0,0,,"
                    "{\\k33}あ{\\k34}い{\\k33}う{\\k0}え{\\k29}お{\\k139}か")
    # rounding each duration on its own would give 33 + 33 + 33 + 0 + 28 + 139 = 266, not 268
    start, end, ks = karaoke(line)
    assert sum(ks) == end - start == 268
    many = {"segments": [seg("ら", start=i / 3, end=(i + 1) / 3) for i in range(30)]}
    for offset in [0, 0.005, 1 / 7, 3599.995]:
        start, end, ks = karaoke(value("toASS", many, {"offset": offset}))
        assert sum(ks) == end - start and len(ks) == 30


def test_ass_offset_and_long_times():
    line = value("toASS", TIMED, {"offset": 36000 + 59.995})
    assert line.startswith("Dialogue: 0,10:01:00.00,10:01:03.50,")
    assert value("toASS", WHOLE, {"offset": -4}).startswith("Dialogue: 0,0:00:00.00,0:00:02.00,")


def test_ass_override_codes_in_text_are_replaced_by_their_full_width_forms():
    tricky = {"start": 0, "end": 1, "segments": [seg("{\\b1}a\\Nb", ("c", "{d}\\h")), seg("e\nf")]}
    line = value("toASS", tricky, {"ruby": "inline"})
    assert line == "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,{\\k100}｛＼b1｝a＼Nbc(｛d｝＼h)e f"
    # the only override block left is the karaoke tag
    assert re.findall(r"\{[^}]*\}", line) == ["{\\k100}"] and line.count("\\") == 1


def test_the_ass_script_is_complete_around_the_line():
    script = value("toASSScript", TIMED, {"ruby": "inline"})
    sections = re.findall(r"^\[(.+)\]$", script, re.M)
    assert sections == ["Script Info", "V4+ Styles", "Events"]
    assert "\nScriptType: v4.00+\n" in script
    styles = [line for line in script.split("\n") if line.startswith("Style: ")]
    assert len(styles) == 1 and styles[0].startswith("Style: Default,")
    fields = re.search(r"^\[V4\+ Styles\]\nFormat: (.+)$", script, re.M).group(1).split(", ")
    assert len(styles[0][len("Style: "):].split(",")) == len(fields) == 23
    events = re.search(r"^\[Events\]\nFormat: (.+)$", script, re.M).group(1).split(", ")
    assert events[-1] == "Text" and len(events) == 10
    assert script.endswith("\n" + value("toASS", TIMED, {"ruby": "inline"}) + "\n")


# --- refusals -----------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["toWebVTT", "toASS", "toASSScript"])
def test_a_sentence_without_times_cannot_be_exported(name):
    assert "has no times" in error(name, {"segments": [seg(("本", "ほん"), "を")]})


@pytest.mark.parametrize("name", ["toWebVTT", "toASS", "toASSScript"])
@pytest.mark.parametrize("sentence, message", [
    ({"segments": [seg("本", start=0, end=1), seg("を")]}, "only 1 of 2 segments have times"),
    ({"segments": [seg("本", start=0, end=1), seg("を", start=0.5, end=1.5)]}, "overlap or are out of order"),
    ({"segments": [seg("本", start=0, end=1), seg("。", punct=True, start=1, end=2)]}, "punctuation carries no time"),
    ({"segments": []}, "non-empty `segments`"),
    (None, "a sentence must be an object"),
])
def test_input_is_refused_with_tsubu_s_own_errors(name, sentence, message):
    assert message in error(name, sentence)


@pytest.mark.parametrize("name, options, message", [
    ("toWebVTT", {"ruby": "inline"}, "options.ruby must be true or false"),
    ("toWebVTT", {"offset": "1"}, "options.offset must be a finite number"),
    ("toWebVTT", {"offset": True}, "options.offset must be a finite number"),
    ("toWebVTT", {"id": ""}, "options.id must be"),
    ("toWebVTT", {"id": "a\nb"}, "options.id must be"),
    ("toWebVTT", {"id": "a-->b"}, "options.id must be"),
    ("toWebVTT", {"id": 7}, "options.id must be"),
    ("toWebVTT", {"rubi": False}, 'toWebVTT has no option "rubi"'),
    ("toWebVTT", [], "options must be an object"),
    ("toWebVTT", {"offset": -0.5}, "cannot be negative"),
    ("toASS", {"ruby": True}, 'options.ruby must be "omit" or "inline"'),
    ("toASS", {"offset": None}, "options.offset must be a finite number"),
    ("toASS", {"id": "x"}, 'toASS has no option "id"'),
    ("toASS", {"offset": -0.01}, "cannot be negative"),
    ("toASSScript", {"ruby": "furigana"}, 'options.ruby must be "omit" or "inline"'),
    ("toASSScript", "inline", "options must be an object"),
])
def test_options_are_checked(name, options, message):
    assert message in error(name, TIMED, options)


def test_a_sentence_too_short_for_the_format_is_refused():
    instant = {"start": 1, "end": 1.0004, "segments": [seg("本")]}
    assert "at least a millisecond" in error("toWebVTT", instant)
    assert "at least a centisecond" in error("toASS", dict(instant, end=1.004))


def test_the_export_object_is_frozen_and_the_output_deterministic():
    found = run_export(("toWebVTT", TIMED, None), ("toWebVTT", TIMED, None), ("toASS", AWKWARD, None), ("toASS", AWKWARD, None))
    assert found["frozen"] and sorted(found["keys"]) == ["toASS", "toASSScript", "toWebVTT"]
    a, b, c, d = (r["value"] for r in found["results"])
    assert a == b and c == d


# --- Chromium parses the WebVTT -----------------------------------------------------------------

PAGE = """<!doctype html><html lang="ja"><head><meta charset="utf-8"></head><body>
<video id="video" width="320" height="180"></video>
<script src="{js}"></script><script src="{export}"></script></body></html>"""

LOAD_TRACK = """async (vtt) => {
  const track = document.createElement("track");
  track.kind = "subtitles"; track.srclang = "ja"; track.default = true;
  track.src = "data:text/vtt;base64," + vtt;
  const loaded = new Promise((ok, no) => { track.onload = ok; track.onerror = () => no(new Error("the track did not load")); });
  document.getElementById("video").append(track);
  track.track.mode = "hidden";
  await loaded;
  const cues = [...track.track.cues];
  const html = (cue) => { const d = document.createElement("div"); d.append(cue.getCueAsHTML()); return d.innerHTML; };
  const stamps = (cue) => { const out = []; const walk = (n) => { for (const c of n.childNodes) {
    if (c.nodeType === Node.PROCESSING_INSTRUCTION_NODE) out.push([c.target, c.data]); else walk(c); } };
    walk(cue.getCueAsHTML()); return out; };
  return cues.map((c) => ({id: c.id, start: c.startTime, end: c.endTime, text: c.text, html: html(c), stamps: stamps(c)}));
}"""


@pytest.mark.parametrize("sentence, options, span", [
    (TIMED, {"id": "s1"}, (0.0, 3.5)),
    (WHOLE, {"offset": 0.25}, (4.25, 6.25)),
    (dict(TIMED, start=-0.5, end=4.0), {"offset": 1}, (0.5, 5.0)),
], ids=["timed", "whole", "padded"])
def test_chromium_parses_the_webvtt_as_one_cue_with_ruby_and_class_spans(browser, tmp_path, sentence, options, span):
    page_file = tmp_path / "track.html"
    page_file.write_text(PAGE.format(js=SCRIPT.as_uri(), export=EXPORT.as_uri()), encoding="utf-8")
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto(page_file.as_uri())
        # the script also works in a page, from the global Tsubu, and writes what Node writes
        vtt = page.evaluate("([input, options]) => TsubuExport.toWebVTT(input, options)", [sentence, options])
        assert vtt == value("toWebVTT", sentence, options)
        cues = page.evaluate(LOAD_TRACK, base64.b64encode(vtt.encode("utf-8")).decode("ascii"))
        assert errors == []
    finally:
        page.close()

    assert len(cues) == 1
    cue = cues[0]
    assert (cue["start"], cue["end"]) == pytest.approx(span, abs=1e-6)
    assert cue["id"] == options.get("id", "")
    assert cue["text"] == vtt.rstrip("\n").split("\n")[-1]
    html = cue["html"]
    spoken = sum(1 for s in sentence["segments"] if s.get("kind") != "punct")
    punct = len(sentence["segments"]) - spoken
    assert html.count('<span class="tsubu-seg">') == spoken
    assert html.count('<span class="tsubu-seg punct">') == punct
    readings = [p["ruby"] for s in sentence["segments"] for p in s["parts"] if "ruby" in p]
    assert re.findall(r"<ruby>[^<]+<rt>([^<]+)</rt></ruby>", html) == readings
    # timestamps survive as processing instructions, in order and inside the cue
    _, _, written = cue_of(vtt)
    assert [t for t, _ in cue["stamps"]] == ["timestamp"] * len(written)
    parsed = [ms(re.fullmatch(VTT_TIME, d).groups()) for _, d in cue["stamps"]]
    assert parsed == written
    assert all(span[0] * 1000 < t < span[1] * 1000 for t in parsed)


# --- libass renders the ASS, when ffmpeg is installed -------------------------------------------

WIDTH, HEIGHT = 960, 540


def ffmpeg_with_libass():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg is not installed, so the ASS script is not rendered (it is not needed otherwise)")
    filters = subprocess.run([ffmpeg, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=30).stdout
    if not re.search(r"^\s*\S+\s+ass\s", filters, re.M):
        pytest.skip("this ffmpeg was built without libass, so the ASS script is not rendered")
    return ffmpeg


def bright_pixels(ffmpeg, folder, times, duration):
    """For each t, how many pixels libass draws in the spoken (white) colour on a black frame."""
    frames = "+".join(f"eq(n,{round(t * 100)})" for t in times)
    done = subprocess.run([ffmpeg, "-v", "error", "-f", "lavfi", "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:r=100:d={duration}",
                           "-vf", f"ass=sentence.ass,select='{frames}'", "-fps_mode", "passthrough",
                           "-f", "rawvideo", "-pix_fmt", "gray", "-"], cwd=folder, capture_output=True, timeout=120)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    size = WIDTH * HEIGHT
    assert len(done.stdout) == size * len(times)
    frames = [done.stdout[i * size:(i + 1) * size] for i in range(len(times))]
    bright = bytes(range(241, 256))
    # (white pixels, all pixels with any ink)
    return [(len(f) - len(f.translate(None, bright)), len(f) - f.count(0)) for f in frames]


def test_libass_reads_the_event_s_times_and_lights_each_syllable_at_its_start(tmp_path):
    ffmpeg = ffmpeg_with_libass()
    (tmp_path / "sentence.ass").write_text(value("toASSScript", TIMED), encoding="utf-8")
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        probe = subprocess.run([ffprobe, "-v", "error", "-show_packets", "-of", "json", "sentence.ass"], cwd=tmp_path,
                               capture_output=True, text=True, timeout=30, check=True)
        packets = json.loads(probe.stdout)["packets"]
        assert [(float(p["pts_time"]), float(p["duration_time"])) for p in packets] == [(0.0, 3.5)]

    times = [0.25, 0.6, 0.65, 0.85, 1.2, 1.45, 1.75, 2.25, 3.0, 3.6]
    lit = dict(zip(times, bright_pixels(ffmpeg, tmp_path, times, 3.7)))
    white = {t: w for t, (w, _) in lit.items()}
    assert white[0.25] > 0
    # the gaps (0.5 to 0.7 and 1.4 to 1.5) are empty syllables: nothing new lights up in them
    assert white[0.25] == white[0.6] == white[0.65] and white[1.2] == white[1.45]
    # every syllable lights up at its own start
    assert white[0.65] < white[0.85] < white[1.2] and white[1.45] < white[1.75] < white[2.25] < white[3.0]
    # the event ends at 3.5 s
    assert lit[3.6] == (0, 0)
