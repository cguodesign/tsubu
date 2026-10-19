/*
 * tsubu-frames: the arithmetic every frame engine needs. An engine counts frames at a frame rate;
 * tsubu takes seconds. Frame n of a video that begins at `from` seconds is t = from + n / fps,
 * computed from n each time rather than added up frame by frame, so no error builds up over a
 * long video. A frame is then s.htmlAt(t), or s.apply(root, t) in a page.
 *
 * It needs nothing else: in a page this defines the global `TsubuFrames`; in Node, or in a
 * bundler such as the one Remotion uses, require() or import returns the same object. The input
 * is the one Tsubu.sentence() takes.
 */
(function (global, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else global.TsubuFrames = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function fail(message) {
    throw new Error(`tsubu-frames: ${message}`);
  }

  function finite(value, name) {
    if (typeof value !== "number" || !Number.isFinite(value)) fail(`${name} must be a finite number`);
    return value;
  }

  function rate(fps) {
    if (finite(fps, "fps") <= 0) fail("fps must be more than 0");
    return fps;
  }

  /**
   * TsubuFrames.span(input) -> { start, end }: the sentence's own start and end when it has them,
   * otherwise the first spoken segment's start and the last one's end. The same span tsubu.js
   * and tsubu-export.js use.
   */
  function span(input) {
    if (!input || typeof input !== "object" || !Array.isArray(input.segments)) fail("a sentence must be an object with `segments`");
    if (input.start !== undefined) return { start: finite(input.start, "the sentence's start"), end: finite(input.end, "the sentence's end") };
    const timed = input.segments.filter((s) => s && s.kind !== "punct" && s.start !== undefined);
    if (!timed.length) fail("this sentence has no times, so it has no frames: give the whole sentence a start and end, or every segment its own");
    return { start: finite(timed[0].start, "a segment's start"), end: finite(timed[timed.length - 1].end, "a segment's end") };
  }

  /** TsubuFrames.timeAt(frame, fps, from = 0) -> the time in seconds of frame number `frame`. */
  function timeAt(frame, fps, from) {
    if (!Number.isInteger(frame) || frame < 0) fail("frame must be a whole number, 0 or more");
    return (from === undefined ? 0 : finite(from, "from")) + frame / rate(fps);
  }

  /**
   * TsubuFrames.frameCount(input, fps, pad = 0) -> how many frames show the sentence from `pad`
   * seconds before its start to `pad` seconds after its end, both ends included, so the last
   * frame shows the whole sentence as spoken. The first frame's time is span(input).start - pad.
   */
  function frameCount(input, fps, pad) {
    const extra = pad === undefined ? 0 : finite(pad, "pad");
    if (extra < 0) fail("pad cannot be negative");
    const { start, end } = span(input);
    // floor with a little room, so that a span of 2.6000000000000005 s at 10 fps is 26 steps, not 27
    return Math.floor((end - start + 2 * extra) * rate(fps) + 1e-6) + 1;
  }

  /** TsubuFrames.htmlAtFrame(sentence, frame, fps, from = 0) -> sentence.htmlAt(timeAt(frame, fps, from)). */
  function htmlAtFrame(sentence, frame, fps, from) {
    if (!sentence || typeof sentence.htmlAt !== "function") fail("htmlAtFrame needs a sentence made by Tsubu.sentence()");
    return sentence.htmlAt(timeAt(frame, fps, from));
  }

  return Object.freeze({ span, timeAt, frameCount, htmlAtFrame });
});
