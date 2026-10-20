// The declarations as an ES module user sees them, through the package's own exports map.
import Tsubu, { sentence, version, setAnnotation, STATES, MOTIONS, checkFit, type Input, type Frame, type Side, type Switch, type Origin } from "tsubu-js";
import TsubuExport, { toSRT } from "tsubu-js/export";
import TsubuImport, { fromKuroshiro, fromSRT, type Caption } from "tsubu-js/import";

const input: Input = {
  segments: [
    { parts: [{ text: "雨", ruby: "あめ" }, { text: "です" }], romaji: "ame desu", start: 0, end: 0.6, id: "rain", tags: ["new-word"] },
    { parts: [{ text: "パン", origin: { text: "pão", lang: "pt" } }, { text: "と" }], start: 0.6, end: 0.9 },
    { parts: [{ text: "サラリーマン", origin: { text: "salaried man", lang: "en", wasei: true } }], start: 0.9, end: 1.4 },
    { parts: [{ text: "。" }], kind: "punct" },
  ],
};
const bread: Origin = { text: "pão", lang: "pt" };
const s = sentence(input, { ruby: false, theme: "dark", motion: ["mask"], writing: "vertical", combineUpright: 2, over: "romaji", under: "ruby" });
const frame: Frame = s.stateAt(0.3);
const current: number | null = frame.current;
const html: string = s.htmlAt(0.3, { revealed: "all" });
const span = s.span(0);
if (span) span.start.toFixed(2);
const sameObject: boolean = Tsubu.sentence === sentence;
const v: string = version;
const first: "future" | "current" | "past" | undefined = STATES[0];
const needs: string = MOTIONS[0]!.needs;
const srt: string = toSRT(input, { mode: "segments", ruby: "inline" });
const vtt: string = TsubuExport.toWebVTT(input, { ruby: true, id: "cue" });

declare const root: Element;
const fit = checkFit(root, { container: root });
const kinds: string[] = fit.issues.map((issue) => issue.kind);
const applied = s.apply(root, 0.3);
const page: number | null = applied.page;
const under: Side = "under";
setAnnotation(root, under, false);
Tsubu.setAnnotation(root, "over", true);
const origins: Switch = "origin";
setAnnotation(root, origins, false);
const withOrigins = sentence(input, { origin: "over", under: "romaji" });

const parts = fromKuroshiro("<ruby>雨<rp>(</rp><rt>あめ</rt><rp>)</rp></ruby>");
const captions: Caption[] = [{ text: " 雨", startMs: 0, endMs: 400, timestampMs: null, confidence: 0.9 }];
const fromRemotion: Input = TsubuImport.fromCaptions(captions);
const oneSentence: Input = fromSRT(srt, { mode: "segments" });
const perCue: Input[] = fromSRT(srt);

// @ts-expect-error writing is horizontal or vertical
sentence(input, { writing: "diagonal" });
// @ts-expect-error a side shows furigana, romaji or nothing
sentence(input, { under: "pinyin" });
// @ts-expect-error the sides are over and under, and the origins have their own switch
setAnnotation(root, "left", true);
// @ts-expect-error origins are drawn over the text or not at all
sentence(input, { origin: "under" });
// @ts-expect-error an origin needs its language
const noLanguage: Origin = { text: "pão" };
// @ts-expect-error a segment needs its parts
sentence({ segments: [{ start: 0, end: 1 }] });
// @ts-expect-error SRT readings are omitted or inline, not a boolean
toSRT(input, { ruby: true });
// @ts-expect-error mode "segments" reads the file as one sentence, not an array
const notAnArray: Input[] = fromSRT(srt, { mode: "segments" });

export { bread, withOrigins, noLanguage, current, html, sameObject, v, first, needs, srt, vtt, kinds, page, parts, fromRemotion, oneSentence, perCue, notAnArray };
