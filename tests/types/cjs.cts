// The declarations as a CommonJS user sees them: require("tsubu-js") and require("tsubu-js/export").
import Tsubu = require("tsubu-js");
import TsubuExport = require("tsubu-js/export");

const s: Tsubu.Sentence = Tsubu.sentence({ segments: [{ parts: [{ text: "家" }], start: 0, end: 1 }] });
const ratio: number = Tsubu.contrast("#000", "#fff");
const thresholds: Readonly<Tsubu.Thresholds> = Tsubu.CONTRAST;
const ass: string = TsubuExport.toASSScript({ segments: [{ parts: [{ text: "家" }], start: 0, end: 1 }] }, { ruby: "omit", offset: 1 });

export = { s, ratio, thresholds, ass };
