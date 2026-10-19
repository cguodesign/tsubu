"""The layout guarantees, measured in a headless browser on the library's own CSS and script."""

import struct
import zlib

import pytest

from support import LONG, TIMED, WHOLE


def base_chars(found):
    return [(c["ch"], c["box"]) for c in found["chars"] if not c["rt"]]


@pytest.mark.parametrize("sentence", [TIMED, WHOLE, LONG], ids=["timed", "whole", "two-lines"])
def test_no_character_moves_when_the_furigana_are_switched_or_the_highlight_moves(drawn, sentence):
    at = drawn(sentence)
    first = at()
    if sentence is LONG:  # furigana on a second line too
        assert len({round(b["top"]) for _, b in base_chars(first)}) == 2
    seen = [first]
    for t in (0.1, 1.05, 2.2, 3.0, 4.6, 5.0, 9.0):
        for on in (False, True):
            seen.append(at(t, on))
    for found in seen[1:]:
        assert base_chars(found) == base_chars(first)
        assert [s["box"] for s in found["segments"]] == [s["box"] for s in first["segments"]]
        assert [r["box"] for r in found["rts"]] == [r["box"] for r in first["rts"]]
        assert found["root"] == first["root"]
    # the switch really does hide and show them
    assert {r["visibility"] for r in at(None, False)["rts"]} == {"hidden"}
    assert {r["visibility"] for r in at(None, True)["rts"]} == {"visible"}


def test_a_sentence_drawn_with_the_furigana_off_has_the_same_layout_as_one_drawn_with_them_on(drawn):
    on, off = drawn(LONG, ruby=True)(), drawn(LONG, ruby=False)()
    assert base_chars(off) == base_chars(on) and off["root"] == on["root"]
    assert {r["visibility"] for r in off["rts"]} == {"hidden"}


@pytest.mark.parametrize("sentence", [TIMED, WHOLE, LONG], ids=["timed", "whole", "two-lines"])
def test_furigana_are_not_clipped_and_do_not_run_into_the_line_above(drawn, sentence):
    found = drawn(sentence)()
    root, bubble = found["root"], found["bubble"]
    base = [c for c in found["chars"] if not c["rt"]]
    for rt in found["rts"]:
        box = rt["box"]
        assert box["height"] > 0 and box["width"] > 0
        # inside the sentence's box, and so inside a container that hides its overflow
        assert box["top"] >= root["top"] and box["top"] >= bubble["top"], (box, root)
        assert box["bottom"] <= rt["base"]["top"] + 1, "the reading sits above its base"
        # nothing of the line above lies under it: neither its characters nor its underlines
        for c in base:
            b = c["box"]
            if b["bottom"] <= box["bottom"] and not (b["right"] <= box["left"] or b["left"] >= box["right"]):
                assert b["bottom"] <= box["top"], (c["ch"], b, box)
        for s in found["segments"]:
            u = s["underline"]
            if u["bottom"] <= box["bottom"] and not s["punct"] and not (u["right"] <= box["left"] or u["left"] >= box["right"]):
                assert u["bottom"] <= box["top"], (u, box)


