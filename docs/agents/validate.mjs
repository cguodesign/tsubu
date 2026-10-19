/*
 * Step 4 of docs/agents/segmenting.md: checks a prepared tsubu input against the sentence it was
 * made from, before anything is drawn. No dependencies; Node 18 or newer.
 *
 *   node docs/agents/validate.mjs input.json --text sentence.txt
 *        [--duration seconds] [--allow-missing-ruby] [--tsubu path/to/tsubu.js]
 *
 * It prints a JSON report, { ok, timing, errors, warnings }, and exits 0 when there are no errors
 * and 1 when there are. The checks:
 *   - the segments' text, joined, is the original sentence exactly;
 *   - a segment of kind "punct" holds only punctuation, and a segment that holds only
 *     punctuation is of kind "punct";
 *   - every part that contains a kanji has a reading (unless --allow-missing-ruby), a part with
 *     a reading holds kanji only (okurigana stay plain), and readings are hiragana;
 *   - spoken segments are all timed or none are, and no time is past --duration;
 *   - Tsubu.sentence(input) does not throw.
 * checkFit and checkContrast need the target page and a browser, so they are not run here.
 *
 * It also exports validate(input, text, options) and the two helpers the guide uses:
 * splitReading(surface, reading), which puts a word's reading on its kanji (step 2), and
 * timesFromCharacters(segments, chars), which turns an aligner's character times into segment
 * times (step 3).
 */
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const DEFAULT_TSUBU = fileURLToPath(new URL("../../tsubu.js", import.meta.url));

// Characters that take a reading: kanji, and the marks that stand for one (々 〆 ヶ ヵ).
const KANJI = /[\p{Script=Han}々〆ヶヵ]/u;
const KANJI_ONLY = /^[\p{Script=Han}々〆ヶヵ]+$/u;
const HIRAGANA_ONLY = /^[ぁ-ゖゝゞー]+$/u;
const PUNCT_ONLY = /^[\p{P}\p{S}\s]+$/u;

/* Katakana to hiragana, leaving everything else (ー included) as it is. */
export function toHiragana(text) {
  return text.replace(/[ァ-ヶヽヾ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));
}

/* A word's parts for tsubu: one part per run of kanji, carrying the piece of the reading that
 * belongs to it, and the kana around and between them as plain parts. The kana in the surface
 * anchor the split, so the reading must contain them literally (compared in hiragana). Returns
 * null when the reading does not fit the surface, or fits it in more than one way: the caller
 * must then decide, or flag the word for a human, rather than guess. */
export function splitReading(surface, reading) {
  const runs = surface.match(/[\p{Script=Han}々〆ヶヵ]+|[^\p{Script=Han}々〆ヶヵ]+/gu) || [];
  const said = toHiragana(reading);
  if (!runs.some((run) => KANJI.test(run))) return toHiragana(surface) === said ? [{ text: surface }] : null;
  const found = [];
  (function fit(i, at, parts) {
    if (found.length > 1) return;
    if (i === runs.length) { if (at === said.length) found.push(parts); return; }
    const run = runs[i];
    if (!KANJI.test(run)) {
      const kana = toHiragana(run);
      if (said.startsWith(kana, at)) fit(i + 1, at + kana.length, [...parts, { text: run }]);
      return;
    }
    for (let end = at + 1; end <= said.length; end++) fit(i + 1, end, [...parts, { text: run, ruby: said.slice(at, end) }]);
  })(0, 0, []);
  return found.length === 1 ? found[0] : null;
}

/* Segment times from character times (step 3). `chars` has one entry per character of the
 * sentence, in order (Array.from(text), so one per code point): { start, end } in seconds, or null
 * where the aligner gave that character no time. A spoken segment runs from its first character's
 * start to its last character's end; punctuation gets no time, and characters that are
 * punctuation are skipped inside a spoken segment too. Nothing is filled in: a spoken segment
 * whose first or last character has no time, or segments whose times overlap, are reported as
 * problems, and then no segment gets a time (a partly timed sentence is refused anyway). Returns
 * { segments, problems }; the input is not changed. */
