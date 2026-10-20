// The declarations as a CommonJS user sees them: require("tsubu-js"), require("tsubu-js/export")
// and require("tsubu-js/import").
import Tsubu = require("tsubu-js");
import TsubuExport = require("tsubu-js/export");
import TsubuImport = require("tsubu-js/import");

const s: Tsubu.Sentence = Tsubu.sentence({ segments: [{ parts: [{ text: "家" }], start: 0, end: 1 }] });
const ratio: number = Tsubu.contrast("#000", "#fff");
const thresholds: Readonly<Tsubu.Thresholds> = Tsubu.CONTRAST;
const ass: string = TsubuExport.toASSScript({ segments: [{ parts: [{ text: "家" }], start: 0, end: 1 }] }, { ruby: "omit", offset: 1 });

const sentences: Tsubu.Input[] = TsubuImport.fromWebVTT("WEBVTT\n\n00:00.000 --> 00:01.000\n家");

export = { s, ratio, thresholds, ass, sentences };
