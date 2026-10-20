"""Vertical writing (writing-mode: vertical-rl): the horizontal guarantees, measured again with
columns instead of lines, in a headless browser on the library's own CSS and script. The HTML is
checked in Node.

In vertical text the lines are columns, running from right to left; the furigana are at the right
of the characters and each segment's underline is a side line at its left.
"""

import itertools
import json

import pytest

from support import BAND_COLOUR, LONG, TIMED, WHOLE, block_slack, run_library, seg
from test_layout import png_rows
from test_lines import KINSOKU, NO_END, NO_START, VERY_LONG, segment_times

V = {"writing": "vertical"}
TALL = "height: 400px"
THEMES = ["light", "dark", "media"]

# 2025年10月、AIの講座が始まります!? ("In October 2025, a course on AI begins!?") A four-digit run,
# which lies on its side, and two-character runs (10, AI, !?), which stand upright.
DIGITS = {"segments": [
    seg("2025", ("年", "ねん"), start=0.0, end=0.5),
    seg("10", ("月", "がつ"), start=0.5, end=1.0),
    seg("、", punct=True),
    seg("AI", "の", start=1.0, end=1.4),
    seg(("講座", "こうざ"), "が", start=1.4, end=1.9),
    seg(("始", "はじ"), "まります", start=1.9, end=2.5),
    seg("!?", punct=True),
]}

# Punctuation, brackets, the long-vowel mark and a small kana, each between kana, so that no two
# marks are next to each other (Chromium would trim the space between them, text-spacing-trim).
PUNCT = {"segments": [seg("あ「い」う"), seg("、", punct=True), seg("えーおょ"), seg("。", punct=True), seg("か（き）く")]}


def visible(found):
    return [c for c in found["chars"] if not c["hidden"]]


def base_chars(found):
    return [(c["ch"], c["box"]) for c in found["chars"] if not c["rt"]]


def columns_of(found):
    """The visible base characters, column by column from right to left, each from top to bottom.
    A character whose middle lies half a character or more to the left of the column's begins the
    next one."""
    chars = sorted((c for c in visible(found) if not c["rt"]), key=lambda c: -(c["box"]["left"] + c["box"]["right"]))
    columns = []
    for c in chars:
        middle = (c["box"]["left"] + c["box"]["right"]) / 2
        if not columns or columns[-1][0] - middle >= found["fontSize"] / 2:
            columns.append((middle, []))
        columns[-1][1].append(c)
    return [sorted(cs, key=lambda c: c["box"]["top"]) for _, cs in columns]


def segment_columns(found):
    """The column of each segment on the page, counted from the right, from its left edge: the side
    away from its reading, which a segment's box takes in (see the stylesheet). A segment whose
    left edge lies half a character or more to the left of the column's begins the next one."""
    half = found["fontSize"] / 2
    starts = []
    for left in sorted((s["box"]["left"] for s in found["segments"] if not s["offPage"]), reverse=True):
        if not starts or starts[-1] - left >= half:
            starts.append(left)
    return [None if s["offPage"] else sum(1 for x in starts if x - s["box"]["left"] >= half) for s in found["segments"]]


def overlaps(a, b, slack=1, across=1):
    """Whether two boxes overlap by more than `slack` along the column and `across` it."""
    return min(a["right"], b["right"]) - max(a["left"], b["left"]) > across and \
        min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]) > slack


