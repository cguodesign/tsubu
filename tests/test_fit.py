"""checkFit: whether a drawn sentence fits where it is drawn, measured in headless Chromium.

The library's own layout guarantees are tested elsewhere over a grid of widths; checkFit is the
tool a caller (or the agent working for it) runs on its own container, font and sentence."""

import json

import pytest

from support import LONG, TIMED, WHOLE, run_library, seg

CHECK = "(options) => Tsubu.checkFit(document.querySelector('.tsubu'), options || undefined)"
ONE_LONG = {"segments": [seg("ありがとうございました", start=0, end=1), seg("。", punct=True)]}


def kinds(found):
    return sorted({i["kind"] for i in found["issues"]})


def test_a_sentence_that_fits_reports_nothing(drawn):
    at = drawn(TIMED, width=900)
    found = at.page.evaluate(CHECK)
    assert found == {"ok": True, "issues": [], "lines": 1, "pages": None}
    assert drawn(LONG, width=900).page.evaluate(CHECK)["lines"] == 2


def test_a_unit_longer_than_the_line_is_too_wide_and_overflows(drawn):
    found = drawn(ONE_LONG, width=200).page.evaluate(CHECK)
    assert not found["ok"] and kinds(found) == ["overflow", "too-wide"]
    wide = next(i for i in found["issues"] if i["kind"] == "too-wide")
    assert wide["segment"] == 0 and wide["by"] > 100 and "ありがとうございました。" in wide["message"]


def test_content_past_a_container_of_fixed_height_overflows(drawn):
    at = drawn(LONG, width=300, style="height: 60px")
    found = at.page.evaluate(CHECK)
    assert "overflow" in kinds(found)
    assert all(i["by"] > 0 for i in found["issues"])


def test_furigana_past_the_container_are_reported_as_clipped(drawn):
    at = drawn(TIMED, width=900, style="--tsubu-ruby-reserve: 0px; padding-top: 0")
    at.page.add_style_tag(content=".tsubu { margin-top: -0.6em; }")
    found = at.page.evaluate(CHECK)
    assert "ruby-clipped" in kinds(found)
    assert {i["segment"] for i in found["issues"] if i["kind"] == "ruby-clipped"} <= {2, 3, 4, 5, 6}


def test_a_sentence_that_cannot_be_paged_has_too_many_lines(drawn):
    found = drawn(WHOLE, width=200, fluid=True, style="--tsubu-max-lines: 1").page.evaluate(CHECK)
    assert kinds(found) == ["too-many-lines"] and found["pages"] is None and found["lines"] > 1


def test_a_paged_sentence_is_checked_page_by_page(drawn):
    from test_lines import VERY_LONG
    at = drawn(VERY_LONG, width=280, fluid=True, style="--tsubu-max-lines: 2; height: 160px")
    at(3.0)
    found = at.page.evaluate(CHECK)
    assert found["ok"], found["issues"]
    assert found["pages"] >= 3 and found["lines"] == 2


def test_check_fit_leaves_the_page_as_it_was(drawn):
    from test_lines import VERY_LONG
    at = drawn(VERY_LONG, width=280, fluid=True, style="--tsubu-max-lines: 2")
    before = at(3.0)
    html = at.page.evaluate("() => document.body.innerHTML")
    at.page.evaluate(CHECK)
    assert at.page.evaluate("() => document.body.innerHTML") == html
    assert json.dumps(at(), sort_keys=True) == json.dumps(before, sort_keys=True)


def test_vertical_text_is_checked_along_its_columns(drawn):
    at = drawn(ONE_LONG, width=600, writing="vertical", style="height: 200px")
    found = at.page.evaluate(CHECK)
    assert "too-wide" in kinds(found)


def test_another_container_can_be_named(drawn):
    at = drawn(TIMED, width=900)
    at.page.evaluate("() => { const box = document.createElement('div'); box.id = 'small'; box.style.cssText = 'position:absolute;left:40px;top:40px;width:100px;height:40px'; document.body.append(box); }")
    found = at.page.evaluate("() => Tsubu.checkFit(document.querySelector('.tsubu'), { container: document.getElementById('small') })")
    assert "overflow" in kinds(found)


def test_check_fit_needs_a_drawn_sentence_and_a_browser():
    assert "checkFit" in run_library(TIMED)["keys"]
