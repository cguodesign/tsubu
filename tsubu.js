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
 * text or adds and removes nodes, so a change of highlight cannot move a character. With a
 * maximum number of lines it also hides the segments that are not on the page being read; which
 * page that is depends on t and the sentence's own layout, never on earlier calls. The input
 * and output contract is described in docs/guide.md and on the website's API page.
 *
 * Colours come from tsubu.css: custom properties, and theme presets selected with
 * data-tsubu-theme. checkContrast() measures them in the browser against the thresholds in
 * CONTRAST, so a theme can be verified rather than trusted.
 *
 * Vertical writing (data-tsubu-writing="vertical") is drawn by tsubu.css; the script marks short
 * runs of half-width characters to be set upright, and pages and checks contrast along the axis
 * the layout actually has.
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
  /* What can be drawn on each side of the text: the parts' furigana, the segments' romaji, or
   * nothing; and the two sides, over (above in horizontal text, at the right in vertical text) and
   * under (below, at the left). */
  const ANNOTATIONS = Object.freeze(["ruby", "romaji", "none"]);
  const SIDES = Object.freeze(["over", "under"]);

  /* The smallest contrast ratio each layer must have against what is behind it, after WCAG 2.2:
   * text and furigana as normal-size text (1.4.3, AA), the underline and the highlight as
   * graphics needed to follow the reading (1.4.11). Furigana are small, so the large-text
   * allowance never applies to them; it is not used for the text either, whose size tsubu does
   * not know. */
  const CONTRAST = Object.freeze({ text: 4.5, ruby: 4.5, underline: 3, highlight: 3 });
  const NAME = /^[a-z][a-z0-9-]*$/;

  /* The motion presets, as a catalogue that templates and agents can read and choose from. Each
   * is drawn by tsubu.css from the state apply() writes, so every frame is still a function of t
   * (and of which segments the caller has revealed). "Unheard" means not yet current or past: in
   * the future, or in a sentence that has not been applied at all. */
  const MOTIONS = deepFreeze([
    { name: "appear", purpose: "Segments appear as they are spoken; nothing unheard is shown, not even its underline.",
      needs: "segments", without: "With timing \"sentence\" the whole sentence appears when it starts. Without times nothing appears until the caller reveals it.",
      parameters: [], reducedMotion: "Unchanged: it is a change of state, not movement.", revealable: true },
    { name: "mask", purpose: "Unheard segments are blanks: their text and readings are not drawn, their underline is, so the length of what is to come shows. For listening and fill-in exercises.",
      needs: "segments", without: "With timing \"sentence\" the whole sentence is unmasked when it starts. Without times every segment stays a blank until the caller reveals it.",
      parameters: [], reducedMotion: "Unchanged: it is a change of state, not movement.", revealable: true },
    { name: "blur", purpose: "Unheard segments are blurred: their shape shows, their words do not.",
      needs: "segments", without: "With timing \"sentence\" the whole sentence sharpens when it starts. Without times every segment stays blurred until the caller reveals it.",
      parameters: [{ property: "--tsubu-blur", default: "0.15em", min: "0.05em", max: "0.4em", meaning: "blur radius" }],
      reducedMotion: "Unchanged: it is a change of state, not movement.", revealable: true },
    { name: "underline-draw", purpose: "The underline of the segment being spoken draws itself in over the segment's time; unheard segments have none yet.",
      needs: "segments", without: "With timing \"sentence\" the underlines of all segments draw in together over the sentence's time.",
      parameters: [], reducedMotion: "The underline of the segment being spoken is drawn whole at once.", revealable: true },
  ]);

  function deepFreeze(value) {
    if (value && typeof value === "object") {
      Object.values(value).forEach(deepFreeze);
      Object.freeze(value);
    }
    return value;
  }

  function motionNames(motion) {
    if (motion === undefined) return [];
    const list = typeof motion === "string" ? motion.split(/\s+/).filter(Boolean) : motion;
    if (!Array.isArray(list)) fail("options.motion must be a name, a space-separated list of names or an array of names");
    const known = MOTIONS.map((m) => m.name);
    for (const name of list)
      if (!known.includes(name)) fail(`options.motion: unknown preset ${JSON.stringify(name)}; the presets are ${known.join(", ")}`);
    return [...new Set(list)];
  }

  /* Japanese line-breaking rules (kinsoku), as in CSS `line-break: strict`: these may not begin
   * a line (closing brackets and punctuation, the long-vowel mark, small kana, iteration marks,
   * middle dots and colons, wave dashes and hyphens) ... */
  const NO_START = /^[、。，．,.)\]}）〕］｝〉》」』】〙〗〟’”｠»ー〜～゠‐–・：；:;？！?!‼⁇⁈⁉ゝゞヽヾ々〻ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶㇰ-ㇿｧ-ｯｰ]/u;
  /* ... and these may not end one (opening brackets). */
  const NO_END = /[(\[{（〔［｛〈《「『【〘〖〝‘“｟«]$/u;

  const WRITING = Object.freeze(["horizontal", "vertical"]);
  /* A run of half-width letters, digits and marks (ASCII other than space and brackets). In
   * vertical text such a run lies on its side (text-orientation: mixed); a short one is set
   * upright across the column instead, with text-combine-upright, as in 10月. Brackets are left
   * out so that ASCII parentheses still turn with the column around what they enclose. */
  const HALF_WIDTH_RUN = /([!-'*-;=?-Z\\^-z|~]+)/;
  const UPRIGHT_MAX = 4;

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
      // An id and tags are the caller's: an id to find the segment by, tags to style it by
      // (data-tags="new-word"). tsubu gives them no meaning.
      if (segment.id !== undefined && (typeof segment.id !== "string" || segment.id === "")) fail(`${where}: \`id\` must be a non-empty string`);
      if (segment.tags !== undefined && (!Array.isArray(segment.tags) || !segment.tags.every((tag) => typeof tag === "string" && NAME.test(tag))))
        fail(`${where}: \`tags\` must be an array of names in lower case, such as "new-word"`);
      // The romanised reading of the whole segment, the unit that is read and never split across
      // lines. It is the caller's: particles and long vowels make it more than a mapping of kana,
      // so tsubu never makes one.
      if (segment.romaji !== undefined) {
        if (punct) fail(`${where}: punctuation carries no romaji`);
        if (typeof segment.romaji !== "string" || segment.romaji === "") fail(`${where}: \`romaji\` must be a non-empty string`);
      }
      const made = { parts, punct };
      if (timed) Object.assign(made, { start: segment.start, end: segment.end });
      if (segment.id !== undefined) made.id = segment.id;
      if (segment.tags !== undefined && segment.tags.length) made.tags = [...new Set(segment.tags)];
      if (segment.romaji !== undefined) made.romaji = segment.romaji;
      return made;
    });
    const ids = segments.filter((s) => "id" in s).map((s) => s.id);
    const twice = ids.find((id, i) => ids.indexOf(id) !== i);
    if (twice !== undefined) fail(`two segments have the id ${JSON.stringify(twice)}`);
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

  /* A part's text as HTML, with each run of half-width characters no longer than `upright` in a
   * span that vertical text sets upright (tsubu.css). In horizontal text the span has no style,
   * so it changes nothing there. */
  function textHTML(text, upright) {
    if (!upright) return escapeHTML(text);
    return text
      .split(HALF_WIDTH_RUN)
      .map((piece, i) => (i % 2 === 1 && piece.length <= upright ? `<span class="tsubu-upright">${escapeHTML(piece)}</span>` : escapeHTML(piece)))
      .join("");
  }

  /* The attributes apply() writes for a state, as HTML (in the order Chromium serialises them,
   * which writes the style attribute last; the order carries no meaning). */
  function stateAttributes(state, progress, current, revealed) {
    const style = progress === null ? "" : ` style="--tsubu-progress: ${String(progress)};"`;
    return ` data-state="${state}"${current ? ' aria-current="true"' : ""}${revealed ? ' data-revealed=""' : ""}${style}`;
  }

  /* The sentence as HTML; with `at` (a state from stateOf), as it is after apply() at that t, and
   * with `revealed` (indexes) as it is after setRevealed(). */
  function renderHTML(sentence, shown, look, at, revealed) {
    // With announceRuby off, screen readers read the sentence once, without each reading after
    // its base.
    const hidden = look.announceRuby === false ? ' aria-hidden="true"' : "";
    // Each reading is wrapped in <rp> parentheses, which a browser that draws ruby does not show
    // (display: none, in its own stylesheet and in tsubu.css) and anything that cannot draw it (a
    // reader view, a feed reader, a text browser) shows as 本（ほん）. The parentheses are
    // full-width, as the text is Japanese or Chinese.
    const open = `<rp${hidden}>（</rp><rt${hidden}>`, close = `</rt><rp${hidden}>）</rp>`;
    // Short runs are marked unless the sentence is horizontal by its own option: without one, a
    // vertical ancestor can still make it vertical, as a theme set on an ancestor applies.
    const upright = look.writing === "horizontal" ? 0 : look.combineUpright;
    // A layer that is on neither side is not written at all, so it takes no room and is not read.
    const drawn = (layer) => look.over === layer || look.under === layer;
    const segments = sentence.segments.map((segment, i) => {
      let inner = segment.parts
        .map((p) => {
          const base = textHTML(p.text, upright);
          return p.ruby === undefined || !drawn("ruby") ? base : `<ruby>${base}${open}${escapeHTML(p.ruby)}${close}</ruby>`;
        })
        .join("");
      // The romaji annotate the whole segment: a ruby around its parts, furigana and all, whose
      // reading is the romaji. Nested ruby is drawn by every engine tsubu is tested in, a reading
      // wider than its base widens the segment as a wide furigana does, and the lines make room
      // for it, as they do for furigana. The ruby sits in a box of its own (.tsubu-stack, an
      // inline-block; see the stylesheet). The romaji are not set upright in vertical text: they
      // lie on their side, as other Latin text does there.
      if (segment.romaji !== undefined && drawn("romaji"))
        inner = `<span class="tsubu-stack"><ruby class="tsubu-romaji">${inner}${open}${escapeHTML(segment.romaji)}${close}</ruby></span>`;
      const kind = segment.punct ? ' data-kind="punct"' : "";
      const id = segment.id === undefined ? "" : ` data-id="${escapeHTML(segment.id)}"`;
      const tags = segment.tags ? ` data-tags="${segment.tags.join(" ")}"` : "";
      const shown = Boolean(revealed && revealed.includes(i));
      const state = at ? stateAttributes(at.segments[i].state, at.segments[i].progress, i === at.current, shown) : shown ? ' data-revealed=""' : "";
      return `<span class="tsubu-seg" data-index="${i}"${kind}${id}${tags}${state}>${inner}</span>`;
    });
    // A line may break between two segments unless the break would put a closing mark, the
    // long-vowel mark or a small kana at the start of a line, or an opening bracket at the end of
    // one. Segments that may not be parted are put in one nowrap unit, and a <wbr> between units
    // gives the line its place to break (Chromium will not break before a <ruby> without one).
    // tsubu applies these rules itself rather than leaving them to the browser's own: Chromium
    // treats the underline, an absolutely positioned box at the end of each segment, as a place
    // to break, and does not apply its line-breaking rules there.
    const texts = sentence.segments.map((segment) => segment.parts.map((p) => p.text).join(""));
    const units = [];
    segments.forEach((html, i) => {
      if (i > 0 && (NO_START.test(texts[i]) || NO_END.test(texts[i - 1]))) units[units.length - 1] += html;
      else units.push(html);
    });
    const joined = units.map((html) => `<span class="tsubu-unit">${html}</span>`).join("<wbr>");
    const theme = look.theme ? ` data-tsubu-theme="${look.theme}"` : "";
    const speaker = look.speaker ? ` data-speaker="${look.speaker}"` : "";
    const motion = look.motion.length ? ` data-tsubu-motion="${look.motion.join(" ")}"` : "";
    const writing = look.writing ? ` data-tsubu-writing="${look.writing}"` : "";
    const state = at ? stateAttributes(at.state, at.progress, at.timing === "sentence" && at.state === "current") : "";
    // data-ruby shows or hides the over side, whatever is drawn there (its name is from when
    // furigana were the only layer), and data-under the under side. Which layer is on which side
    // is written only where it differs from furigana over and nothing under.
    const layers = (look.over === "ruby" ? "" : ` data-over-layer="${look.over}"`) +
      (look.under === "none" ? "" : ` data-under-layer="${look.under}" data-under="${shown.under ? "on" : "off"}"`);
    return `<span class="tsubu" lang="${escapeHTML(sentence.lang)}" data-timing="${sentence.timing}" data-ruby="${shown.over ? "on" : "off"}"${layers}${theme}${speaker}${motion}${writing}${state}>${joined}</span>`;
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
    const elements = root.querySelectorAll(":scope > .tsubu-unit > .tsubu-seg");
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

  /* The lines per page from the root's --tsubu-page-lines (set from --tsubu-max-lines, and by
   * the fluid steps), or null for no limit. */
  function linesPerPage(root) {
    if (typeof getComputedStyle !== "function") return null;
    const raw = getComputedStyle(root).getPropertyValue("--tsubu-page-lines").trim();
    if (raw === "" || raw === "none") return null;
    const n = Number(raw);
    if (!Number.isInteger(n) || n < 1) fail(`--tsubu-max-lines must be a whole number of lines or none, not ${JSON.stringify(raw)}`);
    return n;
  }

  /* The axis along which the lines of a drawn sentence follow one another, read from the layout
   * rather than from an attribute, so a writing mode set on an ancestor counts too: down the
   * page in horizontal text, and from right to left in vertical-rl text, whose lines are columns
   * (left to right in vertical-lr, which tsubu does not set but measures correctly).
   *   start(rect)  where a box lies along that axis, growing from one line to the next; in
   *                vertical text its left edge, the side away from the furigana, which a vertical
   *                segment's box takes in (see the stylesheet);
   *   span(rect)   the box's extent across its line, in page coordinates, as [low, high];
   *   side         the physical side of a segment's line, its block-end side. */
  function blockAxis(root) {
    const mode = getComputedStyle(root).writingMode || "horizontal-tb";
    if (mode === "horizontal-tb") return { vertical: false, start: (r) => r.top, span: (r) => [r.top, r.bottom], side: "bottom" };
    const rl = !/-lr$/.test(mode);
    return { vertical: true, start: (r) => (rl ? -r.left : r.left), span: (r) => [r.left, r.right], side: rl ? "left" : "right" };
  }

  /* Which line each element lies on, from the layout: segments are nowrap, so each lies on one
   * line, and one further along the block axis by half a line or more (lower, or in vertical text
   * further left) begins a new one. Measured as laid out greedily, the way pages are counted,
   * unless `asDrawn`, which takes the layout as it is. */
  function lineIndexes(root, elements, asDrawn) {
    if (!asDrawn) root.setAttribute("data-measuring", "");
    const axis = blockAxis(root);
    const starts = Array.from(elements, (el) => axis.start(el.getBoundingClientRect()));
    if (!asDrawn) root.removeAttribute("data-measuring");
    const half = (parseFloat(getComputedStyle(root).fontSize) || 16) / 2;
    let line = 0, lineStart = starts[0];
    return starts.map((start) => {
      if (start >= lineStart + half) {
        line++;
        lineStart = start;
      }
      return line;
    });
  }


  /* With a maximum number of lines, shows only the page that holds the segment being spoken:
   * between two segments, the page of the one just spoken; before the first, the first page.
   * The lines come from the layout itself: the sentence is laid out whole and greedily, segment
   * by segment, and every `lines` lines make a page. Which page is shown depends on t and that
   * layout alone. A sentence without times for its segments is never paged, because which part
   * of it is being read is not known. In vertical text the lines are columns, read from right to
   * left. A page that balancing would put on more lines than a page holds (WebKit 26 can, though
   * balancing should never add a line) is laid out greedily instead, marked data-greedy. */
  function applyPages(root, elements, s) {
    const lines = linesPerPage(root);
    for (const el of elements) el.removeAttribute("data-off-page");
    root.removeAttribute("data-page");
    root.removeAttribute("data-pages");
    root.removeAttribute("data-greedy");
    if (lines === null || s.timing !== "segments") return { page: null, pages: null };

    const pageOf = lineIndexes(root, elements).map((line) => Math.floor(line / lines));
    const pages = pageOf[pageOf.length - 1] + 1;

    let at = s.current;
    if (at === null) {
      at = 0;
      s.segments.forEach((entry, i) => {
        if (entry.state === "past") at = i;
      });
    }
    const page = pageOf[at];
    elements.forEach((el, i) => {
      if (pageOf[i] !== page) el.setAttribute("data-off-page", "");
    });
    root.setAttribute("data-page", String(page));
    root.setAttribute("data-pages", String(pages));
    const shown = Array.from(elements).filter((el, i) => pageOf[i] === page);
    const drawn = lineIndexes(root, shown, true);
    if (drawn[drawn.length - 1] + 1 > lines) root.setAttribute("data-greedy", "");
    return { page, pages };
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
    return Object.assign(s, applyPages(root, elements, s));
  }

  /**
   * Tsubu.sentence(input, options) -> { html, timing, stateAt(t), htmlAt(t), apply(root, t), span(i), find(id) }
   *   input:   { lang?, start?, end?, segments: [{ parts: [{ text, ruby? }], romaji?, start?, end?, kind?, id?, tags? }] }
   *   options: { ruby: true | false (default true), announceRuby: true | false (default true),
   *              over: "ruby" | "romaji" | "none" (default "ruby"), under: the same (default "none"),
   *              theme?: name, speaker?: name, motion?: names from MOTIONS,
   *              writing?: "horizontal" | "vertical", combineUpright: 0 to 4 (default 2) }
   * `ruby` says whether the over side starts out shown; the under side always starts out shown.
   */
  function sentence(input, options) {
    const opts = options || {};
    for (const key of ["ruby", "announceRuby"])
      if (opts[key] !== undefined && typeof opts[key] !== "boolean") fail(`options.${key} must be true or false`);
    for (const key of ["theme", "speaker"])
      if (opts[key] !== undefined && (typeof opts[key] !== "string" || !NAME.test(opts[key])))
        fail(`options.${key} must be a name in lower case, such as ${JSON.stringify(key === "theme" ? THEMES[0] : SPEAKERS[0])}`);
    if (opts.writing !== undefined && !WRITING.includes(opts.writing)) fail('options.writing must be "horizontal" or "vertical"');
    for (const key of SIDES)
      if (opts[key] !== undefined && !ANNOTATIONS.includes(opts[key])) fail(`options.${key} must be "ruby", "romaji" or "none"`);
    const over = opts.over === undefined ? "ruby" : opts.over, under = opts.under === undefined ? "none" : opts.under;
    if (over === under && over !== "none") fail(`options.over and options.under are both ${JSON.stringify(over)}: a layer can be drawn on one side only`);
    const upright = opts.combineUpright === undefined ? 2 : opts.combineUpright;
    if (!Number.isInteger(upright) || upright < 0 || upright > UPRIGHT_MAX)
      fail(`options.combineUpright must be a whole number of characters from 0 to ${UPRIGHT_MAX}`);
    const normalised = normalise(input);
    const shown = { over: opts.ruby !== false, under: true };
    const look = { theme: opts.theme, speaker: opts.speaker, announceRuby: opts.announceRuby, motion: motionNames(opts.motion),
      writing: opts.writing, combineUpright: upright, over, under };
    return Object.freeze({
      html: renderHTML(normalised, shown, look),
      timing: normalised.timing,
      stateAt: (t) => stateOf(normalised, t),
      // The frame at t as HTML, without a page: what `html` becomes after apply(root, t) (and
      // setRevealed(root, revealed)), for server-side rendering and renderers that take HTML.
      // Paging needs the layout, so it is not done here.
      htmlAt: (t, at) => renderHTML(normalised, shown, look, stateOf(normalised, t), revealedIndexes((at || {}).revealed, normalised.segments.length)),
      apply: (root, t) => applyState(root, normalised, t),
      // A segment's own time, { start, end }, to seek the caller's audio to when it is tapped; null
      // for punctuation and for a sentence without times for its segments (nothing is estimated).
      span: (i) => spanOf(normalised, i),
      // The index of the segment with this id, or null.
      find: (id) => {
        const i = normalised.segments.findIndex((s) => s.id === id);
        return i === -1 ? null : i;
      },
    });
  }

  function spanOf(sentence, i) {
    if (!Number.isInteger(i) || i < 0 || i >= sentence.segments.length) fail(`span needs a segment index from 0 to ${sentence.segments.length - 1}, not ${i}`);
    const segment = sentence.segments[i];
    return "start" in segment ? { start: segment.start, end: segment.end } : null;
  }

  /* Which segments a caller's `which` names: "all", "none", or an array of segment indexes. */
  function revealedIndexes(which, count) {
    if (which === undefined || which === "none") return [];
    if (which === "all") return Array.from({ length: count }, (_, i) => i);
    if (!Array.isArray(which) || !which.every((i) => Number.isInteger(i) && i >= 0 && i < count))
      fail(`revealed segments must be "all", "none" or an array of segment indexes from 0 to ${count - 1}`);
    return [...new Set(which)].sort((a, b) => a - b);
  }

  /* Reveals segments that a motion preset hides while they are unheard (appear, mask, blur,
   * underline-draw), whatever t is: for a word the learner got right, a tap, any event of the
   * caller's. It replaces the previous set; "none" hides them again. Only attributes change, so
   * nothing moves. */
  function setRevealed(root, which) {
    if (!root || !root.classList || !root.classList.contains("tsubu")) fail('setRevealed needs the element with class "tsubu"');
    const elements = root.querySelectorAll(":scope > .tsubu-unit > .tsubu-seg");
    const shown = revealedIndexes(which, elements.length);
    elements.forEach((el, i) => {
      if (shown.includes(i)) el.setAttribute("data-revealed", "");
      else el.removeAttribute("data-revealed");
    });
    return shown;
  }

  /* The index of the segment a node (an event's target, say) lies in, or null: for click and
   * tap handlers. */
  function segmentOf(node) {
    const element = node && node.nodeType === 3 ? node.parentElement : node;
    const segment = element && typeof element.closest === "function" ? element.closest(".tsubu-seg") : null;
    return segment ? Number(segment.getAttribute("data-index")) : null;
  }

  /* Shows or hides one side's annotations of a drawn sentence: "over" (the furigana, unless
   * options.over named another layer) or "under". Each <rt> keeps its place in the layout either
   * way, so no character moves. */
  function setAnnotation(root, side, on) {
    if (!root || !root.classList || !root.classList.contains("tsubu")) fail('setAnnotation needs the element with class "tsubu"');
    if (!SIDES.includes(side)) fail('setAnnotation: the side must be "over" or "under"');
    root.setAttribute(side === "over" ? "data-ruby" : "data-under", on ? "on" : "off");
  }

  /* The over side, by its old name. */
  function setRuby(root, on) {
    if (!root || !root.classList || !root.classList.contains("tsubu")) fail('setRuby needs the element with class "tsubu"');
    setAnnotation(root, "over", on);
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
  /* A segment's readings: the furigana of its parts, and its romaji (see renderHTML). */
  const FURIGANA = "ruby:not(.tsubu-romaji) > rt";
  const ROMAJI = ".tsubu-romaji > rt";

  /* The colour of a highlight's band: the stylesheet paints it as a one-colour gradient (its first
   * colour, read up to the first comma outside parentheses), or, should a theme set a background
   * colour on the band instead, that. */
  function bandColourOf(style) {
    const image = style.backgroundImage;
    const open = image.indexOf("(");
    if (open < 0) return style.backgroundColor;
    let depth = 0;
    for (let i = open + 1; i < image.length; i++) {
      const ch = image[i];
      if (ch === "(") depth++;
      else if (ch === ")" && depth > 0) depth--;
      else if ((ch === "," || ch === ")") && depth === 0) return image.slice(open + 1, i).trim();
    }
    return style.backgroundColor;
  }

  /**
   * Tsubu.checkContrast(root, options) -> { ok, checks, failures }
   * Measures the colours the browser computes for a drawn sentence in every state ("static",
   * before any apply and with timing "none", then each of STATES), for each layer (text,
   * furigana, romaji, underline, and the highlight against what surrounds it), against each
   * backdrop. A layer is measured against the highlight when the highlight covers its middle:
   * readings sit above or below the highlighted em box (to its right or left in vertical text),
   * so they are measured against the plate and the backdrop. Romaji are small text, as furigana
   * are, and are held to the furigana's threshold (`ruby`).
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
      // Across the line: vertically in horizontal text, horizontally in vertical text, where the
      // furigana sit to the right of the highlight and the segment's line to its left.
      const axis = blockAxis(copy);
      const side = axis.side[0].toUpperCase() + axis.side.slice(1);
      const segments = [...copy.querySelectorAll(":scope > .tsubu-unit > .tsubu-seg")];
      // Every segment shown, revealed and with its readings on both sides: whatever can be drawn
      // is checked. (What a motion preset hides while it is unheard is drawn in these colours once
      // revealed.)
      copy.setAttribute("data-ruby", "on");
      if (copy.hasAttribute("data-under")) copy.setAttribute("data-under", "on");
      // Where each segment's highlight and underline lie is measured on probes that take their
      // geometry from the same rules as its ::before and ::after (see the stylesheet).
      const probes = new Map();
      for (const el of segments) {
        el.removeAttribute("data-off-page");
        el.setAttribute("data-revealed", "");
        const band = document.createElement("span"), line = document.createElement("span");
        band.className = "tsubu-band-probe";
        line.className = "tsubu-line-probe";
        el.append(band, line);
        probes.set(el, { band, line });
      }
      // Opacity on a layer or between it and the sentence fades it; a hidden layer is not drawn.
      const fade = (el, own) => {
        let alpha = own ? parseFloat(own.opacity) : 1;
        for (let n = el; n && n !== copy.parentElement; n = n.parentElement) alpha *= parseFloat(getComputedStyle(n).opacity);
        return alpha;
      };
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
            // The highlight is the segment's ::before, a band over the em box of its text that
            // reaches `spread` past it (see the stylesheet). A layer is on the highlight when the
            // band covers its middle (and checked against both when the band covers only part of
            // it); a layer whose middle lies outside the band, like the furigana, which the band
            // at most grazes, is on what is behind the highlight. Positions are compared across
            // the line, which is horizontal in vertical text.
            const band = getComputedStyle(el, "::before");
            const bandColour = bandColourOf(band);
            const highlight = band.visibility === "hidden" ? [0, 0, 0, 0] : parseColour(bandColour);
            const behind = over(highlight, base);
            const [from, to] = axis.span(probes.get(el).band.getBoundingClientRect());
            const backgroundsFor = (top, bottom) => {
              if (highlight[3] === 0) return [base];
              const middle = (top + bottom) / 2;
              if (middle < from || middle > to) return [base];
              return top >= from && bottom <= to ? [behind] : [behind, base];
            };
            const layers = [];
            // The text too: the band covers its middle, wherever the band is drawn as the
            // stylesheet means it.
            const [top, bottom] = axis.span(el.getBoundingClientRect());
            const onBand = (top + bottom) / 2 >= from && (top + bottom) / 2 <= to;
            if (style.visibility !== "hidden") layers.push(["text", style.color, onBand ? behind : base, fade(el)]);
            // The first reading of each layer: the readings of a segment share their colours.
            for (const [layer, rt] of [["ruby", el.querySelector(FURIGANA)], ["romaji", el.querySelector(ROMAJI)]]) {
              const rtStyle = rt && getComputedStyle(rt);
              if (!rt || rtStyle.visibility === "hidden") continue;
              const [a, b] = axis.span(rt.getBoundingClientRect());
              for (const under of backgroundsFor(a, b)) layers.push([layer, rtStyle.color, under, fade(rt)]);
            }
            // The underline, or in vertical text the side line: a border on the block-end side of
            // the segment's ::after, whose box its probe takes.
            const after = getComputedStyle(el, "::after");
            if (after.content !== "none" && after[`border${side}Style`] !== "none" && after.visibility !== "hidden") {
              const width = parseFloat(after[`border${side}Width`]);
              const line = probes.get(el).line.getBoundingClientRect();
              const [a, b] = axis.side === "left" ? [line.left, line.left + width] : axis.side === "right" ? [line.right - width, line.right] : [line.bottom - width, line.bottom];
              for (const under of backgroundsFor(a, b)) layers.push(["underline", after[`border${side}Color`], under, fade(el, after)]);
            }
            if (highlight[3] > 0) layers.push(["highlight", bandColour, base, fade(el, band)]);
            for (const [layer, colour, under, alpha] of layers) {
              const paint = parseColour(colour);
              paint[3] *= alpha;
              if (paint[3] === 0) continue;
              const fg = layer === "highlight" ? over(paint, base) : over(paint, under);
              const bg = layer === "highlight" ? base : under;
              const ratio = ratioOf(fg, bg), minimum = thresholds[layer === "romaji" ? "ruby" : layer];
              const key = [state, layer, colour, alpha, bg.join(), backdrop].join("|");
              if (!seen.has(key)) {
                const hex = (c) => "#" + c.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, "0")).join("");
                seen.set(key, { state, layer, foreground: hex(fg), background: hex(bg), backdrop: String(backdrop),
                  ratio: Math.round(ratio * 100) / 100, minimum, ok: ratio >= minimum });
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

  /**
   * Tsubu.checkFit(root, options) -> { ok, issues, lines, pages }
   * Measures whether a drawn sentence fits where it is drawn: in its container (options.container,
   * else the root's parent element), at the size, font and width it has there. It works on a copy
   * of the sentence the same size as the root, with every segment shown and the readings on both
   * sides on, and removes it again: the page is left as it was. A sentence paged by t is checked
   * page by page. Each issue is { kind, segment, page, by, message }:
   *   "overflow"        a segment or its furigana reach past the container's padding box (by px);
   *   "too-wide"        a unit of segments that may not be parted is longer than a line, so it can
   *                     only overflow: shorten the segment, or make the text smaller;
   *   "ruby-clipped"    a reading, furigana or romaji, reaches past the container's padding box
   *                     (above or below the text, or beside it in vertical text): raise
   *                     --tsubu-ruby-reserve (over) or --tsubu-under-reserve (under), or give the
   *                     container room;
   *   "too-many-lines"  more lines than --tsubu-max-lines in a sentence that cannot be paged (one
   *                     without times for its segments).
   */
  function checkFit(root, options) {
    if (!root || !root.classList || !root.classList.contains("tsubu")) fail('checkFit needs the element with class "tsubu"');
    if (typeof getComputedStyle !== "function") fail("checkFit measures a page, so it needs a browser");
    const opts = options || {};
    const container = opts.container === undefined ? root.parentElement : opts.container;
    if (!container || typeof container.getBoundingClientRect !== "function") fail("options.container must be an element");

    const vertical = blockAxis(root).vertical;
    const at = root.getBoundingClientRect();
    const copy = root.cloneNode(true);
    copy.removeAttribute("id");
    copy.setAttribute("aria-hidden", "true");
    copy.setAttribute("data-ruby", "on");
    if (copy.hasAttribute("data-under")) copy.setAttribute("data-under", "on");
    copy.removeAttribute("data-measuring");
    copy.removeAttribute("data-greedy");
    // The same box as the root: its width (and in vertical text its height, the length of a
    // column), border included; placed out of sight, then measured as if it stood where the
    // root stands.
    Object.assign(copy.style, { position: "absolute", left: "-100000px", top: "0", boxSizing: "border-box", width: `${at.width}px` });
    if (vertical) copy.style.height = `${at.height}px`;
    root.after(copy);
    const issues = [];
    let lines = 0, pages = null;
    try {
      const elements = [...copy.querySelectorAll(":scope > .tsubu-unit > .tsubu-seg")];
      const units = [...copy.querySelectorAll(":scope > .tsubu-unit")];
      for (const el of elements) el.removeAttribute("data-off-page");
      const origin = copy.getBoundingClientRect();
      const shift = (r) => ({ left: r.left - origin.left + at.left, right: r.right - origin.left + at.left, top: r.top - origin.top + at.top, bottom: r.bottom - origin.top + at.top });
      const cs = getComputedStyle(container), cr = container.getBoundingClientRect(), px = (v) => parseFloat(v) || 0;
      const box = { left: cr.left + px(cs.borderLeftWidth), right: cr.right - px(cs.borderRightWidth), top: cr.top + px(cs.borderTopWidth), bottom: cr.bottom - px(cs.borderBottomWidth) };
      const past = (r) => Math.max(box.left - r.left, r.right - box.right, box.top - r.top, r.bottom - box.bottom, 0);
      // a segment's text without its readings or their parentheses, for the messages
      const name = (el) => { const r = el.cloneNode(true); r.querySelectorAll("rt, rp").forEach((x) => x.remove()); return r.textContent; };
      // Where a segment's text lies: its box, but in vertical text the box of its text without the
      // readings, since a vertical segment's line reaches past its text (see the stylesheet).
      const textBox = (el) => {
        if (!vertical) return el.getBoundingClientRect();
        const range = document.createRange(), walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
        let b = null;
        for (let node = walker.nextNode(); node; node = walker.nextNode()) {
          if (node.parentElement.closest("rt, rp")) continue;
          range.selectNodeContents(node);
          const r = range.getBoundingClientRect();
          b = b ? { left: Math.min(b.left, r.left), right: Math.max(b.right, r.right), top: Math.min(b.top, r.top), bottom: Math.max(b.bottom, r.bottom) } : r;
        }
        return b || el.getBoundingClientRect();
      };

      // A unit longer than the line it has: measured along the line, against the root's content box
      // or the container's, whichever is shorter (a vertical sentence without a height of its own
      // grows with its content, so its column is as long as the container lets it be).
      const ps = getComputedStyle(copy), pr = copy.getBoundingClientRect();
      const inner = (r, st) => (vertical ? r.height - px(st.paddingTop) - px(st.paddingBottom) : r.width - px(st.paddingLeft) - px(st.paddingRight));
      const room = Math.min(inner(pr, ps), inner(cr, cs) - (vertical ? px(cs.borderTopWidth) + px(cs.borderBottomWidth) : px(cs.borderLeftWidth) + px(cs.borderRightWidth)));
      units.forEach((unit) => {
        const r = unit.getBoundingClientRect(), length = vertical ? r.height : r.width;
        if (length > room + 0.5) {
          const first = unit.querySelector(".tsubu-seg"), i = Number(first.getAttribute("data-index"));
          const words = [...unit.querySelectorAll(".tsubu-seg")].map(name).join("");
          issues.push({ kind: "too-wide", segment: i, page: null, by: round(length - room),
            message: `segments that may not be parted, ${JSON.stringify(words)}, are ${round(length)}px long on a line of ${round(room)}px` });
        }
      });

      const lineOf = lineIndexes(copy, elements);
      const perPage = linesPerPage(copy);
      const paged = perPage !== null && copy.getAttribute("data-timing") === "segments";
      const pageOf = paged ? lineOf.map((l) => Math.floor(l / perPage)) : lineOf.map(() => 0);
      const count = pageOf[pageOf.length - 1] + 1;
      if (paged) pages = count;
      lines = paged ? Math.min(perPage, lineOf[lineOf.length - 1] + 1) : lineOf[lineOf.length - 1] + 1;
      if (perPage !== null && !paged && lines > perPage)
        issues.push({ kind: "too-many-lines", segment: null, page: null, by: lines - perPage,
          message: `${lines} lines, more than --tsubu-max-lines (${perPage}), in a sentence that cannot be paged: it has no times for its segments` });

      for (let page = 0; page < count; page++) {
        elements.forEach((el, i) => (pageOf[i] === page ? el.removeAttribute("data-off-page") : el.setAttribute("data-off-page", "")));
        elements.forEach((el, i) => {
          if (pageOf[i] !== page) return;
          const r = shift(textBox(el)), by = past(r);
          if (by > 0.5) issues.push({ kind: "overflow", segment: i, page: paged ? page : null, by: round(by),
            message: `segment ${i}, ${JSON.stringify(name(el))}, reaches ${round(by)}px past its container` });
          el.querySelectorAll("rt").forEach((rt) => {
            const q = shift(rt.getBoundingClientRect()), out = past(q);
            const what = rt.matches(ROMAJI) ? "romaji" : "furigana";
            if (out > 0.5) issues.push({ kind: "ruby-clipped", segment: i, page: paged ? page : null, by: round(out),
              message: `the ${what} ${JSON.stringify(rt.textContent)} of segment ${i} reach ${round(out)}px past the container` });
          });
        });
      }
    } finally {
      copy.remove();
    }
    return { ok: issues.length === 0, issues, lines, pages };
  }

  function round(v) { return Math.round(v * 10) / 10; }

  return Object.freeze({ version: VERSION, sentence, setRuby, setAnnotation, setRevealed, segmentOf, contrast, checkContrast, checkFit, STATES, THEMES, SPEAKERS, CONTRAST, MOTIONS });
});
