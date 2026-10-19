"""The guide for agents (docs/agents/segmenting.md), its worked example and its validator.

The validator is run in Node on the hand-made example, which it must accept, and on broken copies
of it, which it must refuse. The guide itself is checked against the library and the example, so
that the three cannot drift apart.
"""

import copy
import json
import re
import shutil
import subprocess

import pytest

from support import ROOT, SCRIPT

AGENTS = ROOT / "docs" / "agents"
GUIDE = AGENTS / "segmenting.md"
VALIDATOR = AGENTS / "validate.mjs"
EXAMPLE = AGENTS / "example" / "hand-made-input.json"
SENTENCE = AGENTS / "example" / "sentence.txt"


def node():
    found = shutil.which("node")
    assert found, "the guide's tests need Node on PATH"
    return found


def validate(input_path, text_path=SENTENCE, *flags):
    done = subprocess.run([node(), str(VALIDATOR), str(input_path), "--text", str(text_path), *flags],
                          capture_output=True, text=True, encoding="utf-8", timeout=30)
    report = json.loads(done.stdout)
    assert done.returncode == (0 if report["ok"] else 1)
    return report


@pytest.fixture
def example():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def write(tmp_path, sentence):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(sentence, ensure_ascii=False), encoding="utf-8")
    return path


def test_the_example_passes():
    report = validate(EXAMPLE)
    assert report == {"ok": True, "timing": "segments", "errors": [], "warnings": []}


def test_the_example_fits_its_own_duration():
    assert validate(EXAMPLE, SENTENCE, "--duration", "3.05")["ok"]
    report = validate(EXAMPLE, SENTENCE, "--duration", "3.0")
    assert not report["ok"] and "after the audio" in report["errors"][0]


def broken(sentence, how):
    s = copy.deepcopy(sentence)
    segs = s["segments"]
    if how == "text changed":
        segs[4]["parts"][0] = {"text": "手帳", "ruby": "てちょう"}
    elif how == "a part dropped":
        del segs[3]["parts"][1]
    elif how == "a reading missing a kanji":
        del segs[5]["parts"][2]["ruby"]
    elif how == "partly timed":
        del segs[3]["start"], segs[3]["end"]
    elif how == "okurigana inside a reading":
        segs[5]["parts"][:2] = [{"text": "受け", "ruby": "うけ"}]
    elif how == "a katakana reading":
        segs[2]["parts"][0]["ruby"] = "キョウト"
    elif how == "punctuation not marked":
        del segs[1]["kind"]
    elif how == "a word marked as punctuation":
        segs[4] = {"parts": segs[4]["parts"], "kind": "punct"}
    elif how == "punctuation with a time":
        segs[6].update(start=3.05, end=3.2)
    elif how == "overlapping times":
        segs[3]["start"] = 1.0
    return s


@pytest.mark.parametrize("how, message", [
    ("text changed", "does not join back into the sentence"),
    ("a part dropped", "does not join back into the sentence"),
    ("a reading missing a kanji", "contains a kanji but has no reading"),
    ("partly timed", "only 4 of 5 spoken segments have times"),
    ("okurigana inside a reading", "holds kanji only"),
    ("a katakana reading", "not all hiragana"),
    ("punctuation not marked", 'give it kind "punct"'),
    ("a word marked as punctuation", "holds more than punctuation"),
    ("punctuation with a time", "punctuation carries no time"),
    ("overlapping times", "overlap or are out of order"),
])
def test_a_broken_example_is_refused(tmp_path, example, how, message):
    report = validate(write(tmp_path, broken(example, how)))
    assert not report["ok"]
    assert any(message in e for e in report["errors"]), report["errors"]


def test_the_changed_text_is_located(tmp_path, example):
    report = validate(write(tmp_path, broken(example, "text changed")))
    assert "from character 11 on" in report["errors"][0]


def test_tsubu_itself_refuses_a_partly_timed_sentence(tmp_path, example):
    report = validate(write(tmp_path, broken(example, "partly timed")))
    assert any(e.startswith("Tsubu.sentence() refuses it: tsubu: only 4 of 5 segments") for e in report["errors"])


def test_a_missing_reading_can_be_allowed_on_purpose(tmp_path, example):
    report = validate(write(tmp_path, broken(example, "a reading missing a kanji")), SENTENCE, "--allow-missing-ruby")
    assert report["ok"] and "contains a kanji but has no reading" in report["warnings"][0]


def test_a_sentence_without_readings_or_times_passes_with_warnings(tmp_path, example):
    bare = {"segments": [{k: v for k, v in seg.items() if k not in ("start", "end")} for seg in example["segments"]]}
    for seg in bare["segments"]:
        seg["parts"] = [{"text": "".join(p["text"] for p in seg["parts"])}]
    report = validate(write(tmp_path, bare))
    assert report["ok"] and report["timing"] == "none"
    assert len(report["warnings"]) == 2


def test_the_sentence_file_must_match_exactly(tmp_path):
    other = tmp_path / "sentence.txt"
    other.write_text("昨日、京都の友達から手紙を受け取りました\n", encoding="utf-8")  # no 。
    assert not validate(EXAMPLE, other)["ok"]


SPLIT_RUNNER = r"""
const { splitReading } = await import(process.argv[1]);
const cases = JSON.parse(require("fs").readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(cases.map(([surface, reading]) => splitReading(surface, reading))));
"""


