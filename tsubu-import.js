/*
 * tsubu-import turns other formats into the input Tsubu.sentence() takes: kuroshiro's furigana
 * HTML, Remotion's captions, WebVTT and SubRip (SRT). It is optional and separate from tsubu.js,
 * which it needs: in a page, load tsubu.js first and this defines the global `TsubuImport`; in
 * Node, require() returns the same object and loads ./tsubu.js itself.
 *
 * Nothing is guessed here either. Segments come only from what the format marks (a caption, a
 * cue, a WebVTT class span or cue timestamp), never from the text, and times only from the file.
 * Every result is checked with Tsubu.sentence(), so input tsubu would refuse is refused here,
 * with the cue or caption it came from named.
 */
(function (global, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory(require("./tsubu.js"));
  else global.TsubuImport = factory(global.Tsubu);
})(typeof globalThis !== "undefined" ? globalThis : this, function (Tsubu) {
  "use strict";

  const SRT_OPTIONS = Object.freeze(["mode"]);
  const SRT_MODES = Object.freeze(["sentence", "segments"]);

  // Text that is punctuation alone (and spaces): a segment of it becomes kind "punct", which
  // tsubu never makes current and which may not carry a time.
  const PUNCT_ONLY = /^[\p{P}\s]+$/u;
  // Han, kana, CJK symbols and punctuation, and full-width forms: no space is put between two of
  // these where a line breaks (CSS Text's segment break rules, as Firefox applies them).
  const WIDE = /[⺀-鿿豈-﫿︰-﹏＀-￯]/;

  function fail(message) {
    throw new Error(`tsubu: ${message}`);
  }

  function need() {
    if (!Tsubu || typeof Tsubu.sentence !== "function") fail("tsubu-import needs tsubu.js: load it first");
  }

  /* Checks a result with tsubu itself; its error names `where` the input came from. */
  function checked(input, where) {
    try {
      Tsubu.sentence(input);
    } catch (e) {
      fail(`${where}: ${String(e.message).replace(/^tsubu: /, "")}`);
    }
    return input;
  }

  function optionsOf(options, known, name) {
    if (options === undefined || options === null) return {};
    if (typeof options !== "object" || Array.isArray(options)) fail(`${name} options must be an object`);
    for (const key of Object.keys(options)) if (!known.includes(key)) fail(`${name} has no option ${JSON.stringify(key)}`);
    return options;
  }

  /* What a line break between these two characters becomes: a space, except between two wide
   * characters, where Japanese and Chinese put none. */
  function lineBreak(before, after) {
    return before && after && WIDE.test(before) && WIDE.test(after) ? "" : " ";
  }

  /* The lines of a cue's text as one. */
  function joinLines(lines) {
    return lines.reduce((text, line) => (text === "" || line === "" ? text + line : text + lineBreak(text[text.length - 1], line[0]) + line), "");
  }

  /* Parts with adjacent plain text joined, and spaces trimmed from the two ends when asked. */
  function tidy(parts, trim) {
    const out = [];
    for (const p of parts) {
      const last = out[out.length - 1];
      if (p.ruby === undefined && last && last.ruby === undefined) last.text += p.text;
      else out.push(p.ruby === undefined ? { text: p.text } : { text: p.text, ruby: p.ruby });
    }
    if (trim && out.length) {
      out[0].text = out[0].text.replace(/^\s+/, "");
      out[out.length - 1].text = out[out.length - 1].text.replace(/\s+$/, "");
    }
    return out.filter((p) => p.text !== "");
  }

  function textOf(parts) {
    return parts.map((p) => p.text).join("");
  }

  /**
   * TsubuImport.fromKuroshiro(html) -> the parts of one segment, [{ text, ruby? }].
   * `html` is what kuroshiro's convert() returns in mode "furigana": <ruby>漢<rp>(</rp><rt>かん</rt><rp>)</rp></ruby>,
   * with any delimiters, and with several base and reading pairs in one <ruby> as the romaji
   * target writes them. kuroshiro does not escape its text, so neither is anything unescaped
   * here. kuroshiro's output is not cut into segments: convert each segment's text on its own and
   * put its parts in that segment.
   */
  function fromKuroshiro(html) {
    need();
    if (typeof html !== "string") fail("fromKuroshiro needs kuroshiro's furigana HTML as a string");
    const parts = [];
    let inRuby = false, base = "", reading = null, inRp = false;
    const TOKEN = /<(\/?)(ruby|rt|rp)>|<[^>]*>|[^<]+|</g;
    for (let m = TOKEN.exec(html); m; m = TOKEN.exec(html)) {
      const [token, close, name] = m;
      if (name === undefined && token.startsWith("<") && token.length > 1)
        fail(`fromKuroshiro takes kuroshiro's furigana HTML, which has no ${token}; use mode "furigana"`);
      if (name === "ruby") {
        if (close ? !inRuby : inRuby) fail(`fromKuroshiro: unexpected ${token}`);
        if (close && base !== "") parts.push({ text: base });
        inRuby = !close;
        base = "";
      } else if (name === "rp") {
        if (!inRuby || inRp === !close) fail(`fromKuroshiro: unexpected ${token}`);
        inRp = !close;
      } else if (name === "rt") {
        if (!inRuby || (reading !== null) === !close) fail(`fromKuroshiro: unexpected ${token}`);
        if (close) {
          if (base === "") fail(`fromKuroshiro: the reading ${JSON.stringify(reading)} has no base text`);
          // an empty reading is no reading
          parts.push(reading === "" ? { text: base } : { text: base, ruby: reading });
          base = "";
          reading = null;
        } else reading = "";
      } else if (inRp) {
        // the parentheses for what cannot draw ruby: tsubu writes its own
      } else if (reading !== null) reading += token;
      else if (inRuby) base += token;
      else parts.push({ text: token });
    }
    if (inRuby) fail("fromKuroshiro: a <ruby> is not closed");
    const out = tidy(parts, false);
    if (!out.length) fail("fromKuroshiro: there is no text");
    checked({ segments: [{ parts: out }] }, "fromKuroshiro");
    return out;
  }

  /**
   * TsubuImport.fromCaptions(captions) -> the input for one sentence.
   * `captions` are Remotion's Caption objects, { text, startMs, endMs, ... }, for one sentence;
   * each becomes a segment with its own time. Spaces around a caption's text are dropped (Remotion
   * puts one before each word; tsubu's segments carry none), a caption of spaces alone is left
   * out, and one of punctuation alone becomes a punctuation segment, which has no time.
   */
  function fromCaptions(captions) {
    need();
    if (!Array.isArray(captions)) fail("fromCaptions needs an array of captions");
    const segments = [];
    captions.forEach((caption, i) => {
      if (!caption || typeof caption.text !== "string") fail(`caption ${i} needs \`text\``);
      if (!Number.isFinite(caption.startMs) || !Number.isFinite(caption.endMs)) fail(`caption ${i} needs startMs and endMs in milliseconds`);
      const text = caption.text.trim();
      if (text === "") return;
      segments.push(PUNCT_ONLY.test(text) ? { parts: [{ text }], kind: "punct" } : { parts: [{ text }], start: caption.startMs / 1000, end: caption.endMs / 1000 });
    });
    if (!segments.length) fail("fromCaptions: no caption has text");
    return checked({ segments }, "fromCaptions");
  }

  /* Text, a byte order mark dropped and line ends made \n, cut into blocks at blank lines. */
  function blocks(text) {
    return text
      .replace(/^\uFEFF/, "")
      .replace(/\r\n?/g, "\n")
      .split(/\n[ \t]*\n/)
      .map((block) => block.split("\n"))
      .filter((lines) => lines.some((line) => line.trim() !== ""));
  }

  /* A time as seconds from its parts, through whole milliseconds so 61.2 is 61.2. */
  function seconds(h, m, s, ms) {
    return (((Number(h) * 60 + Number(m)) * 60 + Number(s)) * 1000 + Number(ms)) / 1000;
  }

  // hh:mm:ss.ttt or mm:ss.ttt, as WebVTT writes times.
  const VTT_TIME = /^(?:(\d{2,}):)?([0-5]\d):([0-5]\d)\.(\d{3})$/;

  function vttTime(text) {
    const m = VTT_TIME.exec(text);
    return m ? seconds(m[1] || 0, m[2], m[3], m[4]) : null;
  }

  const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: "\u00A0", lrm: "\u200E", rlm: "\u200F" };

  function unescapeVTT(text) {
    return text.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (whole, name) => {
      if (name[0] === "#") {
        const code = name[1] === "x" || name[1] === "X" ? parseInt(name.slice(2), 16) : parseInt(name.slice(1), 10);
        return code > 0 && code <= 0x10ffff ? String.fromCodePoint(code) : whole;
      }
      return ENTITIES[name.toLowerCase()] ?? whole;
    });
  }

  /* A cue's text as a list of items: { stamp }, { open: punct } and { close } for a
   * <c.tsubu-seg> span, and { part } for text, with or without a reading. Other tags (<i>, <b>,
   * <u>, <v>, <lang>, <c> of other classes) are styling, and only their text is kept. */
  function cueItems(payload, where) {
    const items = [];
    const stack = [];
    // where in the stack the open <c.tsubu-seg> is, or -1
    let segmentAt = -1, base = "", reading = null;
    const reached = () => {
      if (base === "") fail(`${where}: the reading ${JSON.stringify(reading)} has no base text`);
      items.push({ part: reading === "" ? { text: base } : { text: base, ruby: reading } });
      base = "";
      reading = null;
    };
    const TOKEN = /<([^>]*)>|[^<]+/g;
    const text = (t) => {
      if (reading !== null) reading += t;
      else if (stack.includes("ruby")) base += t;
      else items.push({ part: { text: t } });
    };
    for (let m = TOKEN.exec(payload); m; m = TOKEN.exec(payload)) {
      if (m[1] === undefined) {
        text(unescapeVTT(m[0]));
        continue;
      }
      const tag = m[1].trim();
      const at = vttTime(tag);
      if (at !== null) {
        if (stack.includes("ruby")) fail(`${where}: a cue timestamp inside a <ruby>`);
        items.push({ stamp: at, tag });
        continue;
      }
      const closing = tag.startsWith("/");
      const [name, ...classes] = (closing ? tag.slice(1) : tag).split(/[\s]/)[0].split(".");
      if (closing) {
        if (name === "rt" && reading !== null) reached();
        if (name === "ruby") {
          // a reading's end tag may be left out at the end of its <ruby>
          if (reading !== null) reached();
          else if (base !== "") items.push({ part: { text: base } });
          base = "";
        }
        const open = stack.lastIndexOf(name);
        if (open !== -1) {
          stack.splice(open);
          if (open <= segmentAt) {
            items.push({ close: true });
            segmentAt = -1;
          }
        }
        continue;
      }
      if (name === "rt") {
        if (!stack.includes("ruby") || reading !== null) fail(`${where}: an <rt> outside a <ruby>, or inside another`);
        reading = "";
        continue;
      }
      if (name === "c" && classes.includes("tsubu-seg")) {
        if (segmentAt !== -1) fail(`${where}: a <c.tsubu-seg> inside another`);
        segmentAt = stack.length;
        items.push({ open: classes.includes("punct") });
      }
      stack.push(name);
    }
    if (reading !== null || base !== "") fail(`${where}: a <ruby> is not closed`);
    // Line breaks are settled on the text as shown, without its tags: in "<v Ann>雨が</v>" and
    // "降る" on the next line, が and 降 meet.
    const parts = items.filter((item) => item.part).map((item) => item.part);
    const flat = parts.map((p) => p.text).join("");
    let offset = 0;
    for (const p of parts) {
      const at = offset;
      offset += p.text.length;
      p.text = p.text.replace(/\n+/g, (breaks, i) => lineBreak(flat.slice(0, at + i).replace(/\n+$/, "").slice(-1), flat.slice(at + i + breaks.length).replace(/^\n+/, "")[0]));
      if (p.ruby !== undefined) p.ruby = p.ruby.replace(/\n+/g, " ");
    }
    return items;
  }

  /* One cue as the input for one sentence. Segments are its <c.tsubu-seg> spans, as toWebVTT
   * writes them; failing those, the text between its cue timestamps; failing those, the whole
   * cue is one segment. A cue timestamp says when the text after it begins, and WebVTT gives that
   * text no end: a segment lasts until the next cue timestamp or the next segment, whichever comes
   * first, and the last until the cue ends. A spoken segment with no timestamp of its own begins
   * with the one before it (toWebVTT writes none where two begin in the same millisecond). Without
   * cue timestamps the cue's span is the sentence's. */
  function cueInput(payload, start, end, where) {
    const items = cueItems(payload, where);
    const spans = items.some((item) => "open" in item);
    const stamps = items.some((item) => "stamp" in item);
    const segments = [];
    // when the next segment begins, and the spoken segment still waiting for its end
    let at = start, open = null, current = null;
    const stamp = (time, tag) => {
      // as in WebVTT: inside the cue, and later than the timestamps before it
      if (time < at || time > end) fail(`${where}: the cue timestamp <${tag}> is outside the cue or before an earlier one`);
      if (open) open.end = time;
      open = null;
      at = time;
    };
    const add = (parts, punct, trim) => {
      const tidied = tidy(parts, trim);
      if (!tidied.length) return;
      if (punct === undefined ? PUNCT_ONLY.test(textOf(tidied)) : punct) {
        segments.push({ parts: tidied, kind: "punct" });
        return;
      }
      if (open) open.end = at;
      open = { parts: tidied, start: at };
      segments.push(open);
    };
    if (spans) {
      for (const item of items) {
        if ("stamp" in item) {
          if (current) fail(`${where}: a cue timestamp inside a <c.tsubu-seg>`);
          stamp(item.stamp, item.tag);
        } else if ("open" in item) current = { parts: [], punct: item.open };
        else if ("close" in item) {
          add(current.parts, current.punct, false);
          current = null;
        } else if (current) current.parts.push(item.part);
        else if (item.part.text.trim() !== "") fail(`${where}: text outside the <c.tsubu-seg> spans, ${JSON.stringify(item.part.text)}`);
      }
    } else {
      let parts = [];
      for (const item of items) {
        if ("stamp" in item) {
          add(parts, undefined, true);
          parts = [];
          stamp(item.stamp, item.tag);
        } else parts.push(item.part);
      }
      add(parts, undefined, true);
    }
    if (open) open.end = end;
    if (!segments.length) fail(`${where}: the cue has no text`);
    if (!stamps) return checked({ start, end, segments: segments.map(({ start, end, ...s }) => s) }, where);
    // the cue's own span, where it reaches beyond the segments
    const spoken = segments.filter((s) => s.kind !== "punct");
    const wider = spoken.length && (spoken[0].start > start || spoken[spoken.length - 1].end < end);
    return checked(wider ? { start, end, segments } : { segments }, where);
  }

  /**
   * TsubuImport.fromWebVTT(text) -> an array with the input for one sentence per cue.
   * A part with a reading is <ruby>base<rt>reading</rt></ruby>. Segments and their times come
   * from <c.tsubu-seg> spans and cue timestamps, as toWebVTT writes them; a cue with neither is
   * one segment. A segment of punctuation alone (or one in <c.tsubu-seg.punct>) is punctuation.
   * Cue settings, identifiers, notes, styles and regions are not tsubu's and are passed over.
   */
  function fromWebVTT(text) {
    need();
    if (typeof text !== "string") fail("fromWebVTT needs the text of a WebVTT file");
    const all = blocks(text);
    if (!all.length || !/^WEBVTT(?:[ \t]|$)/.test(all[0][0])) fail('fromWebVTT: a WebVTT file begins with "WEBVTT"');
    const out = [];
    all.slice(1).forEach((lines) => {
      if (/^(NOTE|STYLE|REGION)(?:[ \t]|$)/.test(lines[0])) return;
      const where = `cue ${out.length + 1}`;
      const t = lines.findIndex((line) => line.includes("-->"));
      if (t === -1 || t > 1) fail(`${where} has no timing line ("start --> end")`);
      const m = /^\s*(\S+)[ \t]+-->[ \t]+(\S+)/.exec(lines[t]);
      const start = m && vttTime(m[1]), end = m && vttTime(m[2]);
      if (start === null || end === null) fail(`${where}: cannot read the times in ${JSON.stringify(lines[t])}`);
      out.push(cueInput(lines.slice(t + 1).join("\n"), start, end, where));
    });
    if (!out.length) fail("fromWebVTT: the file has no cues");
    return out;
  }

  // hh:mm:ss,ttt, as SubRip writes times (a full stop is read too: some files have one).
  const SRT_TIME = /^(\d{1,}):([0-5]\d):([0-5]\d)[,.](\d{3})$/;

  function srtTime(text) {
    const m = SRT_TIME.exec(text);
    return m ? seconds(m[1], m[2], m[3], m[4]) : null;
  }

  /* SubRip's text without the tags and override blocks players read: <i>, <b>, <u>, <font> and
   * {\an8}. tsubu writes none, and the text in between is kept. */
  function srtText(lines) {
    return joinLines(lines.map((line) => line.replace(/<\/?(?:i|b|u|s|font)(?:\s[^>]*)?>/gi, "").replace(/\{\\[^}]*\}/g, "").trim()));
  }

  /**
   * TsubuImport.fromSRT(text, options) -> the input for one sentence per cue, or for one sentence.
   *   options: { mode: "sentence" | "segments" (default "sentence") }
   * "sentence" reads each cue as a sentence of one segment, timed as a whole, and returns an
   * array. "segments" reads the whole file as one sentence, each cue a segment with its own time,
   * as toSRT writes it in that mode; a cue of punctuation alone is punctuation. SubRip has no ruby,
   * so readings toSRT wrote inline come back as text.
   */
  function fromSRT(text, options) {
    need();
    const opts = optionsOf(options, SRT_OPTIONS, "fromSRT");
    if (opts.mode !== undefined && !SRT_MODES.includes(opts.mode)) fail('options.mode must be "sentence" or "segments"');
    if (typeof text !== "string") fail("fromSRT needs the text of an SRT file");
    const cues = blocks(text).map((lines, i) => {
      const where = `cue ${i + 1}`;
      const t = /^\s*\d+\s*$/.test(lines[0]) ? 1 : 0;
      const m = /^\s*(\S+)[ \t]+-->[ \t]+(\S+)/.exec(lines[t] || "");
      const start = m && srtTime(m[1]), end = m && srtTime(m[2]);
      if (start === null || end === null) fail(`${where} has no timing line ("00:00:01,000 --> 00:00:02,000")`);
      const body = srtText(lines.slice(t + 1));
      if (body === "") fail(`${where} has no text`);
      return { where, start, end, text: body };
    });
    if (!cues.length) fail("fromSRT: the file has no cues");
    if (opts.mode !== "segments") return cues.map((cue) => checked({ start: cue.start, end: cue.end, segments: [{ parts: [{ text: cue.text }] }] }, cue.where));
    const segments = cues.map((cue) => (PUNCT_ONLY.test(cue.text) ? { parts: [{ text: cue.text }], kind: "punct" } : { parts: [{ text: cue.text }], start: cue.start, end: cue.end }));
    return checked({ segments }, "fromSRT");
  }

  return Object.freeze({ fromKuroshiro, fromCaptions, fromWebVTT, fromSRT });
});
