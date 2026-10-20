"""Loanwords' origins, drawn over the text.

A part may carry `origin`, { text, lang, wasei? }: the word a loanword comes from, its language,
and whether it is a pseudo-loanword coined in Japanese. With options.origin "over" each such part
without furigana is a ruby of its own whose reading is its origin, in the furigana's row;
Tsubu.setAnnotation(root, "origin", on) switches them. The HTML is checked in Node; the layout, the
switches, the checks and the motion presets in a headless browser on the library's own CSS and
script, as tests/test_romaji.py does for romaji."""

import itertools
import json
import shutil
import subprocess

import pytest

from support import ROOT, SCRIPT, block_slack, run_library
from test_romaji import LAYERS, frozen, node, placed, plain, with_romaji
from test_theme import NO_METRIC_OVERRIDES, TALL_FACE


def part(text, ruby=None, origin=None):
    made = {"text": text}
    if ruby:
        made["ruby"] = ruby
    if origin:
        made["origin"] = origin
    return made


def seg(*parts, start=None, end=None, punct=False):
    made = {"parts": [part(p) if isinstance(p, str) else p for p in parts]}
    if punct:
        made["kind"] = "punct"
    if start is not None:
        made.update(start=start, end=end)
    return made


PAO = {"text": "pão", "lang": "pt"}
KOFFIE = {"text": "koffie", "lang": "nl"}
TABACO = {"text": "tabaco", "lang": "pt"}
SALARIED = {"text": "salaried man", "lang": "en", "wasei": True}
GLAS = {"text": "glas", "lang": "nl"}
ARBEIT = {"text": "Arbeit", "lang": "de"}

# けさ、パンとコーヒーと煙草を買いました。 ("This morning I bought bread, coffee and tobacco.")
# パン and コーヒー are loanwords in katakana; 煙草 (tabaco) is one written in kanji, whose
# furigana are drawn and whose origin is not.
O_TIMED = {"segments": [
    seg("けさ", start=0.0, end=0.5),
    seg("、", punct=True),
    seg(part("パン", origin=PAO), "と", start=0.7, end=1.0),
    seg(part("コーヒー", origin=KOFFIE), "と", start=1.0, end=1.4),
    seg(part("煙草", "たばこ", TABACO), "を", start=1.5, end=2.0),
    seg(part("買", "か"), "いました", start=2.0, end=3.0),
    seg("。", punct=True),
]}

# サラリーマンの父は、毎朝パンとコーヒーで朝ごはんを済ませて、ガラスの窓を拭いてからアルバイトに
# 行きます。 Long enough for several lines, with a pseudo-loanword (サラリーマン) and a source word
# with descenders (glas).
O_LONG = {"segments": [
    seg(part("サラリーマン", origin=SALARIED), "の", start=0.0, end=0.6),
    seg(part("父", "ちち"), "は", start=0.6, end=1.0),
    seg("、", punct=True),
    seg(part("毎朝", "まいあさ"), start=1.1, end=1.5),
    seg(part("パン", origin=PAO), "と", start=1.5, end=1.8),
    seg(part("コーヒー", origin=KOFFIE), "で", start=1.8, end=2.2),
    seg(part("朝", "あさ"), "ごはんを", start=2.2, end=2.6),
    seg(part("済", "す"), "ませて", start=2.6, end=3.0),
    seg("、", punct=True),
    seg(part("ガラス", origin=GLAS), "の", start=3.1, end=3.5),
    seg(part("窓", "まど"), "を", start=3.5, end=3.9),
    seg(part("拭", "ふ"), "いてから", start=3.9, end=4.4),
    seg(part("アルバイト", origin=ARBEIT), "に", start=4.4, end=4.9),
    seg(part("行", "い"), "きます", start=4.9, end=5.4),
    seg("。", punct=True),
]}

# The same words timed only as a whole.
O_WHOLE = {"start": 2.0, "end": 4.0, "segments": [{k: v for k, v in s.items() if k not in ("start", "end")} for s in O_TIMED["segments"]]}


def without_origins(sentence):
    return {**sentence, "segments": [{**s, "parts": [{k: v for k, v in p.items() if k != "origin"} for p in s["parts"]]}
                                     for s in sentence["segments"]]}


R_TIMED = with_romaji(O_TIMED, ["kesa", "pan to", "kōhii to", "tabako o", "kaimashita"])
R_LONG = with_romaji(O_LONG, ["sarariiman no", "chichi wa", "maiasa", "pan to", "kōhii de", "asagohan o", "sumasete",
                              "garasu no", "mado o", "fuite kara", "arubaito ni", "ikimasu"])

