"""Colour tokens, theme presets, speakers and the contrast check.

The contrast ratio and the options run in Node; the presets are measured in a headless browser
on the library's own CSS, in every state and for each speaker, at the thresholds in Tsubu.CONTRAST.
"""

import json
import shutil
import subprocess

import pytest

from support import BAND_COLOUR, LONG, SCRIPT, TIMED, VERTICAL_MIRROR, WHOLE
from test_layout import png_rows

THEMES = ["light", "dark", "media"]
SPEAKERS = [None, "a", "b"]
STATES = ["static", "future", "current", "past"]


def node(expression):
    """The value of a JavaScript expression in Node, with the library as `T`."""
    runner = "const T = require(process.argv[1]); process.stdout.write(JSON.stringify((() => { %s })()));"
    done = subprocess.run([shutil.which("node"), "-e", runner % expression, str(SCRIPT)], capture_output=True,
                          text=True, encoding="utf-8", timeout=30, check=True)
    return json.loads(done.stdout)


def refused(expression):
    return node("try { %s; return null; } catch (e) { return e.message; }" % expression)


# --- the ratio, in Node ---------------------------------------------------------------------

def test_the_contrast_ratio_matches_the_wcag_reference_values():
    found = node("""return [T.contrast("#000", "#fff"), T.contrast("#fff", "#000"), T.contrast("#123456", "#123456"),
                            T.contrast("#777777", "#ffffff"), T.contrast("#767676", "#ffffff"),
                            T.contrast("rgb(255, 0, 0)", "#ffffff")];""")
    black_white, white_black, same, grey_77, grey_76, red = found
    assert black_white == white_black == 21
    assert same == 1
    # #767676 is the lightest grey that passes 4.5:1 on white; #777777 just misses it
    assert grey_77 == pytest.approx(4.48, abs=0.005) and grey_77 < 4.5 <= grey_76
    assert red == pytest.approx(4.0, abs=0.005)


def test_translucent_colours_are_painted_over_what_is_behind_them():
    found = node("""return [
      T.contrast("rgba(0, 0, 0, 0.5)", "#ffffff"), T.contrast("rgb(127.5, 127.5, 127.5)", "#ffffff"),
      T.contrast("#ffffff", "rgba(0, 0, 0, 0.75)", "#ffffff"), T.contrast("#ffffff", "rgb(63.75, 63.75, 63.75)"),
      T.contrast("#ffffff", "rgba(0, 0, 0, 0.75)", "#000000"), T.contrast("#ffffff", "#000000"),
      T.contrast("#0008", "#fff"), T.contrast("rgba(0, 0, 0, 0.5333)", "#fff"),
      T.contrast("color(srgb 1 1 1)", "color(srgb 0 0 0 / 1)")];""")
    assert found[0] == pytest.approx(found[1])
    assert found[2] == pytest.approx(found[3])
    assert found[4] == pytest.approx(found[5])
    assert found[6] == pytest.approx(found[7], abs=0.01)
    assert found[8] == 21


def test_a_colour_it_cannot_read_is_refused_not_guessed():
    for colour in ('"oklch(0.5 0.1 200)"', '"red"', '"#12"', '"rgb(1, 2)"'):
        message = refused(f'T.contrast({colour}, "#fff")')
        assert message and message.startswith("tsubu: cannot read the colour"), colour


def test_the_thresholds_themes_and_speakers_are_part_of_the_library():
    found = node("""return {contrast: T.CONTRAST, themes: T.THEMES, speakers: T.SPEAKERS,
                            frozen: [T.CONTRAST, T.THEMES, T.SPEAKERS].every(Object.isFrozen)};""")
    assert found["contrast"] == {"text": 4.5, "ruby": 4.5, "underline": 3, "highlight": 3}
    assert found["themes"] == THEMES and found["speakers"] == ["a", "b"]
    assert found["frozen"]


def test_the_theme_and_speaker_options_are_written_on_the_root():
    found = node("""const one = {segments: [{parts: [{text: "雨"}]}]};
      return [T.sentence(one, {theme: "dark", speaker: "b"}).html, T.sentence(one).html,
              T.sentence(one, {theme: "my-sepia"}).html];""")
    themed, plain, custom = found
    assert ' data-tsubu-theme="dark" data-speaker="b">' in themed
    assert "data-tsubu-theme" not in plain and "data-speaker" not in plain
    assert ' data-tsubu-theme="my-sepia">' in custom  # a theme of the caller's own
    for options in ('{theme: "Dark"}', '{theme: 3}', '{speaker: "a b"}', '{speaker: ""}', '{theme: "x\\"y"}'):
        message = refused(f'T.sentence({{segments: [{{parts: [{{text: "x"}}]}}]}}, {options})')
        assert message and message.startswith("tsubu: options."), options


