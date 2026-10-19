"""Segment ids and tags, and the span of a segment for click-to-seek.

An id and tags are the caller's: tsubu writes them into the HTML (data-id, data-tags) and gives them
no meaning. The caller styles tags with the same tokens as everything else, and checkContrast
measures whatever colours that gives."""

import pytest

from support import TIMED, WHOLE, run_library, seg

TAGGED = {"segments": [
    dict(seg(("雨", "あめ"), "が", start=0.0, end=0.5), id="ame", tags=["new-word", "noun"]),
    dict(seg(("降", "ふ"), "って", start=0.5, end=1.0), id="futte"),
    seg("、", punct=True),
    dict(seg("いる", start=1.2, end=1.6), tags=["grammar"]),
    seg("。", punct=True),
]}


def test_ids_and_tags_are_written_into_the_html_and_escaped():
    html = run_library(TAGGED)["html"]
    assert 'data-index="0" data-id="ame" data-tags="new-word noun">' in html
    assert 'data-index="1" data-id="futte">' in html and 'data-index="3" data-tags="grammar">' in html
    odd = {"segments": [dict(seg("x"), id='a"<b>&', tags=["x", "x"]), dict(seg("y"), tags=[])]}
    html = run_library(odd)["html"]
    assert 'data-id="a&quot;&lt;b&gt;&amp;" data-tags="x">' in html  # escaped, and a tag given twice is written once
    assert 'data-index="1">' in html  # no tags, no attribute


@pytest.mark.parametrize("segment, message", [
    (dict(seg("x"), id=""), "tsubu: segment 0: `id` must be a non-empty string"),
    (dict(seg("x"), id=3), "tsubu: segment 0: `id` must be a non-empty string"),
    (dict(seg("x"), tags="noun"), "tsubu: segment 0: `tags` must be an array of names in lower case"),
    (dict(seg("x"), tags=["New"]), "tsubu: segment 0: `tags` must be an array of names in lower case"),
])
def test_a_bad_id_or_tag_is_refused(segment, message):
    assert run_library({"segments": [segment]})["error"].startswith(message)


def test_ids_must_be_unique():
    found = run_library({"segments": [dict(seg("a"), id="x"), dict(seg("b"), id="x")]})
    assert found["error"] == 'tsubu: two segments have the id "x"'


def test_span_and_find_serve_click_to_seek(drawn):
    page = drawn(TAGGED).page
    found = page.evaluate("""([tagged, whole]) => {
      const s = Tsubu.sentence(tagged), w = Tsubu.sentence(whole);
      let bad = null; try { s.span(9); } catch (e) { bad = e.message; }
      return {spans: [0, 1, 2, 3].map((i) => s.span(i)), ids: [s.find("ame"), s.find("futte"), s.find("nope")],
              whole: w.span(0), bad}; }""", [TAGGED, WHOLE])
    assert found["spans"] == [{"start": 0, "end": 0.5}, {"start": 0.5, "end": 1}, None, {"start": 1.2, "end": 1.6}]
    assert found["ids"] == [0, 1, None]
    assert found["whole"] is None  # without segment times a segment has no span: nothing is estimated
    assert found["bad"] == "tsubu: span needs a segment index from 0 to 4, not 9"
    # a click on a reading lands in its segment, whose span is where to seek
    seek = page.evaluate("""() => { const rt = document.querySelectorAll('rt')[1];
      const i = Tsubu.segmentOf(rt.firstChild); return [i, S.span(i)]; }""")
    assert seek == [1, {"start": 0.5, "end": 1}]


def test_the_caller_styles_tags_with_tokens_and_the_contrast_check_sees_it(drawn):
    at = drawn(TAGGED, theme="light")
    at(0.2)
    page = at.page
    page.add_style_tag(content=".tsubu-seg[data-tags~='grammar'] { --tsubu-future-color: #be123c; }")
    colour = page.evaluate("() => getComputedStyle(document.querySelector('[data-tags~=grammar]')).color")
    assert colour == "rgb(190, 18, 60)"
    assert page.evaluate("() => Tsubu.checkContrast(document.querySelector('.tsubu')).ok")
    page.add_style_tag(content=".tsubu-seg[data-tags~='new-word'] { --tsubu-past-color: #fda4af; }")
    failures = page.evaluate("() => Tsubu.checkContrast(document.querySelector('.tsubu')).failures")
    assert {(f["state"], f["layer"], f["foreground"]) for f in failures} == {("past", "text", "#fda4af")}


def test_ids_and_tags_move_nothing_and_html_at_matches_apply(drawn):
    plain = {"segments": [{k: v for k, v in s.items() if k not in ("id", "tags")} for s in TAGGED["segments"]]}
    boxes = lambda f: [(c["ch"], c["box"]) for c in f["chars"]]
    assert boxes(drawn(TAGGED)(0.7)) == boxes(drawn(plain)(0.7))
    page = drawn(TAGGED).page
    same = page.evaluate("""(input) => [0.2, 0.7, 1.4, 2.0].map((t) => {
      const s = Tsubu.sentence(input), live = document.createElement('div'), made = document.createElement('div');
      live.innerHTML = s.html; document.body.append(live); s.apply(live.firstElementChild, t);
      made.innerHTML = s.htmlAt(t); const equal = live.firstElementChild.isEqualNode(made.firstElementChild); live.remove(); return equal; })""", TAGGED)
    assert same == [True, True, True, True]