# What is over and under the text besides the origins; romaji over the text are refused with them.
LAYOUTS = [("ruby", "none"), ("none", "ruby"), ("ruby", "romaji"), ("none", "romaji"), ("none", "none")]
LAYOUT_IDS = [f"{o}-over-{u}-under" for o, u in LAYOUTS]
V = {"writing": "vertical"}
TALL = "height: 420px"


def romaji_if(under, sentence):
    """The sentence with romaji where they are drawn."""
    if under != "romaji":
        return sentence
    return {id(O_TIMED): R_TIMED, id(O_LONG): R_LONG}[id(sentence)]


# --- the HTML, in Node -------------------------------------------------------------------------

@pytest.mark.parametrize("options", [{}, {"origin": "none"}, {"under": "romaji"}, {"over": "none", "under": "ruby"}, {"ruby": False},
                                     {"announceRuby": False, "theme": "dark", "writing": "vertical", "motion": "mask"},
                                     {"over": "romaji", "origin": "none"}],
                         ids=["defaults", "origin-none", "romaji-under", "ruby-under", "ruby-off", "other-options", "romaji-over"])
def test_without_origins_drawn_the_html_is_what_it_was_origins_or_not(options):
    # origins are not drawn, so the HTML is byte for byte that of the sentence without them
    for sentence in (O_TIMED, O_LONG, O_WHOLE, R_TIMED):
        assert run_library(sentence, options=options)["html"] == run_library(without_origins(sentence), options=options)["html"]
    found = node("""const a = T.sentence(%s, %s), b = T.sentence(%s, %s);
      return [-1, 1.2, 9].every((t) => a.htmlAt(t) === b.htmlAt(t) && a.htmlAt(t, {revealed: [0, 2]}) === b.htmlAt(t, {revealed: [0, 2]}));"""
                 % (json.dumps(O_TIMED), json.dumps(options), json.dumps(without_origins(O_TIMED)), json.dumps(options)))
    assert found is True


def test_an_origin_is_a_ruby_over_its_part():
    html = run_library(O_TIMED, options={"origin": "over"})["html"]
    assert html.startswith('<span class="tsubu" lang="ja" data-timing="segments" data-ruby="on" data-origin="on">')
    assert ('<span class="tsubu-seg" data-index="2"><ruby class="tsubu-origin">パン<rp>（</rp><rt lang="pt">'
            '<span class="tsubu-origin-body">pão<span class="tsubu-origin-sep">, </span><span class="tsubu-origin-lang">pt</span>'
            '</span></rt><rp>）</rp></ruby>と</span>') in html
    assert html.count('class="tsubu-origin"') == 2


def test_a_part_with_furigana_keeps_them_and_has_no_origin_drawn():
    # 煙草 (たばこ, from tabaco): the furigana are drawn, the origin is not, whatever side the
    # furigana are on, and when they are drawn on neither
    for options in ({"origin": "over"}, {"origin": "over", "over": "none", "under": "ruby"}, {"origin": "over", "under": "romaji"}):
        html = run_library(R_TIMED, options=options)["html"]
        assert "<ruby>煙草<rp>（</rp><rt>たばこ</rt><rp>）</rp></ruby>" in html and "tabaco" not in html, options
    bare = run_library(O_TIMED, options={"origin": "over", "over": "none"})["html"]
    assert "たばこ" not in bare and "tabaco" not in bare and "pão" in bare


def test_a_pseudo_loanword_is_marked_wasei():
    html = run_library(O_LONG, options={"origin": "over"})["html"]
    assert ('<ruby class="tsubu-origin">サラリーマン<rp>（</rp><rt lang="en"><span class="tsubu-origin-body">'
            '<span class="tsubu-origin-wasei" lang="ja">和製</span> salaried man<span class="tsubu-origin-sep">, </span>'
            '<span class="tsubu-origin-lang">en</span></span></rt><rp>）</rp></ruby>') in html
    assert html.count("和製") == 1


def test_with_romaji_under_the_text_the_romaji_hold_the_origins():
    html = run_library(R_TIMED, options={"origin": "over", "under": "romaji"})["html"]
    assert ' data-ruby="on" data-under-layer="romaji" data-under="on" data-origin="on">' in html
    assert ('<span class="tsubu-stack"><ruby class="tsubu-romaji"><ruby class="tsubu-origin">パン<rp>（</rp><rt lang="pt">') in html
    assert '</ruby>と<rp>（</rp><rt>pan to</rt><rp>）</rp></ruby></span>' in html