# --- the presets, measured in the browser ---------------------------------------------------

CHECK = "(options) => Tsubu.checkContrast(document.querySelector('.tsubu'), options || undefined)"

CURRENT_COLOURS = """() => { const root = document.querySelector(".tsubu"), seg = root.querySelector("rt").closest(".tsubu-seg");
  const old = seg.dataset.state; seg.dataset.state = "current";
  const s = getComputedStyle(seg), found = {text: s.color, bg: BAND_COLOUR(seg), ruby: getComputedStyle(seg.querySelector("rt")).color,
    underline: getComputedStyle(seg, "::after").borderBottomColor, plate: getComputedStyle(root, "::before").backgroundColor};
  if (old === undefined) delete seg.dataset.state; else seg.dataset.state = old;
  return found; }""".replace("BAND_COLOUR", BAND_COLOUR)


@pytest.mark.parametrize("speaker", SPEAKERS, ids=["no-speaker", "speaker-a", "speaker-b"])
@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("sentence", [TIMED, WHOLE], ids=["timed", "whole"])
def test_every_preset_meets_the_thresholds_in_every_state(drawn, theme, speaker, sentence):
    at = drawn(sentence, theme=theme, **({"speaker": speaker} if speaker else {}))
    at(1.2)
    found = at.page.evaluate(CHECK)
    assert found["ok"], found["failures"]
    covered = {(c["state"], c["layer"]) for c in found["checks"]}
    expected = {(state, layer) for state in STATES for layer in ("text", "ruby", "underline")} | {("current", "highlight")}
    assert covered == expected
    backdrops = {c["backdrop"] for c in found["checks"]}
    assert len(backdrops) == 2, backdrops  # each preset names two backdrops; "any" stands for black and white
    if theme == "media":
        assert backdrops == {"#000000", "#ffffff"}
    assert all(c["ratio"] >= c["minimum"] for c in found["checks"])


def test_the_themes_and_speakers_really_change_the_colours(drawn):
    seen = {}
    for theme in THEMES:
        for speaker in SPEAKERS:
            at = drawn(TIMED, theme=theme, **({"speaker": speaker} if speaker else {}))
            seen[theme, speaker] = at.page.evaluate(CURRENT_COLOURS)
    for theme in THEMES:
        assert seen[theme, None] == seen[theme, "a"]  # speaker A uses the theme's own highlight
        assert seen[theme, "a"]["bg"] != seen[theme, "b"]["bg"]
    assert len({json.dumps(seen[t, None], sort_keys=True) for t in THEMES}) == 3
    assert seen["media", None]["plate"] != "rgba(0, 0, 0, 0)"
    assert {seen[t, None]["plate"] for t in ("light", "dark")} == {"rgba(0, 0, 0, 0)"}


def test_a_theme_set_on_an_ancestor_draws_the_same_as_one_set_on_the_root(drawn):
    on_root = drawn(TIMED, theme="dark", speaker="b").page.evaluate(CURRENT_COLOURS)
    at = drawn(TIMED, speaker="b")
    at.page.evaluate("() => document.getElementById('bubble').dataset.tsubuTheme = 'dark'")
    assert at.page.evaluate(CURRENT_COLOURS) == on_root
    assert at.page.evaluate(CHECK)["ok"]


def test_a_colour_below_its_threshold_is_reported(drawn):
    at = drawn(TIMED, theme="light")
    # on the root itself: the preset is set there too, so a value on an ancestor would lose to it
    at.page.evaluate("() => document.querySelector('.tsubu').style.setProperty('--tsubu-past-color', '#9ca3af')")
    found = at.page.evaluate(CHECK)
    assert not found["ok"]
    assert {(f["state"], f["layer"]) for f in found["failures"]} == {("past", "text")}
    assert all(f["ratio"] < 4.5 and f["minimum"] == 4.5 and f["foreground"] == "#9ca3af" for f in found["failures"])


