"""Several lines: Japanese line-breaking rules, balanced lines, a size that follows the container,
and paging by t. Measured in headless Chromium on the library's own CSS and script, over a grid of
container widths and sentence lengths."""

import itertools
import re

import pytest

from support import LONG, TIMED, WHOLE, run_library, seg

# 昨日の夜、駅前の新しいラーメン屋で、大学時代の友達と久しぶりに会って、遅くまでいろいろな話をしました。
# ("Last night I met a friend from university for the first time in a while, at the new ramen shop by
# the station, and we talked about all sorts of things until late.") Long enough to take several
# lines, and several pages in a narrow container.
PARTS = [(("昨日", "きのう"), "の"), (("夜", "よる"),), "、", (("駅前", "えきまえ"), "の"), (("新", "あたら"), "しい"),
         ("ラーメン", ("屋", "や"), "で"), "、", (("大学", "だいがく"),), (("時代", "じだい"), "の"),
         (("友達", "ともだち"), "と"), (("久", "ひさ"), "しぶりに"), (("会", "あ"), "って"), "、",
         (("遅", "おそ"), "くまで"), ("いろいろな",), (("話", "はなし"), "を"), ("しました",), "。"]


def timed(parts, step=0.5, gap=0.2):
    segments, t = [], 0.0
    for p in parts:
        if isinstance(p, str):
            segments.append(seg(p, punct=True))
            t += gap
        else:
            segments.append(seg(*p, start=round(t, 3), end=round(t + step, 3)))
            t += step
    return {"segments": segments}


VERY_LONG = timed(PARTS)

# 「ちょっと待って」と言われて、コーヒーを一杯飲みました。 ("I was told 'wait a moment', and drank a cup
# of coffee.") Cut in unnatural places on purpose, so that segments begin with a small kana (っと)
# and the long-vowel mark (ーヒーを), next to brackets and commas: none of them may start a line.
KINSOKU = {"segments": [
    seg("「", punct=True), seg("ちょ"), seg("っと"), seg(("待", "ま"), "って"), seg("」", punct=True), seg("と"),
    seg(("言", "い"), "われて"), seg("、", punct=True), seg("コ"), seg("ーヒーを"), seg(("一杯", "いっぱい")),
    seg(("飲", "の"), "みました"), seg("。", punct=True),
]}

NO_START = set("、。」っー")
NO_END = set("「")
SENTENCES = {"short": TIMED, "whole": WHOLE, "two-lines": LONG, "very-long": VERY_LONG, "kinsoku": KINSOKU}
WIDTHS = [200, 280, 360, 480, 720, 960, 1280]


def visible(found):
    return [c for c in found["chars"] if not c["hidden"]]


def lines_of(found):
    """The visible base characters, line by line, from top to bottom."""
    rows = {}
    for c in visible(found):
        if not c["rt"]:
            rows.setdefault(round(c["box"]["top"]), []).append(c)
    return [sorted(rows[top], key=lambda c: c["box"]["left"]) for top in sorted(rows)]


def overlaps(a, b, slack=1):
    return min(a["right"], b["right"]) - max(a["left"], b["left"]) > slack and \
        min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]) > slack


def check_layout(found):
    chars, root, bubble = visible(found), found["root"], found["bubble"]
    for c in chars:
        b = c["box"]
        assert b["width"] > 0 and b["height"] > 0, c
        # nothing overflows the container, and furigana are not clipped at the top
        assert bubble["left"] - 0.5 <= b["left"] and b["right"] <= bubble["right"] + 0.5, (c["ch"], b, bubble)
        assert b["top"] >= root["top"] - 0.5 and b["top"] >= bubble["top"] - 0.5, (c["ch"], b, root)
    # nothing overlaps: plain characters, each <ruby> as a whole and each reading. (A character
    # inside a ruby is not measured on its own: its range box takes in the space the ruby gives it
    # when the reading is wider, which reaches past its neighbour's.)
    rts = [r for r in found["rts"] if not r["hidden"]]
    boxes = [(c["ch"], c["box"]) for c in chars if not c["rt"] and not c["ruby"]]
    boxes += [("ruby", r["base"]) for r in rts] + [("rt", r["box"]) for r in rts]
    for (x, a), (y, b) in itertools.combinations(boxes, 2):
        assert not overlaps(a, b), (x, a, y, b)
    # the Japanese line-breaking rules hold at every line break
    lines = lines_of(found)
    for line in lines[1:]:
        assert line[0]["ch"] not in NO_START, "".join(c["ch"] for c in line)
    for line in lines[:-1]:
        assert line[-1]["ch"] not in NO_END, "".join(c["ch"] for c in line)
    return lines


# --- the HTML, in Node -------------------------------------------------------------------------

