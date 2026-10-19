/* tsubu's site: the pieces every page shares. Loaded after tsubu.js.
   - the masthead and footer, written once here so that every page agrees;
   - the language toggle: English and 简体中文 sit side by side in the markup (class en / zh) and
     data-lang on <html> shows one of them;
   - a clock for the examples: it only chooses t, and every frame is drawn from t alone;
   - small helpers for drawing an example sentence and a section label with tsubu. */
"use strict";
window.Site = (function () {
  const PAGES = [
    ["index.html", "Home", "首页", "ホーム"], ["start.html", "Getting started", "快速开始", "はじめに"], ["guide.html", "Guide", "指南", "ガイド"],
    ["api.html", "API", "API", "API"], ["playground.html", "Playground", "试验场", "プレイグラウンド"], ["gallery.html", "Gallery", "画廊", "ギャラリー"],
  ];
  const LANGS = [["en", "EN", "en"], ["zh", "中文", "zh-CN"], ["ja", "日本語", "ja"]];
  const T = (en, zh, ja) => `<span class="en">${en}</span><span class="zh" lang="zh-CN">${zh}</span><span class="ja" lang="ja">${ja}</span>`;
  // The repository's address, once it is public: the masthead and the footer link to it.
  const REPO = "https://github.com/cguodesign/tsubu";
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const store = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private window */ } } };

  const known = (l) => LANGS.some(([code]) => code === l);
  function lang() { const l = document.documentElement.dataset.lang; return known(l) ? l : "en"; }
  function setLang(l) {
    if (!known(l)) l = "en";
    document.documentElement.dataset.lang = l;
    document.documentElement.lang = LANGS.find(([code]) => code === l)[2];
    store.set("tsubu-lang", l);
    document.querySelectorAll(".lang").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === l)));
    document.dispatchEvent(new CustomEvent("tsubu-lang", { detail: l }));
  }
  // the stored choice applies before the first paint, so the page does not flash another language
  const saved = store.get("tsubu-lang");
  if (known(saved)) { document.documentElement.dataset.lang = saved; document.documentElement.lang = LANGS.find(([code]) => code === saved)[2]; }
  // the words every page's controls share
  const WORDS = { play: ["Play", "播放", "再生"], pause: ["Pause", "暂停", "一時停止"], copied: ["Copied", "已复制", "コピーしました"] };
  const word = (k) => WORDS[k][LANGS.findIndex(([code]) => code === lang())];

  function mast(active) {
    const el = document.querySelector(".mast"); if (!el) return;
    const links = PAGES.map(([href, en, zh, ja]) => `<li><a href="${href}"${href === active ? ' aria-current="page"' : ""}>${T(en, zh, ja)}</a></li>`).join("");
    const repo = REPO ? `<li><a class="ext" href="${REPO}" rel="noopener">GitHub</a></li>` : "";
    const langs = LANGS.map(([code, name, tag]) => `<button type="button" class="lang" data-lang="${code}" lang="${tag}" aria-pressed="false">${name}</button>`).join("");
    el.innerHTML = `<a class="mark" href="index.html">tsubu<span class="kanji">粒</span></a>
      <nav aria-label="Site"><ul class="nav">${links}${repo}<li><span class="langs" role="group" aria-label="Language">${langs}</span></li></ul></nav>`;
    el.querySelectorAll(".lang").forEach((b) => b.addEventListener("click", () => setLang(b.dataset.lang)));
    setLang(lang());
    const foot = document.querySelector("footer.foot");
    if (foot) foot.innerHTML = `<span>tsubu · ${T("MIT licence", "MIT 许可证", "MIT ライセンス")} · v${Tsubu.version}</span>
      <span>${REPO ? `<a href="${REPO}" rel="noopener">GitHub</a> · ` : ""}${T("Colours", "用色", "配色")}: 白練 濃藍 瑠璃 紺青 朱 山吹 白藍 銀鼠 群青</span>`;
  }

  // A clock that drives renderers with t. `render(t)` is the only thing it calls; a scrubber and
  // a play button may be bound to it. It never autoplays under prefers-reduced-motion.
  function clock({ duration, render, loop = true, play, scrub, out, start = 0, autoplay = true }) {
    let t = start, playing = false, origin = 0, from = 0;
    const show = (v) => { t = Math.min(duration, Math.max(0, v)); render(t); if (scrub) scrub.value = String(t); if (out) out.textContent = `${t.toFixed(2)} s`; };
    const tick = (now) => { if (!playing) return; if (!origin) origin = now - from * 1000; let v = (now - origin) / 1000;
      if (v >= duration) { if (loop) v %= duration; else { v = duration; show(v); setPlaying(false); return; } } show(v); requestAnimationFrame(tick); };
    const setPlaying = (on) => { playing = on; if (play) play.textContent = word(on ? "pause" : "play"); if (on) { origin = 0; from = t >= duration ? 0 : t; requestAnimationFrame(tick); } };
    if (play) play.addEventListener("click", () => setPlaying(!playing));
    if (scrub) { scrub.min = scrub.min || "0"; scrub.max = String(duration); scrub.step = scrub.step || "0.01"; scrub.addEventListener("input", () => { if (playing) setPlaying(false); show(Number(scrub.value)); }); }
    document.addEventListener("tsubu-lang", () => { if (play) play.textContent = word(playing ? "pause" : "play"); });
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
  return { PAGES, LANGS, REPO, T, word, reduce, lang, setLang, mast, clock, draw, labels, code, worst, fmt };
})();
