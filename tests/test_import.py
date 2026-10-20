"""The importers in tsubu-import.js: kuroshiro's furigana HTML, Remotion's captions, WebVTT and SRT.

Everything runs in Node: tsubu-import.js itself, and tsubu-export.js for the round trips. Segments
come only from what a format marks and times only from the file, so these tests check what each
format gives and also what it cannot (an end WebVTT does not record, readings SRT has no place for).
"""

import copy
import json
import shutil
import subprocess

import pytest

from support import ROOT, TIMED, WHOLE, seg

NODE_RUNNER = r"""
const importer = require(process.argv[1]), exporter = require(process.argv[2]), lib = { ...importer, ...exporter };
const jobs = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = { keys: Object.keys(importer), frozen: Object.isFrozen(importer) };
out.results = jobs.map((steps) => {
  // each step is [name, ...arguments]; a step's first argument may be "$", the value so far
  try { let value; for (const [name, ...args] of steps) value = lib[name](...args.map((a) => (a === "$" ? value : a))); return { value }; }
  catch (e) { return { error: e.message }; }
});
process.stdout.write(JSON.stringify(out));
"""


def run(*jobs):
    node = shutil.which("node")
    assert node, "the import tests need Node on PATH"
    done = subprocess.run([node, "-e", NODE_RUNNER, str(ROOT / "tsubu-import.js"), str(ROOT / "tsubu-export.js")],
                          input=json.dumps(jobs), capture_output=True, text=True, encoding="utf-8", timeout=30, check=True)
    return json.loads(done.stdout)


def value(*steps):
    found = run(list(steps))["results"][0]
    assert "error" not in found, found
    return found["value"]


def error(*steps):
    found = run(list(steps))["results"][0]
    assert found.get("error", "").startswith("tsubu: "), found
    return found["error"]


def test_the_library_object_is_frozen_and_has_one_function_per_format():
    found = run()
    assert found["frozen"] and found["keys"] == ["fromKuroshiro", "fromCaptions", "fromWebVTT", "fromSRT"]


# ---- kuroshiro ----

# kuroshiro.convert("感じ取れたら手を繋ごう", { mode: "furigana", to: "hiragana" })
KUROSHIRO = ("<ruby>感<rp>(</rp><rt>かん</rt><rp>)</rp></ruby>じ<ruby>取<rp>(</rp><rt>と</rt><rp>)</rp></ruby>れたら"
             "<ruby>手<rp>(</rp><rt>て</rt><rp>)</rp></ruby>を<ruby>繋<rp>(</rp><rt>つな</rt><rp>)</rp></ruby>ごう")


def test_kuroshiro_furigana_become_the_parts_of_a_segment():
    assert value(["fromKuroshiro", KUROSHIRO]) == [
        {"text": "感", "ruby": "かん"}, {"text": "じ"}, {"text": "取", "ruby": "と"}, {"text": "れたら"},
        {"text": "手", "ruby": "て"}, {"text": "を"}, {"text": "繋", "ruby": "つな"}, {"text": "ごう"}]


def test_kuroshiro_delimiters_and_the_romaji_target_are_read():
    # delimiter_start and delimiter_end are kuroshiro options; tsubu writes its own parentheses
    custom = "<ruby>漢字<rp>【</rp><rt>カンジ</rt><rp>】</rp></ruby>"
    assert value(["fromKuroshiro", custom]) == [{"text": "漢字", "ruby": "カンジ"}]
    # the romaji target puts every token in one <ruby>, a reading after each base
    romaji = "<ruby>感じ<rp>(</rp><rt>kanji</rt><rp>)</rp>取れ<rp>(</rp><rt>tore</rt><rp>)</rp></ruby>"
    assert value(["fromKuroshiro", romaji]) == [{"text": "感じ", "ruby": "kanji"}, {"text": "取れ", "ruby": "tore"}]


def test_kuroshiro_text_is_taken_as_it_is_and_empty_readings_are_none():
    # kuroshiro does not escape its text, so nothing is unescaped
    assert value(["fromKuroshiro", "A&amp;B"]) == [{"text": "A&amp;B"}]
    assert value(["fromKuroshiro", "<ruby>雨<rt></rt></ruby>です"]) == [{"text": "雨です"}]
    assert value(["fromKuroshiro", "すべてかな"]) == [{"text": "すべてかな"}]