def png_rows(data):
    """The pixel rows of a screenshot (8-bit RGB or RGBA, not interlaced), as (width, bytes per pixel, rows)."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    at, idat, header = 8, b"", None
    while at < len(data):
        length, kind = struct.unpack(">I4s", data[at:at + 8])
        body = data[at + 8:at + 8 + length]
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat += body
        at += 12 + length
    width, height, depth, colour, _, _, interlace = header
    assert depth == 8 and colour in (2, 6) and interlace == 0, header
    bpp = 4 if colour == 6 else 3
    raw, stride, rows, previous = zlib.decompress(idat), width * bpp, [], bytearray(width * bpp)
    for y in range(height):
        kind, line = raw[y * (stride + 1)], bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b, c = previous[x], previous[x - bpp] if x >= bpp else 0
            if kind == 1:
                line[x] = (line[x] + a) & 255
            elif kind == 2:
                line[x] = (line[x] + b) & 255
            elif kind == 3:
                line[x] = (line[x] + (a + b) // 2) & 255
            elif kind == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rows.append(line)
        previous = line
    return width, bpp, rows


def ink_width(page, box):
    """How wide the dark pixels are in a band through the middle of a box. The upper and lower fifth
    are left out, so neither the furigana above nor the underline below count."""
    band = box["height"] / 5
    clip = {"x": box["left"], "y": box["top"] + band, "width": box["width"], "height": box["height"] - 2 * band}
    width, bpp, rows = png_rows(page.screenshot(clip=clip))
    dark = [x for x in range(width) if any(min(row[x * bpp:x * bpp + 3]) < 128 for row in rows)]
    return dark[-1] - dark[0] + 1


SAME_TEXT = """([text, align]) => {
  const holder = document.createElement("div");
  holder.className = "tsubu";
  holder.style.cssText = "font-size: 40px; margin: 40px";
  holder.innerHTML = align === null ? `<span>${text}</span>` : `<ruby style="ruby-align: ${align}">${text}<rt>${align}</rt></ruby>`;
  document.body.append(holder);
  return holder;
}"""


def test_a_reading_wider_than_its_base_does_not_spread_the_base(drawn):
    at = drawn(WHOLE)
    found = at()
    page = at.page
    assert set(found["rubyAlign"]) == {"center"}
    wide = 0
    for index, ruby in enumerate(page.locator(".tsubu ruby").all()):
        reading = [c["box"] for c in found["chars"] if c["rt"] and c["rubyIndex"] == index]
        base = [c for c in found["chars"] if c["ruby"] and c["rubyIndex"] == index]
        text = "".join(c["ch"] for c in base)
        # measured across the ruby's own box (a character's range box also takes in the reading's
        # overhang onto the next character), through the middle of the base characters
        across = ruby.bounding_box()
        box = {"left": across["x"], "width": across["width"], "top": base[0]["box"]["top"], "height": base[0]["box"]["height"]}
        if reading[-1]["right"] - reading[0]["left"] <= len(text) * 40:
            continue
        wide += 1
        # the base is as wide as the same text without furigana: nothing was put between its characters
        drawn_base = ink_width(page, box)
        plain = page.evaluate_handle(SAME_TEXT, [text, None]).as_element().query_selector("span").bounding_box()
        plain_width = ink_width(page, {"left": plain["x"], "top": plain["y"], "width": plain["width"], "height": plain["height"]})
        assert abs(drawn_base - plain_width) <= 1, (text, drawn_base, plain_width)
        # and the measurement would have noticed: the same ruby with space-around comes out wider
        spread = page.evaluate_handle(SAME_TEXT, [text, "space-around"]).as_element().query_selector("ruby")
        spread_box = page.evaluate("""(ruby) => { const n = ruby.firstChild, r = document.createRange();
            r.setStart(n, 0); r.setEnd(n, n.data.length); const b = r.getBoundingClientRect(), a = ruby.getBoundingClientRect();
            return {left: a.left, width: a.width, top: b.top, height: b.height}; }""", spread)
        assert ink_width(page, spread_box) > plain_width + 3, text
    assert wide == 3  # せんしゅう, とうきょう and じゅぎょう are each wider than their two kanji


def test_every_segment_has_its_own_dotted_underline_apart_from_its_neighbours(drawn):
    for sentence in (TIMED, WHOLE, LONG):
        found = drawn(sentence)()
        spoken = [s for s in found["segments"] if not s["punct"]]
        assert all(s["underline"]["style"] == "dotted" and s["underline"]["width"] > 0 for s in spoken)
        assert all(s["underline"]["content"] == "none" for s in found["segments"] if s["punct"])
        assert {s["decoration"] for s in found["segments"]} == {"none"}, "no text-decoration to run into the next segment"
        for s in spoken:
            u = s["underline"]
            assert s["box"]["left"] < u["left"] < u["right"] < s["box"]["right"]
        for left, right in zip(spoken, spoken[1:]):
            if round(left["box"]["top"]) == round(right["box"]["top"]):  # on the same line
                assert right["underline"]["left"] - left["underline"]["right"] >= 4, (left, right)


def test_a_line_breaks_only_between_segments_and_never_before_punctuation(drawn):
    for width in (900, 520, 300):
        found = drawn(LONG, width=width)()
        chars = [c for c in found["chars"] if not c["rt"]]
        lines = sorted({round(c["box"]["top"]) for c in chars})
        assert len(lines) >= 2, width
        for s in found["segments"]:
            # a segment is never split: its box is one line high
            assert s["box"]["height"] < 80, (width, s)
            assert s["box"]["right"] <= found["bubble"]["right"] + 0.5, (width, s)
        starts = [s for s in found["segments"][1:] if round(s["box"]["left"]) == round(found["root"]["left"])]
        assert starts and not any(s["punct"] for s in starts), width


def test_the_segment_being_spoken_carries_aria_current(drawn):
    at = drawn(TIMED)
    for t, current in ((-1, None), (0.2, 0), (1.2, 3), (1.45, None), (3.0, 6), (3.5, None)):
        found = at(t)
        assert [i for i, s in enumerate(found["segments"]) if s["current"] == "true"] == ([] if current is None else [current])
        assert found["rootCurrent"] is None
        if current is not None:
            assert found["segments"][current]["state"] == "current"


def test_apply_writes_the_progress_as_a_custom_property(drawn):
    at = drawn(TIMED)
    found = at(0.25)
    assert float(found["rootProgress"]) == pytest.approx(0.25 / 3.5)
    assert float(found["segments"][0]["progress"]) == pytest.approx(0.5)
    assert found["segments"][1]["progress"] is None  # punctuation has none


def test_without_segment_times_the_sentence_is_current_and_no_segment_is(drawn):
    at = drawn(WHOLE)
    for t, state in ((3.0, "future"), (5.0, "current"), (6.0, "past")):
        found = at(t)
        assert found["rootState"] == state and {s["state"] for s in found["segments"]} == {state}
        assert found["rootCurrent"] == ("true" if state == "current" else None)
        assert all(s["current"] is None and s["progress"] is None for s in found["segments"])


def test_apply_draws_each_frame_from_t_alone_without_motion_or_new_nodes(drawn):
    at = drawn(LONG)
    fresh = at(2.3)
    for t in (4.9, 0.0, 1.5, 9.0):
        at(t)
    again = at(2.3)
    attributes = lambda f: [(s["state"], s["current"], s["progress"]) for s in f["segments"]]
    assert attributes(again) == attributes(fresh) and again["rootState"] == fresh["rootState"]
    assert again["text"] == fresh["text"] and again["nodes"] == fresh["nodes"]
    assert set(again["motion"]) == {"0s none"}


def test_apply_refuses_an_element_it_did_not_make(drawn):
    at = drawn(TIMED)
    page = at.page
    message = page.evaluate("""() => { try { S.apply(document.getElementById("bubble"), 0); } catch (e) { return e.message; } }""")
    assert message.startswith("tsubu: ") and 'class "tsubu"' in message
    message = page.evaluate("""() => { try { Tsubu.sentence({segments: [{parts: [{text: "x"}], start: 0, end: 1}]})
        .apply(document.querySelector(".tsubu"), 0); } catch (e) { return e.message; } }""")
    assert "segments" in message
