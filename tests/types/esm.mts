// The declarations as an ES module user sees them, through the package's own exports map.
import Tsubu, { sentence, version, STATES, MOTIONS, checkFit, type Input, type Frame } from "tsubu";
import TsubuExport, { toSRT } from "tsubu/export";

const input: Input = {
  segments: [
    { parts: [{ text: "雨", ruby: "あめ" }, { text: "です" }], start: 0, end: 0.6, id: "rain", tags: ["new-word"] },
    { parts: [{ text: "。" }], kind: "punct" },
  ],
};
const s = sentence(input, { ruby: false, theme: "dark", motion: ["mask"], writing: "vertical", combineUpright: 2 });
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

// @ts-expect-error writing is horizontal or vertical
sentence(input, { writing: "diagonal" });
// @ts-expect-error a segment needs its parts
sentence({ segments: [{ start: 0, end: 1 }] });
// @ts-expect-error SRT readings are omitted or inline, not a boolean
toSRT(input, { ruby: true });

export { current, html, sameObject, v, first, needs, srt, vtt, kinds, page };
