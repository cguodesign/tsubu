"""Romaji, and the choice of what is drawn over and under the text.

A segment may carry `romaji`, the romanised reading of the whole segment; options.over and
options.under say which layer (the parts' furigana, the segments' romaji, or nothing) goes on
which side. The HTML is checked in Node; the layout, the switches of both sides, the checks and
the motion presets in a headless browser on the library's own CSS and script."""

import html as entities
import itertools
import json
import re
import shutil
import subprocess

import pytest

from support import LONG, ROOT, SCRIPT, TIMED, WHOLE, block_slack, run_library
from test_theme import NO_METRIC_OVERRIDES, TALL_FACE

# The romaji of every spoken segment of the shared sentences, as a caller would give them: by the
# word, with the particles written as they are said (は as wa) and long vowels marked.
ROMAJI = {
    "timed": ["kesa", "furui", "hon'ya de", "omoshiroi", "chizu o", "kaimashita"],
    "whole": ["senshū", "Tōkyō de", "eigo no", "jugyō o", "ukemashita"],
    "long": ["eki no", "mae no", "chiisana", "mise de wa", "maiasa", "rokuji kara", "yakitate no", "pan ga", "urarete", "imasu"],
}


def with_romaji(sentence, romaji):
    """The sentence with each spoken segment's romaji, in order (None leaves a segment without)."""
    spoken = iter(romaji)
    segments = []
    for s in sentence["segments"]:
        s = dict(s)
        if s.get("kind") != "punct":
            r = next(spoken)
            if r is not None:
                s["romaji"] = r
        segments.append(s)
    return {**sentence, "segments": segments}


R_TIMED = with_romaji(TIMED, ROMAJI["timed"])
R_WHOLE = with_romaji(WHOLE, ROMAJI["whole"])
R_LONG = with_romaji(LONG, ROMAJI["long"])

# Which layer goes over the text and which under it.
LAYOUTS = [("ruby", "romaji"), ("romaji", "ruby"), ("romaji", "none"), ("none", "romaji")]
LAYOUT_IDS = [f"{o}-over-{u}-under" for o, u in LAYOUTS]
V = {"writing": "vertical"}
TALL = "height: 400px"


def node(expression):
    runner = "const T = require(process.argv[1]); process.stdout.write(JSON.stringify((() => { %s })()));"
    done = subprocess.run([shutil.which("node"), "-e", runner % expression, str(SCRIPT)], capture_output=True,
                          text=True, encoding="utf-8", timeout=30, check=True)
    return json.loads(done.stdout)


def plain(html):
    """The text of some HTML as a program that knows no ruby shows it: the tags dropped."""
    return entities.unescape(re.sub(r"<[^>]+>", "", html))


# --- the HTML, in Node -------------------------------------------------------------------------

@pytest.mark.parametrize("options", [{}, {"over": "ruby"}, {"over": "ruby", "under": "none"}, {"ruby": False},
                                     {"announceRuby": False, "theme": "dark", "writing": "vertical", "motion": "mask"}],
                         ids=["defaults", "over-ruby", "over-ruby-under-none", "ruby-off", "other-options"])
def test_with_furigana_over_and_nothing_under_the_html_is_what_it_was_romaji_or_not(options):
    # the romaji are not drawn, so the HTML is byte for byte that of the sentence without them
    for sentence, with_ in ((TIMED, R_TIMED), (WHOLE, R_WHOLE), (LONG, R_LONG)):
        assert run_library(with_, options=options)["html"] == run_library(sentence, options=options)["html"]
    found = node("""const a = T.sentence(%s), b = T.sentence(%s);
      return [1.2, 9].every((t) => a.htmlAt(t) === b.htmlAt(t));""" % (json.dumps(R_TIMED), json.dumps(TIMED)))
    assert found is True


def test_romaji_under_the_text_wrap_each_segment_in_a_ruby_of_its_own():
    html = run_library(R_TIMED, options={"under": "romaji"})["html"]
    assert html.startswith('<span class="tsubu" lang="ja" data-timing="segments" data-ruby="on" data-under-layer="romaji" data-under="on">')
    # the segment's parts, their furigana included, are the base; the romaji are its reading
    assert ('<span class="tsubu-seg" data-index="2"><span class="tsubu-stack"><ruby class="tsubu-romaji"><ruby>古<rp>（</rp>'
            '<rt>ふる</rt><rp>）</rp></ruby>い<rp>（</rp><rt>furui</rt><rp>）</rp></ruby></span></span>') in html
    assert '<span class="tsubu-stack"><ruby class="tsubu-romaji">けさ<rp>（</rp><rt>kesa</rt><rp>）</rp></ruby></span>' in html
    assert html.count('class="tsubu-romaji"') == 6  # not around punctuation
    assert '<span class="tsubu-seg" data-index="1" data-kind="punct">、</span>' in html


