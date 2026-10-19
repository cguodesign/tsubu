<p align="center"><img src="assets/logo.svg" alt="tsubu" width="200"></p>

# tsubu

[English](README.md) · [简体中文](README.zh-CN.md)

**tsubu**（粒，米粒的"粒"）是一个很小、零依赖的浏览器库，只渲染一句话，用于跟读和语言学习：

- 句子传进来时已经切好了段（日语里就是文节），一段一粒；
- 每段有自己的一条点状下划线；
- 可选的注音（`<ruby>`）可以开关，**开关时任何一个字都不移动**；
- 正在读的那一段（或整句）按时间戳高亮，而且是**时间的纯函数**：`stateAt(t)` 和 `apply(root, t)`。不用 `requestAnimationFrame`、不用计时器、不用 CSS 过渡，所以逐帧截图录视频和实时播放画出来的完全一样；
- 颜色是一组组的 token，每个状态一组；有浅色页面、深色页面、叠在图片或视频上三套预设，对话里每个说话人可以有自己的颜色。每套预设的对比度都按库里自带的、基于 WCAG 的阈值实际测量。

它只有一个普通脚本（`tsubu.js`，未压缩约 21 KB）和一个样式表（`tsubu.css`）。可以从 `file://` 页面加载，也可以在任何网页里用，在 Node 里用 `require()` 也行。

