// The declarations as a page that loads tsubu.js with <script> sees them: the global Tsubu.
/// <reference path="../../tsubu.d.ts" />
/// <reference path="../../tsubu-export.d.ts" />
/// <reference path="../../tsubu-import.d.ts" />

const pageSentence = Tsubu.sentence({ segments: [{ parts: [{ text: "茶", ruby: "ちゃ" }] }] }, { theme: "light" });
const pageTiming: Tsubu.Timing = pageSentence.timing;
declare const pageRoot: Element;
const pageResult: Tsubu.ContrastResult = Tsubu.checkContrast(pageRoot, { backdrop: "any", thresholds: { text: 7 } });
const pageRevealed: number[] = Tsubu.setRevealed(pageRoot, [0]);
const pageIndex: number | null = Tsubu.segmentOf(pageRoot.firstChild);
const pageVtt: string = TsubuExport.toWebVTT({ segments: [{ parts: [{ text: "茶" }], start: 0, end: 1 }] });
const pageParts: Tsubu.Part[] = TsubuImport.fromKuroshiro("<ruby>茶<rp>(</rp><rt>ちゃ</rt><rp>)</rp></ruby>");