def test_romaji_over_the_text_and_furigana_under_it():
    html = run_library(R_TIMED, options={"over": "romaji", "under": "ruby", "ruby": False})["html"]
    assert ' data-ruby="off" data-over-layer="romaji" data-under-layer="ruby" data-under="on">' in html
    assert html.count("<rt>") == 11  # five furigana, six romaji


def test_a_layer_on_neither_side_is_not_written():
    over_only = run_library(R_TIMED, options={"over": "romaji"})["html"]
    assert ' data-ruby="on" data-over-layer="romaji">' in over_only and "data-under" not in over_only
    assert "ふる" not in over_only and '<ruby class="tsubu-romaji">古い<rp>（</rp><rt>furui</rt><rp>）</rp></ruby>' in over_only
    bare = run_library(R_TIMED, options={"over": "none"})["html"]
    assert ' data-ruby="on" data-over-layer="none">' in bare and "<rt" not in bare and "<rp" not in bare
    assert plain(bare) == "けさ、古い本屋で面白い地図を買いました。"
    furigana_under = run_library(R_TIMED, options={"over": "none", "under": "ruby"})["html"]
    assert ' data-over-layer="none" data-under-layer="ruby" data-under="on">' in furigana_under and "furui" not in furigana_under


def test_a_segment_without_romaji_has_no_romaji_ruby():
    sentence = with_romaji(TIMED, ["kesa", None, "hon'ya de", None, "chizu o", None])
    html = run_library(sentence, options={"under": "romaji"})["html"]
    assert html.count('class="tsubu-romaji"') == 3
    assert '<span class="tsubu-seg" data-index="2"><ruby>古<rp>（</rp><rt>ふる</rt><rp>）</rp></ruby>い</span>' in html


def test_without_ruby_each_reading_follows_what_it_reads_in_parentheses():
    # what a reader view, a feed reader or a text browser shows: the furigana after their base and
    # the romaji after their segment, in the same full-width parentheses
    assert plain(run_library(R_TIMED, options={"under": "romaji"})["html"]) == (
        "けさ（kesa）、古（ふる）い（furui）本屋（ほんや）で（hon'ya de）面白（おもしろ）い（omoshiroi）"
        "地図（ちず）を（chizu o）買（か）いました（kaimashita）。")
    # whichever side each is on
    assert plain(run_library(R_TIMED, options={"over": "romaji", "under": "ruby"})["html"]) == plain(
        run_library(R_TIMED, options={"under": "romaji"})["html"])
    assert plain(run_library(R_TIMED, options={"over": "romaji"})["html"]) == (
        "けさ（kesa）、古い（furui）本屋で（hon'ya de）面白い（omoshiroi）地図を（chizu o）買いました（kaimashita）。")


def test_with_announce_ruby_off_the_romaji_are_hidden_from_screen_readers_too():
    html = run_library(R_TIMED, options={"under": "romaji", "announceRuby": False})["html"]
    assert html.count('<rt aria-hidden="true">') == html.count("<rt") == 11
    assert html.count('<rp aria-hidden="true">') == html.count("<rp") == 22
    assert '<rp aria-hidden="true">（</rp><rt aria-hidden="true">kesa</rt><rp aria-hidden="true">）</rp>' in html


def test_romaji_are_escaped_and_never_set_upright():
    sentence = {"segments": [{"parts": [{"text": "AI"}, {"text": "は"}], "romaji": "<ei ai> & wa", "start": 0, "end": 1},
                             {"parts": [{"text": "を"}], "romaji": "o", "start": 1, "end": 2}]}
    html = run_library(sentence, options={"under": "romaji", "writing": "vertical"})["html"]
    # the parts' short runs stand upright in vertical text; the romaji lie on their side, as other Latin text does
    assert '<span class="tsubu-upright">AI</span>' in html and "<rt>&lt;ei ai&gt; &amp; wa</rt>" in html and "<rt>o</rt>" in html


@pytest.mark.parametrize("romaji, message", [
    ("", "segment 0: `romaji` must be a non-empty string"),
    (3, "segment 0: `romaji` must be a non-empty string"),
    (["ke", "sa"], "segment 0: `romaji` must be a non-empty string"),
])
def test_romaji_must_be_a_non_empty_string(romaji, message):
    found = run_library({"segments": [{"parts": [{"text": "けさ"}], "romaji": romaji}]})
    assert found["error"] == f"tsubu: {message}"


def test_punctuation_carries_no_romaji():
    found = run_library({"segments": [{"parts": [{"text": "本"}]}, {"parts": [{"text": "。"}], "kind": "punct", "romaji": "."}]})
    assert found["error"] == "tsubu: segment 1: punctuation carries no romaji"


