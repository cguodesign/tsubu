"""The <rp> parentheses around each reading: shown only where ruby cannot be drawn.

Every reading is written as <ruby>本<rp>（</rp><rt>ほん</rt><rp>）</rp></ruby>. A browser that
draws ruby hides the <rp> (its own stylesheet, and tsubu.css for pages whose styles would show it),
so nothing on the page changes; anything that cannot draw ruby (a reader view, a feed reader, a
text browser) shows 本（ほん）.
"""

import re

from support import TIMED, run_library, seg

FALLBACK = "けさ、古（ふる）い本屋（ほんや）で面白（おもしろ）い地図（ちず）を買（か）いました。"


def plain(html):
    """The text of some HTML as a program that knows no ruby shows it: the tags dropped."""
    return re.sub(r"<[^>]+>", "", html)


def test_each_reading_is_wrapped_in_full_width_parentheses():
    html = run_library(TIMED)["html"]
    assert "<ruby>古<rp>（</rp><rt>ふる</rt><rp>）</rp></ruby>" in html
    assert html.count("<rp>（</rp>") == html.count("<rp>）</rp>") == html.count("<rt>") == 5
    assert plain(html) == FALLBACK
    # a part without a reading gets none
    assert plain(run_library({"segments": [seg("けさ")]})["html"]) == "けさ"


def test_hidden_furigana_keep_their_parentheses():
    # the switch is an attribute on the root, so the HTML is the same either way (and htmlAt(t),
    # which tests/test_html_at.py checks against apply(), is built from the same parts)
    assert plain(run_library(TIMED, options={"ruby": False})["html"]) == FALLBACK


def test_with_announce_ruby_off_the_parentheses_are_hidden_with_the_reading():
    # where they are shown, a screen reader would otherwise read empty parentheses after each base
    html = run_library(TIMED, options={"announceRuby": False})["html"]
    assert html.count('<rp aria-hidden="true">') == 10 and html.count("<rp") == 10
    assert '<ruby>古<rp aria-hidden="true">（</rp><rt aria-hidden="true">ふる</rt><rp aria-hidden="true">）</rp></ruby>' in html


def test_a_browser_that_draws_ruby_shows_no_parentheses(drawn):
    at = drawn(TIMED)
    found = at(1.2)
    assert "（" not in "".join(c["ch"] for c in found["chars"])
    shown = at.page.evaluate("""() => [...document.querySelectorAll('.tsubu rp')].map((rp) => {
      const r = rp.getBoundingClientRect();
      return [getComputedStyle(rp).display, r.width, r.height];
    })""")
    assert shown == [["none", 0, 0]] * 10
    assert at.page.evaluate("() => document.querySelector('.tsubu').innerText.includes('（')") is False


def test_a_page_whose_styles_show_rp_still_shows_no_parentheses(drawn):
    at = drawn(TIMED, css="rp { display: inline; }")
    at(1.2)
    assert at.page.evaluate("() => [...document.querySelectorAll('.tsubu rp')].every((rp) => getComputedStyle(rp).display === 'none')")


def test_the_parentheses_move_nothing(drawn):
    at = drawn(TIMED)
    boxes = lambda f: [(c["ch"], c["box"]) for c in f["chars"]]
    with_rp = at(1.2)
    at.page.evaluate("() => document.querySelectorAll('.tsubu rp').forEach((rp) => rp.remove())")
    without = at()
    assert boxes(with_rp) == boxes(without) and with_rp["root"] == without["root"]


def test_a_screen_reader_does_not_read_the_parentheses(drawn):
    spoken = drawn(TIMED).page.locator("#bubble").aria_snapshot()
    assert "ふる" in spoken and "（" not in spoken and "）" not in spoken


def test_without_ruby_layout_the_reading_follows_its_base_in_parentheses(drawn):
    # what a renderer that knows no ruby does: every element inline, so the <rp> text shows
    at = drawn(TIMED, css="ruby, rt, rp { display: inline !important; } .tsubu rt { font-size: inherit; }")
    at(1.2)
    assert at.page.evaluate("() => document.querySelector('.tsubu').innerText.replace(/\\s/g, '')") == FALLBACK
