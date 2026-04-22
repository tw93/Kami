# Design System

## 设计总则

kami 的审美可以浓缩成一句话：**暖米纸底，油墨蓝点缀，serif 承担层级，拒绝冷蓝灰与硬阴影**。

这不是一套 UI 框架，而是一套面向印刷文档的约束系统，目标是让页面稳定、清楚、可读。

**九条规则**（每一条都有代价，破例前先想清楚）：

1. 页面背景 parchment `#f5f4ed`，不用纯白
2. 强调色只有油墨蓝 `#1B365D`，不引入第二种彩色
3. 所有灰色暖调（yellow-brown undertone），禁止冷蓝灰
4. 英文模板: serif 通吃标题和正文。中文模板: 标题 serif，正文 sans。UI 元素 (label, eyebrow, meta) 都用 sans
5. Serif 字重固定 500，不用 bold
6. 行距三档：紧凑标题 1.1-1.3 / 密排正文 1.4-1.45 / 阅读型 1.5-1.55。禁用 1.6+
7. Tag 背景必须实色 hex，禁止 rgba 半透明（WeasyPrint 会渲染出双层矩形）
8. 阴影用 ring 或 whisper shadow，不用硬 drop shadow
9. **禁止 italic**。所有模板和 demo 中不使用 `font-style: italic`，不需要 italic 字体文件

所有文档类型（One-Pager / Long Doc / Letter / Portfolio / Resume / Slides）都依据这份规范。这套系统脱胎于 Anthropic 视觉语言与中文简历设计的长期迭代，两条脉络合并而成。

---

## 1. 色彩系统

**唯一强调色 + 纯暖调中性灰 + 零冷色**是这套设计的核心。

### 主调 · 品牌色

```css
--brand:        #1B365D;   /* Ink Blue Brand - 唯一的彩色，用于 CTA、强调、section-title 左侧竖线 */
--brand-light:  #2D5A8A;   /* 更亮的变体，深色底上的链接偶尔用 */
```

**使用规则**：油墨蓝 `#1B365D` 全文档不超过 **5% 的面积**。超过就是堆砌，不是克制。

### 画布 · 背景色

```css
--parchment:    #f5f4ed;   /* 主页面背景 - 温暖米色，整个设计的情感基础 */
--ivory:        #faf9f5;   /* 卡片/浮起容器 - 比 parchment 更亮的暖白 */
--warm-sand:    #e8e6dc;   /* 按钮默认背景 / 明显的交互表面 */
--dark-surface: #30302e;   /* 深色主题容器 - 暖炭灰 */
--deep-dark:    #141413;   /* 深色主题页面底色 - 不是纯黑，有橄榄绿底色 */
```

**绝对禁止**：`#ffffff` 纯白作页面底 · 任何 `#f8f9fa` / `#f3f4f6` 这类冷灰底。

### 中性文字色

```css
--near-black:   #141413;   /* 主文本 - 最深但不是纯黑，有暖橄榄底色 */
--dark-warm:    #3d3d3a;   /* 次级深色文字 / 深色链接 */
--charcoal:     #4d4c48;   /* 按钮文字 / 高密度正文 */
--olive:        #5e5d59;   /* 副文本 - 描述、caption 等 */
--stone:        #87867f;   /* 三级文字 - 日期、元信息 */
--warm-silver:  #b0aea5;   /* 深色底上的浅色文字 */
```

**记忆法**：每个灰都有 **yellow-brown undertone**。如果你在 `rgb()` 里看到 R ≈ G > B（或 R > G > B 且差距很小），基本就是暖灰。冷灰是 R < G < B（偏蓝）或 R = G = B（中性）。

### 边框与分隔

```css
--border-cream: #e8e5da;   /* 最柔的边框 - 卡片默认 */
--border-warm:  #e0ddd2;   /* 明显的边框 - section 分隔 */
--border-soft:  #e5e3d8;   /* 更淡的虚线分隔 - 列表项之间 */
--border-dark:  #30302e;   /* 深色主题下的边框 */
```

### Ring 阴影（不用传统 box-shadow）

```css
--ring-warm:    #d1cfc5;   /* 按钮 hover/focus 环 */
--ring-deep:    #c2c0b6;   /* 按下状态 */
```

### 功能色（尽量少用）

```css
--error:     #b53333;   /* 错误 - 深暖红，不刺眼 */
--focus:     #3898ec;   /* 聚焦蓝 - 唯一的冷色，只用于 input focus ring，无障碍必要 */
```

### 半透明对应实色对照表（TAG / 标签必须实色）