@pytest.mark.parametrize("options, message", [
    ({"over": "furigana"}, 'options.over must be "ruby", "romaji" or "none"'),
    ({"under": True}, 'options.under must be "ruby", "romaji" or "none"'),
    ({"under": "ruby"}, 'options.over and options.under are both "ruby": a layer can be drawn on one side only'),
    ({"over": "romaji", "under": "romaji"}, 'options.over and options.under are both "romaji": a layer can be drawn on one side only'),
])
def test_the_sides_are_checked(options, message):
    assert run_library(R_TIMED, options=options)["error"] == f"tsubu: {message}"


def test_both_sides_can_be_empty_and_times_are_kept():
    found = run_library(R_TIMED, times=[1.2], options={"over": "none", "under": "none"})
    assert "<rt" not in found["html"] and found["states"][0]["current"] == 3


def test_the_exporters_and_the_importers_take_romaji_and_leave_them_out():
    script = """const T = require(process.argv[1]); global.Tsubu = T; const X = require(process.argv[2]);
      const a = JSON.parse(process.argv[3]), b = JSON.parse(process.argv[4]);
      process.stdout.write(JSON.stringify([X.toWebVTT(a) === X.toWebVTT(b), X.toASS(a) === X.toASS(b),
        X.toSRT(a, {mode: "segments"}) === X.toSRT(b, {mode: "segments"})]));"""
    done = subprocess.run([shutil.which("node"), "-e", script, str(SCRIPT), str(ROOT / "tsubu-export.js"),
                           json.dumps(R_TIMED), json.dumps(TIMED)], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == [True, True, True]


# --- in the browser ------------------------------------------------------------------------------

LAYERS = """() => {
  const root = document.querySelector(".tsubu");
  const box = (r) => ({left: r.left, right: r.right, top: r.top, bottom: r.bottom});
  const segs = [...root.querySelectorAll(":scope > .tsubu-unit > .tsubu-seg")];
  // the boxes of a segment's ::before (the highlight's band) and ::after (the underline), from
  // probes that take the same geometry (see the stylesheet)
  const probe = (el, kind) => { const p = document.createElement("span"); p.className = `tsubu-${kind}-probe`; el.append(p);
    const r = box(p.getBoundingClientRect()); p.remove(); return r; };
  const chars = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (node.parentElement.closest("rt, rp")) continue;
    for (let i = 0; i < node.data.length; i++) {
      const range = document.createRange(); range.setStart(node, i); range.setEnd(node, i + 1);
      chars.push({ch: node.data[i], seg: segs.indexOf(node.parentElement.closest(".tsubu-seg")),
                  hidden: !!node.parentElement.closest("[data-off-page]"), box: box(range.getBoundingClientRect())});
    }
  }
  const readings = [...root.querySelectorAll("rt")].map((rt) => {
    const range = document.createRange(); range.selectNodeContents(rt);
    const classes = rt.parentElement.classList, ink = box(range.getBoundingClientRect());
    const layer = classes.contains("tsubu-romaji") ? "romaji" : classes.contains("tsubu-origin") ? "origin" : "ruby";
    // An origin is moved off the text by relative positioning, past its <rt>'s box (see the
    // stylesheet), so its box is where its text is drawn (tests/test_origin.py).
    return {layer, text: rt.textContent, seg: segs.indexOf(rt.closest(".tsubu-seg")), hidden: !!rt.closest("[data-off-page]"),
            visibility: getComputedStyle(rt).visibility, size: parseFloat(getComputedStyle(rt).fontSize),
            box: layer === "origin" ? ink : box(rt.getBoundingClientRect()), ink};
  });
  const segments = segs.map((el) => ({punct: el.dataset.kind === "punct", offPage: el.hasAttribute("data-off-page"),
    box: box(el.getBoundingClientRect()), band: probe(el, "band"), line: probe(el, "line"),
    lineWidth: parseFloat(getComputedStyle(el, "::after").borderBottomWidth) || parseFloat(getComputedStyle(el, "::after").borderLeftWidth)}));
  return {root: box(root.getBoundingClientRect()), bubble: box(document.getElementById("bubble").getBoundingClientRect()),
          fontSize: parseFloat(getComputedStyle(root).fontSize), writing: getComputedStyle(root).writingMode, chars, readings, segments};
}"""


def layers(at, t=None, over=None, under=None):
    """Applies t and the switches of the two sides (None leaves them), and measures the readings."""
    at.page.evaluate("""([t, over, under]) => { const root = document.querySelector(".tsubu");
      if (over !== null) Tsubu.setAnnotation(root, "over", over);
      if (under !== null) Tsubu.setAnnotation(root, "under", under);
      if (t !== null) S.apply(root, t); }""", [t, over, under])
    return at.page.evaluate(LAYERS)


def side_of(layer, over, under):
    # origins are always over the text (tests/test_origin.py)
    return "over" if layer in (over, "origin") else "under" if layer == under else None


def frozen(found):
    """Everything that must not move: every character, segment, reading and the sentence's box."""
    return ([(c["ch"], c["box"]) for c in found["chars"]], [s["box"] for s in found["segments"]],
            [r["box"] for r in found["readings"]], found["root"])


def overlaps(a, b, slack):
    return min(a["right"], b["right"]) - max(a["left"], b["left"]) > slack and \
        min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]) > slack


