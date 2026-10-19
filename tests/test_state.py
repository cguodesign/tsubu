"""The state at t and the HTML, computed by running tsubu.js itself in Node."""

import re

import pytest

from support import LONG, ROOT, TIMED, WHOLE, run_library, seg


def states(sentence, *times):
    found = run_library(sentence, times)
    assert "error" not in found, found
    return found["states"]


def segment_states(state):
    return [s["state"] for s in state["segments"]]


def test_the_state_at_t_follows_each_segment_s_own_time():
    at = dict(zip(
        ["before", "start", "middle", "boundary", "gap", "last", "end", "after"],
        states(TIMED, -1.0, 0.0, 0.25, 1.0, 1.45, 3.0, 3.5, 9.0)))
    f, c, p = "future", "current", "past"
    assert segment_states(at["before"]) == [f, f, f, f, f, f, f, f]
    assert segment_states(at["start"]) == [c, f, f, f, f, f, f, f]
    assert segment_states(at["middle"]) == [c, f, f, f, f, f, f, f]
    # spans are half-open, [start, end): the instant one segment ends belongs to the next
    assert segment_states(at["boundary"]) == [p, p, p, c, f, f, f, f]
    # in a gap between two segments none is current
    assert segment_states(at["gap"]) == [p, p, p, p, f, f, f, f]
    assert segment_states(at["last"]) == [p, p, p, p, p, p, c, f]
    assert segment_states(at["end"]) == [p, p, p, p, p, p, p, p]
    assert segment_states(at["after"]) == segment_states(at["end"])

    assert [at[k]["current"] for k in at] == [None, 0, 0, 3, None, 6, None, None]
    assert [at[k]["state"] for k in at] == [f, c, c, c, c, c, p, p]
    assert all(at[k]["timing"] == "segments" for k in at)


def test_progress_runs_from_zero_to_one_within_each_segment():
    middle, = states(TIMED, 0.25)
    assert middle["segments"][0]["progress"] == pytest.approx(0.5)
    assert middle["segments"][2]["progress"] == 0
    assert middle["progress"] == pytest.approx(0.25 / 3.5)
    end, = states(TIMED, 3.5)
    assert [s["progress"] for i, s in enumerate(end["segments"]) if i not in (1, 7)] == [1] * 6
    # punctuation has no time of its own, so no progress either
    assert end["segments"][1]["progress"] is None and end["segments"][7]["progress"] is None


def test_the_sentence_span_may_be_wider_than_its_segments():
    padded = dict(TIMED, start=-0.5, end=4.0)
    before, inside, after = states(padded, -0.25, 3.75, 4.0)
    assert before["state"] == "current" and before["current"] is None and before["progress"] == pytest.approx(0.25 / 4.5)
    assert inside["state"] == "current" and set(segment_states(inside)) == {"past"}
    assert after["state"] == "past"


def test_punctuation_is_never_the_current_segment():
    for state in states(TIMED, *[i / 10 for i in range(-5, 40)]):
        assert state["segments"][1]["state"] != "current" and state["segments"][7]["state"] != "current"
    quoted = {"segments": [seg("「", punct=True), seg("はい", start=1.0, end=2.0), seg("」", punct=True)]}
    assert [segment_states(s) for s in states(quoted, 0.5, 1.5, 2.0)] == [
        ["future", "future", "future"], ["past", "current", "future"], ["past", "past", "past"]]


def test_without_segment_times_the_whole_sentence_lights_up_and_nothing_is_estimated():
    times = [3.0, 4.0, 4.01, 5.0, 5.99, 6.0, 7.0]
    found = states(WHOLE, *times)
    for t, state in zip(times, found):
        expected = "future" if t < 4.0 else "current" if t < 6.0 else "past"
        assert state["timing"] == "sentence" and state["state"] == expected
        # every segment, punctuation included, shares the sentence's state: none is singled out
        assert segment_states(state) == [expected] * len(WHOLE["segments"])
        assert state["current"] is None
        assert all(s["progress"] is None for s in state["segments"])
    assert [s["progress"] for s in found] == [0, 0, pytest.approx(0.005), pytest.approx(0.5), pytest.approx(0.995), 1, 1]


def test_the_state_is_a_function_of_t_alone():
    times = [2.2, 0.3, 3.1, 0.3, 2.2, -1, 3.1]
    found = states(TIMED, *times)
    by_t = {}
    for t, state in zip(times, found):
        assert by_t.setdefault(t, state) == state