def test_without_ruby_each_origin_follows_its_part_in_parentheses():
    # what a reader view, a feed reader or a text browser shows
    assert plain(run_library(O_TIMED, options={"origin": "over"})["html"]) == "けさ、パン（pão, pt）とコーヒー（koffie, nl）と煙草（たばこ）を買（か）いました。"
    assert plain(run_library(O_LONG, options={"origin": "over"})["html"]).startswith("サラリーマン（和製 salaried man, en）の父（ちち）は、")
    assert plain(run_library(R_TIMED, options={"origin": "over", "under": "romaji"})["html"]).startswith("けさ（kesa）、パン（pão, pt）と（pan to）")


def test_with_announce_ruby_off_the_origins_are_hidden_from_screen_readers_too():
    html = run_library(O_TIMED, options={"origin": "over", "announceRuby": False})["html"]
    assert html.count(' aria-hidden="true">') == 3 * html.count("<rt") == 3 * 4
    assert '<rp aria-hidden="true">（</rp><rt lang="pt" aria-hidden="true">' in html


def test_origins_are_escaped_and_never_set_upright():
    sentence = {"segments": [{"parts": [{"text": "OK", "origin": {"text": "<o> & \"k\"", "lang": "en-GB"}}, {"text": "です"}], "start": 0, "end": 1}]}
    html = run_library(sentence, options={"origin": "over", "writing": "vertical"})["html"]
    # the part's short run stands upright in vertical text; the origin lies on its side, as other Latin text does
    assert '<ruby class="tsubu-origin"><span class="tsubu-upright">OK</span><rp>（</rp><rt lang="en-GB">' in html
    assert '<span class="tsubu-origin-body">&lt;o&gt; &amp; &quot;k&quot;<span class="tsubu-origin-sep">' in html
    assert html.count("tsubu-upright") == 1


@pytest.mark.parametrize("origin, message", [
    ("pão", "`origin` must be an object, { text, lang, wasei? }"),
    (["pão", "pt"], "`origin` must be an object, { text, lang, wasei? }"),
    (None, "`origin` must be an object, { text, lang, wasei? }"),
    ({"lang": "pt"}, "`origin.text` must be a non-empty string, the source word"),
    ({"text": "", "lang": "pt"}, "`origin.text` must be a non-empty string, the source word"),
    ({"text": "pão"}, '`origin.lang` must be a language tag, such as "pt" or "en", not undefined'),
    ({"text": "pão", "lang": ""}, '`origin.lang` must be a language tag, such as "pt" or "en", not ""'),
    ({"text": "pão", "lang": "Portuguese"}, '`origin.lang` must be a language tag, such as "pt" or "en", not "Portuguese"'),
    ({"text": "pão", "lang": "pt_BR"}, '`origin.lang` must be a language tag, such as "pt" or "en", not "pt_BR"'),
    ({"text": "pão", "lang": "pt", "wasei": "yes"}, "`origin.wasei` must be true or false"),
])
def test_a_malformed_origin_is_refused(origin, message):
    found = run_library({"segments": [{"parts": [{"text": "けさ"}, {"text": "パン", "origin": origin}]}]})
    assert found["error"] == f"tsubu: segment 0, part 1: {message}"


def test_punctuation_carries_no_origin():
    found = run_library({"segments": [{"parts": [{"text": "本"}]}, {"parts": [{"text": "。", "origin": {"text": ".", "lang": "en"}}], "kind": "punct"}]})
    assert found["error"] == "tsubu: segment 1, part 0: punctuation carries no origin"


@pytest.mark.parametrize("options, message", [
    ({"origin": "under"}, 'options.origin must be "over" or "none"'),
    ({"origin": True}, 'options.origin must be "over" or "none"'),
    ({"origin": "over", "over": "romaji"},
     'options.origin "over" and options.over "romaji" would both be drawn over the text: draw the romaji under it (under: "romaji") or the origins not at all'),
    ({"origin": "over", "over": "romaji", "under": "ruby"},
     'options.origin "over" and options.over "romaji" would both be drawn over the text: draw the romaji under it (under: "romaji") or the origins not at all'),
])
def test_the_origin_option_is_checked(options, message):
    assert run_library(R_TIMED, options=options)["error"] == f"tsubu: {message}"


