"""Motion presets, revealing segments on the caller's events, and the preset catalogue.

The catalogue and the options run in Node; the presets are measured in a headless browser on the
library's own CSS: what each one draws, that nothing moves, that every frame is a function of t (and
of what has been revealed), and that every theme still meets its contrast thresholds."""

import json
import shutil
import subprocess

import pytest

from support import LONG, SCRIPT, TIMED, run_library, seg

PRESETS = ["appear", "mask", "blur", "underline-draw"]
THEMES = ["light", "dark", "media"]
UNTIMED = {"segments": [seg(("雨", "あめ"), "が"), seg(("降", "ふ"), "って"), seg("いる"), seg("。", punct=True)]}


def node(expression):
    runner = "const T = require(process.argv[1]); process.stdout.write(JSON.stringify((() => { %s })()));"
    done = subprocess.run([shutil.which("node"), "-e", runner % expression, str(SCRIPT)], capture_output=True,
                          text=True, encoding="utf-8", timeout=30, check=True)
    return json.loads(done.stdout)


# --- the catalogue and the options, in Node -------------------------------------------------------

def test_the_catalogue_describes_every_preset_for_templates_and_agents():
    found = node("""return {motions: T.MOTIONS, frozen: Object.isFrozen(T.MOTIONS) && T.MOTIONS.every((m) =>
      Object.isFrozen(m) && Object.isFrozen(m.parameters) && m.parameters.every(Object.isFrozen))};""")
    assert found["frozen"]
    assert [m["name"] for m in found["motions"]] == PRESETS
    for m in found["motions"]:
        assert set(m) == {"name", "purpose", "needs", "without", "parameters", "reducedMotion", "revealable"}, m
        assert m["needs"] in ("segments", "sentence", "characters")
        assert m["purpose"] and m["without"] and m["reducedMotion"]
        for p in m["parameters"]:
            assert set(p) == {"property", "default", "min", "max", "meaning"} and p["property"].startswith("--tsubu-")
    css = (SCRIPT.parent / "tsubu.css").read_text(encoding="utf-8")
    for m in found["motions"]:  # the catalogue and the stylesheet agree
        assert f'[data-tsubu-motion~="{m["name"]}"]' in css
        for p in m["parameters"]:
            assert f'var({p["property"]}, {p["default"]})' in css


def test_the_motion_option_takes_names_from_the_catalogue_only():
    html = run_library(TIMED, options={"motion": "mask  blur mask"})["html"]
    assert ' data-tsubu-motion="mask blur"' in html
    assert ' data-tsubu-motion="appear"' in run_library(TIMED, options={"motion": ["appear"]})["html"]
    assert "data-tsubu-motion" not in run_library(TIMED)["html"]
    assert run_library(TIMED, options={"motion": ["wipe"]})["error"].startswith('tsubu: options.motion: unknown preset "wipe"')
    assert run_library(TIMED, options={"motion": 3})["error"].startswith("tsubu: options.motion must be")


def test_html_at_draws_what_has_been_revealed():
    found = node("""const s = T.sentence(%s, {motion: "mask"});
      let bad = null; try { s.htmlAt(1, {revealed: [99]}); } catch (e) { bad = e.message; }
      return {one: s.htmlAt(1, {revealed: [4]}), all: s.htmlAt(1, {revealed: "all"}), none: s.htmlAt(1), bad};""" % json.dumps(TIMED))
    assert found["one"].count("data-revealed") == 1 and 'data-index="4" data-state="future" data-revealed=""' in found["one"]
    assert found["all"].count("data-revealed") == len(TIMED["segments"]) and "data-revealed" not in found["none"]
    assert found["bad"].startswith("tsubu: revealed segments must be")


# --- the presets, in the browser --------------------------------------------------------------