tsubu **不做**的事：把文本切成词或段、把音频和文本对齐、估算时间、播放音频、画对话气泡、排多句话。这些由调用方负责。

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
  theme: "light",              // 预设："light"、"dark"、"media"，或你自己起的名字
  speaker: "a",                // 这句话是谁说的，用于按说话人上色："a"、"b" 或你自己起的名字
}
```

- **段**（segment）是一个朗读单位。它的 `parts` 是文字片段；带 `ruby` 的片段画成 `<ruby>text<rt>ruby</rt></ruby>`，所以带读音的词不会被拆开。
- `kind: "punct"` 表示标点：没有下划线，永远不会是正在读的那一段，也不能带时间。
- 时间以秒为单位，用调用方的时钟；`t` 也用同一个时钟。

时间决定句子的 **timing**：

| `timing` | 条件 | 高亮什么 |
|---|---|---|
| `"segments"` | 每个非标点段都有 `start` 和 `end` | 一次一段。整句自己的时间段取 `input.start`/`input.end`；没给就从第一段的开始到最后一段的结束。 |
| `"sentence"` | 没有任何段带时间，整句有 `start` 和 `end` | 整句一起亮。时间段**不会**按长度或音拍分给各段。 |
| `"none"` | 哪里都没有时间 | 不亮：句子可以画出来（静态预览），但 `stateAt` 和 `apply` 会抛错。 |

tsubu 从不猜测。下面这些输入会抛出 `Error`，消息以 `tsubu:` 开头：

- 只有一部分段带时间（把缺的补上就是估算）；
- 段的时间重叠或顺序颠倒，`end` 早于 `start`，时间不是有限的数，或者只给了 `start`/`end` 中的一个；
- 段的时间落在整句的 `start`/`end` 之外；
- 标点带时间，或者没有任何非标点的段；
- `segments`、`parts`、`text`、`ruby` 或 `lang` 为空，`kind` 不认识，`options.ruby` 不是布尔值，或者 `options.theme`、`options.speaker` 不是小写名字（`a-z`、数字和 `-`，以字母开头）。

## 输出

`Tsubu.sentence()` 返回一个冻结的对象：

- **`html`**：一段 HTML 字符串，

  ```html
  <span class="tsubu" lang="ja" data-timing="segments" data-ruby="on">
    <span class="tsubu-seg" data-index="0">…</span><wbr><span class="tsubu-seg" data-index="1">…</span>…
  </span>
  ```

  （实际没有这些空白）。给了 `options.theme` 时根元素还带 `data-tsubu-theme`，给了 `options.speaker` 时带 `data-speaker`。标点段带 `data-kind="punct"`。每段都是 `white-space: nowrap`，所以一段不会被拆到两行；每段前面有一个 `<wbr>`，让行在段与段之间断开；标点前没有，所以标点不会出现在行首。所有文字都经过 HTML 转义。刚生成的 HTML 不带状态，`apply` 之后才有。
- **`timing`**：`"segments"`、`"sentence"` 或 `"none"`。
- **`stateAt(t)`**：只取决于 `t` 的纯函数，返回

  ```js
  { timing, state, progress, current, segments: [{ state, progress }] }
  ```

  - `state` 是 `"future"`、`"current"` 或 `"past"`。每个时间段都是左闭右开的 `[start, end)`：`t < start` 是 future，`start <= t < end` 是 current，`t >= end` 是 past。两段之间有空隙时，前一段是 past，后一段是 future，没有 current 的段。
  - `progress` 是整句或该段从 0 到 1 的进度。timing 为 `"sentence"` 时各段的 `progress` 是 `null`（不知道）；标点的永远是 `null`。
  - `current` 是正在读的那一段的下标，没有就是 `null`。timing 为 `"sentence"` 时永远是 `null`。
  - timing 为 `"segments"` 时，标点和它前面那个非标点段一起变成 past；句首的标点在第一个非标点段开始时变成 past。timing 为 `"sentence"` 时，每一段（包括标点）的状态都和整句相同。
- **`apply(root, t)`**：把 `stateAt(t)` 写到页面上并返回它。`root` 必须是由 `html` 生成的那个 `.tsubu` 元素（是别的元素或段数不对就抛错）。它只设置属性：
  - 根元素：`data-state`、`--tsubu-progress`；timing 为 `"sentence"` 的句子正在读时带 `aria-current="true"`；
  - 每一段：`data-state`、`--tsubu-progress`（只有带时间的段）；正在读的那一段带 `aria-current="true"`。

  它从不改文字，也从不增删节点。

`Tsubu` 上还有：

- **`Tsubu.setRuby(root, on)`**：把根元素的 `data-ruby` 设成 `"on"` 或 `"off"`，显示或隐藏已画好的句子的注音。
- **`Tsubu.checkContrast(root, options)`**：在浏览器里测量已画好的句子的颜色，见[主题与对比度](#主题与对比度)。
- **`Tsubu.contrast(foreground, background, backdrop)`**：两个颜色（十六进制、`rgb()`、`rgba()`）的 WCAG 对比度（1 到 21）。半透明的前景先叠到背景上，半透明的背景先叠到 `backdrop` 上（默认白色）。在 Node 里也能用。
- **`Tsubu.CONTRAST`**：阈值，`{ text: 4.5, ruby: 4.5, underline: 3, highlight: 3 }`。
- **`Tsubu.THEMES`**：`["light", "dark", "media"]`；**`Tsubu.SPEAKERS`**：`["a", "b"]`。
- **`Tsubu.version`**：`"0.1.0"`。
- **`Tsubu.STATES`**：`["future", "current", "past"]`。

某个 `t` 画出来的帧和之前调过哪些 `t` 无关，所以可以在视频渲染器的逐帧回调里、在逐帧截图的无界面浏览器里、或者在媒体元素的时间更新事件里调用 `apply(root, t)`，得到的画面都一样。需要淡入或其他缓动时，在你自己的 CSS 里用 `progress`（`--tsubu-progress`）算，不要用过渡。

## CSS 自定义属性

设在 `.tsubu` 或任何祖先元素上（气泡、卡片、主题的 `:root` 都可以）。字体和字号继承页面。

版面和形状：

| 属性 | 默认值 | 含义 |
|---|---|---|
| `--tsubu-line-height` | `1.75` | 行高 |
| `--tsubu-ruby-reserve` | `0.3em` | 第一行上方给注音留的空间 |
| `--tsubu-ruby-size` | `0.5em` | 注音字号（相对正文） |
| `--tsubu-ruby-weight` | `400` | 注音字重 |
| `--tsubu-underline-style` | `dotted` | 下划线线型（任意 `border-style`） |
| `--tsubu-underline-width` | `0.06em` | 下划线粗细 |
| `--tsubu-underline-offset` | `0.02em` | 下划线在段的框底下方多远 |
| `--tsubu-underline-inset` | `0.12em` | 下划线两端各缩进多少，让相邻的下划线分开 |
| `--tsubu-current-spread` | `0.06em` | 高亮超出文字多少（用 `box-shadow` 画，不占位置） |
| `--tsubu-current-radius` | `0.18em` | 高亮圆角（timing 为 `"sentence"` 时为 0，整句每行是一整条） |
| `--tsubu-plate-spread` | `0px` | 底板超出句子的框多少（不占位置） |
| `--tsubu-plate-radius` | `0` | 底板圆角 |
| `--tsubu-progress` | 由 `apply` 写入 | 0 到 1；在你自己的 CSS 里读取，不要自己设 |

颜色 token 按组划分。基础组用在第一次 `apply` 之前和 timing 为 `"none"` 时；每个状态的组都回退到基础组，所以只设基础组的颜色就能给全部换色。

| 组 | 文字 | 注音 | 下划线 | 背景 |
|---|---|---|---|---|
| 基础 | `--tsubu-text-color`（继承） | `--tsubu-ruby-color`（`#6b7280`） | `--tsubu-underline-color`（`#9ca3af`） | |
| future | `--tsubu-future-color` | `--tsubu-future-ruby-color` | `--tsubu-future-underline-color` | |
| current | `--tsubu-current-color` | `--tsubu-current-ruby-color` | `--tsubu-current-underline-color` | `--tsubu-current-bg`（`#e5e7eb`），即高亮 |
| past | `--tsubu-past-color` | `--tsubu-past-ruby-color` | `--tsubu-past-underline-color` | |
| 说话人 *name* | `--tsubu-speaker-`*name*`-color` | `--tsubu-speaker-`*name*`-ruby-color` | `--tsubu-speaker-`*name*`-underline-color` | `--tsubu-speaker-`*name*`-bg` |
| 底板 | | | | `--tsubu-plate-bg`（透明），在整句后面 |