def test_furigana_over_the_highlight_are_measured_against_the_page_not_the_highlight(drawn):
    # The highlight covers the line of text; the reading above it sits on the page. A pale reading
    # that would pass on the blue highlight is unreadable on white, and must be reported.
    at = drawn(TIMED, theme="light")
    found = at.page.evaluate(CHECK)
    current_ruby = [c for c in found["checks"] if c["state"] == "current" and c["layer"] == "ruby"]
    assert {c["background"] for c in current_ruby} == {"#ffffff", "#f1f5f9"}
    current_underline = [c for c in found["checks"] if c["state"] == "current" and c["layer"] == "underline"]
    assert {c["background"] for c in current_underline} == {"#1d4ed8"}  # inside the highlight's spread
    at.page.evaluate("() => document.querySelector('.tsubu').style.setProperty('--tsubu-current-ruby-color', '#dbeafe')")
    failed = at.page.evaluate(CHECK)["failures"]
    assert {(f["state"], f["layer"]) for f in failed} == {("current", "ruby")}
    # and a spread large enough to cover the reading puts it on the highlight after all
    at.page.evaluate("() => document.querySelector('.tsubu').style.setProperty('--tsubu-current-spread', '1em')")
    covered = at.page.evaluate(CHECK)
    assert {c["background"] for c in covered["checks"] if c["state"] == "current" and c["layer"] == "ruby"} == {"#1d4ed8"}
    assert covered["ok"]


def test_the_thresholds_and_the_backdrop_can_be_given(drawn):
    at = drawn(TIMED, theme="light")
    stricter = at.page.evaluate(CHECK, {"thresholds": {"underline": 7}})
    assert {f["layer"] for f in stricter["failures"]} == {"underline"}
    dark_page = at.page.evaluate(CHECK, {"backdrop": "#111827"})
    assert not dark_page["ok"] and {c["backdrop"] for c in dark_page["checks"]} == {"#111827"}
    message = at.page.evaluate("""() => { try { Tsubu.checkContrast(document.querySelector('.tsubu'),
        {thresholds: {text: 0}}); } catch (e) { return e.message; } }""")
    assert message == "tsubu: thresholds.text must be a ratio from 1 to 21"


def test_without_a_theme_the_backdrop_is_read_from_the_page(drawn):
    at = drawn(TIMED)
    at.page.evaluate("""() => { document.body.style.background = '#0f172a';
        document.getElementById('bubble').style.background = 'rgba(255, 255, 255, 0.5)'; }""")
    found = at.page.evaluate(CHECK)
    # half white over #0f172a
    assert {c["backdrop"] for c in found["checks"]} == {"rgb(135.000, 139.000, 148.500)"}


def test_check_contrast_leaves_the_page_as_it_was(drawn):
    at = drawn(LONG, theme="media", speaker="b")
    before = at(2.3)
    html = at.page.evaluate("() => document.body.innerHTML")
    at.page.evaluate(CHECK)
    assert at.page.evaluate("() => document.body.innerHTML") == html
    # compared as JSON, where the NaN measured for punctuation's missing underline equals itself
    assert json.dumps(at(), sort_keys=True) == json.dumps(before, sort_keys=True)


def test_no_character_moves_when_the_theme_or_the_speaker_changes(drawn):
    at = drawn(LONG)
    first = at(2.3)
    boxes = lambda f: ([(c["ch"], c["box"]) for c in f["chars"]], [s["box"] for s in f["segments"]],
                       [r["box"] for r in f["rts"]], f["root"])
    for where in ("root", "ancestor"):
        for theme in [None] + THEMES:
            for speaker in SPEAKERS:
                at.page.evaluate("""([where, theme, speaker]) => {
                  const root = document.querySelector(".tsubu"), bubble = document.getElementById("bubble");
                  for (const el of [root, bubble]) delete el.dataset.tsubuTheme;
                  const target = where === "root" ? root : bubble;
                  if (theme) target.dataset.tsubuTheme = theme;
                  if (speaker) root.dataset.speaker = speaker; else delete root.dataset.speaker;
                }""", [where, theme, speaker])
                for t in (0.1, 2.3, 9.0):
                    assert boxes(at(t)) == boxes(first), (where, theme, speaker, t)


# --- a font whose content area is taller than its em box ------------------------------------

# Noto Sans JP's metrics (an ascent of 1.16em and a descent of 0.29em: a content area of 1.45em,
# 0.28em of it above the em box of the text) put on a face from the system with ascent-override
# and descent-override, so that the test downloads nothing. Shippori Mincho B1, Zen Kaku Gothic
# New and the rest of the Noto family measure the same; Hiragino Sans has no extra height at all.
TALL_FACE = """@font-face { font-family: "tsubu-tall"; ascent-override: 116%; descent-override: 29%;
  src: local("Hiragino Sans W3"), local("HiraginoSans-W3"), local("Noto Sans JP Regular"), local("NotoSansJP-Regular"),
       local("Noto Sans CJK JP Regular"), local("NotoSansCJKjp-Regular"), local("Noto Sans CJK JP"); }
.bubble { font-family: "tsubu-tall"; }"""