export function timesFromCharacters(segments, chars) {
  const problems = [];
  const timed = (c) => c && Number.isFinite(c.start) && Number.isFinite(c.end);
  const round = (v) => Math.round(v * 1000) / 1000;
  let at = 0;
  const out = segments.map((segment, i) => {
    const own = Array.from(segment.parts.map((p) => p.text).join("")).map((ch, k) => ({ ch, time: chars[at + k] }));
    at += own.length;
    const { start, end, ...rest } = segment;
    if (segment.kind === "punct") return rest;
    const spoken = own.filter(({ ch }) => !PUNCT_ONLY.test(ch));
    if (!spoken.length) { problems.push(`segment ${i} has no character that is not punctuation`); return rest; }
    const first = spoken[0], last = spoken[spoken.length - 1];
    if (!timed(first.time) || !timed(last.time)) {
      problems.push(`segment ${i}: the aligner gave ${JSON.stringify((timed(first.time) ? last : first).ch)} no time, so the segment's ${timed(first.time) ? "end" : "start"} is not measured`);
      return rest;
    }
    return { ...rest, start: round(first.time.start), end: round(last.time.end) };
  });
  if (at !== chars.length) problems.push(`the sentence has ${at} characters but ${chars.length} character times were given`);
  let previous = null;
  out.forEach((segment, i) => {
    if (segment.start === undefined) return;
    if (segment.end < segment.start) problems.push(`segment ${i} ends before it starts`);
    if (previous && segment.start < previous.segment.end)
      problems.push(`segments ${previous.i} and ${i} overlap (${previous.segment.end} > ${segment.start})`);
    previous = { segment, i };
  });
  if (!problems.length) return { segments: out, problems };
  return { segments: out.map(({ start, end, ...rest }) => rest), problems };
}

function isTimed(segment) {
  return segment.start !== undefined || segment.end !== undefined;
}