@pytest.mark.parametrize("html, message", [
    ("<span>雨</span>", "has no <span>"),
    ("<ruby>雨<rt>あめ</rt>", "is not closed"),
    ("<ruby><rt>あめ</rt></ruby>", "has no base text"),
    ("</ruby>", "unexpected </ruby>"),
    ("", "there is no text"),
    (None, "needs kuroshiro's furigana HTML"),
])
def test_kuroshiro_output_that_is_not_furigana_html_is_refused(html, message):
    assert message in error(["fromKuroshiro", html])


# ---- Remotion captions ----

def caption(text, start, end):
    return {"text": text, "startMs": start, "endMs": end, "timestampMs": None, "confidence": 0.9}


def test_each_caption_is_a_segment_with_its_own_time():
    found = value(["fromCaptions", [caption(" けさ", 0, 500), caption("、", 500, 600), caption(" 古い", 700, 1000),
                                    caption(" ", 1000, 1000), caption("本屋で。", 1000, 1400)]])
    assert found == {"segments": [
        {"parts": [{"text": "けさ"}], "start": 0, "end": 0.5},
        # punctuation alone has no time
        {"parts": [{"text": "、"}], "kind": "punct"},
        {"parts": [{"text": "古い"}], "start": 0.7, "end": 1},
        # the caption of a space alone is left out; punctuation inside a caption stays with its text
        {"parts": [{"text": "本屋で。"}], "start": 1, "end": 1.4},
    ]}


def test_captions_tsubu_would_refuse_are_refused():
    assert error(["fromCaptions", [caption("雨", 0, 600), caption("が", 500, 800)]]).startswith("tsubu: fromCaptions: segment times overlap")
    assert error(["fromCaptions", [{"text": "雨", "startMs": 0}]]) == "tsubu: caption 0 needs startMs and endMs in milliseconds"
    assert error(["fromCaptions", [{"startMs": 0, "endMs": 1}]]) == "tsubu: caption 0 needs `text`"
    assert error(["fromCaptions", [caption("  ", 0, 1)]]) == "tsubu: fromCaptions: no caption has text"
    assert "needs an array" in error(["fromCaptions", {"text": "雨"}])


# ---- WebVTT ----

def without_gaps(sentence):
    """The sentence as WebVTT can carry it: a cue timestamp marks when a segment begins and nothing
    marks its end, so each spoken segment lasts until the next one begins."""
    out = copy.deepcopy(sentence)
    spoken = [s for s in out["segments"] if s.get("kind") != "punct"]
    for this, after in zip(spoken, spoken[1:]):
        this["end"] = after["start"]
    return out


def test_a_toWebVTT_cue_comes_back_with_its_segments_readings_and_starts():
    found = value(["toWebVTT", TIMED], ["fromWebVTT", "$"])
    assert found == [without_gaps(TIMED)]
    assert without_gaps(TIMED) != TIMED  # TIMED has gaps, which WebVTT does not keep


def test_a_cue_timed_as_a_whole_comes_back_exactly():
    assert value(["toWebVTT", WHOLE], ["fromWebVTT", "$"]) == [WHOLE]


def test_segments_that_begin_in_the_same_millisecond_come_back():
    # toWebVTT writes no timestamp for the second, which begins as the first ends
    sentence = {"segments": [seg("あ", start=0.0, end=0.5), seg("い", start=0.5, end=0.5), seg("う", start=0.5, end=1.0)]}
    assert value(["toWebVTT", sentence], ["fromWebVTT", "$"]) == [sentence]


def test_a_file_from_elsewhere_gives_one_sentence_per_cue():
    vtt = "\n".join([
        "\ufeffWEBVTT - a title", "",
        "NOTE written by hand", "", "STYLE", "::cue { color: lime }", "",
        "intro",
        "00:01.000 --> 00:02.500 align:start line:0",
        "<v Ann>雨が</v>",
        "<i>降る</i> &amp; <ruby>風<rt>かぜ</ruby>", "",
        "00:00:03.000 --> 00:00:04.000",
        "Hello",
        "world", "",
    ])
    assert value(["fromWebVTT", vtt]) == [
        # no space where a line breaks between two Japanese characters; a reading's end tag may be left out
        {"start": 1, "end": 2.5, "segments": [{"parts": [{"text": "雨が降る & "}, {"text": "風", "ruby": "かぜ"}]}]},
        {"start": 3, "end": 4, "segments": [{"parts": [{"text": "Hello world"}]}]},
    ]