def check_columns(found):
    """Nothing overflows the container or overlaps, no reading is clipped, and every column break
    keeps the Japanese line-breaking rules. Returns the columns."""
    assert found["writing"] == "vertical-rl"
    chars, root, bubble = visible(found), found["root"], found["bubble"]
    # A character set upright with others is measured as their run: WebKit gives the run's box to
    # its first character and none to the rest (measured).
    measured = [(c["ch"], c["box"]) for c in chars if not c["upright"]] + [(u["text"], u["box"]) for u in found["upright"]]
    for ch, b in measured:
        assert b["width"] > 0 and b["height"] > 0, ch
        assert bubble["top"] - 0.5 <= b["top"] and b["bottom"] <= bubble["bottom"] + 0.5, (ch, b, bubble)
        # furigana are not clipped at the right, where the first column's readings are
        assert bubble["left"] - 0.5 <= b["left"] and b["right"] <= root["right"] + 0.5 and b["right"] <= bubble["right"] + 0.5, (ch, b, root)
    # plain characters, each upright run as a whole, each <ruby> and each reading
    rts = [r for r in found["rts"] if not r["hidden"]]
    boxes = [(c["ch"], c["box"]) for c in chars if not c["rt"] and not c["ruby"] and not c["upright"]]
    boxes += [(u["text"], u["box"]) for u in found["upright"]]
    boxes += [("ruby", r["base"]) for r in rts] + [("rt", r["box"]) for r in rts]
    for (x, a), (y, b) in itertools.combinations(boxes, 2):
        assert not overlaps(a, b, across=block_slack(found["engine"])), (x, a, y, b)
    columns = columns_of(found)
    for column in columns[1:]:
        assert column[0]["ch"] not in NO_START, "".join(c["ch"] for c in column)
    for column in columns[:-1]:
        assert column[-1]["ch"] not in NO_END, "".join(c["ch"] for c in column)
    # a segment is never split: it lies in one column. Its box is a line 2em across and its reading
    # at the right (see the stylesheet); across two columns, 1.75em apart, it would be 3.75em or more.
    for s in found["segments"]:
        if not s["offPage"]:
            assert s["box"]["width"] < found["fontSize"] * 3, s
    return columns


# --- the HTML, in Node -------------------------------------------------------------------------

def test_the_writing_option_is_written_on_the_root_and_checked():
    assert ' data-tsubu-writing="vertical">' in run_library(TIMED, options=V)["html"]
    assert ' data-tsubu-writing="horizontal">' in run_library(TIMED, options={"writing": "horizontal"})["html"]
    assert "data-tsubu-writing" not in run_library(TIMED)["html"]
    for bad in ("Vertical", "vertical-rl", "", 1, True):
        assert run_library(TIMED, options={"writing": bad})["error"] == 'tsubu: options.writing must be "horizontal" or "vertical"', bad


def test_short_runs_of_half_width_characters_are_marked_to_stand_upright():
    html = run_library(DIGITS, options=V)["html"]
    # two characters or fewer by default: 10, AI and !? stand upright, 2025 lies on its side
    assert '<span class="tsubu-upright">10</span>' in html and '<span class="tsubu-upright">AI</span>' in html
    assert '<span class="tsubu-upright">!?</span>' in html
    assert ">2025<ruby>" in html and html.count("tsubu-upright") == 3
    # the reading is never marked, and a run inside a ruby base is marked inside the <ruby>
    marked = run_library({"segments": [seg(("10", "じゅう"))]}, options=V)["html"]
    assert '<ruby><span class="tsubu-upright">10</span><rp>（</rp><rt>じゅう</rt><rp>）</rp></ruby>' in marked
    assert run_library({"segments": [seg(("十", "ju"))]}, options=V)["html"].count("tsubu-upright") == 0
    # configurable from 0 (none) to 4
    assert '<span class="tsubu-upright">2025</span>' in run_library(DIGITS, options={**V, "combineUpright": 4})["html"]
    assert "tsubu-upright" not in run_library(DIGITS, options={**V, "combineUpright": 0})["html"]
    assert run_library(DIGITS, options={**V, "combineUpright": 1})["html"].count("tsubu-upright") == 0
    for bad in (5, -1, 1.5, "2", None, True):
        found = run_library(DIGITS, options={**V, "combineUpright": bad})
        assert found["error"] == "tsubu: options.combineUpright must be a whole number of characters from 0 to 4", bad
    # without the option the runs are marked too (an ancestor may make the sentence vertical);
    # a sentence horizontal by its own option has no marks
    assert run_library(DIGITS)["html"].count("tsubu-upright") == 3
    assert "tsubu-upright" not in run_library(DIGITS, options={"writing": "horizontal"})["html"]


def test_brackets_split_runs_and_the_text_is_still_escaped():
    html = run_library({"segments": [seg("(土)A-1<b>&'", ('"', "<i>"))]}, options=V)["html"]
    # ASCII brackets are not part of a run, so they turn with the column around an upright 土
    assert "(土)" in html
    # A-1 is a run of three; b, &' and " are short runs, escaped inside their marks
    assert ")A-1&lt;" in html
    assert '&lt;<span class="tsubu-upright">b</span>&gt;<span class="tsubu-upright">&amp;&#39;</span>' in html
    assert '<ruby><span class="tsubu-upright">&quot;</span><rp>（</rp><rt>&lt;i&gt;</rt><rp>）</rp></ruby>' in html
    assert "<b>" not in html and "<i>" not in html