**原因**：WeasyPrint 渲染 rgba 半透明时 padding 区域和字形区域透明度叠加不一致，放大后产生双层矩形。详见 `production.md Part 4`。

油墨蓝 `#1B365D` 叠加在 parchment `#f5f4ed` 上的等效实色：

| 想要的 rgba 透明度 | 等效实色 hex |
|---|---|
| 0.08 | `#EEF2F7` |
| 0.14 | `#E4ECF5` |
| **0.18** | **`#E4ECF5`** ← tag 推荐默认 |
| 0.22 | `#D0DCE9` |
| 0.30 | `#D6E1EE` |

---

## 2. 字体系统

### 字体栈（按优先级 fallback）

```css
/* Serif 标题（中英文） */
font-family: "TsangerJinKai02",       /* 仓耳今楷，需自备 .ttf */
             "Source Han Serif SC",    /* 思源宋体（免费，Adobe/Google 联合出品）*/
             "Noto Serif CJK SC",      /* 思源宋体的 Google 命名 */
             "Songti SC",              /* macOS 系统宋体 */
             "STSong",                 /* Windows 中文宋体 */
             Georgia, serif;

/* Sans 正文/UI（中英文） */
font-family: "Inter", "TsangerJinKai02",
             -apple-system, BlinkMacSystemFont,
             "Source Han Sans SC", "Noto Sans CJK SC",
             "PingFang SC", "Microsoft YaHei",
             Arial, sans-serif;

/* Mono 代码 */
font-family: "JetBrains Mono", "Fira Code",
             "SF Mono", Consolas, Monaco,
             "Source Han Mono", monospace;
```

### 字号层级（pt 用于 PDF，px 用于屏幕）

**印刷品（A4 PDF）用 pt**：

| 角色 | 字号 | 字重 | line-height | 用途 |
|---|---|---|---|---|
| Display | 36-48 pt | 500 | 1.10 | 封面大标题、one-pager 主标题 |
| H1 Section | 18-22 pt | 500 | 1.20 | 章节大标题 |
| H2 | 14-16 pt | 500 | 1.25 | 子章节 |
| H3 | 12-13 pt | 500 | 1.30 | 条目标题 |
| Body Lead | 11 pt | 400 | 1.55 | 导语、intro |
| Body | 9.5-10 pt | 400 | 1.55 | 正文 |
| Body Dense | 9-9.2 pt | 400 | 1.40 | 密集排版（简历、one-pager 等） |
| Caption | 8.5-9 pt | 400 | 1.45 | 说明文字、图注 |
| Label | 7.5-8 pt | 600 | 1.35 | 小标签、角标 |
| Tiny | 7 pt | 400 | 1.40 | 页脚、minor metadata |

**屏幕（网页/PPT）用 px**：乘以约 1.33 得到等效 px（9 pt ≈ 12 px，18 pt ≈ 24 px）。

### 字重规则

- **Serif 正文**：400（W04 字体文件）
- **Serif 标题**：500（W05 字体文件，真实粗体，非合成）
- **Sans 正文**：400 默认
- **Sans 标签/标题**：500 或 600
- **禁止 900 black 或 100 thin**

**设计原则**：Serif 只用两档字重（400/500），不用合成 bold（600/700），保持版面克制。

### 行距（line-height）三档

中文印刷品比英文网页**更紧凑**。英文网页常见的 1.6-1.75 是针对英文字母和非 fixed-width 的 body 优化的，放在中文 pt 字号的印刷品里会显得松散。

| 档位 | 值 | 用于 |
|---|---|---|
| 紧凑标题 | 1.10-1.30 | 大标题、Display、H1、H2 |
| 密排正文 | 1.40-1.45 | Body Dense（简历、one-pager、名片、索引卡） |
| 阅读型正文 | 1.50-1.55 | Body（long-doc 章节正文、letter 正文） |
| 标签 / caption | 1.30-1.40 | 小字标签、多行 metadata |

**禁用**：
- 1.60+ - 英文网页的节奏，中文印刷会显得松散
- 1.00-1.05 - 除非极致紧凑标题，否则上下文字会粘连

### 字距（letter-spacing）

- body 默认 **0** 或极轻 +0.1 pt
- 中文标题超过 20 pt 的，加 0.5-1 pt 字距
- 小字 label (<10 pt) 可以加 0.15-0.3 pt 提高可读性
- 全大写 overline 加 0.5 px（ALL CAPS 必须加字距）

---

## 3. 间距系统

### 基础单位：4 pt（或 4 px 屏幕）

