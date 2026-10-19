/*
 * tsubu (粒, "grain") renders one sentence for read-along use: the caller cuts the sentence
 * into segments, every segment gets its own dotted underline, furigana can be shown or hidden
 * without moving a character, and the segment being spoken is highlighted from timestamps.
 *
 * No dependencies and no build step. This is a classic script rather than an ES module, so a
 * page opened from file:// can load it (browsers refuse module scripts there). In a page it
 * defines the global `Tsubu`; in Node, require() returns the same object.
 *
 * What is drawn depends on t alone: there is no requestAnimationFrame, no timer and no CSS
 * transition. `apply(root, t)` only sets attributes and one custom property; it never touches
 * text or adds and removes nodes, so a change of highlight cannot move a character. The input
 * and output contract is described in README.md.
 */
(function (global, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else global.Tsubu = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const VERSION = "0.1.0";
  const STATES = Object.freeze(["future", "current", "past"]);

  function fail(message) {
    throw new Error(`tsubu: ${message}`);
  }

  function isTime(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function escapeHTML(text) {
    return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  }

  /* A span of time is half-open, [start, end): "future" before it, "current" inside it and
   * "past" from its end on. */
  function spanState(start, end, t) {
    if (t < start) return "future";
    return t < end ? "current" : "past";
  }

  function spanProgress(start, end, t) {
    if (t <= start) return 0;
    if (t >= end) return 1;
    return (t - start) / (end - start);
  }

  function checkSpan(start, end, where) {
    if (!isTime(start) || !isTime(end)) fail(`${where}: start and end must both be finite numbers of seconds`);
    if (end < start) fail(`${where}: end ${end} is before start ${start}`);
  }

  /* Checks the input and works out its timing:
   *   "segments"  every spoken segment has its own start and end;
   *   "sentence"  only the sentence as a whole has a start and end;
   *   "none"      there are no times at all (it can be drawn, not played).
   * A sentence in which only some segments are timed is refused rather than completed:
   * filling in the missing times would mean guessing them. */
  function normalise(input) {
    if (!input || typeof input !== "object") fail("a sentence must be an object");
    if (!Array.isArray(input.segments) || input.segments.length === 0) fail("a sentence needs a non-empty `segments` array");
    const segments = input.segments.map((segment, i) => {
      const where = `segment ${i}`;
      if (!segment || typeof segment !== "object") fail(`${where} must be an object`);
      if (segment.kind !== undefined && segment.kind !== "punct") fail(`${where}: unknown kind ${JSON.stringify(segment.kind)}`);
      if (!Array.isArray(segment.parts) || segment.parts.length === 0) fail(`${where} needs a non-empty \`parts\` array`);
      const parts = segment.parts.map((part, j) => {
        if (!part || typeof part.text !== "string" || part.text === "") fail(`${where}, part ${j} needs non-empty \`text\``);
        if (part.ruby !== undefined && (typeof part.ruby !== "string" || part.ruby === "")) fail(`${where}, part ${j}: \`ruby\` must be a non-empty string`);
        return part.ruby === undefined ? { text: part.text } : { text: part.text, ruby: part.ruby };
      });
      const punct = segment.kind === "punct";
      const timed = segment.start !== undefined || segment.end !== undefined;
      if (punct && timed) fail(`${where}: punctuation carries no time of its own`);
      if (timed) checkSpan(segment.start, segment.end, where);
      return timed ? { parts, punct, start: segment.start, end: segment.end } : { parts, punct };
    });
    const spoken = segments.filter((s) => !s.punct);
    if (spoken.length === 0) fail("a sentence needs at least one segment that is not punctuation");
    const timedCount = spoken.filter((s) => "start" in s).length;
    if (timedCount !== 0 && timedCount !== spoken.length)
      fail(`only ${timedCount} of ${spoken.length} segments have times; give every segment its own time, or none of them and the whole sentence a start and end`);
    for (let i = 1; timedCount && i < spoken.length; i++)
      if (spoken[i].start < spoken[i - 1].end) fail(`segment times overlap or are out of order at segment ${segments.indexOf(spoken[i])}`);

    const whole = input.start !== undefined || input.end !== undefined;
    if (whole) checkSpan(input.start, input.end, "the sentence");
    let start, end;
    if (timedCount) {
      start = whole ? input.start : spoken[0].start;
      end = whole ? input.end : spoken[spoken.length - 1].end;
      if (spoken[0].start < start || spoken[spoken.length - 1].end > end) fail("segment times fall outside the sentence's start and end");
    } else if (whole) {
      start = input.start;
      end = input.end;
    }
    const timing = timedCount ? "segments" : whole ? "sentence" : "none";
    if (input.lang !== undefined && (typeof input.lang !== "string" || input.lang === "")) fail("`lang` must be a non-empty string");
    return { lang: input.lang || "ja", segments, timing, start, end };
  }

  function renderHTML(sentence, ruby) {
    const segments = sentence.segments.map((segment, i) => {
      const inner = segment.parts
        .map((p) => (p.ruby === undefined ? escapeHTML(p.text) : `<ruby>${escapeHTML(p.text)}<rt>${escapeHTML(p.ruby)}</rt></ruby>`))
        .join("");
      const kind = segment.punct ? ' data-kind="punct"' : "";
      return `<span class="tsubu-seg" data-index="${i}"${kind}>${inner}</span>`;
    });
    // Segments are nowrap, so a segment is never split across two lines. A <wbr> before each
    // segment gives the line an explicit place to break (Chromium will not break before a
    // segment that begins with <ruby> without one). Punctuation gets none: it must not begin
    // a line.
    const joined = segments.map((html, i) => (i > 0 && !sentence.segments[i].punct ? "<wbr>" : "") + html).join("");
    return `<span class="tsubu" lang="${escapeHTML(sentence.lang)}" data-timing="${sentence.timing}" data-ruby="${ruby ? "on" : "off"}">${joined}</span>`;
  }

  /* The state of the sentence and of each segment at t (seconds, on the same clock as the
   * input's times). With timing "sentence", every segment, punctuation included, shares the
   * sentence's state. With timing "segments", punctuation is never "current": it becomes
   * "past" together with the spoken segment before it, or, when it opens the sentence, once
   * the first spoken segment begins. */
  function stateOf(sentence, t) {
    if (!isTime(t)) fail(`t must be a finite number of seconds, not ${t}`);
    if (sentence.timing === "none") fail("this sentence has no times: give the whole sentence a start and end, or every segment its own");
    const state = spanState(sentence.start, sentence.end, t);
    const progress = spanProgress(sentence.start, sentence.end, t);
    const own = sentence.segments.map((s) => {
      if (sentence.timing === "sentence") return { state, progress: null };
      if (s.punct) return null;
      return { state: spanState(s.start, s.end, t), progress: spanProgress(s.start, s.end, t) };
    });
    const segments = own.map((entry, i) => {
      if (entry) return entry;
      let before = i - 1;
      while (before >= 0 && !own[before]) before--;
      if (before >= 0) return { state: own[before].state === "past" ? "past" : "future", progress: null };
      const after = own.findIndex((e) => e);
      return { state: own[after].state === "future" ? "future" : "past", progress: null };
    });
    const current = sentence.timing === "segments" ? own.findIndex((e) => e && e.state === "current") : -1;
    return { timing: sentence.timing, state, progress, current: current === -1 ? null : current, segments };
  }

  function segmentElements(root, sentence) {
    if (!root || typeof root.querySelectorAll !== "function") fail("apply needs the sentence's root element");
    if (!root.classList.contains("tsubu")) fail('apply needs the element with class "tsubu" made from `html`, not a container');
    const elements = root.querySelectorAll(":scope > .tsubu-seg");
    if (elements.length !== sentence.segments.length)
      fail(`the element has ${elements.length} segments, this sentence has ${sentence.segments.length}`);
    return elements;
  }

  function setProgress(element, progress) {
    if (progress === null) element.style.removeProperty("--tsubu-progress");
    else element.style.setProperty("--tsubu-progress", String(progress));
  }

  function setCurrent(element, on) {
    if (on) element.setAttribute("aria-current", "true");
    else element.removeAttribute("aria-current");
  }

  function applyState(root, sentence, t) {
    const elements = segmentElements(root, sentence);
    const s = stateOf(sentence, t);
    root.setAttribute("data-state", s.state);
    setProgress(root, s.progress);
    // Without per-segment times nobody knows which segment is being spoken, so the sentence
    // as a whole is the current one.
    setCurrent(root, s.timing === "sentence" && s.state === "current");
    s.segments.forEach((entry, i) => {
      elements[i].setAttribute("data-state", entry.state);
      setProgress(elements[i], entry.progress);
      setCurrent(elements[i], i === s.current);
    });
    return s;
  }

  /**
   * Tsubu.sentence(input, options) -> { html, timing, stateAt(t), apply(root, t) }
   *   input:   { lang?, start?, end?, segments: [{ parts: [{ text, ruby? }], start?, end?, kind? }] }
   *   options: { ruby: true | false }  (default true)
   */
  function sentence(input, options) {
    const opts = options || {};
    if (opts.ruby !== undefined && typeof opts.ruby !== "boolean") fail("options.ruby must be true or false");
    const normalised = normalise(input);
    return Object.freeze({
      html: renderHTML(normalised, opts.ruby !== false),
      timing: normalised.timing,
      stateAt: (t) => stateOf(normalised, t),
      apply: (root, t) => applyState(root, normalised, t),
    });
  }

  /* Shows or hides the furigana of a drawn sentence. The <rt> keeps its place in the layout
   * either way, so no character moves. */
  function setRuby(root, on) {
    if (!root || !root.classList || !root.classList.contains("tsubu")) fail('setRuby needs the element with class "tsubu"');
    root.setAttribute("data-ruby", on ? "on" : "off");
  }

  return Object.freeze({ version: VERSION, sentence, setRuby, STATES });
});
