"""Browser fixtures for the layout and demo tests (Playwright, headless Chromium)."""

import pytest

from support import SCRIPT, STYLES

PAGE = """<!doctype html><html lang="ja"><head><meta charset="utf-8">
<link rel="stylesheet" href="{css}">
<style>body {{ margin: 0; font-family: "Hiragino Sans", "Noto Sans JP", "Noto Sans CJK JP", sans-serif; }}
.bubble {{ width: {width}px; margin: 40px; font-size: 40px; overflow: hidden; }}</style>
</head><body><div class="bubble" id="bubble"></div>
<script src="{js}"></script></body></html>"""

MEASURE = """() => {
  const root = document.querySelector(".tsubu");
  const box = (r) => ({left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height});
  const rubies = [...root.querySelectorAll("ruby")];
  const chars = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const inRt = !!node.parentElement.closest("rt");
    for (let i = 0; i < node.data.length; i++) {
      const range = document.createRange();
      range.setStart(node, i); range.setEnd(node, i + 1);
      chars.push({ch: node.data[i], rt: inRt, ruby: !inRt && !!node.parentElement.closest("ruby"),
                  rubyIndex: rubies.indexOf(node.parentElement.closest("ruby")),
                  box: box(range.getBoundingClientRect())});
    }
  }
  const segments = [...root.querySelectorAll(".tsubu-seg")].map((el) => {
    const r = el.getBoundingClientRect(), after = getComputedStyle(el, "::after");
    const left = r.left + parseFloat(after.left), width = parseFloat(after.width);
    return {punct: el.dataset.kind === "punct", box: box(r), state: el.dataset.state || null,
            current: el.getAttribute("aria-current"), decoration: getComputedStyle(el).textDecorationLine,
            progress: el.style.getPropertyValue("--tsubu-progress") || null,
            underline: {content: after.content, style: after.borderBottomStyle, width: parseFloat(after.borderBottomWidth),
                        left, right: left + width, bottom: r.bottom + parseFloat(after.bottom) * -1}};
  });
  const rts = [...root.querySelectorAll("rt")].map((rt) => ({box: box(rt.getBoundingClientRect()),
    visibility: getComputedStyle(rt).visibility, base: box(rt.parentElement.getBoundingClientRect())}));
  const motion = [root, ...root.querySelectorAll("*")].map((el) => {
    const s = getComputedStyle(el); return s.transitionDuration + " " + s.animationName; });
  return {root: box(root.getBoundingClientRect()), bubble: box(document.getElementById("bubble").getBoundingClientRect()),
          rootCurrent: root.getAttribute("aria-current"), rootState: root.dataset.state || null,
          rootProgress: root.style.getPropertyValue("--tsubu-progress") || null,
          rubyAlign: rubies.map((r) => getComputedStyle(r).rubyAlign),
          chars, segments, rts, motion, text: root.textContent, nodes: root.querySelectorAll("*").length};
}"""


@pytest.fixture(scope="session")
def browser():
    playwright_api = pytest.importorskip("playwright.sync_api", reason="the layout tests need Playwright")
    with playwright_api.sync_playwright() as playwright:
        launched = playwright.chromium.launch(headless=True)
        try:
            yield launched
        finally:
            launched.close()


@pytest.fixture
def drawn(browser, tmp_path):
    """Draws a sentence on a page that loads the library's own CSS and script, with any other
    options (theme, speaker) passed to Tsubu.sentence. Returns a function that applies t (and the
    furigana switch) and measures the page."""
    pages = []

    def draw(sentence, *, ruby=True, width=900, **options):
        page_file = tmp_path / f"page{len(pages)}.html"
        page_file.write_text(PAGE.format(css=STYLES.as_uri(), js=SCRIPT.as_uri(), width=width), encoding="utf-8")
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        pages.append(page)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(page_file.as_uri())
        page.evaluate("""([input, options]) => {
          window.S = Tsubu.sentence(input, options);
          document.getElementById("bubble").innerHTML = S.html;
          return document.fonts.ready.then(() => true);
        }""", [sentence, {"ruby": ruby, **options}])

        def at(t=None, ruby_on=None):
            page.evaluate("""([t, on]) => {
              const root = document.querySelector(".tsubu");
              if (on !== null) Tsubu.setRuby(root, on);
              if (t !== null) S.apply(root, t);
            }""", [t, ruby_on])
            assert errors == []
            return page.evaluate(MEASURE)

        at.page = page
        return at

    yield draw
    for page in pages:
        page.close()
