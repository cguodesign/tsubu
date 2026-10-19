/*
 * tsubu-export as an ES module: the same object as tsubu-export.js. In a browser the script needs
 * the global `Tsubu`, so tsubu.mjs is imported first; in Node and in bundlers it requires
 * tsubu.js itself.
 */
import "./tsubu.mjs";
import * as script from "./tsubu-export.js";

const TsubuExport = script.default ?? globalThis.TsubuExport;

export default TsubuExport;
export const { toWebVTT, toASS, toASSScript, toSRT } = TsubuExport;