@pytest.mark.parametrize("over, under", LAYOUTS, ids=LAYOUT_IDS)
@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
@pytest.mark.parametrize("sentence", [R_TIMED, R_LONG], ids=["one-line", "two-lines"])
def test_no_character_moves_when_either_side_or_both_are_switched(drawn, sentence, writing, over, under):
    vertical = writing == "vertical"
    at = drawn(sentence, over=over, under=under, width=900 if sentence is R_TIMED else 520,
               **({"style": TALL, "writing": "vertical"} if vertical else {}))
    first = layers(at)
    if sentence is R_LONG:  # readings on a second line (column) too
        across = (lambda b: round(b["left"])) if vertical else (lambda b: round(b["top"]))
        assert len({across(c["box"]) for c in first["chars"]}) >= 2
    seen = []
    for t in (0.1, 1.2, 2.2, 9.0):
        for shown_over, shown_under in itertools.product((False, True), repeat=2):
            found = layers(at, t, shown_over, shown_under)
            assert frozen(found) == frozen(first), (t, shown_over, shown_under)
            # and the switches do hide and show their side's readings, and only those
            for r in found["readings"]:
                side = side_of(r["layer"], over, under)
                assert r["visibility"] == ("visible" if {"over": shown_over, "under": shown_under}[side] else "hidden"), (r, side)
            seen.append(found)
    assert {r["layer"] for r in first["readings"]} == {over, under} - {"none"}


@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
def test_a_box_added_to_a_segment_and_the_blur_preset_move_nothing(drawn, writing):
    # WebKit laid out a line of nested ruby with readings on both sides again, wider, when a
    # positioned box was added to a segment or a reading was blurred; the romaji's ruby is in an
    # inline-block for that (see the stylesheet)
    at = drawn(R_LONG, width=520, over="romaji", under="ruby", motion="blur", **({"style": TALL, **V} if writing == "vertical" else {}))
    page = at.page
    first = frozen(page.evaluate(LAYERS))
    for t in (0.1, 2.3, 4.6):
        page.evaluate("""(t) => { S.apply(document.querySelector('.tsubu'), t);
          for (const seg of document.querySelectorAll('.tsubu-seg')) { const p = document.createElement('span');
            p.style.cssText = 'position: absolute; left: 0; top: 0'; seg.append(p); p.getBoundingClientRect(); p.remove(); } }""", t)
        assert frozen(page.evaluate(LAYERS)) == first, t


def test_set_ruby_is_set_annotation_over(drawn):
    at = drawn(R_TIMED, over="romaji", under="ruby")
    page = at.page
    for on in (False, True):
        page.evaluate("(on) => Tsubu.setRuby(document.querySelector('.tsubu'), on)", on)
        by_ruby = page.evaluate("() => document.querySelector('.tsubu').outerHTML")
        page.evaluate("(on) => Tsubu.setAnnotation(document.querySelector('.tsubu'), 'over', on)", not on)
        page.evaluate("(on) => Tsubu.setAnnotation(document.querySelector('.tsubu'), 'over', on)", on)
        assert page.evaluate("() => document.querySelector('.tsubu').outerHTML") == by_ruby
        assert page.evaluate("() => document.querySelector('.tsubu').dataset.ruby") == ("on" if on else "off")
    errors = page.evaluate("""() => ['left', 'Over', undefined].map((side) => {
      try { Tsubu.setAnnotation(document.querySelector('.tsubu'), side, true); } catch (e) { return e.message; } })
      .concat([(() => { try { Tsubu.setAnnotation(document.body, 'under', true); } catch (e) { return e.message; } })()])""")
    assert errors == ['tsubu: setAnnotation: what is switched must be "over", "under" or "origin"'] * 3 + ['tsubu: setAnnotation needs the element with class "tsubu"']


@pytest.mark.parametrize("over, under", LAYOUTS, ids=LAYOUT_IDS)
@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
def test_a_sentence_drawn_with_a_side_hidden_has_the_same_layout(drawn, writing, over, under):
    options = {"over": over, "under": under, **({"style": TALL, "writing": "vertical"} if writing == "vertical" else {"width": 520})}
    shown = layers(drawn(R_LONG, **options))
    hidden = drawn(R_LONG, ruby=False, **options)
    found = layers(hidden, None, None, False)
    assert frozen(found) == frozen(shown)
    assert all(r["visibility"] == "hidden" for r in found["readings"])