def breaks_before(sentence):
    """The indexes of the segments that have a <wbr> before them."""
    return [int(i) for i in re.findall(r'<wbr><span class="tsubu-unit"><span class="tsubu-seg" data-index="(\d+)"', run_library(sentence)["html"])]


def test_no_break_is_offered_where_a_line_would_start_with_a_closing_mark_or_small_kana():
    # 「 ちょ っと 待って 」 と 言われて 、 コ ーヒーを 一杯 飲みました 。
    #  0  1    2    3     4  5   6      7  8    9      10     11      12
    # not after 「 (an opening bracket ends no line), not before っ, 」, 、, ー or 。
    assert breaks_before(KINSOKU) == [3, 5, 6, 8, 10, 11]
    # an ordinary sentence: before every segment but the first and the punctuation
    assert breaks_before(TIMED) == [2, 3, 4, 5, 6]


# --- the grid, in Chromium ---------------------------------------------------------------------

@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("name", list(SENTENCES))
def test_over_a_grid_of_widths_nothing_overflows_or_overlaps_and_the_furigana_do_not_reflow(drawn, name, width):
    sentence = SENTENCES[name]
    at = drawn(sentence, width=width, fluid=True)
    first = at(1.0 if name != "kinsoku" else None)
    lines = check_layout(first)
    if name in ("very-long",) and width <= 480:
        assert len(lines) >= 3, width  # the grid really does reach several lines
    off = at(None, False)
    base = lambda f: [(c["ch"], c["box"]) for c in visible(f) if not c["rt"]]
    assert base(off) == base(first) and off["root"] == first["root"]
    check_layout(at(None, True))


@pytest.mark.parametrize("width", [300, 520, 900])
def test_with_a_fixed_size_lines_break_by_the_same_rules(drawn, width):
    for sentence in (KINSOKU, VERY_LONG):
        check_layout(drawn(sentence, width=width)())


def test_balanced_lines_keep_the_last_line_from_holding_a_single_segment(drawn):
    def spoken_per_line(found):
        rows = {}
        for s in found["segments"]:
            if not s["punct"]:
                rows.setdefault(round(s["box"]["top"]), []).append(s)
        return [rows[k] for k in sorted(rows)]

    def width_of(row):
        return max(s["box"]["right"] for s in row) - min(s["box"]["left"] for s in row)

    lonely = 0
    for width in range(300, 1300, 40):
        greedy = spoken_per_line(drawn(VERY_LONG, width=width, style="--tsubu-wrap: wrap")())
        balanced = spoken_per_line(drawn(VERY_LONG, width=width)())
        assert len(balanced) == len(greedy), width  # balancing never adds a line
        # Chromium balances a block of up to six lines and leaves a longer one as it is
        if not 2 <= len(greedy) <= 6 or len(greedy[-1]) > 1:
            continue
        lonely += 1
        assert len(balanced[-1]) > 1, width
        widths = [width_of(r) for r in balanced]
        assert min(widths) / max(widths) > width_of(greedy[-1]) / max(width_of(r) for r in greedy), width
    assert lonely >= 2  # the greedy layout really does leave a single segment on the last line somewhere


# --- the size follows the container --------------------------------------------------------------

@pytest.mark.parametrize("width, size", [(120, 14), (280, 280 / 11), (479, 479 / 11), (480, 32), (600, 40),
                                         (959, 959 / 15), (960, 960 / 18), (1280, 1280 / 18), (1500, 72)])
def test_in_a_fluid_container_the_size_follows_the_width_between_a_minimum_and_a_maximum(drawn, width, size):
    assert drawn(TIMED, width=width, fluid=True)()["fontSize"] == pytest.approx(size, abs=0.01)


def test_every_step_of_the_fluid_size_is_configurable(drawn):
    style = "--tsubu-narrow-chars: 8; --tsubu-chars: 10; --tsubu-wide-chars: 20; --tsubu-size-min: 30px; --tsubu-size-max: 50px"
    sizes = [drawn(TIMED, width=w, fluid=True, style=style)()["fontSize"] for w in (200, 400, 600, 1200)]
    assert sizes == pytest.approx([30, 50, 50, 50])
    style = "--tsubu-narrow-chars: 8; --tsubu-chars: 20; --tsubu-wide-chars: 30; --tsubu-size-min: 10px; --tsubu-size-max: 99px"
    sizes = [drawn(TIMED, width=w, fluid=True, style=style)()["fontSize"] for w in (200, 600, 1200)]
    assert sizes == pytest.approx([25, 30, 40])


def test_without_a_fluid_container_the_size_is_inherited(drawn):
    assert drawn(TIMED, width=300)()["fontSize"] == 40


# --- paging by t -------------------------------------------------------------------------------

def segment_times(sentence):
    return [(i, s["start"], s["end"]) for i, s in enumerate(sentence["segments"]) if "start" in s]


