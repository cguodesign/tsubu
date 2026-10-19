"""Forced colours and screen readers, in headless Chromium.

In forced-colours mode (Windows contrast themes and the like) browsers replace backgrounds and drop
box-shadows; the segment being spoken must still stand out, in the user's own colours, and nothing
may move. And with announceRuby off, a screen reader reads the sentence once, without each reading.
"""

import pytest

from support import LONG, TIMED, WHOLE, run_library

SYSTEM = """(names) => { const d = document.createElement('div'); document.body.append(d); const out = {};
  for (const c of names) { d.style.color = c; out[c] = getComputedStyle(d).color; } d.remove(); return out; }"""

LOOK = """() => [...document.querySelectorAll('.tsubu-seg')].map((s) => { const st = getComputedStyle(s), rt = s.querySelector('rt');
  return {state: s.dataset.state, bg: st.backgroundColor, color: st.color, shadow: st.boxShadow,
          rt: rt ? getComputedStyle(rt).color : null, underline: getComputedStyle(s, '::after').borderBottomColor,
          punct: s.dataset.kind === 'punct'}; })"""


@pytest.mark.parametrize("theme", [None, "light", "dark", "media"])
@pytest.mark.parametrize("sentence", [TIMED, WHOLE], ids=["timed", "whole"])
def test_in_forced_colours_the_segment_being_spoken_keeps_a_highlight_in_the_users_colours(drawn, theme, sentence):
    at = drawn(sentence, **({"theme": theme} if theme else {}))
    at(1.2 if sentence is TIMED else 5.0)
    at.page.emulate_media(forced_colors="active")
    system = at.page.evaluate(SYSTEM, ["Canvas", "CanvasText", "Highlight", "HighlightText"])
    looks = at.page.evaluate(LOOK)
    current = [x for x in looks if x["state"] == "current"]
    others = [x for x in looks if x["state"] != "current"]
    assert current
    for x in current:
        assert x["bg"] == system["Highlight"] and x["color"] == system["HighlightText"], x
        assert system["Highlight"] in x["shadow"]
        assert x["rt"] in (None, system["CanvasText"])  # the reading sits on the page, above the highlight
        if not x["punct"]:
            assert x["underline"] == system["HighlightText"]
    for x in others:  # everything else is left to the browser's forced colours
        assert x["bg"] != system["Highlight"] and x["color"] == system["CanvasText"]


def test_forced_colours_move_nothing(drawn):
    at = drawn(LONG, theme="media", speaker="b")
    normal = at(2.3)
    at.page.emulate_media(forced_colors="active")
    forced = at()
    base = lambda f: [(c["ch"], c["box"]) for c in f["chars"]]
    assert base(forced) == base(normal) and forced["root"] == normal["root"]


def test_with_announce_ruby_off_a_screen_reader_reads_each_word_once(drawn):
    spoken = drawn(TIMED).page.locator("#bubble").aria_snapshot()
    quiet_at = drawn(TIMED, announceRuby=False)
    quiet = quiet_at.page.locator("#bubble").aria_snapshot()
    assert "ふる" in spoken and "ほんや" in spoken
    assert "ふる" not in quiet and "ほんや" not in quiet and "古" in quiet and "本屋" in quiet
    # the readings are still drawn, and still switch
    found = quiet_at()
    assert {r["visibility"] for r in found["rts"]} == {"visible"}


def test_announce_ruby_marks_every_reading_and_is_a_boolean():
    html = run_library(TIMED, options={"announceRuby": False})["html"]
    assert html.count('<rt aria-hidden="true">') == html.count("<rt") == 5
    assert "aria-hidden" not in run_library(TIMED)["html"]
    assert run_library(TIMED, options={"announceRuby": "no"})["error"] == "tsubu: options.announceRuby must be true or false"
