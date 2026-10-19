// Writes the HTML of every frame of one tsubu sentence, without a browser, for renderers that
// take HTML (server-side rendering, HTML-to-image services, video tools that render markup).
//
//   node examples/frames-from-node.mjs SENTENCE.json OUT_DIR [fps]
//
// Each file is a whole page: tsubu.css inlined, then Tsubu.sentence(...).htmlAt(t) for that
// frame's time. htmlAt is the same markup apply(root, t) makes in a browser, so these frames
// match live playback. (It does not page: paging needs the layout.)
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const Tsubu = createRequire(import.meta.url)(join(root, "tsubu.js"));
const [input, out, fps = "30"] = process.argv.slice(2);
if (!input || !out) {
  console.error("usage: node examples/frames-from-node.mjs SENTENCE.json OUT_DIR [fps]");
  process.exit(2);
}

const sentence = JSON.parse(readFileSync(input, "utf8"));
const s = Tsubu.sentence(sentence, { theme: "light" });
const times = sentence.segments.flatMap((seg) => ("start" in seg ? [seg.start, seg.end] : []));
if ("start" in sentence) times.push(sentence.start, sentence.end);
const first = Math.min(...times), last = Math.max(...times), rate = Number(fps);
const css = readFileSync(join(root, "tsubu.css"), "utf8");

mkdirSync(out, { recursive: true });
// floor with a little room, so that a span of 2.6000000000000005 s at 10 fps is 26 steps, not 27
const count = Math.floor((last - first) * rate + 1e-6) + 1;
for (let i = 0; i < count; i++) {
  const t = first + i / rate;
  const page = `<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>${css}
body { margin: 0; background: #ffffff; font: 48px "Hiragino Sans", "Noto Sans JP", sans-serif; }</style></head>
<body>${s.htmlAt(t)}</body></html>\n`;
  writeFileSync(join(out, `frame_${String(i).padStart(5, "0")}.html`), page);
}
console.log(`${count} frames in ${out}`);
