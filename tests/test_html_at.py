"""htmlAt(t): the frame at t as HTML, without a page. It must be exactly what the fresh HTML becomes
after apply(root, t) in a browser, so a frame rendered on a server matches one drawn live."""

import json
import shutil
import subprocess

import pytest

from support import LONG, SCRIPT, TIMED, WHOLE

SAME = """([input, options, times]) => times.map((t) => {
  const s = Tsubu.sentence(input, options), holder = document.createElement("div");
  holder.innerHTML = s.html;
  document.body.append(holder);
  s.apply(holder.firstElementChild, t);
  const rendered = document.createElement("div");
  rendered.innerHTML = s.htmlAt(t);
  const result = [t, holder.firstElementChild.isEqualNode(rendered.firstElementChild), holder.innerHTML, rendered.innerHTML];
  holder.remove();
  return result;
})"""

TIMES = [-1, 0, 0.25, 0.5, 1.0, 1.45, 2.2, 3.0, 3.5, 4.0, 4.9, 5.0, 6.0, 9.0]


@pytest.mark.parametrize("options", [{}, {"ruby": False}, {"theme": "media", "speaker": "b", "announceRuby": False},
                                     {"writing": "vertical", "motion": "underline-draw mask"}],
                         ids=["plain", "ruby-off", "themed", "vertical-motion"])
@pytest.mark.parametrize("sentence", [TIMED, WHOLE, LONG], ids=["timed", "whole", "two-lines"])
def test_html_at_t_is_exactly_what_apply_makes_of_the_html(drawn, sentence, options):
    page = drawn(TIMED).page  # any page that has loaded the library
    for t, equal, live, rendered in page.evaluate(SAME, [sentence, options, TIMES]):
        # the same elements, text and attributes (isEqualNode ignores attribute order) ...
        assert equal, (t, live, rendered)
        # ... and in Chromium even the same string
        assert rendered == live, t


def test_html_at_is_a_pure_function_of_t_and_refuses_a_sentence_without_times():
    script = """const T = require(process.argv[1]);
      const s = T.sentence(JSON.parse(process.argv[2]));
      const a = s.htmlAt(1.2), b = (s.htmlAt(3.0), s.htmlAt(1.2));
      let refused = null;
      try { T.sentence({segments: [{parts: [{text: "x"}]}]}).htmlAt(0); } catch (e) { refused = e.message; }
      process.stdout.write(JSON.stringify({same: a === b, refused, fresh: s.html.includes("data-state")}));"""
    done = subprocess.run([shutil.which("node"), "-e", script, str(SCRIPT), json.dumps(TIMED)], capture_output=True,
                          text=True, encoding="utf-8", timeout=30, check=True)
    out = json.loads(done.stdout)
    assert out["same"] and not out["fresh"]
    assert out["refused"].startswith("tsubu: this sentence has no times")


def test_html_at_keeps_short_runs_upright_in_vertical_text(drawn):
    sentence = {"segments": [{"parts": [{"text": "10"}, {"text": "月", "ruby": "がつ"}], "start": 0, "end": 1},
                             {"parts": [{"text": "2025"}], "start": 1, "end": 2}]}
    page = drawn(TIMED).page
    for t, equal, live, rendered in page.evaluate(SAME, [sentence, {"writing": "vertical"}, [0.5, 1.5]]):
        assert equal, (t, live, rendered)
        assert '<span class="tsubu-upright">10</span>' in rendered and "2025</span>" in rendered and ">2025<" in rendered