def test_split_reading_puts_the_reading_on_the_kanji_and_leaves_okurigana_plain():
    cases = [
        ("受け取りました", "ウケトリマシタ"),  # two runs of kanji, kana between and after
        ("友達", "トモダチ"),                  # one run: the reading stays whole
        ("昨日", "キノウ"),                    # a reading of the whole word (jukujikun) cannot be split per kanji
        ("お茶", "オチャ"),
        ("パン屋", "パンヤ"),                  # katakana in the surface is matched in hiragana
        ("ラーメン", "ラーメン"),              # no kanji, no reading
        ("受け取り", "ウケトル"),              # the reading does not fit the surface
    ]
    done = subprocess.run([node(), "--input-type=commonjs", "-e", f"(async () => {{ {SPLIT_RUNNER} }})()",
                           VALIDATOR.as_uri()], input=json.dumps(cases), capture_output=True, text=True,
                          encoding="utf-8", timeout=30, check=True)
    assert json.loads(done.stdout) == [
        [{"text": "受", "ruby": "う"}, {"text": "け"}, {"text": "取", "ruby": "と"}, {"text": "りました"}],
        [{"text": "友達", "ruby": "ともだち"}],
        [{"text": "昨日", "ruby": "きのう"}],
        [{"text": "お"}, {"text": "茶", "ruby": "ちゃ"}],
        [{"text": "パン"}, {"text": "屋", "ruby": "や"}],
        [{"text": "ラーメン"}],
        None,
    ]


@pytest.fixture(scope="module")
def guide():
    return GUIDE.read_text(encoding="utf-8")


def test_the_guide_states_its_version_its_date_and_the_tsubu_version_it_targets(guide):
    head = guide[:1500]
    assert re.search(r"\*\*Guide version:\*\* \d+\.\d+\.\d+\b", head)
    assert re.search(r"\*\*Verified on:\*\* \d{4}-\d{2}-\d{2}\b", head)
    library = re.search(r'const VERSION = "([^"]+)"', SCRIPT.read_text(encoding="utf-8")).group(1)
    assert re.search(r"\*\*Targets tsubu:\*\* " + re.escape(library) + r"\b", head)


def test_the_guide_has_a_changelog_entry_for_its_version(guide):
    version = re.search(r"\*\*Guide version:\*\* (\d+\.\d+\.\d+)", guide).group(1)
    changelog = guide[guide.index("## Changelog"):]
    assert f"### {version} " in changelog


def test_the_guides_worked_example_is_the_example_file(guide, example):
    blocks = re.findall(r"```json\n(.*?)```", guide, re.S)
    assert example in [json.loads(b) for b in blocks]
    assert SENTENCE.read_text(encoding="utf-8").strip() in guide


def test_the_guides_local_links_exist(guide):
    for target in re.findall(r"\]\((?!https?://|#)([^)#\s]+)", guide):
        assert (GUIDE.parent / target).exists(), target


def test_every_tool_claim_cites_a_source(guide):
    sources = guide[guide.index("## Sources"):guide.index("## Changelog")]
    assert len(re.findall(r"https://", sources)) >= 10


TIMES_RUNNER = r"""
const { timesFromCharacters } = await import(process.argv[1]);
const [segments, chars] = JSON.parse(require("fs").readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(timesFromCharacters(segments, chars)));
"""


def times_from_characters(segments, chars):
    done = subprocess.run([node(), "--input-type=commonjs", "-e", f"(async () => {{ {TIMES_RUNNER} }})()",
                           VALIDATOR.as_uri()], input=json.dumps([segments, chars]), capture_output=True,
                          text=True, encoding="utf-8", timeout=30, check=True)
    return json.loads(done.stdout)


@pytest.fixture
def untimed(example):
    return [{k: v for k, v in seg.items() if k not in ("start", "end")} for seg in example["segments"]]


def character_times():
    """One made-up time per character of the example sentence: 0.1 s each, a pause after 、."""
    times, t = [], 0.0
    for ch in SENTENCE.read_text(encoding="utf-8").strip():
        times.append({"start": round(t, 3), "end": round(t + 0.1, 3)})
        t += 0.3 if ch == "、" else 0.1
    return times


def test_character_times_become_segment_times(tmp_path, untimed):
    result = times_from_characters(untimed, character_times())
    assert result["problems"] == []
    spans = [(s.get("start"), s.get("end")) for s in result["segments"]]
    # 昨日 0-0.2; 、 untimed although the aligner timed it; 京都の starts after the pause
    assert spans == [(0.0, 0.2), (None, None), (0.5, 0.8), (0.8, 1.2), (1.2, 1.5), (1.5, 2.2), (None, None)]
    assert validate(write(tmp_path, {"segments": result["segments"]}))["ok"]


def test_an_unmeasured_edge_drops_every_segment_time(untimed):
    chars = character_times()
    chars[3] = None  # 京, the first character of 京都の
    result = times_from_characters(untimed, chars)
    assert result["problems"] == ['segment 2: the aligner gave "京" no time, so the segment\'s start is not measured']
    assert all("start" not in s for s in result["segments"])


def test_a_missing_time_inside_a_segment_is_not_a_problem(untimed):
    chars = character_times()
    chars[4] = None  # 都, inside 京都の
    assert times_from_characters(untimed, chars)["problems"] == []


def test_a_word_across_two_segments_shows_as_an_overlap(untimed):
    chars = character_times()
    chars[5] = chars[6] = {"start": 0.7, "end": 0.9}  # の and 友 given one word's time
    result = times_from_characters(untimed, chars)
    assert result["problems"] == ["segments 2 and 3 overlap (0.9 > 0.7)"]


def test_character_times_must_cover_the_sentence(untimed):
    result = times_from_characters(untimed, character_times()[:-1])
    assert "the sentence has 21 characters but 20 character times were given" in result["problems"]