def test_cue_timestamps_without_class_spans_cut_the_cue_into_segments():
    vtt = "WEBVTT\n\n00:01.000 --> 00:05.000\n雨が<00:02.000> 降る<00:03.000>。<00:04.000>\n"
    assert value(["fromWebVTT", vtt]) == [{"start": 1, "end": 5, "segments": [
        {"parts": [{"text": "雨が"}], "start": 1, "end": 2},
        # a segment ends at the next cue timestamp, even one before punctuation, which has no time
        {"parts": [{"text": "降る"}], "start": 2, "end": 3},
        {"parts": [{"text": "。"}], "kind": "punct"},
    ]}]


@pytest.mark.parametrize("vtt, message", [
    ("1\n00:00.000 --> 00:01.000\n雨", 'begins with "WEBVTT"'),
    ("WEBVTT\n\nno time here\n雨", "cue 1 has no timing line"),
    ("WEBVTT\n\n00:00.000 --> soon\n雨", "cue 1: cannot read the times"),
    ("WEBVTT\n\n00:00.000 --> 00:01.000\n<c.tsubu-seg>雨</c>が", 'text outside the <c.tsubu-seg> spans, "が"'),
    ("WEBVTT\n\n00:02.000 --> 00:03.000\n雨<00:01.000>が", "cue 1: the cue timestamp <00:01.000> is outside the cue"),
    ("WEBVTT\n\n00:00.000 --> 00:01.000\n雨\n\n00:02.000 --> 00:01.000\nが", "cue 2: the sentence: end 1 is before start 2"),
    ("WEBVTT\n\nNOTE only a note", "the file has no cues"),
])
def test_what_is_not_webvtt_or_not_a_sentence_is_refused_with_its_cue(vtt, message):
    assert message in error(["fromWebVTT", vtt])


# ---- SRT ----

def test_each_srt_cue_is_a_sentence_timed_as_a_whole():
    srt = "1\r\n00:00:01,000 --> 00:00:02,500\r\n<i>雨が</i>\r\n{\\an8}降る\r\n\r\n2\r\n00:00:03.000 --> 00:00:04,000\r\nHello\r\nworld\r\n"
    assert value(["fromSRT", srt]) == [
        {"start": 1, "end": 2.5, "segments": [{"parts": [{"text": "雨が降る"}]}]},
        {"start": 3, "end": 4, "segments": [{"parts": [{"text": "Hello world"}]}]},
    ]


def test_srt_in_segments_mode_is_one_sentence_a_cue_per_segment():
    found = value(["toSRT", TIMED, {"mode": "segments"}], ["fromSRT", "$", {"mode": "segments"}])
    # toSRT joins punctuation to the segment before it, and SRT keeps every start and end
    assert found == {"segments": [
        {"parts": [{"text": "けさ、"}], "start": 0, "end": 0.5},
        {"parts": [{"text": "古い"}], "start": 0.7, "end": 1},
        {"parts": [{"text": "本屋で"}], "start": 1, "end": 1.4},
        {"parts": [{"text": "面白い"}], "start": 1.5, "end": 2},
        {"parts": [{"text": "地図を"}], "start": 2, "end": 2.5},
        {"parts": [{"text": "買いました。"}], "start": 2.5, "end": 3.5},
    ]}
    # readings written inline come back as text: SRT has no ruby
    inline = value(["toSRT", TIMED, {"ruby": "inline"}], ["fromSRT", "$"])
    assert inline[0]["segments"][0]["parts"][0]["text"].startswith("けさ、古(ふる)い")


def test_srt_options_and_bad_files_are_refused():
    srt = "1\n00:00:01,000 --> 00:00:02,000\n雨\n"
    assert error(["fromSRT", srt, {"mode": "words"}]) == 'tsubu: options.mode must be "sentence" or "segments"'
    assert error(["fromSRT", srt, {"ruby": "inline"}]) == 'tsubu: fromSRT has no option "ruby"'
    assert "cue 1 has no timing line" in error(["fromSRT", "1\n雨\n"])
    assert "cue 1 has no text" in error(["fromSRT", "1\n00:00:01,000 --> 00:00:02,000\n<i></i>\n"])
    assert "the file has no cues" in error(["fromSRT", "\n\n"])
    assert error(["fromSRT", srt + "\n2\n00:00:01,500 --> 00:00:03,000\nが\n", {"mode": "segments"}]).startswith(
        "tsubu: fromSRT: segment times overlap")