def test_the_line_breaking_units_do_not_depend_on_the_writing_mode():
    def units(options):
        html = run_library(KINSOKU, options=options)["html"]
        return html.replace(' data-tsubu-writing="vertical"', "").replace(' data-tsubu-writing="horizontal"', "")
    assert units(V) == units({"writing": "horizontal"}) == units({})


# --- layout, in the browser --------------------------------------------------------------------

@pytest.mark.parametrize("sentence", [TIMED, WHOLE, LONG], ids=["timed", "whole", "two-columns"])
def test_furigana_sit_at_the_right_unclipped_and_clear_of_the_column_to_the_right(drawn, sentence):
    found = drawn(sentence, style=TALL, **V)()
    root, bubble = found["root"], found["bubble"]
    if sentence is LONG:
        assert len(columns_of(found)) >= 2  # readings in a second column too
    base = [c for c in found["chars"] if not c["rt"]]
    for rt in found["rts"]:
        box = rt["box"]
        assert box["height"] > 0 and box["width"] > 0
        # to the right of its base, alongside it
        assert box["left"] >= rt["base"]["right"] - 1, (box, rt["base"])
        assert box["top"] < rt["base"]["bottom"] and box["bottom"] > rt["base"]["top"]
        # inside the sentence's box, and so inside a container that hides its overflow
        assert box["right"] <= root["right"] and box["right"] <= bubble["right"], (box, root)
        # nothing of the column to the right lies under it: neither its characters nor its side lines
        for c in base:
            b = c["box"]
            if b["left"] >= box["left"] and not (b["bottom"] <= box["top"] or b["top"] >= box["bottom"]):
                assert b["left"] >= box["right"], (c["ch"], b, box)
        for s in found["segments"]:
            line = s["side"]
            if not s["punct"] and line["left"] >= box["left"] - 1 and not (line["bottom"] <= box["top"] or line["top"] >= box["bottom"]):
                assert line["left"] >= box["right"], (line, box)


