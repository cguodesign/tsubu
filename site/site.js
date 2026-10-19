/* tsubu's site: the pieces every page shares. Loaded after tsubu.js.
   - the masthead and footer, written once here so that every page agrees;
   - the language toggle: English and 简体中文 sit side by side in the markup (class en / zh) and
     data-lang on <html> shows one of them;
   - a clock for the examples: it only chooses t, and every frame is drawn from t alone;
   - small helpers for drawing an example sentence and a section label with tsubu. */
"use strict";
window.Site = (function () {
  const PAGES = [
    ["index.html", "Home", "首页"], ["start.html", "Getting started", "快速开始"], ["guide.html", "Guide", "指南"],
    ["api.html", "API", "API"], ["playground.html", "Playground", "试验场"], ["gallery.html", "Gallery", "画廊"],
  ];
  // The repository's address, once it is public: the masthead and the footer link to it.
  const REPO = "";
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private window */ } } };

  function lang() { return document.documentElement.dataset.lang === "zh" ? "zh" : "en"; }
  function setLang(l) {
    document.documentElement.dataset.lang = l;
    document.documentElement.lang = l === "zh" ? "zh-CN" : "en";
    store.set("tsubu-lang", l);
    document.querySelectorAll(".lang").forEach((b) => { b.textContent = l === "zh" ? "English" : "中文"; b.setAttribute("aria-label", l === "zh" ? "Switch to English" : "切换到中文"); });
    document.dispatchEvent(new CustomEvent("tsubu-lang", { detail: l }));
  }
  // the stored choice applies before the first paint, so the page does not flash the other language
  const saved = store.get("tsubu-lang");
  if (saved === "zh" || saved === "en") { document.documentElement.dataset.lang = saved; document.documentElement.lang = saved === "zh" ? "zh-CN" : "en"; }

  function mast(active) {
    const el = document.querySelector(".mast"); if (!el) return;
    const links = PAGES.map(([href, en, zh]) => `<li><a href="${href}"${href === active ? ' aria-current="page"' : ""}><span class="en">${en}</span><span class="zh" lang="zh-CN">${zh}</span></a></li>`).join("");
    const repo = REPO ? `<li><a class="ext" href="${REPO}" rel="noopener">GitHub</a></li>` : "";
    el.innerHTML = `<a class="mark" href="index.html">tsubu<span class="kanji">粒</span></a>
      <nav aria-label="Site"><ul class="nav">${links}${repo}<li><button type="button" class="lang"></button></li></ul></nav>`;
    el.querySelector(".lang").addEventListener("click", () => setLang(lang() === "zh" ? "en" : "zh"));
    setLang(lang());
    const foot = document.querySelector("footer.foot");
    if (foot) foot.innerHTML = `<span>tsubu · <span class="en">MIT licence</span><span class="zh" lang="zh-CN">MIT 许可证</span> · v${Tsubu.version}</span>
      <span>${REPO ? `<a href="${REPO}" rel="noopener">GitHub</a> · ` : ""}<span class="en">Colours</span><span class="zh" lang="zh-CN">用色</span>: 白練 濃藍 瑠璃 紺青 朱 山吹 白藍 銀鼠 群青</span>`;
  }

  // A clock that drives renderers with t. `render(t)` is the only thing it calls; a scrubber and
  // a play button may be bound to it. It never autoplays under prefers-reduced-motion.
  function clock({ duration, render, loop = true, play, scrub, out, start = 0, autoplay = true }) {
    let t = start, playing = false, origin = 0, from = 0;
    const show = (v) => { t = Math.min(duration, Math.max(0, v)); render(t); if (scrub) scrub.value = String(t); if (out) out.textContent = `${t.toFixed(2)} s`; };
    const tick = (now) => { if (!playing) return; if (!origin) origin = now - from * 1000; let v = (now - origin) / 1000;
      if (v >= duration) { if (loop) v %= duration; else { v = duration; show(v); setPlaying(false); return; } } show(v); requestAnimationFrame(tick); };
    const setPlaying = (on) => { playing = on; if (play) play.textContent = on ? (lang() === "zh" ? "暂停" : "Pause") : (lang() === "zh" ? "播放" : "Play"); if (on) { origin = 0; from = t >= duration ? 0 : t; requestAnimationFrame(tick); } };
    if (play) play.addEventListener("click", () => setPlaying(!playing));
    if (scrub) { scrub.min = scrub.min || "0"; scrub.max = String(duration); scrub.step = scrub.step || "0.01"; scrub.addEventListener("input", () => { if (playing) setPlaying(false); show(Number(scrub.value)); }); }
    document.addEventListener("tsubu-lang", () => { if (play) play.textContent = playing ? (lang() === "zh" ? "暂停" : "Pause") : (lang() === "zh" ? "播放" : "Play"); });
    show(start);
    setPlaying(autoplay && !reduce);
    if (!autoplay || reduce) setPlaying(false);
    return { get t() { return t; }, set: show, setPlaying, get playing() { return playing; } };
  }

  // Draws a sentence into an element and returns the root, or writes the error tsubu throws.
  function draw(el, input, options) {
    const s = Tsubu.sentence(input, options);
    el.innerHTML = s.html;
    return { s, root: el.querySelector(".tsubu") };
  }

  // Section labels: the kanji is a one-grain sentence drawn by tsubu, with its reading.
  function labels() {
    document.querySelectorAll(".label .kanji[data-ruby]").forEach((el) => {
      const text = el.textContent.trim();
      el.innerHTML = Tsubu.sentence({ segments: [{ parts: [{ text, ruby: el.dataset.ruby }] }] }, { announceRuby: false }).html;
    });
  }

  // A light touch of colour for code samples: comments, strings and a few keywords.
  function code() {
    document.querySelectorAll("pre code:not(.plain)").forEach((el) => {
      const src = el.textContent.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
      // one pass, so that a span inserted for one token is never matched by the next pattern
      const token = /(\/\/[^\n]*|&lt;!--[\s\S]*?--&gt;|^#[^\n]*)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)|\b(const|let|function|return|new|await|import|from|require|if|else|null|true|false)\b/gm;
      el.innerHTML = src.replace(token, (m, c, s, k) => `<span class="${c ? "c" : s ? "s" : "k"}">${m}</span>`);
    });
  }

  const fmt = (n) => (Math.round(n * 100) / 100).toFixed(2);
  // The lowest contrast checkContrast found, per layer, for a caption under an example.
  function worst(result) {
    const by = {};
    for (const c of result.checks) if (!by[c.layer] || c.ratio < by[c.layer].ratio) by[c.layer] = c;
    return Object.values(by).map((c) => `<span class="${c.ok ? "ok" : "fail"}">${c.layer} ${fmt(c.ratio)}${c.ok ? "" : " ✕"}</span>`).join(" · ");
  }

  document.addEventListener("DOMContentLoaded", () => { labels(); code(); });
  return { PAGES, REPO, reduce, lang, setLang, mast, clock, draw, labels, code, worst, fmt };
})();
