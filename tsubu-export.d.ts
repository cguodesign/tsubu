/*
 * Type declarations for tsubu-export.js: the global `TsubuExport` of the classic script, and what
 * require("tsubu/export") returns. tsubu-export.d.mts declares the ES module form.
 */
import Tsubu = require("./tsubu.js");

declare namespace TsubuExport {
  interface WebVTTOptions {
    /** Default true. */
    ruby?: boolean;
    /** Seconds added to every time. Default 0. */
    offset?: number;
    /** The cue's identifier. */
    id?: string;
  }

  interface ASSOptions {
    /** "omit" (default) or "inline", which writes 雨(あめ). */
    ruby?: "omit" | "inline";
    offset?: number;
  }

  interface SRTOptions {
    /** One cue for the sentence (default), or one per spoken segment. */
    mode?: "sentence" | "segments";
    ruby?: "omit" | "inline";
    offset?: number;
  }

  interface API {
    toWebVTT(input: Tsubu.Input, options?: WebVTTOptions): string;
    toASS(input: Tsubu.Input, options?: ASSOptions): string;
    toASSScript(input: Tsubu.Input, options?: ASSOptions): string;
    toSRT(input: Tsubu.Input, options?: SRTOptions): string;
  }
}

declare const TsubuExport: TsubuExport.API;
export = TsubuExport;
export as namespace TsubuExport;