def placed(found, over, under, graze=1):
    """Each reading on its side of its segment's text, inside the sentence's box, clear of the
    underline (the side line in vertical text) and of every other character and reading. A reading's
    box may reach `graze` pixels into the em box of the text: in a font whose content area is taller
    than its em box, so is the reading's, whose ink is centred in it. There readings are kept apart
    by their em boxes too."""
    vertical = found["writing"] == "vertical-rl"
    em = found["fontSize"]

    def em_box(b, em=em):
        # A character's box is the font's content area, which in some fonts reaches past its em box
        # into the readings (see tests/test_theme.py): the em box lies 62% of the extra height down
        # in horizontal text, and in the middle across a column.
        if vertical:
            middle = (b["left"] + b["right"]) / 2
            return {**b, "left": middle - min(em, b["right"] - b["left"]) / 2, "right": middle + min(em, b["right"] - b["left"]) / 2}
        top = b["top"] + 0.62 * max(0, b["bottom"] - b["top"] - em)
        return {**b, "top": top, "bottom": min(b["bottom"], top + em)}

    text = {}
    for c in found["chars"]:
        if not c["hidden"]:
            box = em_box(c["box"])
            b = text.setdefault(c["seg"], dict(box))
            b.update(left=min(b["left"], box["left"]), right=max(b["right"], box["right"]),
                     top=min(b["top"], box["top"]), bottom=max(b["bottom"], box["bottom"]))
    readings = [r for r in found["readings"] if not r["hidden"]]
    root, bubble = found["root"], found["bubble"]
    for r in readings:
        b, base, line = r["box"], text[r["seg"]], found["segments"][r["seg"]]["line"]
        ink = r["ink"] if graze <= 1 else em_box(r["ink"], r["size"])
        side = side_of(r["layer"], over, under)
        for edge in ("left", "top"):
            assert b[edge] >= root[edge] - 0.5 and b[edge] >= bubble[edge] - 0.5, (r, root)
        for edge in ("right", "bottom"):
            assert b[edge] <= root[edge] + 0.5 and b[edge] <= bubble[edge] + 0.5, (r, root)
        if not vertical:
            assert ink["left"] < base["right"] and ink["right"] > base["left"]  # over or under its own text
            if side == "over":
                assert b["bottom"] <= base["top"] + graze, (r, base)
            else:
                assert b["top"] >= base["bottom"] - graze, (r, base)
                # the underline runs between the text and the reading
                assert ink["top"] >= line["bottom"], (r, line)
        else:
            assert ink["top"] < base["bottom"] and ink["bottom"] > base["top"]
            if side == "over":
                assert b["left"] >= base["right"] - graze, (r, base)
            else:
                assert b["right"] <= base["left"] + graze, (r, base)
                width = found["segments"][r["seg"]]["lineWidth"]
                assert ink["right"] <= line["left"], (r, line)  # the side line's border is at the left of its box
                assert line["left"] + width <= base["left"] + 0.1 * found["fontSize"]
    # nothing overlaps: readings, characters and underlines, across lines and within them
    slack = block_slack(found["engine"])
    chars = [(c["ch"], em_box(c["box"])) for c in found["chars"] if not c["hidden"]]
    trimmed = lambda r: em_box(r["ink"], r["size"])  # the reading's own em box, in a tall face
    boxes = [(r["text"], r["box"] if graze <= 1 else trimmed(r)) for r in readings]
    for (x, a), (y, b) in itertools.combinations(boxes, 2):
        assert not overlaps(a, b, slack), (x, a, y, b)
    for (x, a), (y, b) in itertools.product(boxes, chars):
        assert not overlaps(a, b, max(slack, graze)), (x, a, y, b)
    # and no underline (side line) runs through a reading's text
    for s in found["segments"]:
        if s["punct"] or s["offPage"]:
            continue
        line, width = s["line"], s["lineWidth"]
        drawn_line = {**line, "right": line["left"] + width} if vertical else {**line, "top": line["bottom"] - width}
        for r in readings:
            ink = r["ink"] if graze <= 1 else trimmed(r)
            assert not overlaps(drawn_line, ink, 0.5), (r["text"], ink, drawn_line)


@pytest.mark.parametrize("over, under", LAYOUTS, ids=LAYOUT_IDS)
@pytest.mark.parametrize("sentence", [R_TIMED, R_LONG, R_WHOLE], ids=["one-line", "two-lines", "whole"])
def test_each_layer_sits_on_its_side_inside_the_sentence_and_clear_of_everything(drawn, engine, sentence, over, under):
    found = layers(drawn(sentence, over=over, under=under, width=900 if sentence is R_TIMED else 520), 1.2)
    placed({**found, "engine": engine}, over, under)


@pytest.mark.parametrize("over, under", LAYOUTS, ids=LAYOUT_IDS)
@pytest.mark.parametrize("sentence", [R_TIMED, R_LONG, R_WHOLE], ids=["one-column", "columns", "whole"])
def test_in_vertical_text_over_is_at_the_right_and_under_at_the_left(drawn, engine, sentence, over, under):
    found = layers(drawn(sentence, over=over, under=under, style=TALL, **V), 1.2)
    placed({**found, "engine": engine}, over, under)