| 尺度 | 值 | 用途 |
|---|---|---|
| xs | 2-3 pt | 同行内元素间距 |
| sm | 4-5 pt | tag padding、紧凑布局 |
| md | 8-10 pt | 组件内部 |
| lg | 16-20 pt | 组件之间、卡片 padding |
| xl | 24-32 pt | section 标题 margin |
| 2xl | 40-60 pt | 大 section 之间 |
| 3xl | 80-120 pt | 章节之间（长文档）|

### 页面 margin（A4）

| 文档类型 | 上 | 右 | 下 | 左 |
|---|---|---|---|---|
| Resume（紧凑）| 9 mm | 13 mm | 9 mm | 13 mm |
| One-Pager | 15 mm | 18 mm | 15 mm | 18 mm |
| Long Doc | 20 mm | 22 mm | 22 mm | 22 mm |
| Letter | 25 mm | 25 mm | 25 mm | 25 mm |
| Portfolio | 12 mm | 15 mm | 12 mm | 15 mm |

**规律**：密度越高 margin 越小，越正式（letter）margin 越大。

### Slide 尺度间距

印刷品用 mm/pt，Slide（屏幕）用 px，尺度关系不同：

```css
--slide-pad: 80px;   /* slide 四边 padding baseline */
```

**关键规则**：
- Slide padding-top 72-80px（印刷品是 96-120px，slide 的视觉呼吸感已足够）
- Letter-spacing slide = 印刷值 / 2，8px tracking 照搬到屏幕会"散架"
- 宏观尺度（字号、padding）相较印刷 pt 值乘以约 1.6
- 微观尺度（letter-spacing、border、圆角）乘以约 0.6

---

## 4. 组件样式

### Cards / Containers

```css
.card {
  background: var(--ivory);                /* 比 parchment 略浮起 */
  border: 0.5pt solid var(--border-cream);
  border-radius: 8pt;                       /* 舒适圆角 */
  padding: 16pt 20pt;
}

/* 特色卡片 */
.card-featured {
  border-radius: 16pt;                      /* 更大圆角 */
  box-shadow: 0 4pt 24pt rgba(0,0,0,0.05); /* whisper shadow */
}
```

圆角尺度：4 pt -> 6 pt -> 8 pt（默认）-> 12 pt -> 16 pt -> 24 pt -> 32 pt（hero 容器）。

### Buttons (在 PPT / 作品集 / 图表里用)

```css
/* Primary（品牌色） */
.btn-primary {
  background: var(--brand);
  color: var(--ivory);
  padding: 8pt 16pt;
  border-radius: 8pt;
  box-shadow: 0 0 0 1pt var(--brand);    /* ring shadow，不是外阴影 */
}

/* Secondary（warm sand） */
.btn-secondary {
  background: var(--warm-sand);
  color: var(--charcoal);
  padding: 8pt 16pt;
  border-radius: 8pt;
  box-shadow: 0 0 0 1pt var(--ring-warm);
}
```

### Tags / Badges

三个档位的 tag 样式，按视觉冲击力从弱到强选：

**极淡实色**（最克制、最灵动、推荐默认）：
```css
.tag {
  background: #EEF2F7;           /* rgba(201,100,66, 0.08) 等效色 */
  color: var(--brand);
  font-size: 8pt;
  font-weight: 500;
  padding: 1pt 5pt;
  border-radius: 2pt;
  letter-spacing: 0.05pt;
}
```

**标准实色**（需要稍强区分度，如多种 tag 混排时）：
```css
.tag {
  background: #E4ECF5;           /* rgba(201,100,66, 0.18) 等效色 */
  color: var(--brand);
  padding: 1pt 6pt;
  border-radius: 4pt;
}
```

**笔刷渐变**（仅在需要强化"手感"时用，慎用）：
```css
.tag {
  background: linear-gradient(to right, #D6E1EE, #E4ECF5 70%, #EEF2F7);
  color: var(--brand);
  padding: 1pt 5pt;
  border-radius: 2pt;
}
```

**设计哲学**：tint 浓度要比装饰性需求**低一档**。宁可清淡，不可浓艳。"笔刷渐变"技术上可行，但实战中往往用力过猛，把读者的视线引向背景形状而非文字（详见 production.md Part 4 #1）。

**禁止**：`background: rgba(201, 100, 66, 0.18)`，WeasyPrint 会渲染出双层矩形。用等效实色替代。

### 列表

```css
ul, ol {
  padding-left: 16pt;
  line-height: 1.55;
}
ul li::marker {
  color: var(--brand);   /* bullet 点用品牌色 */
}
```

或者更有书卷气的**短横线代替圆点**：

