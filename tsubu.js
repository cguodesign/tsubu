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
 *
 * Colours come from tsubu.css: custom properties, and theme presets selected with
 * data-tsubu-theme. checkContrast() measures them in the browser against the thresholds in
 * CONTRAST, so a theme can be verified rather than trusted.
 */
(function (global, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else global.Tsubu = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const VERSION = "0.1.0";
  const STATES = Object.freeze(["future", "current", "past"]);
  const THEMES = Object.freeze(["light", "dark", "media"]);
  const SPEAKERS = Object.freeze(["a", "b"]);

  /* The smallest contrast ratio each layer must have against what is behind it, after WCAG 2.2:
   * text and furigana as normal-size text (1.4.3, AA), the underline and the highlight as
   * graphics needed to follow the reading (1.4.11). Furigana are small, so the large-text
   * allowance never applies to them; it is not used for the text either, whose size tsubu does
   * not know. */
  const CONTRAST = Object.freeze({ text: 4.5, ruby: 4.5, underline: 3, highlight: 3 });
  const NAME = /^[a-z][a-z0-9-]*$/;

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

  function renderHTML(sentence, ruby, look) {
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
    const theme = look.theme ? ` data-tsubu-theme="${look.theme}"` : "";
    const speaker = look.speaker ? ` data-speaker="${look.speaker}"` : "";
    return `<span class="tsubu" lang="${escapeHTML(sentence.lang)}" data-timing="${sentence.timing}" data-ruby="${ruby ? "on" : "off"}"${theme}${speaker}>${joined}</span>`;
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
   *   options: { ruby: true | false (default true), theme?: name, speaker?: name }
   */
  function sentence(input, options) {
    const opts = options || {};
    if (opts.ruby !== undefined && typeof opts.ruby !== "boolean") fail("options.ruby must be true or false");
    for (const key of ["theme", "speaker"])
      if (opts[key] !== undefined && (typeof opts[key] !== "string" || !NAME.test(opts[key])))
        fail(`options.${key} must be a name in lower case, such as ${JSON.stringify(key === "theme" ? THEMES[0] : SPEAKERS[0])}`);
    const normalised = normalise(input);
    return Object.freeze({
      html: renderHTML(normalised, opts.ruby !== false, { theme: opts.theme, speaker: opts.speaker }),
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

  /* Colours as [r, g, b, a], channels 0 to 255 and alpha 0 to 1. Accepts what a browser's
   * getComputedStyle returns for colours (rgb(), rgba(), color(srgb ...)) and hex. */
  function parseColour(text) {
    const value = String(text).trim().toLowerCase();
    let m = /^#([0-9a-f]{3,8})$/.exec(value);
    if (m && [3, 4, 6, 8].includes(m[1].length)) {
      const h = m[1].length < 6 ? m[1].replace(/./g, "$&$&") : m[1];
      const n = [0, 2, 4, 6].map((i) => (i < h.length ? parseInt(h.slice(i, i + 2), 16) : 255));
      return [n[0], n[1], n[2], n[3] / 255];
    }
    if (value === "transparent") return [0, 0, 0, 0];
    const channel = (part, scale) => (part.endsWith("%") ? (parseFloat(part) / 100) * scale : parseFloat(part));
    m = /^rgba?\(([^)]*)\)$/.exec(value);
    if (m) {
      const parts = m[1].split(/[\s,/]+/).filter(Boolean);
      if (parts.length === 3 || parts.length === 4) {
        const c = [channel(parts[0], 255), channel(parts[1], 255), channel(parts[2], 255), parts[3] === undefined ? 1 : channel(parts[3], 1)];
        if (c.every(Number.isFinite)) return c;
      }
    }
    m = /^color\(srgb\s+([^)]*)\)$/.exec(value);
    if (m) {
      const parts = m[1].split(/[\s/]+/).filter(Boolean);
      if (parts.length === 3 || parts.length === 4) {
        const c = [channel(parts[0], 1) * 255, channel(parts[1], 1) * 255, channel(parts[2], 1) * 255, parts[3] === undefined ? 1 : channel(parts[3], 1)];
        if (c.every(Number.isFinite)) return c;
      }
    }
    fail(`cannot read the colour ${JSON.stringify(String(text))}: use hex, rgb() or rgba()`);
  }

  /* `top` painted over `below`, which must be opaque. */
  function over(top, below) {
    const a = top[3];
    return [0, 1, 2].map((i) => top[i] * a + below[i] * (1 - a)).concat(1);
  }

  function luminance(c) {
    const [r, g, b] = c.slice(0, 3).map((v) => {
      const s = v / 255;
      return s <= 0.04045 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  function ratioOf(a, b) {
    const la = luminance(a), lb = luminance(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }

  /* The WCAG contrast ratio, 1 to 21, of a foreground colour on a background colour. A
   * translucent foreground is painted over the background first; a translucent background is
   * painted over `backdrop` (default white). */
  function contrast(foreground, background, backdrop) {
    const base = over(parseColour(backdrop === undefined ? "#ffffff" : backdrop), [255, 255, 255, 1]);
    const behind = over(parseColour(background), base);
    return ratioOf(over(parseColour(foreground), behind), behind);
  }

  /* The colours a sentence is checked against: options.backdrop, else the theme's
   * --tsubu-backdrop, else the background colours of the root's ancestors painted over white. */
  function backdropsOf(root, given) {
    const read = (value) => {
      const list = Array.isArray(value) ? value : String(value).match(/#[0-9a-f]+|rgba?\([^)]*\)|color\([^)]*\)|\bany\b|\btransparent\b/gi) || [];
      return list.flatMap((c) => (String(c).trim().toLowerCase() === "any" ? ["#000000", "#ffffff"] : [String(c)]));
    };
    if (given !== undefined) {
      const list = read(given);
      if (!list.length) fail("options.backdrop must be a colour, a list of colours or \"any\"");
      return list;
    }
    const declared = read(getComputedStyle(root).getPropertyValue("--tsubu-backdrop"));
    if (declared.length) return declared;
    const layers = [];
    for (let el = root.parentElement; el; el = el.parentElement) {
      const colour = parseColour(getComputedStyle(el).backgroundColor);
      layers.push(colour);
      if (colour[3] === 1) break;
    }
    const painted = layers.reverse().reduce((below, top) => over(top, below), [255, 255, 255, 1]);
    return [`rgb(${painted.slice(0, 3).map((v) => v.toFixed(3)).join(", ")})`];
  }

  const LAYERS = Object.freeze(["text", "ruby", "underline", "highlight"]);

  /**
   * Tsubu.checkContrast(root, options) -> { ok, checks, failures }
   * Measures the colours the browser computes for a drawn sentence in every state ("static",
   * before any apply and with timing "none", then each of STATES), for each layer (text,
   * furigana, underline, and the highlight against what surrounds it), against each backdrop.
   * A layer is measured against the highlight when the highlight covers its middle: furigana sit
   * above the highlighted line, so they are measured against the plate and the backdrop.
   *   options: { backdrop?: colour | [colours] | "any", thresholds?: { text, ruby, underline, highlight } }
   * It works on a copy of the sentence, which it removes again: the page is left as it was.
   */
  function checkContrast(root, options) {
    if (!root || !root.classList || !root.classList.contains("tsubu")) fail('checkContrast needs the element with class "tsubu"');
    if (typeof getComputedStyle !== "function") fail("checkContrast measures a page, so it needs a browser");
    const opts = options || {};
    const thresholds = Object.assign({}, CONTRAST, opts.thresholds || {});
    for (const layer of LAYERS)
      if (!isTime(thresholds[layer]) || thresholds[layer] < 1 || thresholds[layer] > 21) fail(`thresholds.${layer} must be a ratio from 1 to 21`);
    const backdrops = backdropsOf(root, opts.backdrop);

    const copy = root.cloneNode(true);
    copy.removeAttribute("id");
    copy.setAttribute("aria-hidden", "true");
    copy.style.setProperty("position", "absolute");
    copy.style.setProperty("left", "-100000px");
    copy.style.setProperty("top", "0");
    root.after(copy);
    const seen = new Map();
    try {
      const segments = [...copy.querySelectorAll(":scope > .tsubu-seg")];
      for (const state of ["static"].concat(STATES)) {
        for (const el of [copy, ...segments]) {
          if (state === "static") el.removeAttribute("data-state");
          else el.setAttribute("data-state", state);
        }
        const plate = parseColour(getComputedStyle(copy, "::before").backgroundColor);
        for (const backdrop of backdrops) {
          const base = over(plate, over(parseColour(backdrop), [255, 255, 255, 1]));
          for (const el of segments) {
            const style = getComputedStyle(el);
            const highlight = parseColour(style.backgroundColor);
            const behind = over(highlight, base);
            // The highlight is the segment's background and its box-shadow: it covers the line of
            // text and reaches `spread` past it. A layer is on the highlight when the band covers
            // its middle (and checked against both when the band covers only part of it); a
            // layer whose middle lies outside the band, like the furigana, whose box the spread
            // just grazes, is on what is behind the highlight.
            const box = el.getBoundingClientRect();
            const spread = highlight[3] > 0 ? parseFloat((/(-?[\d.]+)px\s*$/.exec(style.boxShadow) || [])[1]) || 0 : 0;
            const backgroundsFor = (top, bottom) => {
              if (highlight[3] === 0) return [base];
              const from = box.top - spread, to = box.bottom + spread, middle = (top + bottom) / 2;
              if (middle < from || middle > to) return [base];
              return top >= from && bottom <= to ? [behind] : [behind, base];
            };
            const layers = [["text", style.color, behind]];
            const rt = el.querySelector("rt");
            if (rt) {
              const r = rt.getBoundingClientRect();
              for (const under of backgroundsFor(r.top, r.bottom)) layers.push(["ruby", getComputedStyle(rt).color, under]);
            }
            const after = getComputedStyle(el, "::after");
            if (after.content !== "none" && after.borderBottomStyle !== "none") {
              const bottom = box.bottom - parseFloat(after.bottom);
              for (const under of backgroundsFor(bottom - parseFloat(after.borderBottomWidth), bottom))
                layers.push(["underline", after.borderBottomColor, under]);
            }
            if (highlight[3] > 0) layers.push(["highlight", style.backgroundColor, base]);
            for (const [layer, colour, under] of layers) {
              const fg = layer === "highlight" ? behind : over(parseColour(colour), under);
              const bg = layer === "highlight" ? base : under;
              const ratio = ratioOf(fg, bg);
              const key = [state, layer, colour, bg.join(), backdrop].join("|");
              if (!seen.has(key)) {
                const hex = (c) => "#" + c.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, "0")).join("");
                seen.set(key, { state, layer, foreground: hex(fg), background: hex(bg), backdrop: String(backdrop),
                  ratio: Math.round(ratio * 100) / 100, minimum: thresholds[layer], ok: ratio >= thresholds[layer] });
              }
            }
          }
        }
      }
    } finally {
      copy.remove();
    }
    const checks = [...seen.values()];
    const failures = checks.filter((c) => !c.ok);
    return { ok: failures.length === 0, checks, failures };
  }

  return Object.freeze({ version: VERSION, sentence, setRuby, contrast, checkContrast, STATES, THEMES, SPEAKERS, CONTRAST });
});
