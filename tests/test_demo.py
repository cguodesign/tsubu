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


def test_the_demo_page_switches_the_theme_and_reports_the_contrast(browser):
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    contrast = "() => [...document.querySelectorAll('.contrast')].map((e) => e.textContent)"
    try:
        page.goto(DEMO.as_uri() + "?t=14.6&theme=media")
        assert page.evaluate("() => document.getElementById('cards').dataset.tsubuTheme") == "media"
        speakers = page.evaluate("() => [...document.querySelectorAll('.tsubu[data-speaker]')].map((r) => r.dataset.speaker)")
        assert speakers == ["a", "b"]
        for theme in ("media", "dark", "light"):
            page.locator("#theme").select_option(theme)
            lines = page.evaluate(contrast)
            assert len(lines) == page.locator(".tsubu").count() and all(line.startswith("contrast ✓") for line in lines), lines
        # the unthemed defaults are not a preset, and the page says so
        page.locator("#theme").select_option("")
        assert page.evaluate("() => 'tsubuTheme' in document.getElementById('cards').dataset") is False
        assert all(line.startswith("contrast ✗") for line in page.evaluate(contrast))
        assert errors == []
    finally:
        page.close()
