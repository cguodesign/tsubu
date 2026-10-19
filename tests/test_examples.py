"""The examples run, and show that a frame depends on t alone: frames rendered in reverse order are
the same, pixel for pixel, as frames rendered in order."""

import hashlib
import importlib.util
import json
import shutil
import subprocess

import pytest

from support import ROOT

EXAMPLES = ROOT / "examples"
SENTENCE = json.loads((EXAMPLES / "sentence.json").read_text(encoding="utf-8"))


def load_capture():
    spec = importlib.util.spec_from_file_location("capture_frames", EXAMPLES / "capture-frames.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_captured_frames_are_the_same_in_any_order(tmp_path):
    pytest.importorskip("playwright.sync_api", reason="the capture example needs Playwright")
    capture = load_capture()
    times = capture.frame_times(SENTENCE, 10, 0.2)
    assert len(times) == 31 and times[0] == pytest.approx(-0.2) and times[-1] == pytest.approx(2.8)
    forward = capture.render(SENTENCE, tmp_path / "forward", fps=10, width=640, height=360, pad=0.2, motion="underline-draw")
    backward = capture.render(SENTENCE, tmp_path / "backward", fps=10, width=640, height=360, pad=0.2, motion="underline-draw",
                              order=list(reversed(range(len(times)))))
    assert [digest(p) for p in forward] == [digest(p) for p in backward]
    assert not (tmp_path / "forward" / "page.html").exists()
    # and the highlight really moves: the frames are not all alike
    assert len({digest(p) for p in forward}) > 10


def test_html_frames_from_node_match_html_at(tmp_path):
    node = shutil.which("node")
    assert node
    done = subprocess.run([node, str(EXAMPLES / "frames-from-node.mjs"), str(EXAMPLES / "sentence.json"), str(tmp_path), "10"],
                          capture_output=True, text=True, encoding="utf-8", timeout=60, check=True)
    files = sorted(tmp_path.glob("frame_*.html"))
    assert len(files) == 27 and done.stdout.strip().startswith("27 frames")  # 0.0 to 2.6 s at 10 fps
    assert 'data-index="2" data-state="current"' in files[10].read_text(encoding="utf-8")  # t = 1.0: 家で
    assert "aria-current" not in files[-1].read_text(encoding="utf-8").split("<body>")[1]  # the end: nothing is current