@pytest.mark.parametrize("sentence, message", [
    ({"segments": [seg("本", start=0, end=1), seg("を")]}, "only 1 of 2 segments have times"),
    ({"segments": [seg("本", start=0, end=1), seg("を", start=0.5, end=1.5)]}, "overlap or are out of order"),
    ({"segments": [seg("本", start=1, end=0.5)]}, "is before start"),
    ({"segments": [seg("本", start=0)]}, "start and end must both be"),
    ({"segments": [seg("本", start=0, end="1")]}, "start and end must both be"),
    ({"start": 1, "end": 2, "segments": [seg("本", start=0, end=1)]}, "outside the sentence"),
    ({"start": 1, "segments": [seg("本")]}, "the sentence: start and end must both be"),
    ({"segments": [seg("本", start=0, end=1), seg("。", punct=True, start=1, end=2)]}, "punctuation carries no time"),
    ({"segments": [seg("。", punct=True)]}, "not punctuation"),
    ({"segments": []}, "non-empty `segments`"),
    ({"segments": [{"parts": []}]}, "non-empty `parts`"),
    ({"segments": [{"parts": [{"text": ""}]}]}, "non-empty `text`"),
    ({"segments": [{"parts": [{"text": "本", "ruby": ""}]}]}, "`ruby` must be"),
    ({"segments": [seg("本", start=0, end=1) | {"kind": "word"}]}, "unknown kind"),
    ({"lang": "", "segments": [seg("本")]}, "`lang` must be"),
])
def test_a_sentence_that_would_need_guessing_or_is_malformed_is_refused(sentence, message):
    found = run_library(sentence)
    assert found.get("error", "").startswith("tsubu: "), found
    assert message in found["error"], found


def test_options_are_checked():
    assert "options.ruby must be" in run_library(TIMED, options={"ruby": "yes"})["error"]


def test_t_must_be_a_finite_number():
    found = run_library(TIMED, times=[None])
    assert "t must be a finite number" in found["states"][0]["error"]


def test_a_sentence_without_any_time_can_be_drawn_but_not_played():
    found = run_library({"segments": [seg(("本", "ほん"), "を")]}, times=[0.0])
    assert found["timing"] == "none" and "<ruby>本<rt>ほん</rt></ruby>" in found["html"]
    assert 'data-timing="none"' in found["html"]
    assert "has no times" in found["states"][0]["error"]


def test_the_html_keeps_the_furigana_in_the_page_whether_they_are_shown_or_not():
    shown = run_library(TIMED, options={"ruby": True})["html"]
    hidden = run_library(TIMED, options={"ruby": False})["html"]
    assert 'data-ruby="on"' in shown and 'data-ruby="off"' in hidden
    assert shown.replace('data-ruby="on"', 'data-ruby="off"') == hidden
    assert shown.count("<rt>") == hidden.count("<rt>") == 5
    assert 'lang="ja"' in shown and shown.count('class="tsubu-seg"') == len(TIMED["segments"])
    assert shown.startswith('<span class="tsubu" lang="ja" data-timing="segments" data-ruby="on">')
    # a line may break between segments, never before punctuation: a segment and the punctuation
    # after it share a unit
    assert '<wbr><span class="tsubu-unit"><span class="tsubu-seg" data-index="2">' in shown
    assert '<span class="tsubu-seg" data-index="0">けさ</span><span class="tsubu-seg" data-index="1" data-kind="punct">' in shown
    assert shown.count("<wbr>") == len(TIMED["segments"]) - 2 - 1  # not before the first segment or the two punctuation marks
    assert shown.count('class="tsubu-unit"') == shown.count("<wbr>") + 1
    # the fresh HTML carries no state: apply() adds it
    assert "aria-current" not in shown and "data-state" not in shown


def test_lang_is_written_on_the_root():
    html = run_library({"lang": "zh-Hans", "segments": [seg(("你", "nǐ"), "好")]})["html"]
    assert 'lang="zh-Hans"' in html


def test_text_is_escaped():
    # horizontal by its own option, so no run of half-width characters is marked to be set upright
    # (escaping inside those marks is checked in tests/test_vertical.py)
    html = run_library({"segments": [seg("<b>&", ("\"'", "<i>"))]}, options={"writing": "horizontal"})["html"]
    assert "&lt;b&gt;&amp;" in html and "&quot;&#39;<rt>&lt;i&gt;</rt>" in html and "<b>" not in html


def test_the_library_object_is_frozen_and_carries_its_version():
    found = run_library(LONG)
    assert found["frozen"] and sorted(found["keys"]) == ["CONTRAST", "MOTIONS", "SPEAKERS", "STATES", "THEMES", "checkContrast",
                                                    "checkFit", "contrast", "segmentOf", "sentence", "setRevealed",
                                                    "setRuby", "version"]
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    newest = re.search(r"^## \[?(\d+\.\d+\.\d+)", changelog, re.M).group(1)
    assert found["version"] == newest
