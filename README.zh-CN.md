<p align="center"><img src="assets/logo.svg" alt="tsubu" width="200"></p>

# tsubu

[English](README.md) · [简体中文](README.zh-CN.md) · [网站](https://chong.works/tsubu/) ·
[指南（英文）](docs/guide.md) · [npm](https://www.npmjs.com/package/tsubu-js)

**tsubu**（粒，米粒的"粒"）是一个很小、零依赖的浏览器库，只渲染一句日语，用于跟读和语言学习。句子传进来时已经切好了段（文节），tsubu 负责画出：

- 每段下面一条点状下划线；
- 可以开关的注音，**开关时任何一个字都不移动**；
- 正在读的那一段的高亮，而且是**时间的纯函数**：`apply(root, t)` 不用计时器、不用 `requestAnimationFrame`、不用过渡，所以实时播放和逐帧录视频画出来的完全一样；
- 实测对比度的主题、按日语禁则断开的多行、竖排、动效预设，以及 WebVTT、ASS、SRT 导出。

它只有一个普通脚本（`tsubu.js`，未压缩约 21 KB）和一个样式表（`tsubu.css`），可以从 `file://` 页面、任何网页和 Node 里加载。

tsubu **不做**的事：把文本切成词、把音频和文本对齐、估算时间、播放音频、画对话气泡、排多句话。这些由调用方负责。

## 30 秒示例

```html
<link rel="stylesheet" href="tsubu.css">
<div id="line" style="font-size: 40px"></div>
<script src="tsubu.js"></script>
<script>
  const s = Tsubu.sentence({
    segments: [
      { parts: [{ text: "雨", ruby: "あめ" }, { text: "の" }, { text: "日", ruby: "ひ" }, { text: "は" }], start: 0.0, end: 0.7 },
      { parts: [{ text: "、" }], kind: "punct" },
      { parts: [{ text: "家", ruby: "いえ" }, { text: "で" }], start: 0.9, end: 1.3 },
      { parts: [{ text: "お" }, { text: "茶", ruby: "ちゃ" }, { text: "を" }], start: 1.3, end: 1.8 },
      { parts: [{ text: "飲", ruby: "の" }, { text: "みます" }], start: 1.85, end: 2.6 },
      { parts: [{ text: "。" }], kind: "punct" },
    ],
  });
  const line = document.getElementById("line");
  line.innerHTML = s.html;
  const root = line.querySelector(".tsubu");

  // 用任何时钟驱动：<audio> 元素、视频时间轴、帧计数器都可以。
  const audio = document.querySelector("audio");
  audio?.addEventListener("timeupdate", () => s.apply(root, audio.currentTime));
  s.apply(root, 1.0);            // t = 1.0 秒那一帧：高亮「家で」

  Tsubu.setRuby(root, false);    // 隐藏注音；什么都不动
</script>
```

直接从磁盘打开 [`demo/index.html`](demo/index.html)，可以拖动时间、开关注音。

## 安装

从 npm 安装，锁定精确版本。npm 上的包名是 `tsubu-js`（npm 认为 `tsubu` 和已有的包名太像，不予注册）：

```sh
npm install --save-exact tsubu-js
```

包里的文件和本仓库相同，没有构建步骤：`tsubu.js`（普通脚本）、`tsubu.css`、`tsubu-export.js`，
每个脚本各有一个 ES 模块（`tsubu.mjs`、`tsubu-export.mjs`，只把脚本的对象再导出），以及
TypeScript 类型声明。

```js
const Tsubu = require("tsubu-js");                     // Node，CommonJS
const TsubuExport = require("tsubu-js/export");
import Tsubu, { sentence } from "tsubu-js";            // ES 模块和打包工具
import { toSRT } from "tsubu-js/export";
import "tsubu-js/tsubu.css";                           // 打包工具能处理 CSS 时
```

从 CDN 加载时，写精确版本并加上[子资源完整性（SRI）](https://developer.mozilla.org/zh-CN/docs/Web/Security/Subresource_Integrity)，
页面就只会运行它所针对的那个文件：

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tsubu-js@0.1.0/tsubu.css"
      integrity="sha384-SlfIuFrZo0yor05+BcMvDiAP3WJ0dkZmH8a9JUHnmAUI9BGNU+oQ9dDy+5n1PKoG" crossorigin="anonymous">
<script src="https://cdn.jsdelivr.net/npm/tsubu-js@0.1.0/tsubu.js"
        integrity="sha384-KqOxfytJPFgoafKyYmfGSraqQPzpMAopz/++pPUH412E94z3r9qWDgy+b/aoryAE" crossorigin="anonymous"></script>
```

`https://unpkg.com/tsubu-js@0.1.0/tsubu.js` 提供同一个文件。文件的哈希是
`openssl dgst -sha384 -binary tsubu.js | openssl base64 -A`，从包（`npm pack`）或 CDN 上的副本算；
向 CDN 要文件本身，不要它压缩过的版本，那个哈希不同。不用打包工具的页面也可以用
`<script type="module">` 从同样的地址导入 `tsubu.mjs`；这时普通脚本也会定义全局的 `Tsubu`。

也可以直接把 `tsubu.js` 和 `tsubu.css` 复制到页面旁边：页面只需要这两个文件，从 `file://` 打开也能用。

**版本。** tsubu 遵循[语义化版本](https://semver.org/lang/zh-CN/)。1.0 之前，会破坏调用方的改动升次版本号
（0.1 到 0.2），其他改动升修订号。破坏性改动指：输入格式或它拒绝的内容，HTML（元素、class、`data-*` 和
`aria-*` 属性），`--tsubu-*` 属性、主题和动效预设的名字，`Tsubu` 和 `TsubuExport` 上的名字和签名，
`stateAt`、`apply`、`checkContrast`、`checkFit` 返回值的结构，以及导出器写出的文本。`Tsubu.version`
是手上这份脚本的版本；每次改动都记在 [CHANGELOG.md](CHANGELOG.md)。

## 输入

```js
Tsubu.sentence(input, options)

input = {
  lang: "ja",                  // 可选，默认 "ja"；写到根元素的 lang 属性上
  start: 4.0, end: 6.0,        // 可选：整句的开始和结束，单位秒
  segments: [                  // 必填，按朗读顺序
    { parts: [{ text: "家", ruby: "いえ" }, { text: "で" }], start: 0.9, end: 1.3 },
    { parts: [{ text: "、" }], kind: "punct" },
    // ...
  ],
}
options = {                    // 都是可选的
  ruby: true,                  // 注音一开始是否显示（默认 true）
  announceRuby: true,          // 读屏软件是否朗读注音（默认 true）
  theme: "light",              // 预设："light"、"dark"、"media"，或你自己起的名字
  speaker: "a",                // 这句话是谁说的，用于按说话人上色："a"、"b" 或你自己起的名字
  motion: "mask",              // Tsubu.MOTIONS 里的动效预设：一个名字、空格分隔的列表或数组
  writing: "vertical",         // "horizontal"（默认）或 "vertical"
  combineUpright: 2,           // 竖排时，不超过这么多个的半角字符直立显示（0-4）
}
```

段的 `parts` 是文字片段，带 `ruby` 的片段画成 `<ruby>`。`kind: "punct"` 表示标点，它不会被朗读，也不能带时间。时间决定句子的 **timing**：

| `timing` | 条件 | 高亮什么 |
|---|---|---|
| `"segments"` | 每个非标点段都有 `start` 和 `end` | 一次一段。整句自己的时间段取 `input.start`/`input.end`；没给就从第一段的开始到最后一段的结束。 |
| `"sentence"` | 没有任何段带时间，整句有 `start` 和 `end` | 整句一起亮。时间段**不会**按长度或音拍分给各段。 |
| `"none"` | 哪里都没有时间 | 不亮：句子可以画出来（静态预览），但 `stateAt` 和 `apply` 会抛错。 |

tsubu 从不猜测：只有部分段带时间、时间重叠或倒序、输入格式不对，都会抛出 `Error`，消息以 `tsubu:` 开头。完整的约定见[指南](docs/guide.md#input)（英文）。

## 输出

`Tsubu.sentence()` 返回一个冻结的对象，包括：

- `html`：句子的 HTML 字符串；`timing`；
- `stateAt(t)`：在 `t` 时刻每段是未读、正在读还是已读；
- `apply(root, t)`：把这个状态以属性的形式写到画好的句子上，从不改文字或节点；`htmlAt(t)`：同一帧的 HTML，给服务器和渲染器用；
- `span(i)` 和 `find(id)`：点击跳转用。

`Tsubu` 上还有 `setRuby`、`setRevealed`、`segmentOf`、`checkContrast`、`checkFit`、`contrast`，以及目录 `THEMES`、`SPEAKERS`、`MOTIONS`、`CONTRAST`、`STATES`。所有名字、选项和 CSS 自定义属性都在[指南](docs/guide.md#output)（英文）和网站的 [API 页面](https://chong.works/tsubu/api.html)（有中文）里。

## 其他功能

每一项都链接到指南（英文）里对应的一节；网站上有同样内容的中文版和现场示例：

- [**主题与对比度**](docs/guide.md#themes-and-contrast)：`light`、`dark`、`media` 三套预设，按说话人上色，以及 `checkContrast`：按基于 WCAG 的阈值测量画好的句子。
- [**多行**](docs/guide.md#several-lines)：日语禁则、均衡换行、字号随容器变化、超过最大行数时按 `t` 翻页。`checkFit` 判断句子在所画的位置是否放得下。
- [**竖排**](docs/guide.md#vertical-writing)，短的半角字符串直立显示。
- [**动效与揭示**](docs/guide.md#motion-and-revealing)：`appear`、`mask`、`blur`、`underline-draw`，都由状态画出；也可以按调用方的事件揭示某些段。
- [**录制视频**](docs/guide.md#recording-video)（逐帧）和[**字幕**](docs/guide.md#exporting-subtitles)（`tsubu-export.js`：WebVTT、ASS 卡拉 OK、SRT）。
- [**与其他工具配合**](docs/guide.md#using-tsubu-with-other-tools)：Remotion、HyperFrames 等逐帧引擎，视频剪辑软件，PowerPoint。
- [**无障碍**](docs/guide.md#accessibility)：强制颜色模式，可以让读屏软件跳过的注音，以及在画不出 ruby 的地方用括号显示的注音。

## 给 agent

tsubu 接收的输入必须已经切好段、带好读音和真实时间。[`docs/agents/segmenting.md`](docs/agents/segmenting.md)（英文）是给准备这些输入的 AI agent 的版本化指南：用形态分析器切文节、把读音放在汉字上、用强制对齐或语音合成的时间戳、使用前的检查，并附一个零依赖的校验器：

```sh
node docs/agents/validate.mjs input.json --text sentence.txt
```

## 保证与浏览器支持

每一帧都是 `t` 的函数；开关注音、切换高亮、换主题或说话人都不会让任何字移动；只在段与段之间、按禁则断行；在一组宽度和句长下都不溢出。每一条都在真实浏览器里测量，覆盖 Chromium、Firefox 和 WebKit。Chromium 里全部成立；Firefox 和 WebKit 并非在所有情况下都均衡换行。细节和每条怎么测，见 [docs/testing.md](docs/testing.md)（英文）。

## 开发

```sh
python -m pip install -r requirements-dev.txt
python -m playwright install chromium firefox webkit
npm ci
python -m pytest -q                    # 加 --engine firefox 或 --engine webkit
```

要求和选项见 [docs/testing.md](docs/testing.md#running-the-tests)（英文）。每次推送 GitHub Actions 都会跑测试；打版本 tag 时会带来源证明发布到 npm，并部署网站。

## 文件

| 文件 | 内容 |
|---|---|
| `tsubu.js` | 库本身：一个普通脚本，在页面里定义 `Tsubu`，在 Node 里是 `module.exports` |
| `tsubu.css` | 样式；可调的都是自定义属性 |
| `tsubu-export.js` | 可选：用同样的输入生成 WebVTT、ASS 卡拉 OK 和 SRT 字幕 |
| `tsubu.mjs`、`tsubu-export.mjs` | 同样的对象，以 ES 模块的形式，本身没有代码 |
| `*.d.ts`、`*.d.mts` | TypeScript 类型声明，由 `tests/test_package.py` 和 `tests/types` 对照脚本检查 |
| `package.json` | npm 包：导出、发布哪些文件、锁定版本的 TypeScript |
| `docs/agents/` | 给 agent 的版本化指南，讲怎么准备 tsubu 的输入，附校验器（也在包里） |
| `examples/` | 录制视频：用 Playwright 生成 PNG 帧，用 Node 生成 HTML 帧；帧换算 `tsubu-frames.js`，以及 Remotion 和 HyperFrames 示例 |
| `site/` | 项目网站：首页（短片由 `t` 绘制）、快速开始、指南、API 参考、试验场和画廊，中英双语。页面从同级文件加载库（检出里是符号链接），所以从磁盘直接打开就能看 |
| `demo/index.html` | 演示页：拖动时间、开关注音、选主题，有一段对话和一个流式、会翻页的框；地址可带 `?t=秒数&ruby=off&theme=dark&frame=320&lines=2` |
| `tests/` | 测试（pytest；状态用 Node，版面用 Playwright，在 Chromium、Firefox 或 WebKit 里） |
| `.github/workflows/` | 每次推送跑 CI；打版本 tag 时先测试，再带来源证明 `npm publish`，再把网站部署到 GitHub Pages |
| `docs/guide.md` | 指南（英文）：输入、输出、CSS 自定义属性和每项功能的细节 |
| `docs/testing.md` | 版面保证、每条怎么测、浏览器支持、怎么跑测试（英文） |
| `assets/` | logo |

## 许可证

MIT，见 [LICENSE](LICENSE)。计划中的工作见 [ROADMAP.md](ROADMAP.md)（英文），变更记录见 [CHANGELOG.md](CHANGELOG.md)。