def test_the_ruby_reserve_is_room_at_the_right_of_the_first_column(drawn):
    at = drawn(TIMED, style=TALL, **V)
    found = at()
    padding = at.page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.tsubu'));
      return [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft].map(parseFloat); }""")
    assert padding == [0, 0.3 * 40, 0, 0]
    assert found["root"]["top"] == min(c["box"]["top"] for c in found["chars"] if not c["rt"])
    assert max(r["box"]["right"] for r in found["rts"]) <= found["root"]["right"] - 1
    # A column is as wide as the line height whatever its readings (each segment gives back the
    # room its readings take, see the stylesheet), so without the reserve the first column's
    # readings stick out of the sentence's box (by 5px here, measured in every engine), which is
    # why the reserve is there. Either way no character moves: only the sentence's box reaches
    # further right.
    bare = drawn(TIMED, style=TALL + "; --tsubu-ruby-reserve: 0", **V)()
    reach = max(r["box"]["right"] for r in bare["rts"]) - bare["root"]["right"]
    assert 0 < reach <= 0.3 * 40
    assert base_chars(found) == base_chars(bare) and [r["box"] for r in found["rts"]] == [r["box"] for r in bare["rts"]]
    assert found["root"]["left"] == bare["root"]["left"] and 0 < found["root"]["right"] - bare["root"]["right"] <= 0.3 * 40


@pytest.mark.parametrize("sentence", [TIMED, WHOLE, LONG], ids=["timed", "whole", "two-columns"])
def test_no_character_moves_when_the_furigana_are_switched_or_the_highlight_moves(drawn, sentence):
    at = drawn(sentence, style=TALL, **V)
    first = at()
    seen = [first]
    for t in (0.1, 1.05, 2.2, 3.0, 4.6, 5.0, 9.0):
        for on in (False, True):
            seen.append(at(t, on))
    for found in seen[1:]:
        assert base_chars(found) == base_chars(first)
        assert [s["box"] for s in found["segments"]] == [s["box"] for s in first["segments"]]
        assert [r["box"] for r in found["rts"]] == [r["box"] for r in first["rts"]]
        assert found["root"] == first["root"]
    assert {r["visibility"] for r in at(None, False)["rts"]} == {"hidden"}
    assert {r["visibility"] for r in at(None, True)["rts"]} == {"visible"}
    assert set(at(2.3)["motion"]) == {"0s none"}


def test_a_sentence_drawn_with_the_furigana_off_has_the_same_layout_as_one_drawn_with_them_on(drawn):
    on, off = drawn(LONG, style=TALL, **V)(), drawn(LONG, style=TALL, ruby=False, **V)()
    assert base_chars(off) == base_chars(on) and off["root"] == on["root"]


def test_no_character_moves_when_the_theme_or_the_speaker_changes(drawn):
    at = drawn(LONG, style=TALL, **V)
    first = at(2.3)
    boxes = lambda f: (base_chars(f), [s["box"] for s in f["segments"]], [r["box"] for r in f["rts"]], f["root"])
    for where in ("root", "ancestor"):
        for theme in [None] + THEMES:
            for speaker in (None, "a", "b"):
                at.page.evaluate("""([where, theme, speaker]) => {
                  const root = document.querySelector(".tsubu"), bubble = document.getElementById("bubble");
                  for (const el of [root, bubble]) delete el.dataset.tsubuTheme;
                  if (theme) (where === "root" ? root : bubble).dataset.tsubuTheme = theme;
                  if (speaker) root.dataset.speaker = speaker; else delete root.dataset.speaker;
                }""", [where, theme, speaker])
                for t in (0.1, 2.3, 9.0):
                    assert boxes(at(t)) == boxes(first), (where, theme, speaker, t)


def test_every_segment_has_its_own_side_line_at_the_left_apart_from_its_neighbours(drawn):
    for sentence in (TIMED, WHOLE, LONG):
        found = drawn(sentence, style=TALL, **V)()
        spoken = [s for s in found["segments"] if not s["punct"]]
        assert all(s["side"]["style"] == "dotted" and s["side"]["width"] > 0 for s in spoken)
        assert {s["underline"]["style"] for s in spoken} == {"none"}, "no line below the segment"
        assert {s["decoration"] for s in found["segments"]} == {"none"}
        for i, s in enumerate(found["segments"]):
            if s["punct"]:
                continue
            line, box = s["side"], s["box"]
            text = min(c["box"]["left"] for c in found["chars"] if c["seg"] == i and not c["rt"])
            # at the left of the text, the side opposite the furigana, inset at both ends
            assert line["right"] <= text + line["width"] and line["left"] < text
            assert box["top"] < line["top"] < line["bottom"] < box["bottom"]
        column = dict(zip(map(id, found["segments"]), segment_columns(found)))
        for above, below in zip(spoken, spoken[1:]):
            if column[id(above)] == column[id(below)]:
                assert below["side"]["top"] - above["side"]["bottom"] >= 4, (above, below)


# The tallest unit, ラーメン屋で、, takes seven characters: a shorter column would have to overflow,
# as a line narrower than a unit does.
@pytest.mark.parametrize("height", [320, 400, 560])
def test_columns_break_only_between_units_and_by_the_line_breaking_rules(drawn, height):
    for sentence in (KINSOKU, VERY_LONG, DIGITS):
        columns = check_columns(drawn(sentence, style=f"height: {height}px", **V)())
        if sentence is VERY_LONG:
            assert len(columns) >= 4, height


@pytest.mark.parametrize("height", [200, 320, 480, 720])
@pytest.mark.parametrize("sentence", [TIMED, KINSOKU, VERY_LONG], ids=["short", "kinsoku", "very-long"])
def test_in_a_fluid_container_nothing_overflows_or_overlaps_and_the_furigana_do_not_reflow(drawn, sentence, height):
    at = drawn(sentence, fluid=True, style=f"height: {height}px", **V)
    first = at(1.0 if sentence is not KINSOKU else None)
    check_columns(first)
    off = at(None, False)
    assert base_chars(off) == base_chars(first) and off["root"] == first["root"]


@pytest.mark.limitation("firefox", reason="text-wrap: balance is not applied when the only break opportunities are "
                                    "between nowrap units (<wbr>), so columns break greedily")
@pytest.mark.limitation("webkit", reason="text-wrap: balance is not applied to inline content that holds absolutely "
                                   "positioned boxes (each segment's highlight and underline), so columns break greedily")
def test_columns_are_balanced(drawn):
    def spoken_per_column(found):
        rows = {}
        for s, column in zip(found["segments"], segment_columns(found)):
            if not s["punct"]:
                rows.setdefault(column, []).append(s)
        return [rows[k] for k in sorted(rows)]

    lonely = 0
    for height in range(240, 900, 30):
        greedy = spoken_per_column(drawn(VERY_LONG, style=f"height: {height}px; --tsubu-wrap: wrap", **V)())
        balanced = spoken_per_column(drawn(VERY_LONG, style=f"height: {height}px", **V)())
        assert len(balanced) == len(greedy), height
        if not 2 <= len(greedy) <= 6 or len(greedy[-1]) > 1:
            continue
        lonely += 1
        assert len(balanced[-1]) > 1, height
    assert lonely >= 1


# --- digits and Latin letters --------------------------------------------------------------------

def test_short_runs_stand_upright_and_long_runs_lie_on_their_side(drawn):
    found = drawn(DIGITS, style=TALL, **V)(0.7)
    size = found["fontSize"]
    upright = {u["text"]: u for u in found["upright"]}
    assert set(upright) == {"10", "AI", "!?"}
    # a character's box across the column: Firefox 153 gives it the font's ascent and descent, each
    # rounded up to whole pixels (measured: 41px at 40px)
    across = next(c for c in found["chars"] if c["ch"] == "の")["box"]["width"]
    assert across == pytest.approx(size, abs=1)
    for u in upright.values():
        # set across the column in one em square: no taller than one character, and no wider
        assert u["combine"] == "all"
        assert u["box"]["height"] == pytest.approx(size, abs=1) and u["box"]["width"] <= across + 0.5, u
    # 2025 lies on its side: its digits follow one another down the column, each narrower than an em
    digits = [c for c in found["chars"] if c["ch"] in "2025" and not c["upright"] and not c["rt"]][:4]
    assert "".join(c["ch"] for c in digits) == "2025"
    tops = [c["box"]["top"] for c in digits]
    assert tops == sorted(tops) and len({round(c["box"]["left"]) for c in digits}) == 1
    span = digits[-1]["box"]["bottom"] - digits[0]["box"]["top"]
    assert 2 * size < span < 4 * size, span
    check_columns(found)


def test_upright_digits_are_set_upright_and_rotated_ones_are_turned_in_a_screenshot(drawn):
    at = drawn(DIGITS, style=TALL, **V)
    found = at()
    page = at.page

    def ink(box):
        width, bpp, rows = png_rows(page.screenshot(clip={"x": box["left"], "y": box["top"], "width": box["width"], "height": box["height"]}))
        points = [(x, y) for y, row in enumerate(rows) for x in range(width) if min(row[x * bpp:x * bpp + 3]) < 128]
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        return max(xs) - min(xs) + 1, max(ys) - min(ys) + 1

    # "10" set upright: its two digits side by side, so its ink is wider than it is tall
    ten = next(u for u in found["upright"] if u["text"] == "10")
    wide, tall = ink(ten["box"])
    assert wide > tall, (wide, tall)
    # "2025" on its side: one digit's ink is wider than tall too, but the run's is tall and narrow
    digits = [c["box"] for c in found["chars"] if c["ch"] in "2025" and not c["upright"] and not c["rt"]][:4]
    run = {"left": digits[0]["left"], "top": digits[0]["top"], "width": digits[0]["width"], "height": digits[-1]["bottom"] - digits[0]["top"]}
    wide, tall = ink(run)
    assert tall > 2.5 * wide, (wide, tall)


def test_the_marks_change_nothing_in_horizontal_text(drawn, engine):
    marked = drawn(DIGITS)(0.7)
    plain = drawn(DIGITS, writing="horizontal")(0.7)
    assert marked["writing"] == plain["writing"] == "horizontal-tb"
    assert len(marked["upright"]) == 3 and plain["upright"] == []
    assert {u["combine"] for u in marked["upright"]} == {"all"}  # set, but without effect in horizontal text
    # The same boxes, to within one Chromium layout unit (1/64 px): ending a run of Latin letters at
    # an element boundary can round the next character's left edge by that much (measured). WebKit
    # rounds the range box of a character there to whole pixels (by up to 0.6px, measured); the
    # boxes of the segments and readings stay the same to 1/64 px.
    def near(a, b, slack=1 if engine == "webkit" else 1 / 64):
        return all(abs(a[k] - b[k]) <= slack + 1e-6 for k in a)
    assert [ch for ch, _ in base_chars(marked)] == [ch for ch, _ in base_chars(plain)]
    assert all(near(a, b) for (_, a), (_, b) in zip(base_chars(marked), base_chars(plain)))
    assert all(near(a["box"], b["box"], 1 / 64) for a, b in zip(marked["segments"], plain["segments"]))
    assert all(near(a["box"], b["box"], 1 / 64) for a, b in zip(marked["rts"], plain["rts"]))
    assert marked["root"] == plain["root"]


# --- punctuation -----------------------------------------------------------------------------

def ink_box(page, box):
    """Where the dark pixels lie within a character's box, as fractions (left, top, right, bottom)."""
    width, bpp, rows = png_rows(page.screenshot(clip={"x": box["left"], "y": box["top"], "width": box["width"], "height": box["height"]}))
    points = [(x, y) for y, row in enumerate(rows) for x in range(width) if min(row[x * bpp:x * bpp + 3]) < 128]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs) / width, min(ys) / len(rows), (max(xs) + 1) / width, (max(ys) + 1) / len(rows)