# In a face with Noto Sans JP's metrics (a content area of 1.45em; see tests/test_theme.py), whose
# readings are thicker, the layers keep to their sides and clear of each other too.
@NO_METRIC_OVERRIDES
@pytest.mark.parametrize("over, under", LAYOUTS[:2], ids=LAYOUT_IDS[:2])
@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
def test_in_a_font_with_a_tall_content_area_the_layers_keep_apart(drawn, engine, engine_version, writing, over, under):
    options = {"style": TALL, **V} if writing == "vertical" else {"width": 520}
    at = drawn(R_LONG, css=TALL_FACE, over=over, under=under, **options)
    first = layers(at, 1.2)
    across = (lambda b: b["right"] - b["left"]) if writing == "vertical" else (lambda b: b["bottom"] - b["top"])
    # Firefox 139 makes a column of upright text as wide as the em box whatever the face's metrics
    # (see tests/test_theme.py); everywhere else the face must have taken them
    if not (writing == "vertical" and engine == "firefox" and engine_version < 153):
        assert max(across(c["box"]) for c in first["chars"]) / first["fontSize"] > 1.4, "no face matched TALL_FACE"
    placed({**first, "engine": engine}, over, under, graze=0.15 * first["fontSize"])
    for shown in itertools.product((False, True), repeat=2):
        assert frozen(layers(at, 2.3, *shown)) == frozen(first), shown


@pytest.mark.parametrize("over, under", LAYOUTS, ids=LAYOUT_IDS)
def test_in_vertical_text_the_highlight_and_the_side_line_stay_on_the_em_box(drawn, over, under):
    # Each segment's line is wide enough for every reading, so its left edge, from which the
    # highlight and the side line are drawn, lies as far from the text whichever readings it has
    # (see the stylesheet): punctuation, a segment with furigana and romaji, one with romaji alone.
    sentence = with_romaji(TIMED, ["kesa", "furui", None, "omoshiroi", "chizu o", "kaimashita"])
    found = layers(drawn(sentence, over=over, under=under, style=TALL, **V), 1.2)
    em, spread = found["fontSize"], 0.06 * found["fontSize"]
    for i, s in enumerate(found["segments"]):
        chars = [c["box"] for c in found["chars"] if c["seg"] == i]
        centre = sum((b["left"] + b["right"]) / 2 for b in chars) / len(chars)
        assert s["band"]["left"] == pytest.approx(centre - 0.5 * em - spread, abs=0.5), (i, s, centre)
        assert s["band"]["right"] == pytest.approx(centre + 0.5 * em + spread, abs=0.5), (i, s, centre)
        if not s["punct"]:
            assert s["line"]["left"] == pytest.approx(centre - 0.5 * em - 0.02 * em, abs=0.5), (i, s, centre)
    # and every segment of a column has the same left edge, from which the columns are counted
    columns = {round(s["band"]["left"]) for s in found["segments"]}
    assert len(columns) >= 2 and len({round(s["box"]["left"], 1) for s in found["segments"]}) == len(columns)


SAME = """([input, options, times]) => times.map((t) => {
  const s = Tsubu.sentence(input, options), holder = document.createElement("div");
  holder.innerHTML = s.html;
  document.body.append(holder);
  s.apply(holder.firstElementChild, t);
  const rendered = document.createElement("div");
  rendered.innerHTML = s.htmlAt(t);
  const result = [t, holder.firstElementChild.isEqualNode(rendered.firstElementChild), holder.innerHTML, rendered.innerHTML];
  holder.remove();
  return result;
})"""


@pytest.mark.parametrize("options", [{"under": "romaji"}, {"over": "romaji", "under": "ruby", "ruby": False},
                                     {"over": "romaji", "writing": "vertical", "motion": "mask", "announceRuby": False}],
                         ids=["romaji-under", "romaji-over-ruby-under", "romaji-over-vertical"])
def test_html_at_t_is_exactly_what_apply_makes_of_the_html(drawn, engine, options):
    page = drawn(R_TIMED).page
    for sentence in (R_TIMED, R_WHOLE, R_LONG):
        for t, equal, live, rendered in page.evaluate(SAME, [sentence, options, [-1, 0.25, 1.2, 2.2, 5.0, 9.0]]):
            assert equal, (t, live, rendered)
            if engine != "firefox":  # Firefox writes the style attribute elsewhere (see tests/test_html_at.py)
                assert rendered == live, t


# --- the checks ----------------------------------------------------------------------------------

CHECK = "(options) => Tsubu.checkContrast(document.querySelector('.tsubu'), options || undefined)"
FIT = "(options) => Tsubu.checkFit(document.querySelector('.tsubu'), options || undefined)"
STATES = ["static", "future", "current", "past"]


