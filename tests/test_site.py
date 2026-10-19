"""The site prototype (site/index.html): its film draws every frame from t alone, its colours meet
the contrast thresholds, and its loupe's two layers line up character for character.

The page is a fragment, as the artifact host serves it; the test wraps it in a document next to
copies of tsubu.css and tsubu.js. Its fonts come from Google Fonts; without a network the browser
falls back to system fonts, which changes the look but none of these checks."""

import shutil

import pytest

from support import ROOT

SITE = ROOT / "site" / "index.html"
HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
        "<style>:root{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>")


@pytest.fixture
def site(browser, tmp_path):
    (tmp_path / "index.html").write_text(HEAD + SITE.read_text(encoding="utf-8") + "</body></html>", encoding="utf-8")
    for name in ("tsubu.css", "tsubu.js"):
        shutil.copy(ROOT / name, tmp_path / name)
    pages = []

    def open_page(width=1280):
        page = browser.new_page(viewport={"width": width, "height": 900}, reduced_motion="reduce")
        pages.append(page)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto((tmp_path / "index.html").as_uri())
        page.wait_for_function("window.__ready === true", timeout=30000)
        page.errors = errors
        return page

    yield open_page
    for page in pages:
        page.close()


FRAME = """(t) => { renderAt(t); return [document.getElementById('fx').toDataURL(), document.getElementById('line').innerHTML,
  document.getElementById('cap').innerHTML, document.getElementById('endcard').outerHTML]; }"""


def test_every_film_frame_is_a_function_of_t_alone(site):
    page = site()
    times = [0.3, 0.55, 1.3, 1.75, 2.3, 2.95, 3.5, 3.85, 4.68, 5.2, 5.75, 6.9, 7.8]
    first = {t: page.evaluate(FRAME, t) for t in times}
    for t in reversed(times):
        assert page.evaluate(FRAME, t) == first[t], t
    assert len({tuple(f) for f in first.values()}) == len(times)  # and the frames differ (the end card is in the page, not the canvas)
    assert page.errors == []


BAND = """() => { const out = []; const C = (k) => getComputedStyle(document.documentElement).getPropertyValue('--' + k).trim();
  const line = document.getElementById('line'), seg = line.querySelector('[data-index="0"]');
  // the band the canvas draws under the segment being spoken, per field (see BAND in the page)
  const band = { shironeri: 'ruri', ruri: 'yamabuki', koiai: 'yamabuki', konjo: 'yamabuki', shu: 'koiai' };
  for (const field of ['shironeri', 'ruri', 'koiai', 'konjo', 'shu']) {
    line.dataset.field = field; seg.dataset.state = 'current';
    const s = getComputedStyle(seg), rt = getComputedStyle(seg.querySelector('rt')), u = getComputedStyle(seg, '::after');
    out.push({ field, text: Tsubu.contrast(s.color, C(band[field])), ruby: Tsubu.contrast(rt.color, C(field)),
               underline: Tsubu.contrast(u.borderBottomColor, C(band[field])), band: Tsubu.contrast(C(band[field]), C(field)) });
    seg.dataset.state = 'past';
    out.push({ field, past: true, text: Tsubu.contrast(getComputedStyle(seg).color, C(field)),
               ruby: Tsubu.contrast(getComputedStyle(seg.querySelector('rt')).color, C(field)),
               underline: Tsubu.contrast(getComputedStyle(seg, '::after').borderBottomColor, C(field)) });
  }
  return out; }"""


def test_the_film_colours_meet_the_thresholds_on_every_field(site):
    page = site()
    page.evaluate("renderAt(2.3)")
    for found in page.evaluate(BAND):
        assert found["text"] >= 4.5 and found["ruby"] >= 4.5 and found["underline"] >= 3, found
        if not found.get("past"):
            assert found["band"] >= 3, found


LAYERS = """() => { const boxes = (layer) => [...layer.querySelectorAll('.tsubu-seg')].map((s) => { const r = s.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; });
  const chars = (layer) => { const out = [], w = document.createTreeWalker(layer.querySelector('.tsubu'), NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) { if (n.parentElement.closest('rt')) continue;
      for (let i = 0; i < n.data.length; i++) { const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + 1); const b = r.getBoundingClientRect(); out.push([n.data[i], b.left, b.top]); } }
    return out; };
  const base = document.getElementById('base'), top = document.getElementById('top');
  return { segs: [boxes(base), boxes(top)], chars: [chars(base), chars(top)], ruby: [base.querySelector('.tsubu').dataset.ruby, top.querySelector('.tsubu').dataset.ruby] }; }"""


@pytest.mark.parametrize("width", [1280, 390])
def test_the_loupe_layers_line_up_character_for_character(site, width):
    page = site(width)
    found = page.evaluate(LAYERS)
    assert found["ruby"] == ["off", "on"]
    assert found["segs"][0] == found["segs"][1]
    assert found["chars"][0] == found["chars"][1] and len(found["chars"][0]) > 30
    # nothing on the page is wider than the page
    assert page.evaluate("() => document.documentElement.scrollWidth") <= width
    assert page.errors == []


def test_the_loupe_follows_the_pointer_and_the_keyboard(site):
    page = site()
    tag = lambda: page.locator("#utag").text_content()
    assert tag().startswith("09  いっしゅうかん")  # parked on 一週間を
    page.locator("#loupe").focus()
    page.keyboard.press("ArrowRight")
    assert tag().startswith("10  す")
    box = page.locator("#top .tsubu-seg[data-index='2']").bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    assert tag().startswith("02  うみ")
    clip = page.evaluate("() => getComputedStyle(document.getElementById('top')).clipPath")
    assert clip.startswith("circle(")