```css
ul.dash { list-style: none; padding-left: 0; }
ul.dash li { padding-left: 14pt; }
ul.dash li::before {
  content: "\2013";
  color: var(--brand);
}
```

### 引用块

```css
.quote {
  border-left: 2pt solid var(--brand);
  padding: 4pt 0 4pt 14pt;
  color: var(--olive);
  line-height: 1.55;
}
```

### 代码块

```css
.code-block {
  background: var(--ivory);
  border: 0.5pt solid var(--border-cream);
  border-radius: 6pt;
  padding: 10pt 14pt;
  font-family: "JetBrains Mono", monospace;
  font-size: 8.5pt;
  line-height: 1.5;
  color: var(--near-black);
}
```

### Section Title

```css
.section-title {
  font-family: serif;           /* 用 serif 承担所有标题 */
  font-size: 15pt;              /* 比正文 10pt 高 1.5×，无需额外装饰 */
  font-weight: 500;
  color: var(--near-black);
  margin: 24pt 0 10pt 0;
}
```

**设计逻辑**：Section Title 依靠字号层级区分，不加任何装饰线。
- 正文 9-10pt，Section Title 15pt，形成清晰的 1.5× 跳跃，阅读节奏自然
- Quote / Callout 保留左竖线（引用的视觉惯例）；Section Title 无装饰，两者角色泾渭分明
- 越简单越稳——多余的线条只会在多个章节标题并列时制造噪音

### Metric Card（数据卡）

关键指标并排显示（用于 one-pager 顶部、简历顶部、portfolio 封面）：

```css
.metrics {
  display: flex;
  gap: 24pt;
}
.metric {
  flex: 1;
  display: flex;
  align-items: baseline;
  gap: 6pt;
}
.metric-value {
  font-family: serif;
  font-size: 16pt;
  font-weight: 500;
  color: var(--brand);
  font-variant-numeric: tabular-nums;   /* 数字等宽对齐 */
}
.metric-label {
  font-size: 9pt;
  color: var(--olive);
}
```

### Section Header (`.kami-section-header`)

用于内容页的小节起始，比 Section Title 更轻量，带 eyebrow 和横线。

```css
.kami-section-header {
  margin-bottom: 36px;
}
.kami-section-header .eyebrow {
  display: flex;
  align-items: center;             /* 圆点是几何图形，center 比 baseline 好 */
  gap: 8px;
  font-family: var(--sans);
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--stone);
  margin-bottom: 14px;
}
.kami-section-header .eyebrow::before {
  content: "";
  display: inline-block;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--brand);
  flex-shrink: 0;
}
.kami-section-header .rule {
  height: 1px;
  background: var(--border-warm);
  margin-bottom: 36px;             /* 横线下方 gap >= 36px（上方 14px 的 2 倍以上）*/
}
.kami-section-header h1 {
  font-family: var(--serif);
  font-size: 38px;
  font-weight: 500;
  line-height: 1.1;
  color: var(--near-black);
}
```

**间距规则**：eyebrow → 横线 14px，横线 → H1 **≥ 36px**（下方 gap 是上方 gap 的 2 倍以上，形成视觉锚点）。

### Code Card (`.kami-code-card`)

用于 Slide 中展示伪代码或代码片段，比普通 code-block 更有结构感。

```css
.kami-code-card {
  background: var(--ivory);
  border: 1px solid var(--border-cream);
  border-radius: 8px;
  padding: 20px 24px;
  overflow: hidden;
}
.kami-code-card pre {
  font-family: var(--mono);
  font-size: 13px;                 /* 或 14px，slide 上更大 */
  line-height: 1.55;
  color: var(--near-black);
  margin: 0;
  white-space: pre;
}
/* 语法色：只用现有 token，不引入新颜色 */
.kami-code-card .k { color: var(--brand); }    /* keyword / string */
.kami-code-card .c { color: var(--stone); }    /* comment */

/* 可选行号：左侧 1px divider */
.kami-code-card.numbered {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0 16px;
}
.kami-code-card .line-nums {
  font-family: var(--mono);
  font-size: 13px;
  line-height: 1.55;
  color: var(--stone);
  text-align: right;
  border-right: 1px solid var(--border-soft);
  padding-right: 12px;
  user-select: none;
}
```

**内容哲学**：代码卡用**伪代码风格**，注释行数 > 代码行数。读者看到的是逻辑，不是语法。

---

## 5. 阴影与深度

**核心原则**：kami **不用传统硬阴影**。深度通过三种方式创造：

### 1. Ring Shadow（边框式阴影）