@pytest.mark.parametrize("over, under", LAYOUTS[:3], ids=LAYOUT_IDS[:3])
@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
@pytest.mark.parametrize("theme", ["light", "dark", "media"])
def test_every_theme_meets_its_thresholds_with_romaji_on_either_side(drawn, theme, writing, over, under):
    at = drawn(R_TIMED, theme=theme, over=over, under=under, **({"style": TALL, **V} if writing == "vertical" else {}))
    layers(at, 1.2, False, False)  # hidden readings are checked too: checkContrast shows both sides
    found = at.page.evaluate(CHECK)
    assert found["ok"], found["failures"]
    covered = {(c["state"], c["layer"]) for c in found["checks"]}
    drawn_layers = {"ruby", "romaji"} & {over, under}
    assert covered == {(s, layer) for s in STATES for layer in {"text", "underline"} | drawn_layers} | {("current", "highlight")}
    # romaji are held to the furigana's threshold, and sit on the page, not on the highlight
    romaji = [c for c in found["checks"] if c["layer"] == "romaji"]
    assert {c["minimum"] for c in romaji} == {4.5}
    page = {"light": {"#ffffff", "#f1f5f9"}, "dark": {"#0f172a", "#1e293b"}, "media": {"#000000", "#404040"}}[theme]
    assert {c["background"] for c in romaji if c["state"] == "current"} == page


def test_romaji_take_the_furigana_colours_and_threshold(drawn):
    at = drawn(R_TIMED, theme="light", under="romaji")
    at.page.evaluate("() => document.querySelector('.tsubu').style.setProperty('--tsubu-current-ruby-color', '#dbeafe')")
    failed = at.page.evaluate(CHECK)["failures"]
    assert {(f["state"], f["layer"]) for f in failed} == {("current", "ruby"), ("current", "romaji")}
    stricter = at.page.evaluate(CHECK, {"thresholds": {"ruby": 9}})
    assert {f["layer"] for f in stricter["failures"]} >= {"romaji"}
    assert {c["minimum"] for c in stricter["checks"] if c["layer"] == "romaji"} == {9}


@pytest.mark.parametrize("over, under", LAYOUTS[:3], ids=LAYOUT_IDS[:3])
@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
def test_a_sentence_with_romaji_that_fits_reports_nothing(drawn, writing, over, under):
    style = "height: 400px; width: max-content" if writing == "vertical" else ""
    for sentence in (R_TIMED, R_LONG):
        at = drawn(sentence, over=over, under=under, width=520, style=style, **(V if writing == "vertical" else {}))
        layers(at, 1.2, False, False)  # the check shows both sides itself
        found = at.page.evaluate(FIT)
        assert found["ok"], found["issues"]


def test_romaji_past_the_container_are_reported_as_clipped(drawn):
    at = drawn(R_TIMED, width=900, under="romaji", style="--tsubu-under-reserve: 0px; height: 70px")
    at.page.add_style_tag(content=".tsubu { margin-top: 0.2em; }")
    found = at.page.evaluate(FIT)
    clipped = [i for i in found["issues"] if i["kind"] == "ruby-clipped"]
    assert clipped and all("the romaji" in i["message"] for i in clipped), found["issues"]
    assert {i["segment"] for i in clipped} <= {0, 2, 3, 4, 5, 6}


# --- motion, forced colours, screen readers, paging -------------------------------------------------

LOOK = """() => [...document.querySelectorAll('.tsubu-seg')].map((s) => { const rt = s.querySelector('.tsubu-romaji > rt');
  if (!rt) return null; const st = getComputedStyle(rt);
  return {state: s.dataset.state || null, visibility: st.visibility, color: st.color, filter: st.filter,
          segFilter: getComputedStyle(s).filter}; }).filter(Boolean)"""


@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
@pytest.mark.parametrize("preset", ["appear", "mask", "blur", "underline-draw"])
def test_motion_presets_treat_romaji_as_they_treat_furigana(drawn, preset, writing):
    at = drawn(R_TIMED, motion=preset, under="romaji", **({"style": TALL, **V} if writing == "vertical" else {}))
    layers(at, 1.2)  # けさ、古い past; 本屋で current; the rest future
    look = at.page.evaluate(LOOK)
    later = [x for x in look if x["state"] == "future"]
    now = [x for x in look if x["state"] in ("current", "past")]
    assert later and now
    if preset == "appear":
        assert {x["visibility"] for x in later} == {"hidden"} and {x["visibility"] for x in now} == {"visible"}
    if preset == "mask":
        assert {x["color"] for x in later} == {"rgba(0, 0, 0, 0)"} and "rgba(0, 0, 0, 0)" not in {x["color"] for x in now}
    if preset == "blur":
        if writing == "horizontal":  # blurred on their own, as furigana are: 0.15em of 20px
            assert {x["filter"] for x in later} == {"blur(3px)"}
        else:  # the inline-block segment's filter reaches them
            assert {x["segFilter"] for x in later} == {"blur(6px)"} and {x["filter"] for x in later} == {"none"}
        assert {x["filter"] for x in now} == {"none"} and {x["segFilter"] for x in now} == {"none"}
    if preset == "underline-draw":
        assert {(x["visibility"], x["filter"]) for x in look} == {("visible", "none")}
        assert "rgba(0, 0, 0, 0)" not in {x["color"] for x in look}
    # and a revealed segment's romaji are drawn whatever t is
    at.page.evaluate("() => Tsubu.setRevealed(document.querySelector('.tsubu'), 'all')")
    assert all(x["visibility"] == "visible" and x["filter"] == "none" and x["color"] != "rgba(0, 0, 0, 0)" for x in at.page.evaluate(LOOK))


