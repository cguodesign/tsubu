/* Type declarations for tsubu.mjs, the ES module form of tsubu.js; the types are in tsubu.d.ts. */
import Tsubu from "./tsubu.js";

export default Tsubu;
export declare const version: typeof Tsubu.version;
export declare const sentence: typeof Tsubu.sentence;
export declare const setRuby: typeof Tsubu.setRuby;
export declare const setAnnotation: typeof Tsubu.setAnnotation;
export declare const setRevealed: typeof Tsubu.setRevealed;
export declare const segmentOf: typeof Tsubu.segmentOf;
export declare const contrast: typeof Tsubu.contrast;
export declare const checkContrast: typeof Tsubu.checkContrast;
export declare const checkFit: typeof Tsubu.checkFit;
export declare const STATES: typeof Tsubu.STATES;
export declare const THEMES: typeof Tsubu.THEMES;
export declare const SPEAKERS: typeof Tsubu.SPEAKERS;
export declare const CONTRAST: typeof Tsubu.CONTRAST;
export declare const MOTIONS: typeof Tsubu.MOTIONS;
export type {
  Part, Segment, Input, Writing, Annotation, Side, Options, Timing, State, Revealed, SegmentState, Frame, AppliedFrame,
  Span, Sentence, Layer, Thresholds, ContrastOptions, ContrastCheck, ContrastResult, FitOptions,
  FitIssue, FitResult, MotionParameter, Motion, API,
} from "./tsubu.js";