# The boxes of a segment's ::before (the highlight's band) and ::after (the underline), from probes
# that take the same geometry (see the stylesheet): WebKit reports the computed insets of a box
# positioned inside an inline against the block around it.
PROBES = """(seg) => { const out = {};
  for (const kind of ["band", "line"]) { const p = document.createElement("span"); p.className = `tsubu-${kind}-probe`;
    seg.append(p); out[kind] = p.getBoundingClientRect(); p.remove(); }
  return out; }"""

# The current segment's text and furigana in colours nothing else has, its highlight's band and
# the underline, and the baseline of the text.
GEOMETRY = """() => { const root = document.querySelector(".tsubu"), seg = root.querySelector('.tsubu-seg[data-state="current"]');
  const box = seg.getBoundingClientRect(), after = getComputedStyle(seg, "::after"), {band, line} = (PROBES)(seg);
  const probe = document.createElement("span"); probe.style.cssText = "display: inline-block; width: 0; height: 0; vertical-align: baseline";
  seg.append(probe); const baseline = probe.getBoundingClientRect().top; probe.remove();
  const rt = seg.querySelector("rt").getBoundingClientRect();
  const em = parseFloat(getComputedStyle(seg).fontSize), content = box.height / em;
  return {box: {left: box.left, right: box.right, top: box.top, bottom: box.bottom}, root: root.getBoundingClientRect().toJSON(),
          em, content, baseline, rt: {top: rt.top, bottom: rt.bottom, left: rt.left, right: rt.right},
          band: {top: band.top, bottom: band.bottom, left: band.left, right: band.right, color: BAND_COLOUR(seg)},
          underline: {bottom: line.bottom, width: parseFloat(after.borderBottomWidth)}}; }""".replace("BAND_COLOUR", BAND_COLOUR).replace("PROBES", PROBES)


# WebKit ignores the two descriptors, so the face keeps the system's metrics there (measured).
NO_METRIC_OVERRIDES = pytest.mark.limitation("webkit", reason="ascent-override and descent-override are not supported, so "
                                             "the test cannot give a face Noto Sans JP's metrics")


def tall(found):
    assert found["content"] > 1.4, "no face matched TALL_FACE: add the system's Japanese face to its src list"
    return found


def rows_with(page, clip, colour, tolerance=40):
    """The rows of a screenshot of the clip that hold a pixel within `tolerance` of the colour, in page coordinates."""
    width, bpp, rows = png_rows(page.screenshot(clip=clip))
    return [clip["y"] + y for y, row in enumerate(rows)
            if any(all(abs(row[x * bpp + i] - colour[i]) <= tolerance for i in range(3)) for x in range(width))]


@NO_METRIC_OVERRIDES
@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("sentence", [TIMED, WHOLE], ids=["timed", "whole"])
def test_every_preset_meets_the_thresholds_in_a_font_with_a_tall_content_area(drawn, theme, sentence):
    at = drawn(sentence, css=TALL_FACE, theme=theme)
    at(1.2 if sentence is TIMED else 5.0)
    tall(at.page.evaluate(GEOMETRY))
    found = at.page.evaluate(CHECK)
    assert found["ok"], found["failures"]
    covered = {(c["state"], c["layer"]) for c in found["checks"]}
    assert covered == {(state, layer) for state in STATES for layer in ("text", "ruby", "underline")} | {("current", "highlight")}
    # the current segment's furigana are on the page (on the plate, over media), not on the highlight
    assert {c["background"] for c in found["checks"] if c["state"] == "current" and c["layer"] == "ruby"} == set(
        {"light": ["#ffffff", "#f1f5f9"], "dark": ["#0f172a", "#1e293b"], "media": ["#000000", "#404040"]}[theme])


