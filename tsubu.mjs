/*
 * tsubu as an ES module: the same object as the classic script, with no code of its own.
 * In a browser, importing tsubu.js runs it as a script would and it defines the global `Tsubu`;
 * in Node and in bundlers it is a CommonJS module, and its exports arrive as `default`.
 */
import * as script from "./tsubu.js";

const Tsubu = script.default ?? globalThis.Tsubu;

export default Tsubu;
export const { version, sentence, setRuby, setAnnotation, setRevealed, segmentOf, contrast, checkContrast, checkFit,
  STATES, THEMES, SPEAKERS, CONTRAST, MOTIONS } = Tsubu;
