# Preparing a Japanese sentence for tsubu: a guide for agents

**Guide version:** 1.0.0
**Verified on:** 2026-10-19
**Targets tsubu:** 0.1.0

tsubu draws one sentence for read-along use, but it never segments text, guesses a reading or
estimates a time. It takes a sentence that is already cut into segments, with readings and times
where there are any, and refuses anything it would have to complete by guessing. This guide is
the step before tsubu: how an agent turns raw Japanese text (one sentence, perhaps with its audio)
into the input that `Tsubu.sentence()` takes, using tools that do the analysis, and how it checks
the result before anything is drawn.

The steps, in order:

1. [Segment into bunsetsu](#step-1-segment-into-bunsetsu-文節), and mark punctuation.
2. [Add readings](#step-2-readings-furigana) from the analyser, on the kanji only.
3. [Add times](#step-3-times) from forced alignment or from the speech synthesiser, or none.
4. [Validate](#step-4-validate-before-use) with [`validate.mjs`](validate.mjs), then on the page.

## Why this guide is versioned

The tools and models an agent uses change: packages are renamed, APIs move, models are replaced
and retired. Every tool claim below was checked against the tool's own documentation or
repository on the date at the top, at the version named next to it, and the pages are listed
under [Sources](#sources). Before you rely on a claim:

- compare the version you have with the version named here; if they differ, re-read the tool's
  own page;
- read the [Changelog](#changelog) at the end, which says what changed between versions of this
  guide;
- treat anything marked **unverified** as a lead, not a fact.

The guide's version follows semantic versioning: a major version when the target format or a
required step changes, a minor version when tools or advice are added, a patch for corrections.

## The target format

What `Tsubu.sentence(input)` takes (the full contract is in the
[README's Input section](../../README.md#input)):

- `segments`, in reading order. Each segment is one unit of reading, here one bunsetsu.
- Each segment has `parts`: pieces of text. A part with `ruby` carries a reading and is drawn as
  `<ruby>`; a part without one is plain text. Joined, the parts of all segments are the sentence.
- `kind: "punct"` marks a punctuation segment: no underline, never spoken, never timed.
- `start` and `end`, in seconds on the audio's clock, on **every** spoken segment or on **none**.
  A span is half-open, `[start, end)`. Without segment times, the sentence as a whole may have
  `start` and `end`; with no times at all it can be drawn but not played.

The worked example, for 昨日、京都の友達から手紙を受け取りました。 ("Yesterday I received a letter
from a friend in Kyoto."). **It was made by hand, and its times are invented** (there is no
recording); see [`example/`](example/README.md):

```json
{
  "segments": [
    { "parts": [{ "text": "昨日", "ruby": "きのう" }], "start": 0.0, "end": 0.42 },
    { "parts": [{ "text": "、" }], "kind": "punct" },
    { "parts": [{ "text": "京都", "ruby": "きょうと" }, { "text": "の" }], "start": 0.62, "end": 1.1 },
    { "parts": [{ "text": "友達", "ruby": "ともだち" }, { "text": "から" }], "start": 1.1, "end": 1.68 },
    { "parts": [{ "text": "手紙", "ruby": "てがみ" }, { "text": "を" }], "start": 1.68, "end": 2.12 },
    { "parts": [{ "text": "受", "ruby": "う" }, { "text": "け" }, { "text": "取", "ruby": "と" }, { "text": "りました" }], "start": 2.12, "end": 3.05 },
    { "parts": [{ "text": "。" }], "kind": "punct" }
  ]
}
```

Things to notice: the punctuation is its own segment; 受け取りました has two runs of kanji, each
with its own reading, and the kana between and after them are plain parts; 昨日 has a reading of
the whole word (きのう), which cannot be split per character; there is a pause after 、 (0.42 to
0.62), where nothing is highlighted.

## Step 1: segment into bunsetsu (文節)

A bunsetsu is one content word with the function words that follow it (京都の, 友達から,
受け取りました). It is the unit a reader takes in at once and the unit tsubu highlights. Use a
tool that produces bunsetsu if you can; otherwise merge a morphological analyser's words with
the rule below.

Whatever the tool, keep the **surface** text of every token (what is written in the sentence),
never a normalised or dictionary form, so that the segments join back into the sentence exactly.

### Recommended: GiNZA (spaCy), with its bunsetu API

[GiNZA](https://github.com/megagonlabs/ginza) is a spaCy pipeline for Japanese built on
Sudachi. Verified at **ginza 5.3.0** (released 2026-09-30, MIT, Python 3.10 or later; its
changelog asks for spaCy 3.8.16 or later). Models: `ja_ginza` (standard), `ja_ginza_electra`
(transformer), `ja_ginza_bert_large` (transformer; its README asks for at least 16 GB of memory).
The bunsetu (GiNZA's spelling) functions are imported from `ginza`; `bunsetu_spans(span)` takes
a spaCy `Span` and yields one `Span` per bunsetsu.

```sh
pip install -U ja_ginza
```

```python
import spacy
from ginza import bunsetu_spans

nlp = spacy.load("ja_ginza")
doc = nlp("昨日、京都の友達から手紙を受け取りました。")
for sent in doc.sents:
    for bunsetsu in bunsetu_spans(sent):
        for token in bunsetsu:
            # surface, reading (katakana), offset of the token in the text
            print(token.orth_, token.morph.get("Reading"), token.idx)
        print("--")
```

`token.morph.get("Reading")` is a list holding the reading in katakana (GiNZA 5.1 moved it there
from `doc.user_data`). A bunsetsu span may begin or end with punctuation tokens; split those off
into their own punctuation segments (see [Punctuation](#which-tokens-are-kind-punct)). The text
between two spans (spaces, for instance) belongs to the sentence too: take each segment's text
from the sentence by offsets ([`span.start_char`, `span.end_char`](https://spacy.io/api/span)),
not by joining tokens with a separator.

### Also recommended: KNP or KWJA, through rhoknp

[KNP](https://github.com/ku-nlp/knp) (Kyoto University) parses the output of the morphological
analysers JUMAN or Juman++ into bunsetsu and base phrases. Verified: its
[home page](https://nlp.ist.i.kyoto-u.ac.jp/?KNP) lists **KNP 4.20** (2020-04-19) as the latest
release, which accepts Juman++ 2.0.0-rc3 output; the repository's `COPYING` is a three-clause
BSD-style licence. The same group's [KWJA](https://github.com/ku-nlp/kwja) (**kwja 2.5.1** on
PyPI, MIT, Python 3.10 or later) is a newer analyser built on neural language models that writes
the same KNP format. Read either output with
[rhoknp](https://github.com/ku-nlp/rhoknp) (**rhoknp 1.8.2**, MIT), whose `sentence.phrases` are
the bunsetsu:

```python
from rhoknp import KWJA

document = KWJA().apply("昨日、京都の友達から手紙を受け取りました。")
for phrase in document.phrases:   # a.k.a. bunsetsu
    print(phrase.text)            # its surface text
```

(`KWJA` needs the `kwja` command on the path; `apply` returns a `Document`, whose `phrases` and
units' `text` are defined in rhoknp's `units/document.py` and `units/unit.py`.)

KWJA can **correct typos** (its `typo` task), which changes the text: choose its tasks with
`--tasks` so that it does not, and rely on step 4's text check to catch any change. The readings
in KNP-format output were not checked for this guide (**unverified**); take readings from one of
the analysers in step 2 instead.

### Fallbacks: a morphological analyser, then merge

These give words (morphemes), not bunsetsu, plus a part of speech and a reading for each.

- **[SudachiPy](https://github.com/WorksApplications/sudachi.rs)** (Python bindings of
  sudachi.rs). Verified at **SudachiPy 0.7.0** (2026-09-24, Apache-2.0, Python 3.10 or later)
  with **SudachiDict-core 20261015** (Apache-2.0). The sudachi.rs README warns that 0.7.x
  releases may break between patch versions and asks you to pin the exact version; 0.7 also
  introduced a new dictionary format. Split mode `C` (the default) keeps named entities whole;
  `A` gives the shortest units.

  ```python
  from sudachipy import Dictionary, SplitMode

  tokenizer = Dictionary().tokenizer()
  for m in tokenizer.tokenize("昨日、京都の友達から手紙を受け取りました。", SplitMode.C):
      print(m.surface(), m.reading_form(), m.part_of_speech(), m.begin(), m.end())
  ```

  `reading_form()` is katakana, and `part_of_speech()` a list whose first item is the main part
  of speech (`['名詞', '固有名詞', ...]`). `begin()` and `end()` are documented as the morpheme's
  begin and end index in the input text.
- **MeCab with UniDic, through [fugashi](https://github.com/polm/fugashi)**. Verified at
  **fugashi 1.5.2** (MIT; it bundles MeCab, BSD-3-Clause) with
  **[unidic](https://github.com/polm/unidic-py) 1.1.0** (UniDic 3.1.0, BSD; about 770 MB once
  downloaded) or **unidic-lite 1.0.8** (UniDic 2.1.2, small).

  ```sh
  pip install 'fugashi[unidic]'
  python -m unidic download
  ```

  ```python
  from fugashi import Tagger

  tagger = Tagger()
  for word in tagger("昨日、京都の友達から手紙を受け取りました。"):
      print(word.surface, word.feature.kana, word.feature.pos1)
  ```

  Use the `kana` field for readings: per the unidic-py documentation it is the surface's reading
  in katakana, while `pron` is the pronunciation and writes long vowels as ー (講師 is コウシ in
  `kana` and コーシ in `pron`). fugashi's oldest UniDic schema (2.1.2 source) has no `kana`
  field, only `pron`; do not use `pron` for furigana.
- **[kuromoji.js](https://github.com/takuyaa/kuromoji.js)**, for JavaScript. Verified at
  **kuromoji 0.1.2** on npm (Apache-2.0; published 2018-03-19, so not recently released; the
  package ships its dictionary in `dict/`). Tokens have `surface_form`, `reading` (katakana),
  `pronunciation` and `pos`; the tag set appears to be IPADIC's (**unverified**: the README does
  not name the dictionary).

  ```js
  const kuromoji = require("kuromoji");
  kuromoji.builder({ dicPath: "node_modules/kuromoji/dict/" }).build((err, tokenizer) => {
    if (err) throw err;
    for (const t of tokenizer.tokenize("昨日、京都の友達から手紙を受け取りました。"))
      console.log(t.surface_form, t.reading, t.pos);
  });
  ```

### Merging morphemes into bunsetsu

When only words are available, build bunsetsu with this rule. It is this guide's heuristic, not
a tool's output. The part-of-speech names are UniDic's short-unit tags, as listed in the
[Universal Dependencies mapping for Japanese](https://universaldependencies.org/docsv1/ja/overview/morphology.html);
Sudachi's README example shows the same top-level names (名詞, 固有名詞). IPADIC's tags, which
kuromoji.js appears to use, are a different set (for example 接頭詞 rather than 接頭辞; not
checked against IPADIC's documentation for this guide, **unverified**). Check the names against
your analyser's actual output before relying on them.

1. Punctuation words (see the next section) become their own segments.
2. A **content word** starts a new bunsetsu: 名詞, 代名詞, 形状詞, 連体詞, 副詞, 接続詞, 感動詞,
   動詞, 形容詞.
3. A **function word** joins the bunsetsu before it: 助詞, 助動詞, 接尾辞.
4. A **prefix** (接頭辞) joins the bunsetsu after it; a bunsetsu that has begun with a prefix
   does not start again at the content word that follows.
5. Consecutive nouns (a compound such as 国会議事堂前駅, or a number and its counter) stay in one
   bunsetsu.
6. A verb or adjective tagged 非自立可能 (can be functional) right after て or で (食べて / いる,
   読んで / みる) may be joined to the bunsetsu before it or start its own: both read naturally.
   Choose one and keep to it.

Then check that each bunsetsu joins back into its stretch of the sentence (step 4 does this for
the whole sentence).

### Which tokens are `kind: "punct"`

A segment is punctuation when every character in it is punctuation, a symbol or a space: in
Unicode terms, general categories `P*`, `S*` or white space, which covers 、 。 「 」 『 』 （ ）
・ … ！ ？ and full-width spaces. The validator uses exactly this test
(`/^[\p{P}\p{S}\s]+$/u`). Such a segment has `kind: "punct"` and no times; a segment with any
other character is spoken. Keep brackets and quotation marks as their own punctuation segments:
tsubu keeps an opening bracket on the same line as what follows it and a closing one with what
precedes it. Long-vowel marks (ー) and small kana are letters, not punctuation; they stay inside
their word.

## Step 2: readings (furigana)

Take readings from the analyser, never from memory:

| Tool | Field | Script |
|---|---|---|
| GiNZA | `token.morph.get("Reading")[0]` | katakana |
| SudachiPy | `m.reading_form()` | katakana |
| fugashi + UniDic | `word.feature.kana` (not `pron`) | katakana |
| kuromoji.js | `token.reading` | katakana |

Then, for each word:

1. **Convert katakana to hiragana** (subtract 0x60 from U+30A1 to U+30F6; keep ー).
2. **Put the reading on the kanji only.** Split the word into runs of kanji and runs of kana;
   the kana in the surface must appear literally in the reading, and they fix where each kanji
   run's reading begins and ends. Each kanji run becomes a part with `ruby`; the kana
   (okurigana, particles, katakana) become plain parts. 受け取りました with うけとりました gives
   受/う, け, 取/と, りました.
3. **Do not split a run of kanji further** unless a tool gives you the reading of each
   character. 友達/ともだち stays one part. Readings of a whole word (jukujikun such as 昨日/きのう
   or 今日/きょう) cannot be split per character at all.
4. If the reading does not fit the surface, or fits it in more than one way, **do not choose**:
   leave the word without a reading and flag it for a human.

[`validate.mjs`](validate.mjs) exports `splitReading(surface, reading)`, which does steps 1 and
2 and returns `null` in the case of step 4:

```js
import { splitReading } from "./validate.mjs";
splitReading("受け取りました", "ウケトリマシタ");
// [{ text: "受", ruby: "う" }, { text: "け" }, { text: "取", ruby: "と" }, { text: "りました" }]
```

It cannot tell whether a reading is right, only whether it fits; the reading must come from the
analyser (or a human).

**Words that need care:**

- **Characters with several readings.** 昨日 is きのう in speech and さくじつ in formal speech;
  今日 is きょう or こんにち; 生 has dozens of readings. The analyser picks one from context, and
  may pick wrong. When there is audio, the reading must be what the speaker said: if you cannot
  confirm it, flag the sentence.
- **Proper nouns.** Names of people and places often have readings no dictionary knows, or
  several. Take the reading from the source (the speaker, a reading the caller gave, the audio);
  otherwise flag it.
- **Numbers.** Digits (１泊, 3人) have no kanji to carry a reading. Leave them plain, or write the
  sentence as the caller wants it; never change the text to make it easier to read.

**An LLM must not invent readings.** If no tool gives a reading you can trust, either leave
readings out for the whole sentence (it is then drawn without furigana) or keep the reading out
of that one word and flag the sentence for a human. The validator refuses a kanji without a
reading in a sentence that has other readings, because a learner would see a gap; pass
`--allow-missing-ruby` only when the product accepts that gap on purpose.

## Step 3: times

There are three honest outcomes: every spoken segment has its own measured time; only the whole
sentence has a start and end; or there are no times. **A partly timed sentence is refused** by
tsubu, so if some segments cannot be timed, drop the segment times and give the sentence its
span, or no times at all. Never fill a gap by dividing time by length or by mora: that is an
estimate, which is what tsubu exists to avoid.

### Recorded speech: forced alignment

Forced alignment matches a known text to its recording. Align the sentence exactly as it will be
shown (the text of your segments), not a fresh transcript.

- **[WhisperX](https://github.com/m-bain/whisperX)**. Verified at **whisperx 3.8.6**
  (BSD-2-Clause, Python 3.10 to 3.13). In its `alignment.py`, Japanese (`"ja"`) has a default
  alignment model, `jonatasgrosman/wav2vec2-large-xlsr-53-japanese`
  ([model card](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-japanese):
  Apache-2.0, fine-tuned on Common Voice 6.1, CSS10 and JSUT; it reports a character error rate of
  about 20% on Common Voice when used for recognition). Japanese is in
  `LANGUAGES_WITHOUT_SPACES`, so each character is aligned as its own "word". What this means
  for you:
  - Pass your sentence as the transcript, one segment with its rough `start` and `end`, and ask
    for characters with `return_char_alignments=True`. Each character entry has `char`, `start`,
    `end` and `score`, and `start`/`end` are **left out** when the character got no time.
  - **Use the character times, not the word times.** WhisperX fills in missing word times by
    interpolation (`interpolate_method`, default `"nearest"`): those are estimates. Character
    times are not interpolated.
  - Characters missing from the model's vocabulary (digits, symbols, other scripts) are aligned
    against a wildcard token, so they still get a time without being matched to a particular
    sound; look at their `score` before trusting it.

  ```python
  import whisperx

  device = "cpu"
  audio = whisperx.load_audio("sentence.wav")
  model_a, metadata = whisperx.load_align_model(language_code="ja", device=device)
  transcript = [{"text": "昨日、京都の友達から手紙を受け取りました。", "start": 0.0, "end": len(audio) / 16000}]
  result = whisperx.align(transcript, model_a, metadata, audio, device, return_char_alignments=True)
  chars = result["segments"][0]["chars"]   # [{"char", "start", "end", "score"}, ...]
  ```

  (`load_audio` returns 16 kHz audio, `SAMPLE_RATE` in WhisperX's `audio.py`, hence the
  duration. The `align` signature and the `chars` keys were read in the source.)
- **[Montreal Forced Aligner](https://montreal-forced-aligner.readthedocs.io/)** (MFA). Verified
  at **montreal-forced-aligner 3.4.3** (MIT). It has a pretrained Japanese acoustic model and
  dictionary, `japanese_mfa` (v3.0.0, CC BY 4.0; the acoustic model was trained on about 154
  hours from five corpora, among them Common Voice, GlobalPhone, JVS and TEDxJP-10K), and a Japanese G2P model. Its
  [alignment tutorial](https://montreal-forced-aligner.readthedocs.io/en/latest/first_steps/alignment_example.html)
  shows the Japanese setup: `mfa model download acoustic japanese_mfa`,
  `mfa model download dictionary japanese_mfa`, the dependencies `spacy sudachipy
  sudachidict-core` (MFA tokenises Japanese with SudachiPy), and
  `mfa align <corpus> japanese_mfa japanese_mfa <output>`. It gives **word** intervals for the
  SudachiPy words, not characters. A word missing from the dictionary is aligned as `spn` and can
  pull its neighbours' times off (the tutorial's own example is １泊); fix it with a dictionary
  entry or the G2P model (`--g2p_model_path`), not by editing the text shown to the reader.

### Synthesised speech: timestamps from the engine

When the audio is synthesised, ask the engine for timing instead of aligning afterwards. These
engines' documentation confirms word or character timing; none of them states how it behaves for
Japanese specifically, so check the first sentences by ear.

| Engine | What its docs confirm | Notes |
|---|---|---|
| [ElevenLabs](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps) | `POST /v1/text-to-speech/{voice_id}/with-timestamps` returns `alignment` with `characters`, `character_start_times_seconds` and `character_end_times_seconds` | use `alignment` (the text you sent), not `normalized_alignment` (after numbers are spelled out); it has a Japanese-only text normalisation option |
| [Amazon Polly](https://docs.aws.amazon.com/polly/latest/dg/speechmarks.html) | `word` speech marks: `time` in milliseconds, `start` and `end` as **byte** offsets into the input | convert byte offsets to characters (UTF-8 is **unverified**; a Japanese character is three bytes in UTF-8); speech marks are returned instead of audio, so make a second request for the audio |
| [Azure AI Speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis) | the `WordBoundary` event, raised for each word, punctuation and sentence, with an audio offset and duration and a text offset and length | the units of the text offset are **unverified**; check them against your text |
| [Google Cloud Text-to-Speech](https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1beta1/text/synthesize) | only SSML `<mark>` timepoints (`enableTimePointing: ["SSML_MARK"]`, v1beta1), each `markName` with `timeSeconds` | no word timing: put a mark before and after each spoken segment and read their times |

### From character or word times to segment times

With one time per character (WhisperX `chars`, ElevenLabs `alignment`):

- A spoken segment starts at its first character's `start` and ends at its last character's
  `end`. Skip punctuation characters, inside a segment or as their own segment: punctuation
  carries no time in tsubu, even if the aligner gave it one.
- If the first or last spoken character of a segment has no time, that edge is not measured.
  Do not borrow a neighbour's time: re-align, or drop the segment times (see above).
- Gaps are fine and real: between 、 and the next word the speaker pauses, and in a gap nothing is
  current. Spans are half-open, `[start, end)`, so one segment may end exactly where the next
  starts.
- Times may not overlap or go backwards. A clear overlap means the alignment is wrong. A tiny
  overlap at one boundary (aligners work in frames of some milliseconds) may be resolved by
  ending the earlier segment at the later one's start; record that you did so.

`timesFromCharacters(segments, chars)` in [`validate.mjs`](validate.mjs) applies these rules and
reports problems instead of filling anything in (when there are problems, it returns the
segments without times):

```js
import { timesFromCharacters } from "./validate.mjs";
// chars: one entry per character of the sentence, { start, end } in seconds or null
const chars = whisperxChars.map((c) => ("start" in c ? { start: c.start, end: c.end } : null));
const { segments, problems } = timesFromCharacters(untimedSegments, chars);
```

With word times (MFA, Polly, Azure), give every character of a word its word's start and end and
use the same function. A word that straddles two segments makes them overlap, and is reported:
merge the two segments, or re-segment so that the word lies in one.

## Step 4: validate before use

Run these checks every time, and do not draw a sentence that fails them.

1. **The text joins back exactly.** All parts' `text`, joined in order, equal the original
   sentence character for character: no normalised forms, no lost spaces, no changed punctuation.
2. **`Tsubu.sentence(input)` does not throw.** It refuses partly timed sentences, overlapping or
   out-of-order times, punctuation with a time, and empty parts.
3. Readings are hiragana, sit on kanji only, and no kanji is left without one (unless allowed on
   purpose); punctuation segments hold only punctuation.

[`validate.mjs`](validate.mjs) does all three (Node 18 or newer, no dependencies):

```sh
node docs/agents/validate.mjs input.json --text sentence.txt --duration 3.2
```

It prints `{ ok, timing, errors, warnings }` and exits with 1 when there are errors. `--duration`
also checks that no time is past the end of the audio; `--tsubu` points at a copy of `tsubu.js`
elsewhere.

Then, **on the target page**, with its font, size and container (these need a browser):

```js
await document.fonts.ready;
const s = Tsubu.sentence(input, { theme: "light" });
container.innerHTML = s.html;
const root = container.querySelector(".tsubu");
const fit = Tsubu.checkFit(root);            // { ok, issues, lines, pages }
const contrast = Tsubu.checkContrast(root);  // { ok, checks, failures }
if (!fit.ok || !contrast.ok) { /* report; do not ship the frame */ }
```

`checkFit` reports segments that overflow the container, are too long for a line, furigana that
are clipped, and too many lines; `checkContrast` measures every colour in every state against
`Tsubu.CONTRAST`. Both are described in the [README](../../README.md#output).

## Using an LLM in the loop

A language model is useful between the tools, as long as it only chooses and never writes data.

It **may**:

- choose among analysers' outputs when they disagree on a bunsetsu boundary;
- apply the merge rule above where an analyser's parts of speech leave it unclear;
- set `kind: "punct"` on segments that are obviously punctuation, or remove it from ones that are
  not;
- decide that a sentence needs a human (an unknown name, a doubtful reading, a bad alignment) and
  say why.

It **must not**:

- rewrite, correct or normalise the sentence (step 4 would catch it, but do not try);
- invent, "fix" or complete a reading that no tool gave;
- invent, round to look nicer, or fill in a time.

Ask for structured output (the segments as JSON) and run step 4 on whatever comes back.

As of 2026-10-19, examples of models that suit this role are Anthropic's Claude Opus 5.5
(`claude-opus-5-5`) for decisions that need judgement and Claude Haiku 5.5 (`claude-haiku-5-5`)
for high-volume, simple choices ([models overview](https://platform.claude.com/docs/en/about-claude/models/overview)).
Models are replaced often; check the current list rather than these names.

## Sources

Read on 2026-10-19. Versions, dates and licences come from these pages or from the package
registries (PyPI, npm) at that date.

- Universal Dependencies: [UniDic tags mapped to UD for Japanese](https://universaldependencies.org/docsv1/ja/overview/morphology.html);
  spaCy: [`Span`](https://spacy.io/api/span)
- GiNZA: [repository and changelog](https://github.com/megagonlabs/ginza),
  [bunsetu API](https://megagonlabs.github.io/ginza/bunsetu_api.html),
  [`bunsetu_recognizer.py`](https://github.com/megagonlabs/ginza/blob/develop/ginza/bunsetu_recognizer.py),
  [PyPI](https://pypi.org/project/ginza/)
- KNP: [repository](https://github.com/ku-nlp/knp), [home page](https://nlp.ist.i.kyoto-u.ac.jp/?KNP);
  KWJA: [repository](https://github.com/ku-nlp/kwja), [PyPI](https://pypi.org/project/kwja/);
  rhoknp: [repository](https://github.com/ku-nlp/rhoknp),
  [`units/`](https://github.com/ku-nlp/rhoknp/tree/main/src/rhoknp/units)
- SudachiPy: [sudachi.rs](https://github.com/WorksApplications/sudachi.rs),
  [Python README](https://github.com/WorksApplications/sudachi.rs/blob/develop/python/README.md),
  [Python API stubs](https://github.com/WorksApplications/sudachi.rs/blob/develop/python/py_src/sudachipy/sudachipy.pyi),
  [PyPI](https://pypi.org/project/SudachiPy/); SudachiDict:
  [repository](https://github.com/WorksApplications/SudachiDict)
- fugashi: [repository](https://github.com/polm/fugashi),
  [UniDic schemas in `fugashi.pyx`](https://github.com/polm/fugashi/blob/main/fugashi/fugashi.pyx);
  unidic-py: [repository and field list](https://github.com/polm/unidic-py)
- kuromoji.js: [repository](https://github.com/takuyaa/kuromoji.js),
  [npm](https://www.npmjs.com/package/kuromoji)
- WhisperX: [repository](https://github.com/m-bain/whisperX),
  [`alignment.py`](https://github.com/m-bain/whisperX/blob/main/whisperx/alignment.py),
  [`audio.py`](https://github.com/m-bain/whisperX/blob/main/whisperx/audio.py),
  [PyPI](https://pypi.org/project/whisperx/); Japanese alignment model:
  [model card](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-japanese)
- Montreal Forced Aligner: [alignment tutorial](https://montreal-forced-aligner.readthedocs.io/en/latest/first_steps/alignment_example.html),
  [Japanese acoustic model v3.0.0](https://mfa-models.readthedocs.io/en/latest/acoustic/Japanese/Japanese%20MFA%20acoustic%20model%20v3_0_0.html),
  [Japanese dictionary v3.0.0](https://mfa-models.readthedocs.io/en/latest/dictionary/Japanese/Japanese%20MFA%20dictionary%20v3_0_0.html),
  [PyPI](https://pypi.org/project/montreal-forced-aligner/)
- ElevenLabs: [create speech with timing](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)
- Amazon Polly: [speech marks](https://docs.aws.amazon.com/polly/latest/dg/speechmarks.html),
  [speech mark output](https://docs.aws.amazon.com/polly/latest/dg/output.html)
- Azure AI Speech: [how to synthesise speech](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-speech-synthesis)
- Google Cloud Text-to-Speech: [`text:synthesize` (v1beta1)](https://docs.cloud.google.com/text-to-speech/docs/reference/rest/v1beta1/text/synthesize)
- Claude models: [models overview](https://platform.claude.com/docs/en/about-claude/models/overview)

## Changelog

### 1.0.0 (2026-10-19)

- First version, for tsubu 0.1.0: bunsetsu with GiNZA 5.3.0 or KNP/KWJA, fallbacks SudachiPy
  0.7.0, fugashi 1.5.2 with UniDic, kuromoji.js 0.1.2; readings from the analyser with
  `splitReading`; times from WhisperX 3.8.6 character alignment, MFA 3.4.3, or TTS timing
  (ElevenLabs, Amazon Polly, Azure AI Speech, Google Cloud SSML marks) with
  `timesFromCharacters`; the validator `validate.mjs` and a hand-made worked example.
