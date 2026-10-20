/*
 * tsubu-import as an ES module: the same object as tsubu-import.js. In a browser the script needs
 * the global `Tsubu`, so tsubu.mjs is imported first; in Node and in bundlers it requires
 * tsubu.js itself.
 */
import "./tsubu.mjs";
import * as script from "./tsubu-import.js";

const TsubuImport = script.default ?? globalThis.TsubuImport;

export default TsubuImport;
export const { fromKuroshiro, fromCaptions, fromWebVTT, fromSRT } = TsubuImport;