/* The checks on one input. `text` is the sentence the input was made from. */
export function validate(input, text, options = {}) {
  const errors = [], warnings = [];
  let timing = null;
  const segments = input && Array.isArray(input.segments) ? input.segments : [];
  if (!segments.length) errors.push("the input has no `segments` array");
  const textOf = (segment) => (Array.isArray(segment?.parts) ? segment.parts.map((p) => (typeof p?.text === "string" ? p.text : "")).join("") : "");

  // The text, joined back, is the sentence.
  const joined = segments.map(textOf).join("");
  if (joined !== text) {
    let at = 0;
    while (at < joined.length && at < text.length && joined[at] === text[at]) at++;
    errors.push(`the segments' text does not join back into the sentence: they differ from character ${at} on ` +
      `(segments: ${JSON.stringify(joined.slice(at, at + 12))}, sentence: ${JSON.stringify(text.slice(at, at + 12))})`);
  }

  // Punctuation.
  segments.forEach((segment, i) => {
    const t = textOf(segment);
    if (!t) return;
    if (segment.kind === "punct" && !PUNCT_ONLY.test(t)) errors.push(`segment ${i}, ${JSON.stringify(t)}, is of kind "punct" but holds more than punctuation`);
    if (segment.kind !== "punct" && PUNCT_ONLY.test(t)) errors.push(`segment ${i}, ${JSON.stringify(t)}, holds only punctuation: give it kind "punct"`);
    if (segment.kind === "punct" && Array.isArray(segment.parts) && segment.parts.some((p) => p?.ruby !== undefined)) errors.push(`segment ${i} is punctuation with a reading`);
  });

  // Readings.
  const parts = segments.flatMap((segment, i) => (Array.isArray(segment?.parts) ? segment.parts.map((part, j) => ({ part, where: `segment ${i}, part ${j}` })) : []));
  const withRuby = parts.filter(({ part }) => part?.ruby !== undefined);
  for (const { part, where } of withRuby) {
    if (typeof part.ruby !== "string" || !part.ruby) continue; // tsubu itself refuses it, below
    if (!KANJI_ONLY.test(part.text)) errors.push(`${where}, ${JSON.stringify(part.text)}: a part with a reading holds kanji only; split the kana around it into plain parts`);
    if (!HIRAGANA_ONLY.test(part.ruby)) {
      const hint = toHiragana(part.ruby) !== part.ruby ? ` (in hiragana: ${JSON.stringify(toHiragana(part.ruby))})` : "";
      errors.push(`${where}: the reading ${JSON.stringify(part.ruby)} is not all hiragana${hint}`);
    }
  }
  const unread = parts.filter(({ part }) => typeof part?.text === "string" && KANJI.test(part.text) && part.ruby === undefined);
  if (!withRuby.length && unread.length) warnings.push("no part has a reading: the sentence will be drawn without furigana");
  else for (const { part, where } of unread) {
    const message = `${where}, ${JSON.stringify(part.text)}, contains a kanji but has no reading`;
    if (options.allowMissingRuby) warnings.push(message);
    else errors.push(`${message}: give it one, or flag the sentence for a human`);
  }

  // Times: all spoken segments or none.
  const spoken = segments.filter((segment) => segment && segment.kind !== "punct");
  const timed = spoken.filter(isTimed);
  if (timed.length && timed.length !== spoken.length) {
    const missing = segments.map((segment, i) => (segment && segment.kind !== "punct" && !isTimed(segment) ? i : null)).filter((i) => i !== null);
    errors.push(`only ${timed.length} of ${spoken.length} spoken segments have times (no time: ${missing.join(", ")}); time every spoken segment, or none`);
  }
  if (options.duration !== undefined) {
    const late = [...timed, input].filter((s) => s && typeof s.end === "number" && s.end > options.duration);
    if (late.length) errors.push(`a time ends after the audio does (${options.duration} s)`);
  }

  // tsubu itself.
  try {
    const tsubu = require(options.tsubu ? resolve(options.tsubu) : DEFAULT_TSUBU);
    timing = tsubu.sentence(input).timing;
    if (timing === "none") warnings.push("the sentence has no times: it can be drawn, not played");
  } catch (e) {
    errors.push(e.code === "MODULE_NOT_FOUND" ? `cannot load tsubu.js: ${e.message.split("\n")[0]}` : `Tsubu.sentence() refuses it: ${e.message}`);
  }

  return { ok: errors.length === 0, timing, errors, warnings };
}

function main(argv) {
  const args = [...argv];
  const take = (flag) => {
    const i = args.indexOf(flag);
    if (i < 0) return undefined;
    const [, value] = args.splice(i, 2);
    if (value === undefined) throw new Error(`${flag} needs a value`);
    return value;
  };
  const flag = (name) => {
    const i = args.indexOf(name);
    if (i >= 0) args.splice(i, 1);
    return i >= 0;
  };
  const textFile = take("--text"), duration = take("--duration"), tsubu = take("--tsubu");
  const allowMissingRuby = flag("--allow-missing-ruby");
  if (args.length !== 1 || !textFile) throw new Error("usage: node validate.mjs input.json --text sentence.txt [--duration seconds] [--allow-missing-ruby] [--tsubu path/to/tsubu.js]");
  const input = JSON.parse(readFileSync(args[0], "utf8"));
  // The sentence file may end with one line break; the sentence itself does not.
  const text = readFileSync(textFile, "utf8").replace(/\r?\n$/, "");
  const options = { allowMissingRuby };
  if (duration !== undefined) {
    options.duration = Number(duration);
    if (!Number.isFinite(options.duration)) throw new Error("--duration must be a number of seconds");
  }
  if (tsubu !== undefined) options.tsubu = tsubu;
  return validate(input, text, options);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  let report;
  try {
    report = main(process.argv.slice(2));
  } catch (e) {
    report = { ok: false, timing: null, errors: [e.message], warnings: [] };
  }
  process.stdout.write(JSON.stringify(report, null, 2) + "\n");
  process.exitCode = report.ok ? 0 : 1;
}
