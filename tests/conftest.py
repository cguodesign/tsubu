"""Browser fixtures for the layout and demo tests (Playwright, headless). The engine is Chromium
unless `--engine firefox` or `--engine webkit` is given."""

import pytest

from support import SCRIPT, STYLES

PAGE = """<!doctype html><html lang="ja"><head><meta charset="utf-8">
<link rel="stylesheet" href="{css}">
<style>body {{ margin: 0; font-family: "Hiragino Sans", "Noto Sans JP", "Noto Sans CJK JP", sans-serif; }}
.bubble {{ width: {width}px; margin: 40px; font-size: 40px; overflow: hidden; }}
{extra}</style>
</head><body><div class="bubble{cls}" id="bubble" style="{style}"></div>
<script src="{js}"></script></body></html>"""

MEASURE = """() => {
  const root = document.querySelector(".tsubu");
  const box = (r) => ({left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height});
  const rubies = [...root.querySelectorAll("ruby")], segs = [...root.querySelectorAll(".tsubu-seg")];
  const chars = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (node.parentElement.closest("rp")) continue;  // not drawn: for what cannot draw ruby
    const inRt = !!node.parentElement.closest("rt");
    for (let i = 0; i < node.data.length; i++) {
      const range = document.createRange();
      range.setStart(node, i); range.setEnd(node, i + 1);
      chars.push({ch: node.data[i], rt: inRt, ruby: !inRt && !!node.parentElement.closest("ruby"),
                  hidden: !!node.parentElement.closest("[data-off-page]"), upright: !!node.parentElement.closest(".tsubu-upright"),
                  rubyIndex: rubies.indexOf(node.parentElement.closest("ruby")), seg: segs.indexOf(node.parentElement.closest(".tsubu-seg")),
                  box: box(range.getBoundingClientRect())});
    }
  }
  // The box of each segment's ::after, from a probe that takes the same geometry (see the
  // stylesheet): WebKit reports the computed insets of a box positioned inside an inline against
  // the block around it.
  const lineOf = (el) => {
    const probe = document.createElement("span");
    probe.className = "tsubu-line-probe";
    el.append(probe);
    const r = probe.getBoundingClientRect();
    probe.remove();
    return r;
  };
  const segments = [...root.querySelectorAll(".tsubu-seg")].map((el) => {
    const r = el.getBoundingClientRect(), after = getComputedStyle(el, "::after"), line = lineOf(el);
    return {punct: el.dataset.kind === "punct", box: box(r), state: el.dataset.state || null, offPage: el.hasAttribute("data-off-page"),
            current: el.getAttribute("aria-current"), decoration: getComputedStyle(el).textDecorationLine,
            progress: el.style.getPropertyValue("--tsubu-progress") || null,
            underline: {content: after.content, style: after.borderBottomStyle, width: parseFloat(after.borderBottomWidth),
                        left: line.left, right: line.right, bottom: line.bottom},
            // in vertical-rl text the underline is a side line: the left border of the ::after
            side: {style: after.borderLeftStyle, width: parseFloat(after.borderLeftWidth), color: after.borderLeftColor,
                   left: line.left, right: line.left + parseFloat(after.borderLeftWidth), top: line.top, bottom: line.bottom}};
  });
  const upright = [...root.querySelectorAll(".tsubu-upright")].map((el) => ({text: el.textContent, box: box(el.getBoundingClientRect()),
    combine: getComputedStyle(el).textCombineUpright}));
  // The base of a ruby: its box, but no further than its own text reaches. WebKit's ruby box takes
  // in a reading that overhangs the kana next to it; Chromium's range box of the text takes in the
  // space a wider reading gives it.
  const baseOf = (ruby) => {
    const r = ruby.getBoundingClientRect(), range = document.createRange();
    range.setStartBefore(ruby.firstChild);
    range.setEndBefore(ruby.querySelector("rt"));
    const t = range.getBoundingClientRect(), left = Math.max(r.left, t.left), top = Math.max(r.top, t.top);
    const right = Math.min(r.right, t.right), bottom = Math.min(r.bottom, t.bottom);
    return {left, right, top, bottom, width: right - left, height: bottom - top};
  };
  const rts = [...root.querySelectorAll("rt")].map((rt) => ({box: box(rt.getBoundingClientRect()), hidden: !!rt.closest("[data-off-page]"),
    visibility: getComputedStyle(rt).visibility, base: baseOf(rt.parentElement)}));
  const motion = [root, ...root.querySelectorAll("*")].map((el) => {
    const s = getComputedStyle(el); return s.transitionDuration + " " + s.animationName; });
  return {root: box(root.getBoundingClientRect()), bubble: box(document.getElementById("bubble").getBoundingClientRect()),
          rootCurrent: root.getAttribute("aria-current"), rootState: root.dataset.state || null,
          rootProgress: root.style.getPropertyValue("--tsubu-progress") || null,
          page: root.dataset.page ?? null, pages: root.dataset.pages ?? null,
          fontSize: parseFloat(getComputedStyle(root).fontSize), writing: getComputedStyle(root).writingMode, upright,
          rubyAlign: rubies.map((r) => getComputedStyle(r).rubyAlign),
          chars, segments, rts, motion, text: root.textContent, nodes: root.querySelectorAll("*").length};
}"""


