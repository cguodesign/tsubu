"""What is published names nothing outside the project: no local paths, no private terms.

Every tracked file and every commit message is checked. The general rules live here; terms that
are private to a machine go in an optional, untracked `.leakcheck.local` at the repository root,
one per line (lines starting with # are comments), and are matched case-insensitively.
"""

import re
import shutil
import subprocess

import pytest

from support import ROOT

# Written so that this file does not match itself.
LOCAL_PATHS = [
    re.compile(rb"/(?:Users|home)/[A-Za-z0-9._-]+"),
    re.compile(rb"[A-Za-z]:\\(?:Users|Documents and Settings)\\", re.IGNORECASE),
    re.compile(rb"file://(?:localhost)?/(?!/)"),
]


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True, timeout=30).stdout


@pytest.fixture(scope="module")
def tracked():
    if not shutil.which("git") or not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    return {name: (ROOT / name).read_bytes()
            for name in git("ls-files", "-z").decode("utf-8").split("\0") if name and (ROOT / name).is_file()}


@pytest.fixture(scope="module")
def messages():
    if not shutil.which("git") or not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    return git("log", "--all", "--format=%H%n%B%x00").split(b"\0")


@pytest.fixture(scope="module")
def private_terms():
    path = ROOT / ".leakcheck.local"
    if not path.exists():
        return []
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line.lower().encode("utf-8") for line in lines if line and not line.startswith("#")]


def found_in(blob, private_terms):
    hits = [m.group(0).decode("utf-8", "replace") for p in LOCAL_PATHS for m in p.finditer(blob)]
    lowered = blob.lower()
    return hits + [t.decode("utf-8") for t in private_terms if t in lowered]


def test_the_private_term_list_is_never_tracked(tracked):
    assert ".leakcheck.local" not in tracked


def test_no_tracked_file_names_a_local_path_or_a_private_term(tracked, private_terms):
    leaks = {name: hits for name, blob in tracked.items() if (hits := found_in(blob, private_terms))}
    assert not leaks, leaks


def test_no_commit_message_names_a_local_path_or_a_private_term(messages, private_terms):
    leaks = [hits for message in messages if (hits := found_in(message, private_terms))]
    assert not leaks, leaks