def test_punctuation_brackets_and_the_long_vowel_mark_take_their_vertical_forms(drawn):
    shapes = {}
    for mode, options in (("horizontal", {}), ("vertical", V)):
        # without kerning, which in horizontal text pulls a kana into the box of the mark after it
        at = drawn(PUNCT, style="font-kerning: none; " + (TALL if mode == "vertical" else ""), **options)
        found = at()
        for c in found["chars"]:
            if c["ch"] in "「」、。ー（）ょ":
                # a whole em each: nothing was trimmed, so the fractions compare (across the line,
                # Firefox rounds the font's ascent and descent up to whole pixels: 41px, measured)
                along, across = ("width", "height") if mode == "horizontal" else ("height", "width")
                assert c["box"][along] == pytest.approx(40, abs=0.5) and 39.5 <= c["box"][across] <= 41.5, c
                left, top, right, bottom = ink_box(at.page, c["box"])
                shapes[mode, c["ch"]] = {"x": (left + right) / 2, "y": (top + bottom) / 2, "w": right - left, "h": bottom - top}
    h = {ch: shapes["horizontal", ch] for ch in "「」、。ー（）ょ"}
    v = {ch: shapes["vertical", ch] for ch in "「」、。ー（）ょ"}
    for ch in "、。":  # at the lower left of the em in horizontal text, the upper right in vertical text
        assert h[ch]["x"] < 0.5 < h[ch]["y"], (ch, h[ch])
        assert v[ch]["y"] < 0.5 < v[ch]["x"], (ch, v[ch])
    # the long-vowel mark runs along the line: across in horizontal text, down in vertical text
    assert h["ー"]["w"] > 3 * h["ー"]["h"] and v["ー"]["h"] > 3 * v["ー"]["w"], (h["ー"], v["ー"])
    for ch in "「（":  # an opening bracket sits next to what it opens: at the right, or below
        assert h[ch]["x"] > 0.5 and h[ch]["h"] > h[ch]["w"], (ch, h[ch])
        assert v[ch]["y"] > 0.5 and v[ch]["w"] > v[ch]["h"], (ch, v[ch])
    for ch in "」）":  # a closing bracket after what it closes: at the left, or above
        assert h[ch]["x"] < 0.5 and h[ch]["h"] > h[ch]["w"], (ch, h[ch])
        assert v[ch]["y"] < 0.5 and v[ch]["w"] > v[ch]["h"], (ch, v[ch])
    # a small kana moves towards the upper right of its em
    assert v["ょ"]["x"] > h["ょ"]["x"] + 0.05 and v["ょ"]["y"] < h["ょ"]["y"] - 0.05, (h["ょ"], v["ょ"])


