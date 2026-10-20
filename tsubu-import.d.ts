/*
 * Type declarations for tsubu-import.js: the global `TsubuImport` of the classic script, and what
 * require("tsubu-js/import") returns. tsubu-import.d.mts declares the ES module form.
 */
import Tsubu = require("./tsubu.js");

declare namespace TsubuImport {
  /** Remotion's Caption (@remotion/captions); only text, startMs and endMs are read. */
  interface Caption {
    text: string;
    startMs: number;
    endMs: number;
    timestampMs?: number | null;
    confidence?: number | null;
    pageBreakAfter?: boolean;
  }

  interface SRTOptions {
    /** Each cue a sentence of its own (default), or the whole file one sentence, a cue per segment. */
    mode?: "sentence" | "segments";
  }

  interface API {
    fromKuroshiro(html: string): Tsubu.Part[];
    fromCaptions(captions: readonly Caption[]): Tsubu.Input;
    fromWebVTT(text: string): Tsubu.Input[];
    fromSRT(text: string, options?: SRTOptions & { mode?: "sentence" }): Tsubu.Input[];
    fromSRT(text: string, options: SRTOptions & { mode: "segments" }): Tsubu.Input;
  }
}

declare const TsubuImport: TsubuImport.API;
export = TsubuImport;
export as namespace TsubuImport;