@pytest.mark.parametrize("css", ["", pytest.param(TALL_FACE, marks=NO_METRIC_OVERRIDES)], ids=["system-face", "tall-face"])
def test_the_highlight_and_the_underline_are_drawn_from_the_em_box_whatever_the_font(drawn, css):
    at = drawn(TIMED, css=css, theme="light")
    at(1.2)
    found = at.page.evaluate(GEOMETRY)
    if css:
        tall(found)
    else:
        # the system face: content area = em box (Firefox rounds the ascent and descent up to whole pixels)
        assert found["content"] == pytest.approx(1, abs=1 / found["em"])
    em, baseline, spread = found["em"], found["baseline"], 0.06 * found["em"]
    # the band: the em box (0.88em above the baseline to 0.12em below it) and the spread past it,
    # within the rounding of the font's ascent and descent to whole pixels
    assert found["band"]["top"] == pytest.approx(baseline - 0.88 * em - spread, abs=0.75), css
    assert found["band"]["bottom"] == pytest.approx(baseline + 0.12 * em + spread, abs=0.75), css
    assert found["band"]["left"] == pytest.approx(found["box"]["left"] - spread, abs=0.05)
    assert found["band"]["right"] == pytest.approx(found["box"]["right"] + spread, abs=0.05)
    assert found["band"]["color"] == "rgb(29, 78, 216)"
    # the underline: its offset below the em box, not below the segment's box
    assert found["underline"]["bottom"] == pytest.approx(baseline + 0.12 * em + 0.02 * em, abs=0.75), css
    # the reading's box is above the band, apart from what the spread grazes
    assert (found["rt"]["top"] + found["rt"]["bottom"]) / 2 < found["band"]["top"]
    assert found["rt"]["bottom"] - found["band"]["top"] < 0.5 * em, css
    # and in a screenshot: the text's ink lies inside the band, the reading's ink above it
    at.page.evaluate("""() => { const root = document.querySelector(".tsubu");
      root.style.setProperty("--tsubu-current-color", "#00ff00"); root.style.setProperty("--tsubu-current-ruby-color", "#ff0000"); }""")
    clip = {"x": found["box"]["left"] + 2, "y": found["root"]["y"], "width": found["box"]["right"] - found["box"]["left"] - 4, "height": found["root"]["height"]}
    text, reading, band = (rows_with(at.page, clip, c) for c in ((0, 255, 0), (255, 0, 0), (29, 78, 216)))
    assert text and reading and band, css
    assert band[0] <= text[0] and text[-1] <= band[-1], (css, band[0], band[-1], text[0], text[-1])
    assert reading[-1] <= band[0] + 1, (css, reading[-1], band[0])  # one row for anti-aliasing


@pytest.mark.limitation("webkit", reason=VERTICAL_MIRROR)
def test_in_vertical_text_the_highlight_is_drawn_from_the_em_box_too(drawn, engine):
    at = drawn(TIMED, css=TALL_FACE, style="height: 700px", theme="light", writing="vertical")
    at(1.2)
    found = at.page.evaluate("""() => { const seg = document.querySelector('.tsubu-seg[data-state="current"]');
      const box = seg.getBoundingClientRect(), {band, line} = (PROBES)(seg);
      const rt = seg.querySelector("rt").getBoundingClientRect(), em = parseFloat(getComputedStyle(seg).fontSize);
      return {em, content: box.width / em, centre: (box.left + box.right) / 2, rtMiddle: (rt.left + rt.right) / 2,
              band: {left: band.left, right: band.right}, sideLine: line.left}; }""".replace("PROBES", PROBES))
    if engine == "chromium":
        tall(found)
    else:
        # Firefox makes a column of upright text as wide as the em box, whatever the font's ascent
        # and descent; WebKit ignores the overrides (both measured). The content area is the em box.
        assert found["content"] == pytest.approx(1, abs=1 / found["em"])
    em, spread = found["em"], 0.06 * found["em"]
    # across the column the em box is centred in the content area; the band is that and the spread
    assert found["band"]["left"] == pytest.approx(found["centre"] - 0.5 * em - spread, abs=0.25)
    assert found["band"]["right"] == pytest.approx(found["centre"] + 0.5 * em + spread, abs=0.25)
    assert found["sideLine"] == pytest.approx(found["centre"] - 0.5 * em - 0.02 * em, abs=0.25)
    assert found["band"]["right"] < found["rtMiddle"]  # the reading at the right is clear of it
    assert at.page.evaluate(CHECK)["ok"]


def test_nothing_moves_in_a_font_with_a_tall_content_area(drawn):
    at = drawn(LONG, css=TALL_FACE, theme="dark")
    first = at(2.3)
    boxes = lambda f: ([(c["ch"], c["box"]) for c in f["chars"]], [s["box"] for s in f["segments"]], [r["box"] for r in f["rts"]], f["root"])
    for t in (0.1, 2.3, 9.0):
        for on in (False, True):
            assert boxes(at(t, on)) == boxes(first), (t, on)