# --- paging by t, across columns -----------------------------------------------------------------

PAGED = "height: 280px; --tsubu-max-lines: 2"


def test_beyond_the_maximum_number_of_columns_the_page_with_the_current_segment_is_shown(drawn):
    at = drawn(VERY_LONG, fluid=True, style=PAGED, **V)
    end = segment_times(VERY_LONG)[-1][2]
    shown_with, pages_seen = {}, []
    for i, start, stop in segment_times(VERY_LONG):
        found = at((start + stop) / 2)
        segments = found["segments"]
        assert not segments[i]["offPage"] and segments[i]["current"] == "true", i
        assert len(columns_of(found)) <= 2
        check_columns(found)
        # a page begins at the top of a column
        first = next(s for s in segments if not s["offPage"])
        assert abs(first["box"]["top"] - found["root"]["top"]) < 1
        page = int(found["page"])
        pages_seen.append(page)
        shown_with.setdefault(page, set()).update(k for k, s in enumerate(segments) if not s["offPage"])
    pages = int(found["pages"])
    assert pages >= 3
    assert pages_seen == sorted(pages_seen) and set(pages_seen) == set(range(pages))
    assert sorted(k for ks in shown_with.values() for k in ks) == list(range(len(VERY_LONG["segments"])))
    assert int(at(-1)["page"]) == 0 and int(at(end + 5)["page"]) == pages - 1

    # The pages are the columns of the whole sentence laid out greedily, two by two from the right.
    whole = drawn(VERY_LONG, fluid=True, style="height: 280px; --tsubu-wrap: wrap", **V)()
    column = segment_columns(whole)
    for page, indexes in shown_with.items():
        assert {column[k] // 2 for k in indexes} == {page}, (page, sorted(indexes))


def test_the_page_is_a_function_of_t_alone_and_switching_the_furigana_does_not_reflow_it(drawn):
    at = drawn(VERY_LONG, fluid=True, style=PAGED, **V)
    seen = {}
    for t in (0.1, 6.0, 2.2, 8.9, 0.1, 4.4, 6.0):
        found = at(t)
        key = (found["page"], tuple(s["offPage"] for s in found["segments"]),
               tuple((c["ch"], c["box"]["left"], c["box"]["top"]) for c in visible(found)))
        assert seen.setdefault(t, key) == key, t
    on, off = at(5.0), at(5.0, False)
    assert on["page"] == off["page"] and base_chars(on) == base_chars(off)


# --- fluid size --------------------------------------------------------------------------------

@pytest.mark.parametrize("height, size", [(120, 14), (300, 300 / 11), (479, 479 / 11), (480, 32), (600, 40),
                                          (959, 959 / 15), (960, 960 / 18), (1200, 1200 / 18), (1500, 72)])
def test_in_a_fluid_container_the_size_follows_the_height_in_vertical_text(drawn, height, size):
    found = drawn(TIMED, fluid=True, style=f"height: {height}px", **V)()
    assert found["fontSize"] == pytest.approx(size, abs=0.01)


def test_in_vertical_text_the_width_does_not_change_the_size_and_every_step_is_configurable(drawn):
    sizes = [drawn(TIMED, width=w, fluid=True, style="height: 600px", **V)()["fontSize"] for w in (200, 700, 1200)]
    assert sizes == pytest.approx([40, 40, 40])
    style = "--tsubu-narrow-chars: 8; --tsubu-chars: 20; --tsubu-wide-chars: 30; --tsubu-size-min: 10px; --tsubu-size-max: 99px"
    sizes = [drawn(TIMED, fluid=True, style=f"height: {h}px; {style}", **V)()["fontSize"] for h in (200, 600, 1200)]
    assert sizes == pytest.approx([25, 30, 40])
    # a step can have its own maximum number of columns
    style = "height: 300px; --tsubu-max-lines: 3; --tsubu-narrow-max-lines: 1"
    assert len(columns_of(drawn(VERY_LONG, fluid=True, style=style, **V)(3.0))) == 1


def test_the_writing_mode_can_come_from_an_ancestor_and_the_root_can_refuse_it(drawn, engine):
    at = drawn(DIGITS, fluid=True, style="height: 600px")
    assert at()["writing"] == "horizontal-tb"
    at.page.evaluate("() => document.getElementById('bubble').dataset.tsubuWriting = 'vertical'")
    if engine == "webkit":
        # WebKit draws the change, but the range boxes of the characters after an upright run
        # keep their horizontal advance until the boxes are built again (measured)
        at.page.evaluate("() => { const r = document.querySelector('.tsubu'); r.style.display = 'none'; r.offsetHeight; r.style.display = ''; }")
    found = at(0.7)
    assert found["writing"] == "vertical-rl" and found["fontSize"] == pytest.approx(40)  # 600px tall / 15
    assert {u["text"] for u in found["upright"]} == {"10", "AI", "!?"}  # marked without the option
    assert all(u["box"]["height"] == pytest.approx(40, abs=1) for u in found["upright"])
    check_columns(found)
    kept = drawn(TIMED, writing="horizontal")
    kept.page.evaluate("() => document.getElementById('bubble').dataset.tsubuWriting = 'vertical'")
    assert kept()["writing"] == "horizontal-tb"


# --- contrast, plate and forced colours --------------------------------------------------------

CHECK = "(options) => Tsubu.checkContrast(document.querySelector('.tsubu'), options || undefined)"


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("sentence", [TIMED, WHOLE], ids=["timed", "whole"])
def test_every_preset_meets_the_thresholds_in_vertical_text(drawn, theme, sentence):
    at = drawn(sentence, style=TALL, theme=theme, **V)
    at(1.2)
    found = at.page.evaluate(CHECK)
    assert found["ok"], found["failures"]
    layers = {(c["state"], c["layer"]) for c in found["checks"]}
    assert {("current", "ruby"), ("current", "underline"), ("current", "highlight")} <= layers


def test_furigana_at_the_right_of_the_highlight_are_measured_against_the_page(drawn):
    # The geometry runs across the column, which is horizontal here: the readings sit at the right
    # of the highlight, on the page, and the side line at its left, inside the highlight's spread.
    at = drawn(TIMED, style=TALL, theme="light", **V)
    found = at.page.evaluate(CHECK)
    current = lambda f, layer: {c["background"] for c in f["checks"] if c["state"] == "current" and c["layer"] == layer}
    assert current(found, "ruby") == {"#ffffff", "#f1f5f9"}
    assert current(found, "underline") == {"#1d4ed8"}
    at.page.evaluate("() => document.querySelector('.tsubu').style.setProperty('--tsubu-current-ruby-color', '#dbeafe')")
    assert {(f["state"], f["layer"]) for f in at.page.evaluate(CHECK)["failures"]} == {("current", "ruby")}
    at.page.evaluate("() => document.querySelector('.tsubu').style.setProperty('--tsubu-current-spread', '1em')")
    covered = at.page.evaluate(CHECK)
    assert current(covered, "ruby") == {"#1d4ed8"} and covered["ok"]


def test_the_highlight_and_the_plate_are_drawn_around_the_columns(drawn):
    at = drawn(TIMED, style=TALL, theme="media", **V)
    found = at(1.2)
    look = at.page.evaluate("""() => { const root = document.querySelector('.tsubu'), plate = getComputedStyle(root, '::before');
      const seg = root.querySelector('[data-state="current"]'), band = getComputedStyle(seg, '::before');
      return {plate: [plate.left, plate.top, plate.right, plate.bottom].map(parseFloat), bg: plate.backgroundColor,
              band: [band.top, band.bottom, band.width].map(parseFloat), current: BAND_COLOUR(seg)}; }""".replace("BAND_COLOUR", BAND_COLOUR))
    # the plate reaches 0.25em past the sentence's box on every side, and the highlight (the segment's
    # ::before, turned with the text) 0.06em past the segment's em box along the column and across it
    assert look["plate"] == pytest.approx([-10, -10, -10, -10])
    assert look["bg"] == "rgba(0, 0, 0, 0.75)" and look["current"] == "rgb(253, 224, 71)"
    assert look["band"] == pytest.approx([-2.4, -2.4, 40 + 2 * 2.4], abs=0.02)
    assert found["root"] == drawn(TIMED, style=TALL, **V)(1.2)["root"]  # the plate takes no room


def test_in_forced_colours_the_segment_being_spoken_keeps_its_highlight_and_nothing_moves(drawn):
    at = drawn(LONG, style=TALL, theme="media", **V)
    normal = at(2.3)
    at.page.emulate_media(forced_colors="active")
    forced = at()
    system = at.page.evaluate("""() => { const d = document.createElement('div'); document.body.append(d); const out = {};
      for (const c of ['Highlight', 'HighlightText', 'CanvasText']) { d.style.color = c; out[c] = getComputedStyle(d).color; } d.remove(); return out; }""")
    current = at.page.evaluate("""() => { const s = document.querySelector('.tsubu-seg[data-state="current"]'), st = getComputedStyle(s);
      return {bg: BAND_COLOUR(s), color: st.color, rt: getComputedStyle(s.querySelector('rt')).color,
              side: getComputedStyle(s, '::after').borderLeftColor}; }""".replace("BAND_COLOUR", BAND_COLOUR))
    assert current == {"bg": system["Highlight"], "color": system["HighlightText"], "rt": system["CanvasText"], "side": system["HighlightText"]}
    assert base_chars(forced) == base_chars(normal) and forced["root"] == normal["root"]
    assert json.dumps([s["box"] for s in forced["segments"]]) == json.dumps([s["box"] for s in normal["segments"]])
