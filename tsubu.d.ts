/*
 * Type declarations for tsubu.js: the object that the classic script defines as the global
 * `Tsubu`, and that require("tsubu-js") returns. tsubu.d.mts declares the ES module form. The
 * behaviour behind each name is described in docs/guide.md; tests/test_package.py checks that
 * every name the library exports is declared here.
 */

declare namespace Tsubu {
  /** A piece of a segment's text; with `ruby` it is drawn as <ruby>text<rp>（</rp><rt>ruby</rt><rp>）</rp></ruby>. */
  interface Part {
    text: string;
    ruby?: string;
  }

  /** One unit of reading. Times are in seconds on the caller's clock. */
  interface Segment {
    parts: Part[];
    /**
     * The romanised reading of the whole segment, drawn where options.over or options.under says;
     * tsubu never makes one. Not on punctuation.
     */
    romaji?: string;
    start?: number;
    end?: number;
    /** Punctuation: no underline, never the segment being spoken, and never timed. */
    kind?: "punct";
    /** The caller's own name for the segment, unique in the sentence; written as data-id. */
    id?: string;
    /** Lower-case names, written as data-tags. */
    tags?: string[];
  }

  interface Input {
    /** Default "ja". */
    lang?: string;
    start?: number;
    end?: number;
    segments: Segment[];
  }

  type Writing = "horizontal" | "vertical";
  /** What a side of the text shows: the parts' furigana, the segments' romaji, or nothing. */
  type Annotation = "ruby" | "romaji" | "none";
  /** Over: above the text (at its right in vertical text); under: below it (at its left). */
  type Side = "over" | "under";

  interface Options {
    /** Whether the over side (the furigana, by default) starts out shown. Default true. */
    ruby?: boolean;
    /** Whether screen readers read each reading, furigana and romaji. Default true. */
    announceRuby?: boolean;
    /** What is drawn over the text. Default "ruby". Not the same layer as `under`. */
    over?: Annotation;
    /** What is drawn under the text. Default "none". Not the same layer as `over`. */
    under?: Annotation;
    /** A preset from THEMES, or a lower-case name of your own. */
    theme?: string;
    /** A speaker from SPEAKERS, or a lower-case name of your own. */
    speaker?: string;
    /** Motion presets from MOTIONS: a name, a space-separated list of names, or an array. */
    motion?: string | string[];
    writing?: Writing;
    /** In vertical text, runs of up to this many half-width characters stand upright. 0 to 4, default 2. */
    combineUpright?: number;
  }

  type Timing = "segments" | "sentence" | "none";
  type State = "future" | "current" | "past";
  /** Segments to reveal: indexes, "all" or "none". */
  type Revealed = number[] | "all" | "none";

  interface SegmentState {
    state: State;
    /** 0 to 1 through the segment; null for punctuation and with timing "sentence". */
    progress: number | null;
  }

  interface Frame {
    timing: Timing;
    state: State;
    /** 0 to 1 through the sentence. */
    progress: number;
    /** The index of the segment being spoken, or null. */
    current: number | null;
    segments: SegmentState[];
  }

  interface AppliedFrame extends Frame {
    /** The page being shown, from 0; null when the sentence is not paged. */
    page: number | null;
    pages: number | null;
  }

  interface Span {
    start: number;
    end: number;
  }

  interface Sentence {
    readonly html: string;
    readonly timing: Timing;
    stateAt(t: number): Frame;
    htmlAt(t: number, options?: { revealed?: Revealed }): string;
    apply(root: Element, t: number): AppliedFrame;
    span(i: number): Span | null;
    find(id: string): number | null;
  }

  /** "romaji" is measured against the `ruby` threshold. */
  type Layer = "text" | "ruby" | "romaji" | "underline" | "highlight";

  interface Thresholds {
    text: number;
    ruby: number;
    underline: number;
    highlight: number;
  }

  interface ContrastOptions {
    /** A colour, a list of colours, or "any" for black and white. */
    backdrop?: string | string[];
    thresholds?: Partial<Thresholds>;
  }

  interface ContrastCheck {
    state: "static" | State;
    layer: Layer;
    foreground: string;
    background: string;
    backdrop: string;
    ratio: number;
    minimum: number;
    ok: boolean;
  }

  interface ContrastResult {
    ok: boolean;
    checks: ContrastCheck[];
    failures: ContrastCheck[];
  }

  interface FitOptions {
    /** Default: the root's parent element. */
    container?: Element;
  }

  interface FitIssue {
    kind: "overflow" | "too-wide" | "ruby-clipped" | "too-many-lines";
    segment: number | null;
    page: number | null;
    /** How far, in pixels (lines, for "too-many-lines"). */
    by: number;
    message: string;
  }

  interface FitResult {
    ok: boolean;
    issues: FitIssue[];
    lines: number;
    pages: number | null;
  }

  interface MotionParameter {
    readonly property: string;
    readonly default: string;
    readonly min: string;
    readonly max: string;
    readonly meaning: string;
  }

  interface Motion {
    readonly name: string;
    readonly purpose: string;
    readonly needs: Timing;
    readonly without: string;
    readonly parameters: readonly MotionParameter[];
    readonly reducedMotion: string;
    readonly revealable: boolean;
  }

  interface API {
    readonly version: string;
    sentence(input: Input, options?: Options): Sentence;
    setRuby(root: Element, on: boolean): void;
    setAnnotation(root: Element, side: Side, on: boolean): void;
    setRevealed(root: Element, which: Revealed): number[];
    segmentOf(node: Node | null | undefined): number | null;
    contrast(foreground: string, background: string, backdrop?: string): number;
    checkContrast(root: Element, options?: ContrastOptions): ContrastResult;
    checkFit(root: Element, options?: FitOptions): FitResult;
    readonly STATES: readonly State[];
    readonly THEMES: readonly string[];
    readonly SPEAKERS: readonly string[];
    readonly CONTRAST: Readonly<Thresholds>;
    readonly MOTIONS: readonly Motion[];
  }
}

declare const Tsubu: Tsubu.API;
export = Tsubu;
export as namespace Tsubu;