LOOK = """() => [...document.querySelectorAll('.tsubu-seg')].map((s) => { const st = getComputedStyle(s), after = getComputedStyle(s, '::after'), rt = s.querySelector('rt');
  return {state: s.dataset.state || null, punct: s.dataset.kind === 'punct', visibility: st.visibility, color: st.color, filter: st.filter,
          rtFilter: rt ? getComputedStyle(rt).filter : null,
          rt: rt ? getComputedStyle(rt).color : null, line: after.content === 'none' ? null : after.visibility, transform: after.transform}; })"""


def unheard(look):
    return [x for x in look if x["state"] not in ("current", "past")]


def heard(look):
    return [x for x in look if x["state"] in ("current", "past")]


@pytest.mark.parametrize("preset", PRESETS)
def test_each_preset_draws_what_it_says_for_unheard_segments_only(drawn, preset):
    at = drawn(TIMED, motion=preset)
    at(1.2)  # けさ、古い past; 本屋で current; the rest future
    look = at.page.evaluate(LOOK)
    later, now = unheard(look), heard(look)
    assert later and now
    if preset == "appear":
        assert {x["visibility"] for x in later} == {"hidden"} and {x["visibility"] for x in now} == {"visible"}
    if preset == "mask":
        assert {x["color"] for x in later} == {"rgba(0, 0, 0, 0)"} and {x["rt"] for x in later if x["rt"]} == {"rgba(0, 0, 0, 0)"}
        assert {x["line"] for x in later if not x["punct"]} == {"visible"}  # the blank keeps its underline
        assert "rgba(0, 0, 0, 0)" not in {x["color"] for x in now}
    if preset == "blur":
        assert {x["filter"] for x in later} == {"blur(6px)"}  # 0.15em of 40px
        # the readings too, which the segment's filter does not reach: 0.15em of 20px
        assert {x["rtFilter"] for x in later if x["rtFilter"]} == {"blur(3px)"}
        assert {x["filter"] for x in now} == {"none"}
    if preset == "underline-draw":
        assert {x["line"] for x in later if not x["punct"]} == {"hidden"}
        current = next(x for x in look if x["state"] == "current")
        assert current["transform"] == "matrix(0.5, 0, 0, 1, 0, 0)"  # halfway through 本屋で, 1.0 to 1.4 s
        assert {x["transform"] for x in look if x["state"] == "past"} == {"none"}


@pytest.mark.parametrize("preset", ["appear", "mask", "blur"])
def test_a_segment_revealed_by_the_caller_is_drawn_whatever_t_is(drawn, preset):
    at = drawn(TIMED, motion=preset)
    plain = drawn(TIMED)
    at(0.2), plain(0.2)
    page = at.page
    shown = page.evaluate("() => Tsubu.setRevealed(document.querySelector('.tsubu'), [5, 6])")
    assert shown == [5, 6]
    look, reference = page.evaluate(LOOK), plain.page.evaluate(LOOK)
    for i in (5, 6):
        assert look[i] == reference[i], i  # drawn as it would be without the preset
    assert look[4] != reference[4]  # an unrevealed future segment is still hidden
    page.evaluate("() => Tsubu.setRevealed(document.querySelector('.tsubu'), 'none')")
    assert page.evaluate(LOOK)[5] != reference[5]


def test_without_times_every_segment_waits_to_be_revealed(drawn):
    at = drawn(UNTIMED, motion="mask")
    page = at.page
    before = page.evaluate(LOOK)
    assert {x["color"] for x in before} == {"rgba(0, 0, 0, 0)"}
    page.evaluate("() => Tsubu.setRevealed(document.querySelector('.tsubu'), 'all')")
    assert "rgba(0, 0, 0, 0)" not in {x["color"] for x in page.evaluate(LOOK)}