用于**按钮**的 hover/focus 状态。

```css
/* 按钮默认 */
box-shadow: 0 0 0 1pt var(--ring-warm);

/* 按钮 hover/active 时加深 */
box-shadow: 0 0 0 1pt var(--ring-deep);
```

**不要用于卡片 hover**：ring shadow 本质是边框替代，叠加在已有 border 上会产生三层视觉堆叠（border + ring + offset），感觉数字化，不像纸质。

### 2. Whisper Shadow（极软投影）

用于**卡片 hover** 和 **featured card** 的浮起效果。

```css
/* 卡片 hover - 模拟纸张轻微抬起 */
.card {
  transition: box-shadow 0.2s;
}
.card:hover {
  box-shadow: 0 4pt 24pt rgba(0, 0, 0, 0.05);
}

/* Featured card 默认状态 */
.featured-card {
  box-shadow: 0 4pt 24pt rgba(0, 0, 0, 0.05);
}
```

**为什么用 whisper 而不是 ring**：纸张浮起是深度变化，不是轮廓变化。Whisper shadow 单一、柔和、无轮廓线，符合纸质感调性。

### 3. 明暗交替（section 级别）

长文档里 parchment `#f5f4ed` 底 section 和 `#141413` 深色 section 交替，对比最明显。

**禁止**：`box-shadow: 0 2px 8px rgba(0,0,0,0.3)` 这类传统硬阴影。

---

## 6. 打印与分页

### break-inside 保护

以下元素不允许跨页断开：

```css
.card,
.metric,
.project-item,
.quote,
.code-block,
figure,
.callout {
  break-inside: avoid;
}
```

### 强制分页

```css
.page-break { break-before: page; }
```

用于封面与正文之间、章节之间。

### 页边背景

```css
@page {
  size: A4;
  margin: 20mm 22mm;
  background: #f5f4ed;   /* 背景延伸到 margin 外，避免打印时留白边 */
}
```

---

## 7. 决策速查

遇到 "该用什么" 的时候查这张表：

| 要做什么 | 怎么做 |
|---|---|
| 大标题 | serif 500，字号根据层级，line-height 1.10-1.30 |
| 正文阅读 | sans 400，9.5-10 pt，line-height 1.55 |
| 强调一个数字 | `color: var(--brand)`，不要粗体 |
| 分隔两段内容 | 2.5pt 品牌色左侧竖线，或 0.5pt 暖灰虚线 |
| 引用某人的话 | 左 2pt 品牌色实线 + olive 色 |
| 展示代码 | ivory 底 + 0.5pt border + 6pt 圆角 + mono 字体 |
| 区分主次按钮 | Primary 用品牌色填充 + 白字，Secondary 用 warm-sand + charcoal |
| 在卡片列表里区分某张特殊的 | `border: 0.5pt solid var(--brand)` 或 `border-left: 3pt solid var(--brand)` |
| 章节开始 | serif <code>500</code> · 15pt · 纯字号层级，比正文高 1.5×，无额外装饰 |
| 文档封面 | 单页 Display 字号标题 + 作者/日期 right align，中间大量留白 |
| 一张数据卡 | ivory 底 + 8 pt 圆角 + serif 大数字 + sans 小标签 |

不在这张表里的情况 -> 回到原则：**serif 承担权威，sans 承担功能，暖灰承担节奏，油墨蓝承担焦点**。

---

## 8. Deck Recipe（长 Deck 规范）

长 deck (> 20 slides) 必须遵循以下规则表。条目来自实战经验沉淀，违反前先想清楚原因。

| 规则 | 内容 |
|------|------|
| R1 | Slide 容器固定 1920×1080，外部 scale 适配。不用 vh/vw 动态单位 |
| R2 | Slide 标题用 Display (64px)，不用 H1 (30px)。H1 是印刷品的层级 |
| R4 | Slide letter-spacing = 印刷值 / 2。8px tracking 在屏幕上会"散架" |
| R5 | Section header 横线下方 gap ≥ 36px（上方 gap 的 2 倍以上） |
| R6 | Eyebrow 圆点用 `align-items: center`，不用 baseline（圆点是几何图形） |
| R7 | Slide padding-top 72-80px（印刷品 96-120px，slide 更紧凑） |
| R8 | 图片用 `object-fit: contain` + flex 居中，不拉伸不裁切 |
| R9 | 统一用 `.kami-slide-footer` 放置页码和 deck 标识，绝对定位到 bottom |
| R10 | 代码用伪代码风格：注释行数 > 代码行数，读者看逻辑不看语法 |
