"""The demo page loads from file://, scrubs time and switches the furigana."""

from support import DEMO

CURRENT = """() => [...document.querySelectorAll('.tsubu')].map((r) =>
  [...r.querySelectorAll('[aria-current]')].map((e) => e.dataset.index)
  .concat(r.getAttribute('aria-current') ? ['sentence'] : []))"""
RUBY = "() => [...document.querySelectorAll('.tsubu')].map((r) => r.dataset.ruby)"


def test_the_demo_page_scrubs_time_and_switches_the_furigana(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    try:
        page.goto(DEMO.as_uri() + "?t=1.5")
        assert page.locator(".tsubu").count() >= 3
        before = page.evaluate(CURRENT)
        assert ["3"] in before  # 温かい is being spoken at 1.5 s
        page.locator("#t").fill("5")
        page.locator("#t").dispatch_event("input")
        after = page.evaluate(CURRENT)
        assert after != before and ["sentence"] in after
        assert set(page.evaluate(RUBY)) == {"on"}
        page.locator("#ruby").uncheck()
        assert set(page.evaluate(RUBY)) == {"off"}
        assert page.evaluate("() => document.querySelector('header img').naturalWidth") > 0
        assert errors == []
    finally:
        page.close()


def test_the_demo_page_reads_ruby_off_from_its_address(browser):
    page = browser.new_page(viewport={"width": 390, "height": 844})
    try:
        page.goto(DEMO.as_uri() + "?t=9&ruby=off")
        assert set(page.evaluate(RUBY)) == {"off"}
        assert not page.locator("#ruby").is_checked()
        # nothing on a phone-sized page is wider than the page
        assert page.evaluate("() => document.documentElement.scrollWidth") <= 390
    finally:
        page.close()


def test_the_demo_page_switches_the_theme_and_reports_the_contrast(browser, engine):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    # (in WebKit the vertical card's highlight is drawn off its segment, a limitation recorded in
    # the vertical tests, and its report says so; it is left out here)
    contrast = """(webkit) => [...document.querySelectorAll('.contrast')].filter((e) => !webkit ||
      getComputedStyle(e.closest('.card').querySelector('.tsubu')).writingMode === 'horizontal-tb').map((e) => e.textContent)"""
    try:
        page.goto(DEMO.as_uri() + "?t=14.6&theme=media")
        assert page.evaluate("() => document.getElementById('cards').dataset.tsubuTheme") == "media"
        speakers = page.evaluate("() => [...document.querySelectorAll('.tsubu[data-speaker]')].map((r) => r.dataset.speaker)")
        assert speakers == ["a", "b"]
        for theme in ("media", "dark", "light"):
            page.locator("#theme").select_option(theme)
            lines = page.evaluate(contrast, engine == "webkit")
            assert len(lines) == page.locator(".tsubu").count() - (engine == "webkit"), lines
            assert all(line.startswith("contrast ✓") for line in lines), lines
        # the unthemed defaults are not a preset, and the page says so
        page.locator("#theme").select_option("")
        assert page.evaluate("() => 'tsubuTheme' in document.getElementById('cards').dataset") is False
        assert all(line.startswith("contrast ✗") for line in page.evaluate(contrast))
        assert errors == []
    finally:
        page.close()


def test_the_demo_frame_follows_its_width_and_pages_by_t(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    frame = """() => { const root = document.querySelector('#frame .tsubu');
      return {size: parseFloat(getComputedStyle(root).fontSize), page: root.dataset.page ?? null, pages: root.dataset.pages ?? null,
              hidden: root.querySelectorAll('[data-off-page]').length}; }"""
    try:
        page.goto(DEMO.as_uri() + "?t=7.2&frame=320&lines=1")
        narrow = page.evaluate(frame)
        assert narrow["page"] == "0" and int(narrow["pages"]) > 1 and narrow["hidden"] > 0
        page.locator("#t").fill("11.5")
        page.locator("#t").dispatch_event("input")
        assert page.evaluate(frame)["page"] == str(int(narrow["pages"]) - 1)
        page.locator("#fw").fill("900")
        page.locator("#fw").dispatch_event("input")
        page.locator("#ml").select_option("none")
        wide = page.evaluate(frame)
        assert wide["size"] > narrow["size"] and wide["page"] is None and wide["hidden"] == 0
        assert errors == []
    finally:
        page.close()


def test_the_demo_motion_card_hides_what_is_unheard_and_reveals_a_clicked_segment(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    masked = """() => [...document.querySelectorAll('#motion-bubble .tsubu-seg')].map((s) => getComputedStyle(s).color === 'rgba(0, 0, 0, 0)')"""
    try:
        page.goto(DEMO.as_uri() + "?t=0.3&motion=mask")
        before = page.evaluate(masked)
        assert before[0] is False and before[2] is True  # 雨の日は is being spoken; 家で is still a blank
        page.locator("#motion-bubble .tsubu-seg[data-index='2']").click()
        assert page.evaluate(masked)[2] is False
        assert page.locator("#clicked").text_content() == "segment 2: 0.90–1.30 s"
        assert page.evaluate("() => getComputedStyle(document.querySelector('[data-tags~=new-word]'), '::after').borderBottomStyle") == "solid"
        page.locator("#motion-bubble .tsubu-seg[data-index='2']").click()
        assert page.evaluate(masked)[2] is True
        page.locator("#reveal-all").click()
        assert not any(page.evaluate(masked))
        assert errors == []
    finally:
        page.close()


VERTICAL = """() => { const root = document.querySelector('.bubble.vertical .tsubu'), card = root.closest('.card');
  const box = (e) => { const r = e.getBoundingClientRect(); return {left: r.left, right: r.right, top: r.top, bottom: r.bottom}; };
  return {writing: getComputedStyle(root).writingMode, root: box(root), card: box(card), bubble: box(root.parentElement),
          current: [...root.querySelectorAll('[aria-current]')].map((e) => e.dataset.index),
          upright: [...root.querySelectorAll('.tsubu-upright')].map((e) => [e.textContent, getComputedStyle(e).textCombineUpright]),
          rts: [...root.querySelectorAll('rt')].map((rt) => [box(rt), box(rt.parentElement)]),
          contrast: card.querySelector('.contrast').textContent}; }"""


def test_the_demo_page_has_a_vertical_card_that_fits_a_phone(browser, engine):
    for width, height in ((1280, 900), (390, 844)):
        page = browser.new_page(viewport={"width": width, "height": height})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        try:
            page.goto(DEMO.as_uri() + "?t=17.0")
            found = page.evaluate(VERTICAL)
            assert found["writing"] == "vertical-rl"
            assert found["current"] == ["1"]  # 10月 is being spoken at 17.0 s
            assert found["upright"] == [["10", "all"], ["1", "all"], ["AI", "all"]]
            # WebKit draws the highlight off the segment in vertical text (a limitation recorded in
            # the vertical tests), and the check reports the text it leaves on the page
            assert found["contrast"].startswith("contrast ✗" if engine == "webkit" else "contrast ✓"), found["contrast"]
            # the furigana are at the right of their bases, and the sentence stays inside its card,
            # set at the right of it, where vertical text begins
            assert found["rts"] and all(rt["left"] >= base["right"] - 1 for rt, base in found["rts"])
            assert found["card"]["left"] <= found["root"]["left"] and found["root"]["right"] <= found["card"]["right"]
            assert abs(found["root"]["right"] - found["bubble"]["right"]) < 1
            assert page.evaluate("() => document.documentElement.scrollWidth") <= width
            assert errors == []
        finally:
            page.close()