def test_beyond_the_maximum_number_of_lines_the_page_with_the_current_segment_is_shown(drawn):
    at = drawn(VERY_LONG, width=280, fluid=True, style="--tsubu-max-lines: 2")
    end = segment_times(VERY_LONG)[-1][2]
    shown_with, pages_seen = {}, []
    for i, start, stop in segment_times(VERY_LONG):
        found = at((start + stop) / 2)
        segments = found["segments"]
        assert not segments[i]["offPage"], i  # the segment being spoken is on the page
        assert segments[i]["current"] == "true"
        assert len(lines_of(found)) <= 2
        check_layout(found)
        # a page begins at the start of a line
        first = next(s for s in segments if not s["offPage"])
        assert abs(first["box"]["left"] - found["root"]["left"]) < 1
        page = int(found["page"])
        pages_seen.append(page)
        shown_with.setdefault(page, set()).update(k for k, s in enumerate(segments) if not s["offPage"])
    pages = int(found["pages"])
    assert pages >= 3
    assert pages_seen == sorted(pages_seen) and set(pages_seen) == set(range(pages))
    # the pages share no segment, and together they hold every one
    assert sorted(k for ks in shown_with.values() for k in ks) == list(range(len(VERY_LONG["segments"])))
    assert int(at(-1)["page"]) == 0 and int(at(end + 5)["page"]) == pages - 1


def test_between_two_segments_the_page_of_the_one_just_spoken_stays(drawn):
    at = drawn(VERY_LONG, width=280, fluid=True, style="--tsubu-max-lines: 1")
    times = segment_times(VERY_LONG)
    turned = 0
    for (i, _, end), (j, start, _) in zip(times, times[1:]):
        if start <= end:
            continue
        before, during = at(end - 0.01), at((end + start) / 2)
        assert during["page"] == before["page"]
        assert not during["segments"][i]["offPage"]
        turned += at(start)["page"] != during["page"]
    assert turned >= 1


def test_the_page_is_a_function_of_t_alone(drawn):
    at = drawn(VERY_LONG, width=280, fluid=True, style="--tsubu-max-lines: 2")
    times = [0.1, 6.0, 2.2, 8.9, 0.1, 4.4, 6.0]
    seen = {}
    for t in times:
        found = at(t)
        key = (found["page"], tuple(s["offPage"] for s in found["segments"]),
               tuple((c["ch"], c["box"]["left"], c["box"]["top"]) for c in visible(found)))
        assert seen.setdefault(t, key) == key, t


def test_switching_the_furigana_does_not_reflow_a_page(drawn):
    at = drawn(VERY_LONG, width=280, fluid=True, style="--tsubu-max-lines: 2")
    on = at(5.0)
    off = at(5.0, False)
    assert on["page"] == off["page"]
    assert [(c["ch"], c["box"]) for c in visible(on) if not c["rt"]] == [(c["ch"], c["box"]) for c in visible(off) if not c["rt"]]


def test_a_step_can_have_its_own_maximum_number_of_lines(drawn):
    style = "--tsubu-max-lines: 3; --tsubu-narrow-max-lines: 1; --tsubu-wide-max-lines: none"
    narrow = drawn(VERY_LONG, width=300, fluid=True, style=style)(3.0)
    medium = drawn(VERY_LONG, width=600, fluid=True, style=style)(3.0)
    wide = drawn(VERY_LONG, width=1200, fluid=True, style=style)(3.0)
    assert len(lines_of(narrow)) == 1 and int(narrow["pages"]) > 1
    assert len(lines_of(medium)) <= 3
    assert wide["pages"] is None and not any(s["offPage"] for s in wide["segments"])


def test_a_sentence_without_segment_times_is_not_paged(drawn):
    at = drawn(WHOLE, width=200, fluid=True, style="--tsubu-max-lines: 1")
    found = at(5.0)
    assert found["page"] is None and not any(s["offPage"] for s in found["segments"])
    assert len(lines_of(found)) > 1


def test_apply_returns_the_page_and_refuses_a_maximum_that_is_not_a_number_of_lines(drawn):
    at = drawn(VERY_LONG, width=280, fluid=True, style="--tsubu-max-lines: 2")
    page = at.page
    result = page.evaluate("() => S.apply(document.querySelector('.tsubu'), 6.0)")
    assert result["page"] >= 1 and result["pages"] >= 3 and result["current"] is not None
    assert "page" not in page.evaluate("() => S.stateAt(6.0)")  # stateAt knows nothing of layout
    for bad in ("2.5", "0", "two"):
        message = page.evaluate("""(bad) => { const root = document.querySelector('.tsubu');
            root.style.setProperty('--tsubu-max-lines', bad);
            try { S.apply(root, 1); } catch (e) { return e.message; } }""", bad)
        assert message.startswith("tsubu: --tsubu-max-lines must be a whole number"), bad