def test_segment_of_tells_which_segment_a_click_landed_in(drawn):
    page = drawn(TIMED).page
    found = page.evaluate("""() => { const root = document.querySelector('.tsubu');
      const rt = root.querySelectorAll('rt')[1], text = rt.firstChild, plain = root.querySelector('.tsubu-seg').firstChild;
      return [Tsubu.segmentOf(rt), Tsubu.segmentOf(text), Tsubu.segmentOf(plain), Tsubu.segmentOf(root), Tsubu.segmentOf(document.body), Tsubu.segmentOf(null)]; }""")
    assert found == [3, 3, 0, None, None, None]  # 本屋 is the second reading, in segment 3


def test_reduced_motion_draws_the_underline_whole_at_once(drawn):
    at = drawn(TIMED, motion="underline-draw")
    at(1.2)
    at.page.emulate_media(reduced_motion="reduce")
    current = next(x for x in at.page.evaluate(LOOK) if x["state"] == "current")
    assert current["transform"] == "none" and current["line"] == "visible"


def test_no_preset_and_no_reveal_moves_a_character(drawn):
    base = lambda f: ([(c["ch"], c["box"]) for c in f["chars"]], [s["box"] for s in f["segments"]], f["root"])
    first = drawn(LONG)(2.3)
    for preset in PRESETS + ["appear mask blur underline-draw"]:
        at = drawn(LONG, motion=preset)
        for t in (0.1, 2.3, 4.6):
            assert base(at(t)) == base(first), (preset, t)
        at.page.evaluate("() => Tsubu.setRevealed(document.querySelector('.tsubu'), [0, 3, 7])")
        assert base(at(2.3)) == base(first), preset


@pytest.mark.parametrize("preset", PRESETS)
def test_every_frame_is_a_function_of_t_and_of_what_is_revealed(drawn, preset):
    at = drawn(LONG, motion=preset, theme="light")
    page = at.page
    bubble = page.locator("#bubble")

    def frame(t, revealed):
        page.evaluate("([t, r]) => { const root = document.querySelector('.tsubu'); Tsubu.setRevealed(root, r); S.apply(root, t); }", [t, revealed])
        return bubble.screenshot()

    first = {(t, json.dumps(r)): frame(t, r) for t, r in [(0.5, "none"), (2.3, "none"), (2.3, [9]), (4.0, "all")]}
    for (t, r) in reversed(list(first)):
        assert frame(t, json.loads(r)) == first[t, r], (t, r)
    assert len(set(first.values())) == len(first)  # and the frames do differ


@pytest.mark.parametrize("theme", THEMES)
def test_with_every_preset_each_theme_still_meets_its_thresholds(drawn, theme):
    at = drawn(TIMED, theme=theme, motion=" ".join(PRESETS))
    at(1.2)
    found = at.page.evaluate("() => Tsubu.checkContrast(document.querySelector('.tsubu'))")
    assert found["ok"], found["failures"]
    covered = {(c["state"], c["layer"]) for c in found["checks"]}
    assert {("future", "text"), ("future", "ruby"), ("static", "text"), ("current", "highlight")} <= covered


def test_a_faded_layer_is_measured_with_its_opacity(drawn):
    at = drawn(TIMED, theme="light")
    at.page.add_style_tag(content=".tsubu-seg[data-state='past'] { opacity: 0.3; }")
    found = at.page.evaluate("() => Tsubu.checkContrast(document.querySelector('.tsubu'))")
    assert {(f["state"], f["layer"]) for f in found["failures"]} >= {("past", "text")}
    assert {f["state"] for f in found["failures"]} == {"past"}


def test_in_vertical_text_the_side_line_draws_in_from_the_top(drawn):
    at = drawn(TIMED, motion="underline-draw", writing="vertical")
    at(1.2)  # halfway through 本屋で
    found = at.page.evaluate("""() => { const s = document.querySelector('.tsubu-seg[data-state="current"]'), a = getComputedStyle(s, '::after');
      return [a.transform, a.transformOrigin, a.borderLeftStyle]; }""")
    transform, origin, side = found
    assert transform == "matrix(1, 0, 0, 0.5, 0, 0)" and side == "dotted"
    assert origin.split()[1] == "0px"  # from the top