根元素带某个 `data-speaker` 时，那个说话人的组代替 current 组；主题没给这个说话人定义的颜色，就用 current 组。`tsubu.css` 只映射了说话人 `a` 和 `b`；别的名字照抄那条四行的 `.tsubu[data-speaker="a"]` 规则即可。`--tsubu-backdrop` 不会画出来：它写的是主题设计时假定的背景色，给 `checkContrast` 用。

高亮盖住的是那一行文字，不包括上面的注音，所以正在读的那一段的注音是落在页面上的：它的颜色要在页面上看得清，而不是在高亮上。

状态、主题和说话人只改变颜色、背景和 `box-shadow`，从不改字重、内边距或尺寸，所以它们都不会让任何字移动。

## 主题与对比度

用 `options.theme`，或者在任何祖先元素上设 `data-tsubu-theme` 来选预设（在页面或播放器上设一个属性，里面所有句子都用这个主题）：

| `data-tsubu-theme` | 用途 | 检查时的背景（`--tsubu-backdrop`） |
|---|---|---|
| `light` | 白色或近白页面上的深色文字；蓝色高亮配白字 | `#ffffff` 和 `#f1f5f9` |
| `dark` | 深色页面上的浅色文字；浅蓝高亮配深色字 | `#0f172a` 和 `#1e293b` |
| `media` | 叠在图片或视频上：句子后面一块半透明的黑色底板，黄色高亮 | 任意：底板分别叠在纯黑和纯白上检查 |

每套预设也给说话人 `a`（用预设自己的高亮）和 `b`（琥珀色；media 里是青色）定义了颜色。要改预设里的某一个颜色，就设在 `.tsubu` 元素本身上；或者把主题设在祖先上，把颜色设在它里面的任何元素上：设在根元素上的预设会盖过它继承来的值。

不设主题时的默认值不是预设，也不做检查：文字颜色继承页面，浅灰的高亮和灰色下划线在白底上达不到 3:1。在意对比度时，请用预设，或者自己检查颜色。

**阈值**是 `Tsubu.CONTRAST`，依据 WCAG 2.2：文字和注音 4.5:1（1.4.3，普通字号；注音很小，tsubu 也不知道你的字号，所以从不用大字号的放宽），下划线和高亮相对周围 3:1（1.4.11，跟读时需要看清的图形）。

**`Tsubu.checkContrast(root, options)`** 测量浏览器为已画好的句子算出的颜色，覆盖每个状态：`"static"`（第一次 `apply` 之前，以及 timing 为 `"none"`）、`"future"`、`"current"` 和 `"past"`。对每一段，它检查文字、注音和下划线相对它们后面的颜色（半透明的颜色先叠到下面的颜色上），以及高亮相对周围的底板和背景。高亮盖住某一层的中线时，那一层才算在高亮上，所以高亮段上方的注音是对着页面检查的。它在句子的一个隐藏副本上测量，测完就删掉，页面保持原样。

```js
const result = Tsubu.checkContrast(root);
// { ok, checks: [{ state, layer, foreground, background, backdrop, ratio, minimum, ok }], failures }
Tsubu.checkContrast(root, { backdrop: "#fdf6e3", thresholds: { text: 7 } });  // 你的页面，文字按 AAA
```

背景依次取 `options.backdrop`（一个颜色、一组颜色，或表示黑和白的 `"any"`）、主题的 `--tsubu-backdrop`、根元素各祖先的背景色叠在白色上的结果。它看不到背景图片、`text-shadow` 和抗锯齿：叠在图片上时，请用 `media` 底板，或者把图片最亮和最暗的颜色作为背景传进去。

## 版面保证，以及怎么测

下面每一条都在无界面 Chromium 里实际测量页面来检查（见 `tests/test_layout.py`）：