ENGINES = ("chromium", "firefox", "webkit")


def pytest_addoption(parser):
    parser.addoption("--engine", choices=ENGINES, default="chromium",
                     help="the browser engine the layout tests run in (default: chromium)")
    parser.addoption("--engine-executable", default=None, metavar="PATH",
                     help="a build of that engine to launch instead of the one Playwright installed")


def pytest_configure(config):
    config.addinivalue_line("markers", "limitation(engine, reason): a limitation of that engine that tsubu cannot "
                                       "work around; the test is expected to fail there, and only there")


def pytest_collection_modifyitems(config, items):
    engine = config.getoption("engine")
    for item in items:
        for mark in item.iter_markers("limitation"):
            if mark.args[0] == engine:
                # strict: if the engine starts to pass, the limitation is gone and the mark must go too
                item.add_marker(pytest.mark.xfail(reason=f"{engine}: {mark.kwargs['reason']}", strict=True))


def pytest_report_header(config):
    executable = config.getoption("engine_executable")
    return f"browser engine: {config.getoption('engine')}" + (" (a build given by --engine-executable)" if executable else "")


@pytest.fixture(scope="session")
def engine(request):
    """The name of the engine the browser tests run in: chromium, firefox or webkit."""
    return request.config.getoption("engine")


@pytest.fixture(scope="session")
def browser(engine, request):
    playwright_api = pytest.importorskip("playwright.sync_api", reason="the layout tests need Playwright")
    with playwright_api.sync_playwright() as playwright:
        launched = getattr(playwright, engine).launch(headless=True,
                                                      executable_path=request.config.getoption("engine_executable"))
        try:
            yield launched
        finally:
            launched.close()


@pytest.fixture(scope="session")
def engine_version(browser):
    """The major version of the browser the tests run in, such as 153."""
    return int(browser.version.split(".")[0])


@pytest.fixture
def drawn(browser, engine, tmp_path):
    """Draws a sentence on a page that loads the library's own CSS and script, in a bubble of the
    given width (a fluid container if asked, with extra inline style, and with extra CSS such as a
    font face), with any other options (theme, speaker) passed to Tsubu.sentence. Returns a
    function that applies t (and the furigana switch) and measures the page."""
    pages = []

    def draw(sentence, *, ruby=True, width=900, fluid=False, style="", css="", **options):
        page_file = tmp_path / f"page{len(pages)}.html"
        page_file.write_text(PAGE.format(css=STYLES.as_uri(), js=SCRIPT.as_uri(), width=width,
                                         cls=" tsubu-fluid" if fluid else "", style=style, extra=css), encoding="utf-8")
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
            return {**page.evaluate(MEASURE), "engine": engine}

        at.page = page
        return at

    yield draw
    for page in pages:
        page.close()