def test_a_valid_origin_changes_no_time_or_state():
    a = run_library(O_TIMED, times=[0.2, 1.2, 9], options={"origin": "over"})
    b = run_library(without_origins(O_TIMED), times=[0.2, 1.2, 9])
    assert a["states"] == b["states"] and a["timing"] == b["timing"] == "segments"


def test_the_exporters_and_the_importers_take_origins_and_leave_them_out():
    script = """const T = require(process.argv[1]); global.Tsubu = T; const X = require(process.argv[2]); const I = require(process.argv[3]);
      const a = JSON.parse(process.argv[4]), b = JSON.parse(process.argv[5]);
      const back = I.fromWebVTT(X.toWebVTT(a))[0];
      process.stdout.write(JSON.stringify([X.toWebVTT(a) === X.toWebVTT(b), X.toASS(a, {ruby: "inline"}) === X.toASS(b, {ruby: "inline"}),
        X.toSRT(a, {mode: "segments"}) === X.toSRT(b, {mode: "segments"}),
        back.segments.every((s) => s.parts.every((p) => !("origin" in p)))]));"""
    done = subprocess.run([shutil.which("node"), "-e", script, str(SCRIPT), str(ROOT / "tsubu-export.js"), str(ROOT / "tsubu-import.js"),
                           json.dumps(O_TIMED), json.dumps(without_origins(O_TIMED))], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == [True, True, True, True]


# --- in the browser ------------------------------------------------------------------------------

def switched(at, t=None, over=None, under=None, origin=None):
    """Applies t and the switches of the two sides and of the origins (None leaves them), and
    measures the readings."""
    at.page.evaluate("""([t, over, under, origin]) => { const root = document.querySelector(".tsubu");
      if (over !== null) Tsubu.setAnnotation(root, "over", over);
      if (under !== null) Tsubu.setAnnotation(root, "under", under);
      if (origin !== null) Tsubu.setAnnotation(root, "origin", origin);
      if (t !== null) S.apply(root, t); }""", [t, over, under, origin])
    return at.page.evaluate(LAYERS)


def options_for(writing, over, under, **more):
    made = {"origin": "over", "over": over, "under": under, **more}
    return {**made, "style": TALL, **V} if writing == "vertical" else made


@pytest.mark.parametrize("over, under", LAYOUTS, ids=LAYOUT_IDS)
@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
@pytest.mark.parametrize("sentence", [O_TIMED, O_LONG], ids=["one-line", "lines"])
def test_no_character_moves_when_the_origins_or_either_side_are_switched(drawn, sentence, writing, over, under):
    vertical = writing == "vertical"
    at = drawn(romaji_if(under, sentence), width=900 if sentence is O_TIMED else 520, **options_for(writing, over, under))
    first = switched(at)
    if sentence is O_LONG:  # origins on several lines (columns)
        across = (lambda b: round(b["left"])) if vertical else (lambda b: round(b["top"]))
        assert len({across(c["box"]) for c in first["chars"]}) >= 3
        assert len({across(r["box"]) for r in first["readings"] if r["layer"] == "origin"}) >= 2
    assert {r["layer"] for r in first["readings"]} == {"origin"} | ({over, under} - {"none"})
    for t in (0.1, 1.2, 3.2, 9.0):
        for shown_over, shown_under, shown_origin in itertools.product((False, True), repeat=3):
            found = switched(at, t, shown_over, shown_under, shown_origin)
            assert frozen(found) == frozen(first), (t, shown_over, shown_under, shown_origin)
            # and each switch hides and shows its own readings, and only those: the over side's
            # switch leaves the origins alone, and the origins' switch the furigana
            for r in found["readings"]:
                side = {"origin": "origin", over: "over", under: "under"}[r["layer"]]
                shown = {"over": shown_over, "under": shown_under, "origin": shown_origin}[side]
                assert r["visibility"] == ("visible" if shown else "hidden"), (r, side)


def test_set_annotation_switches_the_origins_by_their_own_attribute(drawn):
    page = drawn(O_TIMED, origin="over").page
    for on in (False, True):
        page.evaluate("(on) => Tsubu.setAnnotation(document.querySelector('.tsubu'), 'origin', on)", on)
        assert page.evaluate("() => [document.querySelector('.tsubu').dataset.origin, document.querySelector('.tsubu').dataset.ruby]") == [
            "on" if on else "off", "on"]
    page.evaluate("() => Tsubu.setRuby(document.querySelector('.tsubu'), false)")
    assert page.evaluate("() => document.querySelector('.tsubu').dataset.origin") == "on"
    # on a sentence drawn without origins the switch writes nothing, since the attribute also gives
    # the origins their room
    page = drawn(O_TIMED).page
    before = page.evaluate(LAYERS)
    page.evaluate("() => Tsubu.setAnnotation(document.querySelector('.tsubu'), 'origin', false)")
    assert page.evaluate("() => document.querySelector('.tsubu').hasAttribute('data-origin')") is False
    assert frozen(page.evaluate(LAYERS)) == frozen(before)


@pytest.mark.parametrize("over, under", LAYOUTS, ids=LAYOUT_IDS)
@pytest.mark.parametrize("sentence", [O_TIMED, O_LONG, O_WHOLE], ids=["one-line", "lines", "whole"])
def test_each_origin_sits_over_its_part_inside_the_sentence_and_clear_of_everything(drawn, engine, sentence, over, under):
    width = 520 if sentence is O_LONG else 900
    sentence = sentence if sentence is O_WHOLE else romaji_if(under, sentence)
    found = switched(drawn(sentence, width=width, origin="over", over=over, under=under), 1.2)
    placed({**found, "engine": engine}, over, under)
    clear_of_the_highlight(found)


@pytest.mark.parametrize("over, under", LAYOUTS, ids=LAYOUT_IDS)
@pytest.mark.parametrize("sentence", [O_TIMED, O_LONG], ids=["one-column", "columns"])
def test_in_vertical_text_the_origins_are_at_the_right(drawn, engine, sentence, over, under):
    found = switched(drawn(romaji_if(under, sentence), **options_for("vertical", over, under)), 1.2)
    placed({**found, "engine": engine}, over, under)
    clear_of_the_highlight(found)


def clear_of_the_highlight(found):
    """Every origin's ink, descenders included, is clear of its segment's highlight band: above it,
    or at its right in vertical text."""
    vertical = found["writing"] == "vertical-rl"
    origins = [r for r in found["readings"] if r["layer"] == "origin" and not r["hidden"]]
    assert origins
    for r in origins:
        band = found["segments"][r["seg"]]["band"]
        if vertical:
            assert r["ink"]["left"] >= band["right"] - 0.01, (r, band)
        else:
            assert r["ink"]["bottom"] <= band["top"] + 0.01, (r, band)


# In a face with Noto Sans JP's metrics (a content area of 1.45em; see tests/test_theme.py), the
# origins keep to their row and clear of everything too.
@NO_METRIC_OVERRIDES
@pytest.mark.parametrize("over, under", [("ruby", "none"), ("none", "ruby"), ("ruby", "romaji")], ids=["ruby-over", "ruby-under", "romaji-under"])
@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
def test_in_a_font_with_a_tall_content_area_the_origins_keep_apart(drawn, engine, engine_version, writing, over, under):
    options = options_for(writing, over, under) if writing == "vertical" else {"width": 520, **options_for(writing, over, under)}
    at = drawn(romaji_if(under, O_LONG), css=TALL_FACE, **options)
    first = switched(at, 1.2)
    across = (lambda b: b["right"] - b["left"]) if writing == "vertical" else (lambda b: b["bottom"] - b["top"])
    if not (writing == "vertical" and engine == "firefox" and engine_version < 153):
        assert max(across(c["box"]) for c in first["chars"]) / first["fontSize"] > 1.4, "no face matched TALL_FACE"
    placed({**first, "engine": engine}, over, under, graze=0.15 * first["fontSize"])
    for shown in itertools.product((False, True), repeat=3):
        assert frozen(switched(at, 2.3, *shown)) == frozen(first), shown


@pytest.mark.parametrize("over, under", LAYOUTS, ids=LAYOUT_IDS)
def test_in_vertical_text_the_highlight_and_the_side_line_stay_on_the_em_box(drawn, over, under):
    found = switched(drawn(romaji_if(under, O_TIMED), **options_for("vertical", over, under)), 1.2)
    em, spread = found["fontSize"], 0.06 * found["fontSize"]
    for i, s in enumerate(found["segments"]):
        chars = [c["box"] for c in found["chars"] if c["seg"] == i]
        centre = sum((b["left"] + b["right"]) / 2 for b in chars) / len(chars)
        assert s["band"]["left"] == pytest.approx(centre - 0.5 * em - spread, abs=0.5), (i, s, centre)
        assert s["band"]["right"] == pytest.approx(centre + 0.5 * em + spread, abs=0.5), (i, s, centre)
        if not s["punct"]:
            assert s["line"]["left"] == pytest.approx(centre - 0.5 * em - 0.02 * em, abs=0.5), (i, s, centre)


@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
@pytest.mark.parametrize("under", ["ruby", "romaji"])
def test_a_box_added_to_a_segment_and_the_blur_preset_move_nothing(drawn, writing, under):
    # WebKit lays out a line of nested ruby with readings on both sides again, wider, when a box is
    # added to a segment or a reading is blurred (see tests/test_romaji.py); origins under romaji are
    # nested in the romaji's ruby, and origins with furigana under the text are readings on both
    # sides of a line
    at = drawn(romaji_if(under, O_LONG), width=520, motion="blur", **options_for(writing, "none" if under == "ruby" else "ruby", under))
    page = at.page
    first = frozen(page.evaluate(LAYERS))
    for t in (0.1, 2.3, 4.6):
        page.evaluate("""(t) => { S.apply(document.querySelector('.tsubu'), t);
          for (const seg of document.querySelectorAll('.tsubu-seg')) { const p = document.createElement('span');
            p.style.cssText = 'position: absolute; left: 0; top: 0'; seg.append(p); p.getBoundingClientRect(); p.remove(); } }""", t)
        assert frozen(page.evaluate(LAYERS)) == first, t


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


@pytest.mark.parametrize("options", [{"origin": "over"}, {"origin": "over", "under": "romaji", "ruby": False},
                                     {"origin": "over", "over": "none", "under": "ruby", "writing": "vertical", "motion": "mask", "announceRuby": False}],
                         ids=["origin", "origin-romaji-under", "origin-ruby-under-vertical"])
def test_html_at_t_is_exactly_what_apply_makes_of_the_html(drawn, engine, options):
    page = drawn(O_TIMED).page
    for sentence in (R_TIMED, O_WHOLE, R_LONG):
        for t, equal, live, rendered in page.evaluate(SAME, [sentence, options, [-1, 0.25, 1.2, 2.2, 5.0, 9.0]]):
            assert equal, (t, live, rendered)
            if engine != "firefox":  # Firefox writes the style attribute elsewhere (see tests/test_html_at.py)
                assert rendered == live, t


# --- the checks ----------------------------------------------------------------------------------

CHECK = "(options) => Tsubu.checkContrast(document.querySelector('.tsubu'), options || undefined)"
FIT = "(options) => Tsubu.checkFit(document.querySelector('.tsubu'), options || undefined)"
STATES = ["static", "future", "current", "past"]


@pytest.mark.parametrize("over, under", [("ruby", "none"), ("none", "ruby"), ("ruby", "romaji")], ids=["ruby-over", "ruby-under", "romaji-under"])
@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
@pytest.mark.parametrize("theme", ["light", "dark", "media"])
def test_every_theme_meets_its_thresholds_with_origins(drawn, theme, writing, over, under):
    at = drawn(romaji_if(under, O_TIMED), theme=theme, **options_for(writing, over, under))
    switched(at, 1.2, False, False, False)  # hidden readings are checked too: checkContrast shows them
    found = at.page.evaluate(CHECK)
    assert found["ok"], found["failures"]
    covered = {(c["state"], c["layer"]) for c in found["checks"]}
    drawn_layers = {"ruby", "romaji", "origin"} & {over, under, "origin"}
    assert covered == {(s, layer) for s in STATES for layer in {"text", "underline"} | drawn_layers} | {("current", "highlight")}
    # origins are held to the furigana's threshold, and sit on the page, not on the highlight
    origins = [c for c in found["checks"] if c["layer"] == "origin"]
    assert {c["minimum"] for c in origins} == {4.5}
    page = {"light": {"#ffffff", "#f1f5f9"}, "dark": {"#0f172a", "#1e293b"}, "media": {"#000000", "#404040"}}[theme]
    assert {c["background"] for c in origins if c["state"] == "current"} == page


def test_origins_take_the_furigana_colours_and_threshold_and_their_labels_are_measured(drawn):
    at = drawn(O_TIMED, theme="light", origin="over")
    at.page.evaluate("() => document.querySelector('.tsubu').style.setProperty('--tsubu-current-ruby-color', '#dbeafe')")
    failed = at.page.evaluate(CHECK)["failures"]
    assert {(f["state"], f["layer"]) for f in failed} == {("current", "ruby"), ("current", "origin")}
    stricter = at.page.evaluate(CHECK, {"thresholds": {"ruby": 9}})
    assert {f["layer"] for f in stricter["failures"]} >= {"origin"}
    assert {c["minimum"] for c in stricter["checks"] if c["layer"] == "origin"} == {9}
    # a theme that colours the language code on its own is held to the same threshold
    at.page.evaluate("() => document.querySelector('.tsubu').style.removeProperty('--tsubu-current-ruby-color')")
    at.page.add_style_tag(content=".tsubu-origin-lang { color: #d1d5db; }")
    failed = at.page.evaluate(CHECK)["failures"]
    assert failed and {f["layer"] for f in failed} == {"origin"} and {f["foreground"] for f in failed} == {"#d1d5db"}


@pytest.mark.parametrize("over, under", [("ruby", "none"), ("none", "ruby"), ("ruby", "romaji")], ids=["ruby-over", "ruby-under", "romaji-under"])
@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
def test_a_sentence_with_origins_that_fits_reports_nothing(drawn, writing, over, under):
    style = "height: 420px; width: max-content" if writing == "vertical" else ""
    for sentence in (O_TIMED, O_LONG):
        at = drawn(romaji_if(under, sentence), width=520, style=style, origin="over", over=over, under=under, **(V if writing == "vertical" else {}))
        switched(at, 1.2, False, False, False)  # the check shows them itself
        found = at.page.evaluate(FIT)
        assert found["ok"], found["issues"]


def test_origins_past_the_container_are_reported_as_clipped(drawn):
    at = drawn(O_TIMED, width=900, origin="over", over="none")
    at.page.add_style_tag(content=".tsubu { margin-top: -0.8em; }")
    found = at.page.evaluate(FIT)
    clipped = [i for i in found["issues"] if i["kind"] == "ruby-clipped"]
    assert clipped and all(i["message"].startswith("the origin ") for i in clipped), found["issues"]
    assert [i for i in found["issues"] if i["kind"] != "ruby-clipped"] == []
    assert {i["segment"] for i in clipped} == {2, 3}
    assert any('"pão, pt"' in i["message"] for i in clipped)


# --- motion, forced colours, screen readers, the fallback, paging ----------------------------------

LOOK = """() => [...document.querySelectorAll('.tsubu-seg')].map((s) => { const rt = s.querySelector('.tsubu-origin > rt');
  if (!rt) return null; const st = getComputedStyle(rt), code = getComputedStyle(rt.querySelector('.tsubu-origin-lang'));
  return {state: s.dataset.state || null, visibility: st.visibility, color: st.color, codeColor: code.color, filter: st.filter,
          segFilter: getComputedStyle(s).filter}; }).filter(Boolean)"""


@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
@pytest.mark.parametrize("preset", ["appear", "mask", "blur", "underline-draw"])
def test_motion_presets_treat_origins_as_they_treat_furigana(drawn, preset, writing):
    at = drawn(O_LONG, motion=preset, origin="over", **({"style": TALL, **V} if writing == "vertical" else {}))
    switched(at, 1.6)  # サラリーマンの past; パンと current; コーヒーで, ガラスの and アルバイトに future
    look = at.page.evaluate(LOOK)
    later = [x for x in look if x["state"] == "future"]
    now = [x for x in look if x["state"] in ("current", "past")]
    assert len(later) == 3 and len(now) == 2
    if preset == "appear":
        assert {x["visibility"] for x in later} == {"hidden"} and {x["visibility"] for x in now} == {"visible"}
    if preset == "mask":
        assert {x["color"] for x in later} == {x["codeColor"] for x in later} == {"rgba(0, 0, 0, 0)"}
        assert "rgba(0, 0, 0, 0)" not in {x["color"] for x in now} | {x["codeColor"] for x in now}
    if preset == "blur":
        if writing == "horizontal":  # blurred on their own, as furigana are: 0.15em of 20px
            assert {x["filter"] for x in later} == {"blur(3px)"}
        else:  # the inline-block segment's filter reaches them
            assert {x["segFilter"] for x in later} == {"blur(6px)"} and {x["filter"] for x in later} == {"none"}
        assert {x["filter"] for x in now} == {"none"} and {x["segFilter"] for x in now} == {"none"}
    if preset == "underline-draw":
        assert {(x["visibility"], x["filter"]) for x in look} == {("visible", "none")}
        assert "rgba(0, 0, 0, 0)" not in {x["color"] for x in look}
    # and a revealed segment's origin is drawn whatever t is
    at.page.evaluate("() => Tsubu.setRevealed(document.querySelector('.tsubu'), 'all')")
    assert all(x["visibility"] == "visible" and x["filter"] == "none" and x["color"] != "rgba(0, 0, 0, 0)" for x in at.page.evaluate(LOOK))


def test_no_preset_moves_a_character_or_a_reading(drawn):
    first = frozen(switched(drawn(R_LONG, width=520, origin="over", under="romaji"), 2.3))
    for preset in ("appear", "mask", "blur", "underline-draw"):
        at = drawn(R_LONG, width=520, origin="over", under="romaji", motion=preset)
        for t in (0.1, 2.3, 4.6):
            assert frozen(switched(at, t)) == first, (preset, t)


def test_in_forced_colours_the_origin_of_the_segment_being_spoken_takes_the_page_colour(drawn):
    at = drawn(O_TIMED, theme="light", origin="over")
    before = frozen(switched(at, 1.2))
    at.page.emulate_media(forced_colors="active")
    canvas_text = at.page.evaluate("() => { const d = document.createElement('div'); d.style.color = 'CanvasText'; document.body.append(d); const c = getComputedStyle(d).color; d.remove(); return c; }")
    current = at.page.evaluate("""() => { const rt = document.querySelector('.tsubu-seg[data-state="current"] .tsubu-origin > rt');
      return [getComputedStyle(rt).color, getComputedStyle(rt.querySelector('.tsubu-origin-lang')).color]; }""")
    assert current == [canvas_text, canvas_text]
    assert frozen(switched(at)) == before


def test_screen_readers_read_the_origins_in_their_language_unless_announce_ruby_is_off(drawn):
    at = drawn(O_LONG, origin="over")
    spoken = at.page.locator("#bubble").aria_snapshot()
    assert "pão" in spoken and "salaried man" in spoken and "和製" in spoken and "（" not in spoken and ", pt" not in spoken
    langs = at.page.evaluate("""() => [...document.querySelectorAll('.tsubu-origin > rt')].map((rt) => [rt.lang,
      (rt.querySelector('.tsubu-origin-wasei') || {}).lang || null])""")
    assert langs == [["en", "ja"], ["pt", None], ["nl", None], ["nl", None], ["de", None]]
    quiet_at = drawn(O_LONG, origin="over", announceRuby=False)
    quiet = quiet_at.page.locator("#bubble").aria_snapshot()
    assert "pão" not in quiet and "和製" not in quiet and "パン" in quiet
    assert {r["visibility"] for r in switched(quiet_at)["readings"]} == {"visible"}  # still drawn


def test_without_ruby_or_the_stylesheet_the_origins_follow_their_part_in_parentheses(drawn):
    # a reader view keeps the elements and drops the page's styles; with ruby laid out inline the
    # origins read as they do with the tags dropped
    at = drawn(O_LONG, origin="over")
    text = at.page.evaluate("""() => { for (const sheet of document.querySelectorAll('link[rel=stylesheet]')) sheet.disabled = true;
      const style = document.createElement('style'); style.textContent = 'ruby, rt, rp { display: inline !important; }'; document.head.append(style);
      return document.querySelector('.tsubu').innerText; }""")
    assert text.startswith("サラリーマン（和製 salaried man, en）の父（ちち）は、毎朝（まいあさ）パン（pão, pt）とコーヒー（koffie, nl）で")


@pytest.mark.parametrize("writing", ["horizontal", "vertical"])
def test_pages_hold_their_lines_and_the_switches_do_not_reflow_them(drawn, engine, writing):
    style = "--tsubu-max-lines: 2; " + ("height: 420px" if writing == "vertical" else "")
    at = drawn(R_LONG, width=420, style=style, origin="over", under="romaji", **(V if writing == "vertical" else {}))
    across = (lambda b: -round(b["left"])) if writing == "vertical" else (lambda b: round(b["top"]))
    pages = set()
    for i, s in enumerate(R_LONG["segments"]):
        if "start" not in s:
            continue
        found = switched(at, s["start"])
        pages.add(at.page.evaluate("() => document.querySelector('.tsubu').dataset.page"))
        shown = [c for c in found["chars"] if not c["hidden"]]
        assert any(c["seg"] == i for c in shown), i  # the segment being spoken is on the page
        starts = sorted({across(found["segments"][j]["box"]) for j in {c["seg"] for c in shown}})
        assert len(starts) <= 2 or starts[2] - starts[0] < found["fontSize"], (i, starts)
        for shown_switches in itertools.product((False, True), repeat=3):
            assert frozen(switched(at, s["start"], *shown_switches)) == frozen(found), (i, shown_switches)
        placed({**found, "chars": shown, "engine": engine}, "ruby", "romaji")
    assert len(pages) >= 2
