/*
 * tsubu-export turns one tsubu sentence into subtitles: a WebVTT file with one cue, an ASS
 * (Advanced SubStation Alpha) karaoke line, or a SubRip (SRT) file of plain text. It is optional
 * and separate from tsubu.js, which it needs: in a page, load tsubu.js first and this defines the
 * global `TsubuExport`; in Node, require() returns the same object and loads ./tsubu.js itself.
 *
 * The input is the one Tsubu.sentence() takes, and is checked by Tsubu.sentence(), so the same
 * input is refused with the same error. Nothing is estimated here either: a sentence without
 * times cannot be exported, and with timing "sentence" the span is not divided among segments.
 * The output depends on the input and options alone.
 */
(function (global, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./tsubu.js"));
  else global.TsubuExport = factory(global.Tsubu);
})(typeof globalThis !== "undefined" ? globalThis : this, function (Tsubu) {
  "use strict";

  const WEBVTT_OPTIONS = Object.freeze(["ruby", "offset", "id"]);
  const ASS_OPTIONS = Object.freeze(["ruby", "offset"]);
  const ASS_RUBY = Object.freeze(["omit", "inline"]);
  const SRT_OPTIONS = Object.freeze(["mode", "ruby", "offset"]);
  const SRT_MODES = Object.freeze(["sentence", "segments"]);

  function fail(message) {
    throw new Error(`tsubu: ${message}`);
  }

  /* No options, undefined or null, means the defaults. */
  function optionsOf(options, known, name) {
    if (options === undefined || options === null) return {};
    if (typeof options !== "object" || Array.isArray(options)) fail(`${name} options must be an object`);
    // An unknown option is most likely a misspelt or misplaced one (ruby: "inline" is an ASS
    // option): refusing it beats silently ignoring it.
    for (const key of Object.keys(options)) if (!known.includes(key)) fail(`${name} has no option ${JSON.stringify(key)}`);
    return options;
  }

  function checkOffset(offset) {
    if (offset === undefined) return 0;
    if (typeof offset !== "number" || !Number.isFinite(offset)) fail("options.offset must be a finite number of seconds");
    return offset;
  }

  /* Checks the input with tsubu itself, then reads what the export needs from it: the timing,
   * the sentence's span (the same one tsubu.js uses) and the segments in reading order. */
  function read(input) {
    if (!Tsubu || typeof Tsubu.sentence !== "function") fail("tsubu-export needs tsubu.js: load it first");
    const timing = Tsubu.sentence(input).timing;
    if (timing === "none")
      fail("this sentence has no times, so it cannot be a subtitle: give the whole sentence a start and end, or every segment its own");
    const segments = input.segments.map((s) => ({
      parts: s.parts.map((p) => ({ text: p.text, ruby: p.ruby })),
      punct: s.kind === "punct",
      start: s.start,
      end: s.end,
    }));
    const spoken = segments.filter((s) => !s.punct);
    const whole = input.start !== undefined;
    return {
      timing,
      segments,
      start: whole ? input.start : spoken[0].start,
      end: whole ? input.end : spoken[spoken.length - 1].end,
    };
  }

  /* Each spoken segment with the punctuation that goes with it: punctuation joins the spoken
   * segment before it, or the first one when it opens the sentence. This is the same rule by
   * which tsubu.js lets punctuation become past. */
  function groups(segments) {
    const out = [];
    let opening = [];
    for (const segment of segments) {
      if (segment.punct && out.length) out[out.length - 1].segments.push(segment);
      else if (segment.punct) opening.push(segment);
      else {
        out.push({ start: segment.start, end: segment.end, segments: opening.concat(segment) });
        opening = [];
      }
    }
    return out;
  }

  /* A time, plus the offset, as a whole number of milliseconds or centiseconds. Times are written
   * in decimal, but 0.285 * 100 is 28.499999999999996 in binary; rounding to 12 significant
   * digits first drops that noise, so a time is rounded half up as it was written. */
  function units(seconds, offset, perSecond, what) {
    const n = Math.round(Number(((seconds + offset) * perSecond).toPrecision(12)));
    if (!Number.isSafeInteger(n)) fail(`${what} is too large to write`);
    if (n < 0) fail(`${what} is ${seconds + offset} s with the offset; subtitle times cannot be negative`);
    return n;
  }

  /* Text is one line: a line break in the input becomes a space, as it does when tsubu's HTML is
   * drawn. In WebVTT a blank line would end the cue; in ASS any line break ends the event. */
  function oneLine(text) {
    return text.replace(/\r\n|[\r\n]/g, " ");
  }

  function pad(n, width) {
    return String(n).padStart(width, "0");
  }

  /* hh:mm:ss.ttt, hours always written with at least two digits, as WebVTT requires. */
  function vttTime(ms) {
    return `${pad(Math.floor(ms / 3600000), 2)}:${pad(Math.floor(ms / 60000) % 60, 2)}:${pad(Math.floor(ms / 1000) % 60, 2)}.${pad(ms % 1000, 3)}`;
  }

  function vttEscape(text) {
    // `>` needs no escape in cue text, but escaping it keeps "-->" out of the payload, where it
    // is not allowed.
    return oneLine(text).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
  }

  /**
   * TsubuExport.toWebVTT(input, options) -> a WebVTT file with one cue for the sentence.
   *   options: { ruby: true | false (default true), offset: seconds (default 0), id?: cue identifier }
   * Each segment is a class span, <c.tsubu-seg> (<c.tsubu-seg.punct> for punctuation), and a part
   * with a reading is <ruby>base<rt>reading</rt></ruby>. With timing "segments", a cue timestamp
   * <hh:mm:ss.ttt> before each spoken segment marks its start, so ::cue(:past) follows the reading.
   */
  function toWebVTT(input, options) {
    const opts = optionsOf(options, WEBVTT_OPTIONS, "toWebVTT");
    if (opts.ruby !== undefined && typeof opts.ruby !== "boolean") fail("options.ruby must be true or false");
    const offset = checkOffset(opts.offset);
    if (opts.id !== undefined && (typeof opts.id !== "string" || opts.id === "" || /[\r\n]/.test(opts.id) || opts.id.includes("-->")))
      fail('options.id must be a non-empty string on one line, without "-->"');
    const sentence = read(input);

    const start = units(sentence.start, offset, 1000, "the sentence's start");
    const end = units(sentence.end, offset, 1000, "the sentence's end");
    if (end <= start) fail("the sentence must last at least a millisecond: a WebVTT cue must end after it starts");

    const segmentText = (segment) => {
      const inner = segment.parts
        .map((p) => (p.ruby === undefined || opts.ruby === false ? vttEscape(p.text) : `<ruby>${vttEscape(p.text)}<rt>${vttEscape(p.ruby)}</rt></ruby>`))
        .join("");
      return `<c.tsubu-seg${segment.punct ? ".punct" : ""}>${inner}</c>`;
    };

    let payload;
    if (sentence.timing === "sentence") payload = sentence.segments.map(segmentText).join("");
    else {
      // A cue timestamp must be later than the cue's start and every earlier timestamp, and
      // earlier than the cue's end. Text before the first timestamp counts as already spoken from
      // the cue's start, so a first segment that begins later gets a timestamp too. A segment
      // that begins in the same millisecond as the one before it needs none: the text before it
      // already turns at that time.
      let mark = start;
      payload = groups(sentence.segments)
        .map((group) => {
          const at = units(group.start, offset, 1000, "a segment's start");
          let stamp = "";
          if (at > mark) {
            if (at >= end) fail(`a segment begins as the sentence ends (${vttTime(at)}); a WebVTT cue timestamp must lie inside the cue`);
            stamp = `<${vttTime(at)}>`;
            mark = at;
          }
          return stamp + group.segments.map(segmentText).join("");
        })
        .join("");
    }
    const id = opts.id === undefined ? "" : `${opts.id}\n`;
    return `WEBVTT\n\n${id}${vttTime(start)} --> ${vttTime(end)}\n${payload}\n`;
  }

  /* H:MM:SS.cc, as ASS writes times. */
  function assTime(cs) {
    return `${Math.floor(cs / 360000)}:${pad(Math.floor(cs / 6000) % 60, 2)}:${pad(Math.floor(cs / 100) % 60, 2)}.${pad(cs % 100, 2)}`;
  }

  /* ASS has no way to escape override braces or a backslash in text: `{` opens an override block
   * and `\` starts \N, \n and \h even outside one. They are written as their full-width forms,
   * ｛ ｝ and ＼, which look alike and are never read as codes. */
  function assEscape(text) {
    return oneLine(text).replace(/[{}\\]/g, (c) => ({ "{": "｛", "}": "｝", "\\": "＼" })[c]);
  }

  function checkASS(options, name) {
    const opts = optionsOf(options, ASS_OPTIONS, name);
    if (opts.ruby !== undefined && !ASS_RUBY.includes(opts.ruby)) fail('options.ruby must be "omit" or "inline"');
    return { inline: opts.ruby === "inline", offset: checkOffset(opts.offset) };
  }

  function dialogue(input, opts) {
    const sentence = read(input);
    const cs = (seconds, what) => units(seconds, opts.offset, 100, what);
    const start = cs(sentence.start, "the sentence's start");
    const end = cs(sentence.end, "the sentence's end");
    if (end <= start) fail("the sentence must last at least a centisecond to be an ASS event");

    const text = (segments) =>
      segments
        .map((segment) => segment.parts.map((p) => assEscape(p.text) + (opts.inline && p.ruby !== undefined ? `(${assEscape(p.ruby)})` : "")).join(""))
        .join("");

    let karaoke;
    if (sentence.timing === "sentence") karaoke = `{\\k${end - start}}${text(sentence.segments)}`;
    else {
      // Every boundary is rounded to centiseconds first and the durations are their differences,
      // so they add up to the event's own length however the times fall; rounding each duration
      // instead would let the highlight drift from the audio. A gap is an empty syllable.
      let at = start;
      karaoke = "";
      for (const group of groups(sentence.segments)) {
        const from = cs(group.start, "a segment's start");
        const to = cs(group.end, "a segment's end");
        if (from > at) karaoke += `{\\k${from - at}}`;
        karaoke += `{\\k${to - from}}${text(group.segments)}`;
        at = to;
      }
      if (end > at) karaoke += `{\\k${end - at}}`;
    }
    return `Dialogue: 0,${assTime(start)},${assTime(end)},Default,,0,0,0,,${karaoke}`;
  }

  /**
   * TsubuExport.toASS(input, options) -> one ASS "Dialogue:" line (no line break) with \k karaoke.
   *   options: { ruby: "omit" | "inline" (default "omit"), offset: seconds (default 0) }
   * "inline" writes a reading in brackets after its base, 雨(あめ): ASS has no ruby.
   */
  function toASS(input, options) {
    return dialogue(input, checkASS(options, "toASS"));
  }

  /* The style: white once spoken (PrimaryColour), grey before (SecondaryColour), with a black
   * outline, bottom centre on a 1920 x 1080 frame. */
  const SCRIPT_HEAD = [
    "[Script Info]",
    "ScriptType: v4.00+",
    "PlayResX: 1920",
    "PlayResY: 1080",
    "WrapStyle: 0",
    "ScaledBorderAndShadow: yes",
    "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    "Style: Default,Arial,72,&H00FFFFFF,&H00A0A0A0,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,2,60,60,60,1",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
  ].join("\n");

  /**
   * TsubuExport.toASSScript(input, options) -> a complete ASS script around toASS's line.
   *   options: as for toASS.
   */
  function toASSScript(input, options) {
    return `${SCRIPT_HEAD}\n${dialogue(input, checkASS(options, "toASSScript"))}\n`;
  }

  /* hh:mm:ss,ttt, as SubRip writes times: a comma before the milliseconds. */
  function srtTime(ms) {
    return vttTime(ms).replace(".", ",");
  }

  /* SubRip has no escapes, and players read <i>-style tags, {\an8}-style override blocks and \N
   * in its text, each in its own way. tsubu writes no tags, and so that the text cannot be read as
   * one, angle brackets, braces and the backslash are written as their full-width forms,
   * ＜ ＞ ｛ ｝ ＼, as in ASS. */
  function srtText(segments, inline) {
    return segments
      .map((segment) => segment.parts.map((p) => p.text + (inline && p.ruby !== undefined ? `(${p.ruby})` : "")).join(""))
      .map((text) => oneLine(text).replace(/[<>{}\\]/g, (c) => ({ "<": "＜", ">": "＞", "{": "｛", "}": "｝", "\\": "＼" })[c]))
      .join("");
  }

  /**
   * TsubuExport.toSRT(input, options) -> a SubRip (.srt) file of plain text, without tags.
   *   options: { mode: "sentence" | "segments" (default "sentence"), ruby: "omit" | "inline"
   *   (default "omit"), offset: seconds (default 0) }
   * "sentence" writes one cue for the sentence. "segments" writes one cue per spoken segment, from
   * its start to its end, with punctuation joined to the segment before it; it needs timing
   * "segments". SubRip has no karaoke, so a highlight that follows the reading needs ASS or WebVTT.
   */
  function toSRT(input, options) {
    const opts = optionsOf(options, SRT_OPTIONS, "toSRT");
    if (opts.mode !== undefined && !SRT_MODES.includes(opts.mode)) fail('options.mode must be "sentence" or "segments"');
    if (opts.ruby !== undefined && !ASS_RUBY.includes(opts.ruby)) fail('options.ruby must be "omit" or "inline"');
    const offset = checkOffset(opts.offset);
    const inline = opts.ruby === "inline";
    const sentence = read(input);
    const ms = (seconds, what) => units(seconds, offset, 1000, what);

    let cues;
    if (opts.mode !== "segments") {
      const start = ms(sentence.start, "the sentence's start");
      const end = ms(sentence.end, "the sentence's end");
      if (end <= start) fail("the sentence must last at least a millisecond: an SRT cue must end after it starts");
      cues = [{ start, end, text: srtText(sentence.segments, inline) }];
    } else {
      if (sentence.timing !== "segments")
        fail('mode "segments" needs a time for every segment; this sentence is timed as a whole, and its span is not divided among segments');
      // Each boundary is rounded on its own, so a cue ends in the very millisecond the next one
      // starts when the two segments meet, and no cue moves however many come before it.
      cues = groups(sentence.segments).map((group) => {
        const start = ms(group.start, "a segment's start");
        const end = ms(group.end, "a segment's end");
        if (end <= start)
          fail(`a segment lasts less than a millisecond (${srtTime(start)}); an SRT cue must end after it starts`);
        return { start, end, text: srtText(group.segments, inline) };
      });
    }
    return cues.map((cue, i) => `${i + 1}\n${srtTime(cue.start)} --> ${srtTime(cue.end)}\n${cue.text}\n`).join("\n");
  }

  return Object.freeze({ toWebVTT, toASS, toASSScript, toSRT });
});