def test_no_preset_moves_a_character_or_a_reading(drawn):
    first = frozen(layers(drawn(R_LONG, width=520, over="romaji", under="ruby"), 2.3))
    for preset in ("appear", "mask", "blur", "underline-draw"):
        at = drawn(R_LONG, width=520, over="romaji", under="ruby", motion=preset)
        for t in (0.1, 2.3, 4.6):
            assert frozen(layers(at, t)) == first, (preset, t)


def test_in_forced_colours_the_romaji_of_the_segment_being_spoken_take_the_page_colour(drawn):
    at = drawn(R_TIMED, theme="light", under="romaji")
    before = frozen(layers(at, 1.2))
    at.page.emulate_media(forced_colors="active")
    canvas_text = at.page.evaluate("() => { const d = document.createElement('div'); d.style.color = 'CanvasText'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; }")
    current = at.page.evaluate("() => getComputedStyle(document.querySelector('.tsubu-seg[data-state=\"current\"] .tsubu-romaji > rt')).color")
    assert current == canvas_text
    assert frozen(layers(at)) == before


def test_screen_readers_read_the_romaji_unless_announce_ruby_is_off(drawn):
    spoken = drawn(R_TIMED, under="romaji").page.locator("#bubble").aria_snapshot()
    assert "furui" in spoken and "ふる" in spoken and "（" not in spoken
    quiet_at = drawn(R_TIMED, under="romaji", announceRuby=False)
    quiet = quiet_at.page.locator("#bubble").aria_snapshot()
    assert "furui" not in quiet and "ふる" not in quiet and "古" in quiet
    assert {r["visibility"] for r in layers(quiet_at)["readings"]} == {"visible"}  # still drawn


def test_without_ruby_layout_the_romaji_follow_their_segment_in_parentheses(drawn):
    at = drawn(R_TIMED, under="romaji", css="ruby, rt, rp { display: inline !important; } .tsubu rt { font-size: inherit; }")
    text = at.page.evaluate("() => document.querySelector('.tsubu').innerText.replace(/\\s/g, '')")
    assert text == "けさ（kesa）、古（ふる）い（furui）本屋（ほんや）で（hon'yade）面白（おもしろ）い（omoshiroi）地図（ちず）を（chizuo）買（か）いました（kaimashita）。"


@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
def test_pages_hold_their_lines_and_the_switches_do_not_reflow_them(drawn, engine, writing):
    from test_lines import VERY_LONG
    romaji = ["kinō no", "yoru", "ekimae no", "atarashii", "rāmen'ya de", "daigaku", "jidai no", "tomodachi to",
              "hisashiburi ni", "atte", "osoku made", "iroiro na", "hanashi o", "shimashita"]
    sentence = with_romaji(VERY_LONG, romaji)
    style = "--tsubu-max-lines: 2; " + ("height: 420px" if writing == "vertical" else "")
    at = drawn(sentence, width=420, style=style, over="ruby", under="romaji", **(V if writing == "vertical" else {}))
    across = (lambda b: -round(b["left"])) if writing == "vertical" else (lambda b: round(b["top"]))
    pages = set()
    for i, s in enumerate(sentence["segments"]):
        if "start" not in s:
            continue
        found = layers(at, s["start"])
        page = at.page.evaluate("() => document.querySelector('.tsubu').dataset.page")
        pages.add(page)
        shown = [c for c in found["chars"] if not c["hidden"]]
        assert any(c["seg"] == i for c in shown), i  # the segment being spoken is on the page
        starts = sorted({across(found["segments"][j]["box"]) for j in {c["seg"] for c in shown}})
        assert len(starts) <= 2 or starts[2] - starts[0] < found["fontSize"], (i, starts)
        for over in (False, True):
            for under in (False, True):
                assert frozen(layers(at, s["start"], over, under)) == frozen(found), (i, over, under)
        placed({**found, "chars": shown, "engine": engine}, "ruby", "romaji")
    assert len(pages) >= 3
