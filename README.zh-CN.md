<p align="center"><img src="assets/logo.svg" alt="tsubu" width="200"></p>

# tsubu

[English](README.md) · [简体中文](README.zh-CN.md)

**tsubu**（粒，米粒的"粒"）是一个很小、零依赖的浏览器库，只渲染一句话，用于跟读和语言学习：

- 句子传进来时已经切好了段（日语里就是文节），一段一粒；
- 每段有自己的一条点状下划线；
- 可选的注音（`<ruby>`）可以开关，**开关时任何一个字都不移动**；
- 正在读的那一段（或整句）按时间戳高亮，而且是**时间的纯函数**：`stateAt(t)` 和 `apply(root, t)`。不用 `requestAnimationFrame`、不用计时器、不用 CSS 过渡，所以逐帧截图录视频和实时播放画出来的完全一样；
- 颜色是一组组的 token，每个状态一组；有浅色页面、深色页面、叠在图片或视频上三套预设，对话里每个说话人可以有自己的颜色。每套预设的对比度都按库里自带的、基于 WCAG 的阈值实际测量；
- 占好几行的句子只在段与段之间、按日语禁则断行，各行长度接近，字号可以随容器变化，超过最大行数时按 `t` 翻页。

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
  announceRuby: true,          // 读屏软件是否朗读注音（默认 true）
  theme: "light",              // 预设："light"、"dark"、"media"，或你自己起的名字
  speaker: "a",                // 这句话是谁说的，用于按说话人上色："a"、"b" 或你自己起的名字
  motion: "mask",              // Tsubu.MOTIONS 里的动效预设：一个名字、空格分隔的列表或数组
  writing: "vertical",         // "horizontal"（默认）或 "vertical"
  combineUpright: 2,           // 竖排时，不超过这么多个的半角字符直立显示（0-4）
}
```

- **段**（segment）是一个朗读单位。它的 `parts` 是文字片段；带 `ruby` 的片段画成 `<ruby>text<rt>ruby</rt></ruby>`，所以带读音的词不会被拆开。
- `kind: "punct"` 表示标点：没有下划线，永远不会是正在读的那一段，也不能带时间。
- 一段可以带 `id`（非空字符串，句内唯一）和 `tags`（小写名字，比如 `["new-word"]`）。它们属于调用方：tsubu 把它们写成 `data-id` 和 `data-tags`，不赋予任何含义。给标签上样式用的是和其他地方一样的 token，比如 `.tsubu-seg[data-tags~="new-word"] { --tsubu-future-color: #be123c; }`；`checkContrast` 会测量由此得到的颜色。标签的样式只改颜色和线条，这样不会让字移动。
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
- `segments`、`parts`、`text`、`ruby` 或 `lang` 为空，`kind` 不认识，`options.ruby` 或 `options.announceRuby` 不是布尔值，`options.theme`、`options.speaker` 不是小写名字（`a-z`、数字和 `-`，以字母开头），或者 `options.motion` 里有 `Tsubu.MOTIONS` 之外的预设；
- `id` 为空或不是字符串，同一个 `id` 用了两次，或者 `tags` 不是小写名字组成的数组。

## 输出

`Tsubu.sentence()` 返回一个冻结的对象：

- **`html`**：一段 HTML 字符串，

  ```html
  <span class="tsubu" lang="ja" data-timing="segments" data-ruby="on">
    <span class="tsubu-unit"><span class="tsubu-seg" data-index="0">…</span><span class="tsubu-seg" data-index="1" data-kind="punct">、</span></span>
    <wbr><span class="tsubu-unit"><span class="tsubu-seg" data-index="2">…</span></span>…
  </span>
  ```

  （实际没有这些空白）。给了 `options.theme` 时根元素还带 `data-tsubu-theme`，给了 `options.speaker` 时带 `data-speaker`。标点段带 `data-kind="punct"`。段被分进一个个单元，行只在单元之间断开（见[多行](#多行)）：一段不会被拆到两行；不能出现在行首的段（以闭合符号、`ー` 或小假名开头的段）和它前面那段在同一个单元里，紧跟在开括号后面的段也是。所有文字都经过 HTML 转义。刚生成的 HTML 不带状态，`apply` 之后才有。
- **`timing`**：`"segments"`、`"sentence"` 或 `"none"`。
- **`span(i)`**：第 `i` 段自己的时间 `{ start, end }`，点中它时把调用方的音频跳到这里（`i` 用 `Tsubu.segmentOf(event.target)` 得到）；标点，以及没有逐段时间的句子，返回 `null`，因为不做任何估算。
- **`find(id)`**：带这个 `id` 的段的下标，没有就是 `null`。
- **`stateAt(t)`**：只取决于 `t` 的纯函数，返回

  ```js
  { timing, state, progress, current, segments: [{ state, progress }] }
  ```

  - `state` 是 `"future"`、`"current"` 或 `"past"`。每个时间段都是左闭右开的 `[start, end)`：`t < start` 是 future，`start <= t < end` 是 current，`t >= end` 是 past。两段之间有空隙时，前一段是 past，后一段是 future，没有 current 的段。
  - `progress` 是整句或该段从 0 到 1 的进度。timing 为 `"sentence"` 时各段的 `progress` 是 `null`（不知道）；标点的永远是 `null`。
  - `current` 是正在读的那一段的下标，没有就是 `null`。timing 为 `"sentence"` 时永远是 `null`。
  - timing 为 `"segments"` 时，标点和它前面那个非标点段一起变成 past；句首的标点在第一个非标点段开始时变成 past。timing 为 `"sentence"` 时，每一段（包括标点）的状态都和整句相同。
- **`htmlAt(t, { revealed })`**：不需要页面，把第 `t` 秒那一帧作为 HTML 字符串返回：也就是带上 `apply(root, t)`（以及 `setRevealed(root, revealed)`）会写的那些属性的 `html`。用在服务器上、Node 里，或者接受 HTML 的渲染器里（服务端渲染、HTML 转图片、视频渲染器的逐帧画面）。测试检查它和刚生成的 `html` 在 Chromium 里经过 `apply` 之后是同样的元素树、文字和属性，在 Chromium 里连字符串都相同。它不翻页（翻页需要版面），和 `stateAt` 一样，句子没有时间时会拒绝。
- **`apply(root, t)`**：把 `stateAt(t)` 写到页面上并返回它。`root` 必须是由 `html` 生成的那个 `.tsubu` 元素（是别的元素或段数不对就抛错）。它只设置属性：
  - 根元素：`data-state`、`--tsubu-progress`；timing 为 `"sentence"` 的句子正在读时带 `aria-current="true"`；
  - 每一段：`data-state`、`--tsubu-progress`（只有带时间的段）；正在读的那一段带 `aria-current="true"`；
  - 设了最大行数时（见[按 t 翻页](#按-t-翻页)）：根元素带 `data-page` 和 `data-pages`，不在当前页的段带 `data-off-page`。这时返回的对象还有 `page`（从 0 开始）和 `pages`；句子不翻页时两者都是 `null`。

  它从不改文字，也从不增删节点。

`Tsubu` 上还有：

- **`Tsubu.setRuby(root, on)`**：把根元素的 `data-ruby` 设成 `"on"` 或 `"off"`，显示或隐藏已画好的句子的注音。
- **`Tsubu.setRevealed(root, which)`**：揭示动效预设在"还没听到"时隐藏的段。`which` 是段下标的数组、`"all"` 或 `"none"`，会替换之前的集合。它写入 `data-revealed` 并返回下标。见[动效与揭示](#动效与揭示)。
- **`Tsubu.segmentOf(node)`**：某个节点（比如事件的 target）所在的段的下标，不在任何段里就是 `null`；给点击、轻触的处理函数用。
- **`Tsubu.MOTIONS`**：动效预设的目录。
- **`Tsubu.checkContrast(root, options)`**：在浏览器里测量已画好的句子的颜色，见[主题与对比度](#主题与对比度)。
- **`Tsubu.checkFit(root, options)`**：测量已画好的句子在它所在的地方是否放得下：在它的容器里（`options.container`，否则是根元素的父元素），按它在那里的字号、字体和宽度。它在一个隐藏副本上测量（所有段都显示、注音打开），按 `t` 翻页的句子逐页检查。返回 `{ ok, issues, lines, pages }`；每个问题是 `{ kind, segment, page, by, message }`，`by` 以像素计：
  - `"overflow"`：某段超出容器的内边距框；
  - `"too-wide"`：不能分开的几段比一行（或一列）还长，只会溢出：缩短这一段或调小字号；
  - `"ruby-clipped"`：注音超出容器：调大 `--tsubu-ruby-reserve` 或给容器留出空间；
  - `"too-many-lines"`：不能翻页的句子超过了 `--tsubu-max-lines`。

  库本身的保证已经在各种宽度的网格上测过（见下文）；`checkFit` 是给调用方、或替调用方工作的 agent，在自己的容器、字体和句子上运行的。
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
| `--tsubu-underline-offset` | `0.02em` | 下划线在文字的 em 框下方多远 |
| `--tsubu-underline-inset` | `0.12em` | 下划线两端各缩进多少，让相邻的下划线分开 |
| `--tsubu-current-spread` | `0.06em` | 高亮超出文字的 em 框多少（画在一个定位的图层上，不占位置） |
| `--tsubu-current-radius` | `0.18em` | 高亮圆角（timing 为 `"sentence"` 时为 0，整句每行是一整条） |
| `--tsubu-plate-spread` | `0px` | 底板超出句子的框多少（不占位置） |
| `--tsubu-plate-radius` | `0` | 底板圆角 |
| `--tsubu-wrap` | `balance` | 句子的 `text-wrap`：`balance`、`pretty` 或 `wrap` |
| `--tsubu-max-lines` | `none` | 超过这么多行就按 `t` 翻页 |
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

高亮盖住的是文字的 em 框，不包括上面的注音，所以正在读的那一段的注音是落在页面上的：它的颜色要在页面上看得清，而不是在高亮上。

状态、主题和说话人只改变颜色和一个定位图层的背景，从不改字重、内边距或尺寸，所以它们都不会让任何字移动。

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

**内容区偏高的字体。** 一段自己的框是字体的内容区（content area）；许多网页字体（Noto Sans JP 以及整个 Noto / 思源家族、Shippori Mincho、Zen Kaku Gothic）的内容区约有 1.45em 高，比文字的 em 框高出 0.28em，伸进了上方的注音里，而注音的墨迹就贴在汉字 em 框的上沿。所以高亮和下划线不是按这个框画的，而是按 em 框画：一条 1em 高的带子，再向外伸 `--tsubu-current-spread`；下划线在 em 框下方 `--tsubu-underline-offset` 处。CSS 读不到字体的 ascent，所以 em 框在内容区里的位置按多出高度的固定比例来定（横排时上方 62%、下方 38%；竖排时各一半，Chromium 在竖排里把 em 框居中），这对内容区就是 em 框的 Hiragino Sans 和整个 Noto 家族都是精确的，对其余字体误差在百分之几 em 以内。因此不管什么字体，正在读的那一段的注音都落在页面上，`checkContrast` 也在高亮实际画出的位置上测量。

## 多行

### 断行

行只在段与段之间断开，而且不在日语禁则不允许的地方断：闭合括号和标点、长音符 `ー`、小假名、叠字符号、中点和冒号不出现在行首，开括号不出现在行尾（即 CSS `line-break: strict` 的那一组）。这些规则由 tsubu 自己执行：不能分开的段放在同一个 `white-space: nowrap` 单元里，单元之间的 `<wbr>` 给出断行的位置。

为什么不交给浏览器的 `line-break`：Chromium 把绝对定位的框（比如每段的下划线）当作可以断行的地方，而且在那里不执行它的断行规则；`<wbr>` 同样会绕过这些规则。这两点都实测过（Chromium 139）。规则只看调用方切出来的每段的首字和末字，不看段的内部，反正段内从不断行。比一行还宽的段会超出这一行，而不会被拆开。闭合标点不会悬挂到行外（Chromium 不支持 `hanging-punctuation`），所以一段会和它后面的逗号一起换到下一行。

### 均衡换行

句子设了 `text-wrap: balance`（用 `--tsubu-wrap` 修改），所以占好几行的句子各行长度接近，最后一行不会只剩一段。均衡由浏览器完成：Chromium 只均衡不超过六行的块，更长的照常贪心断行（在 Chromium 139 里实测）；据 MDN，Firefox 的上限是十行。下面的翻页能让每页都足够短。

### 字号随容器变化

放在带 `tsubu-fluid` 类的元素里时（这个元素会成为名为 `tsubu` 的查询容器），句子的字号等于容器宽度除以每行字数，并限制在最小值和最大值之间。tsubu 其他尺寸都用 `em`，所以间距、注音和下划线一起缩放。宽度分成三档；分档的位置是固定的，因为容器查询读不了自定义属性，但每一档的每个值都可以配置：

| 档 | 容器宽度 | 每行字数 | 最大行数 |
|---|---|---|---|
| 窄 | 小于 480px | `--tsubu-narrow-chars`（`11`） | `--tsubu-narrow-max-lines`（否则用 `--tsubu-max-lines`） |
| 中 | 480px 到 960px | `--tsubu-chars`（`15`） | `--tsubu-max-lines` |
| 宽 | 960px 及以上 | `--tsubu-wide-chars`（`18`） | `--tsubu-wide-max-lines`（否则用 `--tsubu-max-lines`） |

`--tsubu-size-min`（`14px`）和 `--tsubu-size-max`（`72px`）在每一档都限制字号。手机上 280px 宽的对话气泡大约是 25px 的字；1280px 宽的 16:9 画面是 71px。容器要有自己的宽度：查询容器不根据内容决定宽度，所以随文字收缩的气泡要改为给定宽度或 `max-width`。不加 `tsubu-fluid` 时字号照旧继承。

```html
<div class="tsubu-fluid" style="width: 100%; --tsubu-narrow-max-lines: 3; --tsubu-max-lines: 2">
  <!-- 由 Tsubu.sentence() 生成的 .tsubu 元素 -->
</div>
```

### 按 t 翻页

设了 `--tsubu-max-lines`（设在句子或任何祖先上，或按档设）时，超过这么多行的句子一次只显示一页，由 `apply(root, t)` 决定显示哪一页：

- 正在读的那一段所在的页；
- 两段之间，刚读完的那一段所在的页；第一段之前是第一页；最后一段之后是最后一页。

页来自版面：`apply` 把整句贪心排一遍，每 `--tsubu-max-lines` 行为一页，所以每页都从行首开始；单独显示时它断成同样的几行，再在页内均衡。显示哪一页只取决于 `t` 和这个版面，和之前的调用无关：不滚动，也不估算。因为要读版面，请在字体加载完之后（`document.fonts.ready`）调用 `apply`，容器尺寸变化后也要再调用一次。

没有每段时间的句子（timing 为 `"sentence"`）从不翻页，因为不知道读到了哪一部分：整句都显示。其他页的段是 `display: none`，所以在翻到那一页之前，辅助技术也读不到它们。

## 竖排

```js
Tsubu.sentence(input, { writing: "vertical" })   // 或在任一祖先元素上写 data-tsubu-writing="vertical"
```

`options.writing`（`"horizontal"` 或 `"vertical"`）会在根元素上写入 `data-tsubu-writing`。和 `data-tsubu-theme` 一样，这个属性写在祖先元素上也有效；根元素上的 `"horizontal"` 可以让句子在竖排的祖先里保持横排。竖排就是 `writing-mode: vertical-rl`：列从右向左排，注音在字的右侧，每段的下划线变成它**左侧的点状边线**，两端内缩。注音预留空间变成第一列右侧的空白。高亮、它的外扩和 `media` 底板是随文字一起转过来的同一组盒子；`underline-draw` 从上往下画出边线。列长就是句子的高度，所以请给容器设定高度；不设时，句子高度取决于内容，最高到视口高度。

**数字和拉丁字母。** 不超过 `options.combineUpright` 个字符（0 到 4，默认 2）的半角字符串（空格和括号以外的 ASCII）会用 `text-combine-upright` 在列中横向直立显示（10月、AI、!?）；更长的字符串侧躺（`text-orientation: mixed`），比如 2025年。Chromium 会把任何直立字符串压进一个 em，所以上限是四个字符。除非句子用自己的选项指定为横排，这些字符串都会包在 `<span class="tsubu-upright">` 里，因为画好之后祖先还可能把它变成竖排；这个 span 在横排里不起作用（实测各个框相差不超过 1/64 px）。

**标点、括号和长音符 ー** 用字体的竖排替代字形。用 Hiragino Sans 或 Noto Sans CJK 时，Chromium 把 、。 画在右上方，ー 画成竖线，括号转过来（从截图实测）。没有竖排替代字形的字体会让部分符号保持横排的形状。

**保证。** 横排的所有保证在竖排里以"列"代替"行"同样成立，由 `tests/test_vertical.py` 测试：开关注音、高亮、换主题或说话人都不移动任何字；每一帧只取决于 `t`；只在单元之间并按禁则换列；`checkContrast` 沿列的横向测量（注音对着页面，边线在高亮的外扩之内）；强制颜色下仍保留高亮。**翻页**按列计数：`--tsubu-max-lines` 就是每页的列数，从右边数起。

**随容器缩放。** 竖排里列沿容器的高度延伸，所以由高度决定字号：`.tsubu-fluid` 容器成为尺寸容器（必须有确定的高度），字号等于它的高度除以每列字数，三个档（480px、960px）和它们的属性也按高度划分。这用到了 `:has()` 和 `cqh`。

## 动效与揭示

动效预设改变句子显示"已经听到"和"还没听到"的方式。每一个都由 `tsubu.css` 根据 `apply` 写的状态画出来，所以每一帧仍然只取决于 `t`；没有定时器，也没有过渡。用 `options.motion` 或任何祖先上的 `data-tsubu-motion` 选择，可以组合几个。*还没听到*是指既不是 current 也不是 past：在未来，或者句子还没被 apply 过（timing 为 `"none"`）。

| 预设 | 画出来的样子 |
|---|---|
| `appear` | 段在被读到时出现；还没听到的什么都不画，连下划线也不画 |
| `mask` | 还没听到的段是空格：不画文字和读音，但画下划线，所以能看出后面还有多长；用于听力和填空练习 |
| `blur` | 还没听到的段连同读音一起模糊（`--tsubu-blur`，`0.15em`） |
| `underline-draw` | 正在读的那一段的下划线在这段时间里逐渐画出来；还没听到的段还没有下划线 |

**由调用方的事件来揭示。** `Tsubu.setRevealed(root, [2, 3])` 让第 2、3 段像已经听到一样显示出来，不管 `t` 是多少：比如学习者说对了一个词、点了一下、按了按钮。tsubu 自己不处理任何事件。`Tsubu.segmentOf(event.target)` 告诉点击处理函数点中了哪一段。这样画出来的东西只取决于 `t` 和已揭示的集合，`htmlAt(t, { revealed })` 不需要页面就能画出同样的结果。

```js
const s = Tsubu.sentence(input, { motion: "mask" });   // 没有时间：每段一开始都是空格
let shown = [];
root.addEventListener("click", (event) => {
  const i = Tsubu.segmentOf(event.target);
  if (i !== null) shown = Tsubu.setRevealed(root, [...shown, i]);
});
recogniser.onCorrect = (i) => { shown = Tsubu.setRevealed(root, [...shown, i]); };  // 你自己的语音判断
```

`Tsubu.MOTIONS` 是同一份清单的数据形式：每个预设的 `name`、`purpose`、需要的 timing（`needs`）、没有那种 timing 时怎么办（`without`）、参数 `parameters`（自定义属性、默认值、范围、含义）、在 `prefers-reduced-motion: reduce` 下怎么办，以及能否被揭示（`revealable`）。测试检查目录和样式表一致。

**怎么选动效（给 agent 和模板作者）。** 从目录里选，不要自己发明动效；动效只用来表现"读到哪儿了"的变化，不用来装饰。

- 普通跟读、字幕：不用预设。高亮已经表明读到哪儿了。
- 在视频里逐行讲解一句话：`appear`；整句要一直可读时用 `underline-draw`。
- 听力和听写：`mask`（空格显示长度）或 `blur`（显示轮廓），按时间或按学习者的回答揭示。
- 不要把 `appear` 和 `mask` 或 `blur` 组合：它们要藏的东西 `appear` 已经都藏了。也不要把 `mask` 和 `underline-draw` 组合：后者让还没听到的段没有线，填空就失去了表示长度的那条线。
- timing 为 `"sentence"` 时，预设一次作用于整句；照实告诉观看者，不要加暗示有逐段时间的动效。
- 不要用透明度把读过的部分调暗：会低于对比度阈值。用 past 颜色组，主题已经在阈值之内设好了。

没有提供：逐字擦除，因为那需要 tsubu 没有的逐字时间。在 `prefers-reduced-motion: reduce` 下，`underline-draw` 一次把下划线画完；其他几个是状态变化，不是移动。被 `mask` 藏起来的文字仍在页面里，读屏软件会读出来；用来考试时，请不要把答案放进页面，或者用 `appear`。`checkContrast` 在它的副本里揭示所有段，所以所有可能画出来的颜色都被检查，而且它会把图层上的透明度算进去。

## 录制视频

每一帧只取决于 `t`，所以一段视频就是按每帧时间循环一遍。有两个示例，测试（`tests/test_examples.py`）都会运行它们，用的是 `examples/sentence.json`：

- **`examples/capture-frames.py`** 在无界面 Chromium 里画出句子，在每帧的时间调用 `apply(root, t)`，每帧存一张 PNG，然后打印把帧和你的音频合成视频的 ffmpeg 命令（它不运行这条命令）：

  ```sh
  python examples/capture-frames.py examples/sentence.json frames --fps 30 --theme media --motion appear
  ```

- **`examples/frames-from-node.mjs`** 不需要浏览器，用 `htmlAt(t)` 把每一帧写成一个 HTML 页面，给接受标记的渲染器用：

  ```sh
  node examples/frames-from-node.mjs examples/sentence.json frames 30
  ```

测试先按顺序、再倒序渲染所有帧，要求 PNG 逐字节相同。它发现了一件事：在同一个元素上逐帧调用 `apply`，状态是一样的，但 Chromium 只重画变化的部分；高亮的圆角压在半透明的 `media` 底板上时，边缘的几个像素会受前一帧影响。示例在每帧都用一份新的句子副本来画（`innerHTML = s.html`，然后 `apply`），这样任何顺序画出的帧都相同，也可以并行渲染。在逐帧绘制标记的渲染器里（比如 Remotion 的 composition），渲染 `s.htmlAt(frame / fps)` 即可（这里没有测试：测试套件里没有 Remotion）。

## 导出字幕

可选脚本 `tsubu-export.js` 把同样的输入转成字幕。在 `tsubu.js` 之后加载（它定义 `TsubuExport`），或在 Node 里 `require("./tsubu-export.js")`。输入由 `Tsubu.sentence()` 检查，因此会以相同的错误拒绝。没有时间的句子无法导出，任何时间都不做估算。

- **`TsubuExport.toWebVTT(input, { ruby = true, offset = 0, id })`** 返回一个 WebVTT 文件，只有一条覆盖整句的 cue。每一段是一个类 span：`<c.tsubu-seg>`（标点为 `<c.tsubu-seg.punct>`）；读音写成 `<ruby>雨<rt>あめ</rt></ruby>`。timing 为 `"segments"` 时，每个非标点段的开始处有一个 cue 时间戳，所以 `::cue(:past)` 会跟着朗读走。时间戳严格递增，都在 cue 之内。`ruby: false` 去掉读音，`offset` 以秒平移所有时间，`id` 设置 cue 标识符。`&`、`<`、`>` 会被转义。
- **`TsubuExport.toASS(input, { ruby = "omit", offset = 0 })`** 返回一行 ASS 卡拉 OK `Dialogue:`，使用 `\k` 时长。段与段之间的空隙是一个空音节，标点并入它前面的音节。先把每个边界取整到百分之一秒再求差，所以各时长之和总是等于这一行的长度。ASS 没有 ruby：`ruby: "inline"` 写成 `雨(あめ)`。ASS 无法转义 `{`、`}` 和 `\`，所以写成全角的 ｛ ｝ ＼。**`toASSScript`** 用只含一个 `Default` 样式的最小脚本把这一行包起来。

时间按书写的十进制值四舍五入（到毫秒或百分之一秒），文本里的换行变成空格，负时间会被拒绝。测试（`tests/test_export.py`）在 Node 里检查精确输出，检查 Chromium 把 WebVTT 解析成一条带 span、ruby 和时间戳的 cue；装了带 libass 的 ffmpeg 时，还检查 ASS 卡拉 OK 在每个音节开始时亮起。

## 无障碍

- **强制颜色。** 在强制颜色模式下（Windows 的对比度主题等），浏览器会替换背景，正在读的那一段就和别的段一样了。tsubu 只给这一段保留高亮，用的是用户自己为选中文字设定的颜色（`Highlight` 和 `HighlightText`）；它的注音落在页面上，所以用 `CanvasText`。其余的都交给浏览器。
- **读屏软件。** 默认会在汉字后面读出注音（Chromium 暴露的是「雨 あめ が 降る」）。设 `options.announceRuby: false` 时，每个 `<rt>` 都带 `aria-hidden="true"`，整句只读一遍；注音照样显示、照样能开关。隐藏的注音是 `visibility: hidden`，本来就不会被读出。
- 正在读的那一段带 `aria-current="true"`；其他页的段和那一页一起对辅助技术隐藏（见[按 t 翻页](#按-t-翻页)）。

## 版面保证，以及怎么测

下面每一条都在无界面 Chromium 里实际测量页面来检查（见 `tests/test_layout.py`）：

- **开关注音什么都不动。** 隐藏的注音用 `visibility: hidden`，不用 `display: none`，所以仍然占位：如果用 `display: none`，读音比汉字宽的词会变窄，后面所有的字都会移动。测试记下每个字、每一段、每个读音的框，然后开关注音、来回改变 `t`，要求每个框都留在原处，单行和两行都测。
- **高亮什么都不动。** 同一个测试：在许多 `t` 值之间比较这些框。
- **换主题或说话人什么都不动**（`tests/test_theme.py`）：每套预设和每个说话人，设在根元素上和祖先上，在几个 `t` 值下，都和不设主题时的框比较。`media` 的底板是句子后面一个定位的图层，不占位置。
- **每套预设都达到对比度阈值**（`tests/test_theme.py`），每个状态、每个说话人都测，用 `checkContrast` 在库自己的 CSS 上测量。测试也确认低于阈值的颜色会被报告出来，以及高亮上方的注音是对着页面而不是对着高亮测量的。
- **不管字体的度量如何，高亮都不碰注音**（`tests/test_theme.py`）。用 `ascent-override` 和 `descent-override` 给系统字体套上 Noto Sans JP 的度量（内容区 1.45em，其中 0.28em 在 em 框上方），每套预设在每个状态下仍然达到阈值，横排竖排都测。高亮的带子和下划线在这个字体和系统自己的字体里都对着文字的基线测量；截图里文字的墨迹在带子之内、读音的墨迹在带子之上；在这个字体里也没有字移动。
- **注音不被裁掉，也不碰到上一行。** `--tsubu-ruby-reserve` 在第一行上方留出空间，因为各浏览器对"第一行的行框是否撑高来放注音"做法不同；有了这个留白，读音就留在句子的框里（因此也在 `overflow: hidden` 的容器里）。测试检查每个读音都在根元素之内，并且避开上一行的字和下划线。如果调大注音字号或调小行高，要一起调大这个留白。
- **读音比汉字宽时不会把汉字拉开。** tsubu 设了 `ruby-align: center`；默认的 `space-around` 会在汉字之间插入空隙。测试在截图里比较带注音和不带注音时汉字的墨迹宽度，并确认 `space-around` 的情况会被测出来。
- **每段有自己的下划线。** 下划线是每段自己的 `::after`，两端缩进，段上没有 `text-decoration`，所以相邻的下划线不会连在一起。测试检查同一行相邻两段下划线之间的间隙。
- **只在段与段之间、按日语禁则断行**（`tests/test_lines.py`），在许多容器宽度下测，包括一个故意切得让段以 `っ` 和 `ー` 开头、旁边还有括号和逗号的句子。
- **在容器宽度和句子长度组成的网格上**（`tests/test_lines.py`，流式容器里 200px 到 1280px 共 7 种宽度，从一行到很多行共 5 个句子）：没有内容超出容器，没有两个字、ruby 或读音重叠，没有读音在顶部被裁掉，开关注音没有字移动。
- **均衡换行**：在贪心排版不超过六行、最后一行只剩一段的地方，均衡后的最后一行都不止一段，各行长度也更接近。
- **流式字号**在每个分档点和它两边检查，默认值和每一档都配置过的情况都测。
- **翻页**：设了最大行数时，每一段被读时都在当前页上，没有一页超过允许的行数，每页从行首开始，各页没有共同的段、合起来包含全部的段，随 `t` 增大只往后翻，两段之间的空隙保持刚读完那段的页，同一个 `t` 总是显示同一页，开关注音不会让一页重排。
- **强制颜色和读屏**（`tests/test_a11y.py`）：模拟强制颜色时，每种主题、每种 timing 下正在读的那一段都是系统高亮色，而且没有字移动；关掉 `announceRuby` 时，无障碍树里没有注音。
- **动效预设**（`tests/test_motion.py`）：每个预设只对还没听到的段画出它说的样子，被揭示的段和不用预设时一样，任何预设和揭示都不让字移动，不管 `t` 和揭示以什么顺序来，截图逐字节相同，每种主题配上每个预设都达到阈值，目录和样式表一致。
- **没有动效。** 每个元素都是 `transition: none` 和 `animation: none`；反复调用 `apply` 得到相同的属性、文字和节点数。

状态逻辑（`tests/test_state.py`）在 Node 里运行 `tsubu.js` 本身：左闭右开的时间段、空隙、标点、进度、每一种被拒绝的输入，以及 `stateAt` 只取决于 `t`。

## 浏览器支持

如实说明：

- 竖排只在 Chromium 里实测过：Firefox 和 Safari 的竖排替代字形、`text-combine-upright`，以及竖排的流式字号（`:has()`、`cqh`）都没有检查。
- 目前**只在 Chromium 里测过**（Playwright 自带的版本，写这份说明时是 Chromium 139）。Firefox 和 WebKit 还没有跑过版面测试。
- "宽读音不拉开汉字"这条保证需要 `ruby-align`。据 MDN，**Chrome 128** 和 **Safari 18.2** 起支持。在更旧的浏览器里，注音开关仍然不会重排，但读音比汉字宽时汉字会被拉开。
- 均衡换行用 `text-wrap: balance`（Chrome 114、Firefox 121、Safari 17.5）；不支持时按贪心断行。流式字号用容器查询和 `cqi` 单位（Chrome 105、Firefox 110、Safari 16）。
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
| `tsubu-export.js` | 可选：用同样的输入生成 WebVTT 和 ASS 卡拉 OK 字幕 |
| `examples/` | 录制视频：用 Playwright 生成 PNG 帧，用 Node 生成 HTML 帧 |
| `site/` | 项目网站：首页（短片由 `t` 绘制）、快速开始、指南、API 参考、试验场和画廊，中英双语。页面从同级文件加载库（检出里是符号链接），所以从磁盘直接打开就能看 |
| `demo/index.html` | 演示页：拖动时间、开关注音、选主题，有一段对话和一个流式、会翻页的框；地址可带 `?t=秒数&ruby=off&theme=dark&frame=320&lines=2` |
| `tests/` | 测试（pytest；状态用 Node，版面用 Playwright 的 Chromium） |
| `assets/` | logo |

## 许可证

MIT，见 [LICENSE](LICENSE)。计划中的工作见 [ROADMAP.md](ROADMAP.md)（英文），变更记录见 [CHANGELOG.md](CHANGELOG.md)。
