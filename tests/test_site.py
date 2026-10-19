"""The site (site/): every page loads without errors and without a horizontal scroll at phone
width, every colour pair on it meets the thresholds, both languages are complete, the API page
agrees with the README and the library, and the home page's film draws every frame from t alone
while its loupe's two layers line up character for character.

Every page is a whole document. All are copied into tmp_path next to the library files, as the
symlinks in site/ place them. Fonts come from Google Fonts; without a network the browser falls
back to system fonts, which changes the look but none of these checks."""

import re
import shutil

import pytest

from support import ROOT, run_library

SITE = ROOT / "site"
PAGES = ["index.html", "start.html", "guide.html", "api.html", "playground.html", "gallery.html"]


@pytest.fixture(scope="module")
def copied(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    for name in ("tsubu.css", "tsubu.js", "tsubu-export.js"):
        shutil.copy(ROOT / name, out / name)
    for path in SITE.iterdir():
        if path.is_symlink() or not path.is_file():
            continue
        shutil.copy(path, out / path.name)
    return out


@pytest.fixture
def site(browser, copied):
    pages = []

    def open_page(name="index.html", width=1280):
        page = browser.new_page(viewport={"width": width, "height": 900}, reduced_motion="reduce")
        pages.append(page)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto((copied / name).as_uri())
        page.wait_for_function("window.__ready === true", timeout=30000)
        page.errors = errors
        return page

    yield open_page
    for page in pages:
        page.close()


def test_the_library_files_in_site_are_the_library(copied):
    for name in ("tsubu.css", "tsubu.js", "tsubu-export.js"):
        assert (SITE / name).is_symlink() and (SITE / name).read_bytes() == (ROOT / name).read_bytes()



def test_the_not_found_page_stands_alone_and_links_home(browser, copied):
    # GitHub Pages serves 404.html at any missing path, so it may not rely on relative files.
    text = (SITE / "404.html").read_text(encoding="utf-8")
    assert not re.search(r'<(?:link|script)[^>]+(?:href|src)=', text)
    page = browser.new_page(viewport={"width": 390, "height": 800})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    try:
        page.goto((copied / "404.html").as_uri())
        assert errors == []
        assert page.evaluate("() => document.documentElement.scrollWidth") <= 390
        links = page.evaluate("() => [...document.querySelectorAll('main a')].map((a) => a.getAttribute('href'))")
    finally:
        page.close()
    assert links == ["/", "/", "/"]  # a file:// page is not on github.io, so home is the root


# ---- every page ----

@pytest.mark.parametrize("width", [1280, 390])
@pytest.mark.parametrize("name", PAGES)
def test_every_page_loads_and_fits_the_screen(site, name, width):
    page = site(name, width)
    assert page.errors == []
    assert page.evaluate("() => document.documentElement.scrollWidth") <= width
    assert page.evaluate("() => document.querySelectorAll('.tsubu').length") > 0  # Japanese is drawn by tsubu


# Every element with text of its own, in the colour the browser computed, against the nearest
# painted background behind it (translucent colours composited), through any opacity between.
# Canvas (the film) and the sentences drawn by tsubu are left to their own checks; outline text
# (colour transparent) and elements over a background image are not measured here.
PAIRS = """() => {
  const cv = document.createElement('canvas').getContext('2d');
  const norm = (c) => { cv.fillStyle = '#000'; cv.fillStyle = c; return cv.fillStyle; };  // hex or rgba()
  const alpha = (c) => { const m = /rgba?\\([^)]*,\\s*([\\d.]+)\\)$/.exec(c); return c === 'transparent' ? 0 : m ? parseFloat(m[1]) : 1; };
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('.tsubu, canvas, script, style, [data-unchecked]')) continue;
    const text = [...el.childNodes].filter((n) => n.nodeType === 3 && n.data.trim()).map((n) => n.data.trim()).join(' ');
    if (!text) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || el.getBoundingClientRect().width === 0) continue;
    const fg = norm(cs.color); if (alpha(fg) === 0) continue;
    let opacity = 1, bg = null, image = false;
    for (let n = el; n; n = n.parentElement) {
      const s = getComputedStyle(n); opacity *= parseFloat(s.opacity);
      if (s.backgroundImage !== 'none') { image = true; break; }
      const b = norm(s.backgroundColor);
      if (alpha(b) > 0) { if (bg === null) bg = b; else break; if (alpha(b) === 1) break; }
    }
    if (image || opacity === 0) continue;
    const under = bg || '#ffffff';
    const ratio = Tsubu.contrast(opacity < 1 ? fg.replace(/^#(..)(..)(..)$/, (m, r, g, b) => `rgba(${parseInt(r, 16)}, ${parseInt(g, 16)}, ${parseInt(b, 16)}, ${opacity})`) : fg, under, '#ffffff');
    out.push({ text: text.slice(0, 40), tag: el.tagName + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : ''), fg, bg: under, ratio: Math.round(ratio * 100) / 100 });
  }
  return out; }"""

SENTENCES = """() => [...document.querySelectorAll('.tsubu')].filter((r) => !r.closest('[data-unchecked]')).map((r) => {
  const res = Tsubu.checkContrast(r, r.closest('[data-tsubu-theme]') ? {} : { backdrop: getComputedStyle(document.body).backgroundColor });
  return { text: r.textContent.slice(0, 12), ok: res.ok, failures: res.failures.slice(0, 3) }; })"""


@pytest.mark.parametrize("name", PAGES)
@pytest.mark.parametrize("lang", ["en", "zh", "ja"])
def test_every_colour_pair_on_the_page_meets_the_thresholds(site, name, lang):
    page = site(name)
    page.evaluate(f"() => Site.setLang('{lang}')")
    low = [p for p in page.evaluate(PAIRS) if p["ratio"] < 4.5]
    assert low == [], low
    bad = [s for s in page.evaluate(SENTENCES) if not s["ok"]]
    assert bad == [], bad


@pytest.mark.parametrize("name", PAGES)
def test_all_three_languages_are_complete_and_the_switch_shows_one(site, name):
    """Every string exists in English, 简体中文 and 日本語 (the same count of each, none left as the
    missing marker), the switch shows exactly one language, the document's lang follows it, and
    the Japanese view fits a phone."""
    page = site(name)
    counts = page.evaluate("() => ({ en: document.querySelectorAll('.en').length, zh: document.querySelectorAll('.zh').length, ja: document.querySelectorAll('.ja').length })")
    assert counts["en"] == counts["zh"] == counts["ja"] and counts["en"] > 5, counts
    assert page.evaluate("() => document.body.innerText.includes('⟦missing⟧')") is False
    assert page.evaluate("() => [...document.querySelectorAll('.ja')].every((e) => e.lang === 'ja')")
    shown = "(cls) => [...document.querySelectorAll('.' + cls)].filter((e) => getComputedStyle(e).display !== 'none').length"
    assert page.evaluate(shown, "zh") == 0 and page.evaluate(shown, "ja") == 0 and page.evaluate(shown, "en") == counts["en"]
    for code, tag in (("zh", "zh-CN"), ("ja", "ja"), ("en", "en")):
        page.click(f".lang[data-lang='{code}']")
        assert page.evaluate("() => document.documentElement.lang") == tag
        assert page.evaluate(shown, code) == counts[code]
        assert sum(page.evaluate(shown, other) for other in ("en", "zh", "ja") if other != code) == 0
        assert page.evaluate("() => document.querySelector('.lang[aria-pressed=true]').dataset.lang") == code
    assert page.errors == []


@pytest.mark.parametrize("name", PAGES)
def test_the_japanese_view_fits_a_phone(site, name):
    page = site(name, 390)
    page.click(".lang[data-lang='ja']")
    page.wait_for_timeout(100)
    assert page.evaluate("() => document.documentElement.scrollWidth") <= 390
    assert page.evaluate("() => getComputedStyle(document.body).lineBreak") == "strict"
    assert page.errors == []


def test_the_navigation_links_every_page_and_marks_the_current_one(site):
    for name in PAGES:
        page = site(name)
        hrefs = page.evaluate("() => [...document.querySelectorAll('.nav a')].map((a) => a.getAttribute('href'))")
        assert hrefs[:len(PAGES)] == PAGES and all(h.startswith("https://github.com/") for h in hrefs[len(PAGES):])
        assert page.evaluate("() => document.querySelector('.nav a[aria-current=page]').getAttribute('href')") == name


def test_the_design_system_holds_on_every_page(site):
    """The section label keeps its proportion (a 22px kanji, a 13px title) whatever heading rules
    surround it, no example surface has an outline, and the footer sits at the bottom of the
    window when the page is shorter than it."""
    for name in PAGES:
        page = site(name)
        labels = page.evaluate("""() => [...document.querySelectorAll('h2.label')].map((h) => [getComputedStyle(h.querySelector('.kanji')).fontSize, getComputedStyle(h).fontSize])""")
        assert labels and all(l == ["22px", "13px"] for l in labels), (name, labels)
        outlines = page.evaluate("""() => [...document.querySelectorAll('.stage, .frame')].map((e) => getComputedStyle(e).outlineStyle + ' ' + getComputedStyle(e).borderStyle)""")
        assert all(o == "none none" for o in outlines), (name, outlines)
    page = site("playground.html")
    page.set_viewport_size({"width": 1280, "height": 2400})
    found = page.evaluate("() => ({ foot: document.querySelector('footer.foot').getBoundingClientRect().bottom, inner: innerHeight, doc: document.documentElement.scrollHeight })")
    assert found["doc"] <= found["inner"] and found["inner"] - found["foot"] < 60, found


def test_the_api_tables_share_a_grid(site):
    """Every table's first two columns are two twelfths each, so their edges line up down the page."""
    page = site("api.html")
    edges = page.evaluate("""() => [...document.querySelectorAll('.api table')].map((t) => {
      const cells = [...t.querySelector('tbody tr').children].map((c) => c.getBoundingClientRect()); const w = t.getBoundingClientRect().width;
      return cells.slice(0, 2).map((c) => Math.round((c.width / w) * 12 * 10) / 10); })""")
    assert len(edges) >= 10
    for e in edges:
        assert abs(e[0] - 2) < 0.15 and (len(e) < 2 or abs(e[1] - 2) < 0.15 or abs(e[1] - 10) < 0.15), edges


# ---- the API page against the README and the library ----

def test_the_api_page_names_everything_the_readme_and_the_library_do(site):
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    page = site("api.html")
    text = page.evaluate("() => document.getElementById('api').innerText")  # innerText keeps cells apart
    # the speaker group is written with a placeholder name in both, and left out here
    names = lambda s: {p for p in re.findall(r"--tsubu-[a-z-]+", s) if not p.startswith("--tsubu-speaker-")}
    assert names(readme) == names(text), names(readme) ^ names(text)
    found = run_library({"segments": [{"parts": [{"text": "a"}]}]})
    for key in found["keys"]:
        assert f"Tsubu.{key}" in text, key
    assert f'"{found["version"]}"' in text and f'`"{found["version"]}"`' in readme
    for name in ("toWebVTT", "toASS", "toASSScript", "toSRT"):
        assert f"TsubuExport.{name}" in text and f"`TsubuExport.{name}" in readme or f"**`{name}`**" in readme
    for motion in ("appear", "mask", "blur", "underline-draw"):
        assert motion in text and f"`{motion}`" in readme


# ---- the home page's film ----

FRAME = """(t) => { renderAt(t); return [document.getElementById('fx').toDataURL(), document.getElementById('line').innerHTML,
  document.getElementById('cap').innerHTML, document.getElementById('endcard').outerHTML]; }"""


def test_every_film_frame_is_a_function_of_t_alone(site):
    page = site()
    times = [0.3, 0.55, 1.3, 1.75, 2.3, 2.95, 3.5, 3.85, 4.68, 5.2, 5.75, 6.0, 6.5, 7.1, 7.3, 7.8, 8.6]
    first = {t: page.evaluate(FRAME, t) for t in times}
    for t in reversed(times):
        assert page.evaluate(FRAME, t) == first[t], t
    assert len({tuple(f) for f in first.values()}) == len(times)  # and the frames differ
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


def test_the_film_cuts_stay_under_three_a_second(site):
    page = site()
    # the field's colour at every frame; a cut is a frame whose base colour differs from the one before
    fields = page.evaluate("() => { const out = []; for (let i = 0; i <= 270; i++) { renderAt(i / 30); out.push(document.getElementById('line').dataset.field); } return out; }")
    cuts = [i / 30 for i in range(1, len(fields)) if fields[i] != fields[i - 1]]
    for a in cuts:
        assert sum(1 for b in cuts if a <= b < a + 1) <= 2, cuts


# ---- the loupe ----

LAYERS = """() => { const boxes = (layer) => [...layer.querySelectorAll('.tsubu-seg')].map((s) => { const r = s.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; });
  const chars = (layer) => { const out = [], w = document.createTreeWalker(layer.querySelector('.tsubu'), NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) { if (n.parentElement.closest('rt')) continue;
      for (let i = 0; i < n.data.length; i++) { const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + 1); const b = r.getBoundingClientRect(); out.push([n.data[i], b.left, b.top]); } }
    return out; };
  const base = document.getElementById('base'), top = document.getElementById('top');
  return { segs: [boxes(base), boxes(top)], chars: [chars(base), chars(top)], ruby: [base.querySelector('.tsubu').dataset.ruby, top.querySelector('.tsubu').dataset.ruby] }; }"""


@pytest.mark.parametrize("width", [1280, 390])
def test_the_loupe_layers_line_up_character_for_character(site, width):
    page = site("index.html", width)
    found = page.evaluate(LAYERS)
    assert found["ruby"] == ["off", "on"]
    assert found["segs"][0] == found["segs"][1]
    assert found["chars"][0] == found["chars"][1] and len(found["chars"][0]) > 30
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


# ---- the other pages do what they say ----

def test_the_start_page_redraws_the_edited_sentence_and_shows_errors(site):
    page = site("start.html")
    assert page.evaluate("() => document.querySelectorAll('#ex2 .tsubu-seg').length") == 6
    page.fill("#ex2-src", '{"segments": [{"parts": [{"text": "猫", "ruby": "ねこ"}], "start": 0, "end": 1}, {"parts": [{"text": "。"}], "kind": "punct"}]}')
    assert page.evaluate("() => document.querySelector('#ex2 .tsubu').textContent") == "猫ねこ。"
    page.fill("#ex2-src", '{"segments": [{"parts": [{"text": "猫"}], "start": 0, "end": 1}, {"parts": [{"text": "。"}], "kind": "punct", "start": 1, "end": 2}]}')
    assert page.locator("#ex2-err").text_content().startswith("tsubu:")
    assert page.errors == []


def test_the_playground_switches_everything_and_checks_the_contrast(site):
    page = site("playground.html")
    assert page.locator("#verdict").text_content().startswith("ok")
    assert page.evaluate("() => document.querySelector('#stage .tsubu').dataset.tsubuTheme") == "light"
    page.select_option("#theme", "")
    assert "fail" in page.locator("#verdict").text_content()  # the unthemed defaults are not a preset
    page.select_option("#theme", "dark")
    page.select_option("#writing", "vertical")
    page.check('input[name="motion"][value="mask"]')
    root = "document.querySelector('#stage .tsubu')"
    assert page.evaluate(f"() => [{root}.dataset.tsubuWriting, {root}.dataset.tsubuMotion, {root}.dataset.tsubuTheme]") == ["vertical", "mask", "dark"]
    assert page.evaluate(f"() => getComputedStyle({root}).writingMode") == "vertical-rl"
    page.fill("#t", "3.5")
    page.dispatch_event("#t", "input")
    assert "current: 9" in page.locator("#state").text_content()
    assert page.locator("#vtt").text_content().startswith("WEBVTT")
    assert "Dialogue:" in page.locator("#ass").text_content()
    assert page.locator("#srt").text_content().startswith("1\n00:00:")
    assert page.errors == []


def test_the_gallery_shows_every_theme_speaker_motion_and_writing_mode(site):
    page = site("gallery.html")
    found = run_library({"segments": [{"parts": [{"text": "a"}]}]})
    themes = page.evaluate("() => [...document.querySelectorAll('#theme-grid .tsubu')].map((r) => [r.dataset.tsubuTheme || null, r.dataset.speaker || null])")
    assert themes == [[t, s] for t in ("light", "dark", "media") for s in ("a", "b")] + [[None, None]]
    motions = page.evaluate("() => [...document.querySelectorAll('#motion-grid .tsubu')].map((r) => r.dataset.tsubuMotion)")
    assert motions == ["appear", "mask", "blur", "underline-draw"]
    writing = page.evaluate("() => [...document.querySelectorAll('#writing-grid .tsubu')].map((r) => getComputedStyle(r).writingMode)")
    assert writing == ["horizontal-tb", "vertical-rl", "vertical-rl"]
    metas = page.evaluate("() => [...document.querySelectorAll('.card .meta')].map((m) => m.textContent)")
    assert all("✕" not in m for i, m in enumerate(metas) if i != 6) and "✕" in metas[6]
    assert "keys" in found


def test_the_guide_reveals_on_a_click_and_exports_subtitles(site):
    page = site("guide.html")
    page.click("#reveal .tsubu-seg[data-index='2']")
    assert page.evaluate("() => [...document.querySelectorAll('#reveal .tsubu-seg')].map((s) => s.hasAttribute('data-revealed'))") == [False, False, True, False, False, False]
    assert page.locator("#rv-out").text_content() == "revealed: [2]"
    page.click("#rv-all")
    assert page.locator("#rv-out").text_content() == "revealed: [0, 1, 2, 3, 4, 5]"
    assert page.locator("#sb-vtt").text_content().startswith("WEBVTT")
    assert page.evaluate("() => document.querySelectorAll('#strip .tsubu').length") == 6
    assert "aria-current" in page.locator("#ax-html").text_content()
    page.uncheck("#ax-announce")
    assert 'aria-hidden="true"' in page.locator("#ax-html").text_content()
    assert page.errors == []