- **开关注音什么都不动。** 隐藏的注音用 `visibility: hidden`，不用 `display: none`，所以仍然占位：如果用 `display: none`，读音比汉字宽的词会变窄，后面所有的字都会移动。测试记下每个字、每一段、每个读音的框，然后开关注音、来回改变 `t`，要求每个框都留在原处，单行和两行都测。
- **高亮什么都不动。** 同一个测试：在许多 `t` 值之间比较这些框。
- **换主题或说话人什么都不动**（`tests/test_theme.py`）：每套预设和每个说话人，设在根元素上和祖先上，在几个 `t` 值下，都和不设主题时的框比较。`media` 的底板是句子后面一个定位的图层，不占位置。
- **每套预设都达到对比度阈值**（`tests/test_theme.py`），每个状态、每个说话人都测，用 `checkContrast` 在库自己的 CSS 上测量。测试也确认低于阈值的颜色会被报告出来，以及高亮上方的注音是对着页面而不是对着高亮测量的。
- **注音不被裁掉，也不碰到上一行。** `--tsubu-ruby-reserve` 在第一行上方留出空间，因为各浏览器对"第一行的行框是否撑高来放注音"做法不同；有了这个留白，读音就留在句子的框里（因此也在 `overflow: hidden` 的容器里）。测试检查每个读音都在根元素之内，并且避开上一行的字和下划线。如果调大注音字号或调小行高，要一起调大这个留白。
- **读音比汉字宽时不会把汉字拉开。** tsubu 设了 `ruby-align: center`；默认的 `space-around` 会在汉字之间插入空隙。测试在截图里比较带注音和不带注音时汉字的墨迹宽度，并确认 `space-around` 的情况会被测出来。
- **每段有自己的下划线。** 下划线是每段自己的 `::after`，两端缩进，段上没有 `text-decoration`，所以相邻的下划线不会连在一起。测试检查同一行相邻两段下划线之间的间隙。
- **只在段与段之间断行，标点不在行首**，在几种容器宽度下都测。
- **没有动效。** 每个元素都是 `transition: none` 和 `animation: none`；反复调用 `apply` 得到相同的属性、文字和节点数。

状态逻辑（`tests/test_state.py`）在 Node 里运行 `tsubu.js` 本身：左闭右开的时间段、空隙、标点、进度、每一种被拒绝的输入，以及 `stateAt` 只取决于 `t`。

## 浏览器支持

如实说明：

- 目前**只在 Chromium 里测过**（Playwright 自带的版本，写这份说明时是 Chromium 138）。Firefox 和 WebKit 还没有跑过版面测试。
- "宽读音不拉开汉字"这条保证需要 `ruby-align`。据 MDN，**Chrome 128** 和 **Safari 18.2** 起支持。在更旧的浏览器里，注音开关仍然不会重排，但读音比汉字宽时汉字会被拉开。
- 脚本用了 ES2015 以上的语法（`const`、箭头函数、模板字符串）和 `:scope` 选择器。
- 还不输出 `<rp>` 后备括号，所以不支持 ruby 的浏览器会把读音直接显示在汉字后面。

已知限制：读音比汉字宽很多时（一週間上的いっしゅうかん），ruby 的框取读音的宽度，汉字两边会出现明显的空隙；浏览器不让读音伸到相邻的假名上方。

## 运行测试

需要：

- `PATH` 上有 Node 18 或更新的版本（用 Node 22 测过）；
- Python 3.9 或更新的版本（用 3.13 测过），装好 `pytest` 和 `playwright`，以及 Playwright 的 Chromium：

  ```sh
  python -m pip install pytest playwright
  python -m playwright install chromium
  ```

然后在仓库根目录用一条命令跑全部测试（状态、版面和演示页）：

```sh
python -m pytest -q
```

版面测试使用系统里的日文字体（Hiragino Sans、Noto Sans JP 或 Noto Sans CJK JP）；测量都是相对的，换别的 CJK 字体结果应该相同。

## 文件

| 文件 | 内容 |
|---|---|
| `tsubu.js` | 库本身：一个普通脚本，在页面里定义 `Tsubu`，在 Node 里是 `module.exports` |
| `tsubu.css` | 样式；可调的都是自定义属性 |
| `demo/index.html` | 演示页：拖动时间、开关注音、选主题，还有一段对话；地址可带 `?t=秒数&ruby=off&theme=dark` |
| `tests/` | 测试（pytest；状态用 Node，版面用 Playwright 的 Chromium） |
| `assets/` | logo |

## 许可证

MIT，见 [LICENSE](LICENSE)。计划中的工作见 [ROADMAP.md](ROADMAP.md)（英文），变更记录见 [CHANGELOG.md](CHANGELOG.md)。
