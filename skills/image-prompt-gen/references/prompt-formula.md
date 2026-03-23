# 信息图提示词构建原则

## 核心公式

信息图提示词 = 布局结构 + 视觉风格 + 内容标签 + 排版规则 + 模型优化

```
[格式声明] + [布局空间描述] + [风格视觉描述] + [内容区块详情] + [排版规则] + [质量修饰词]
```

## 与普通图片提示词的关键区别

| 维度 | 普通图片 | 信息图 |
|------|---------|--------|
| 主体 | 视觉对象（人/物/场景） | 信息结构（布局+内容） |
| 文字 | 可无文字 | **必须有精确文字标签** |
| 构图 | 摄影/艺术构图 | **信息架构构图** |
| 核心挑战 | 视觉美感 | **文字可读性 + 布局准确性** |

## 模块详解

### 1. 格式声明 — 必填

开头明确说明这是信息图，确立整体基调：

```
A professional infographic in [ASPECT_RATIO] format on a [white/light] background.
```

或中文模型：
```
一张专业的信息图，[ASPECT_RATIO] 比例，[白色/浅灰色] 背景。
```

### 2. 布局空间描述 — 核心

这是最关键的部分，明确描述信息的空间排列方式，直接决定图片结构是否正确。

**好的布局描述**（具体、可执行）：
```
Five equal-width rounded rectangle cards arranged in a single row from left to right, connected by bold rightward arrows. Each card contains a large icon at top and a bold label in the center.
```

**差的布局描述**（模糊、难执行）：
```
A nice infographic showing a workflow process with some steps.
```

从 `references/layouts/<layout>.md` 的 **Image Prompt 空间描述语言** 章节获取对应布局的描述模板。

### 3. 视觉风格描述 — 必填

从 `references/styles/<style>.md` 的**核心关键词**获取风格词汇，描述视觉美学：

```
Flat vector illustration style. Clean geometric shapes, vibrant solid colors, minimal decoration, bold sans-serif typography.
```

### 4. 内容区块详情 — 必填

按布局的区块结构，逐一描述每个区块的文字标签和视觉元素：

```
Cards (left to right):
- Card 1 (indigo): icon of pencil sketch, label "PRODUCT DESIGN", subtitle "AI Leads All Roles"
- Card 2 (blue): icon of stacked documents, label "SPEC LAYERS", subtitle "Rules + Templates + Visual"
```

**黄金规则**：
- **主标题**：≤ 8 汉字 / 5 英文词
- **区块标签**：≤ 4 汉字 / 3 英文词（这是 AI 渲染文字成功的关键）
- **副标签**：≤ 8 汉字 / 5 英文词
- **数据值**：直接写数字，如 "36%"、"25K"

### 5. 排版规则声明 — 必填

明确告诉模型字体要求，这对文字准确性影响极大：

```
Typography: large bold title at top center, section labels in medium bold sans-serif, data values in oversized numerals. All text legible and readable. Clean sans-serif typeface throughout.
```

### 6. 质量修饰词 — 推荐

根据目标模型调整（见 `references/model-formats.md`）：

- **nano-banana / Flux**：`professional infographic design, clean layout, legible text`
- **DALL-E**：不需要质量词，自然语言更有效
- **Midjourney**：`--style raw --v 7`，追加在提示词末尾

## 文字渲染优化技巧

AI 图片生成模型文字渲染是最大难点，以下策略可提高准确率：

| 技巧 | 说明 | 示例 |
|------|------|------|
| **列举法** | 把所有文字按顺序列出，加引号 | `label "CODING"`, `subtitle "Claude Code"` |
| **简短原则** | 每标签 ≤ 3 个词 | ✅ "AI Coding" ❌ "How AI Handles the Coding Phase" |
| **英文优先** | 英文比中文渲染稳定 | 用 "产品设计" 或 "PRODUCT DESIGN"（英文更稳） |
| **纯数字** | 数字比文字准确 | "36%" 而非"百分之三十六" |
| **指定字体风格** | `bold sans-serif`, `clean typeface` | 告诉模型字体风格 |
| **强调可读性** | 在提示词末加 `legible text, readable labels` | 提醒模型优先确保文字清晰 |

## 中文 vs 英文标签选择

| 目标模型 | 推荐语言 | 理由 |
|----------|---------|------|
| nano-banana / Google | 英文 | 英文渲染更准确 |
| 通义万象（DashScope） | 中文 | 专门优化了中文文字渲染 |
| DALL-E / GPT-Image | 英文 | 英文更准确 |
| Midjourney | 英文 | 不支持中文 |
| Flux | 英文 | 英文更稳定 |

## 完整提示词构建示例

**场景**：AI 开发工作流，5 步流程，flat-vector 风格，16:9，nano-banana

```
Create a professional infographic in 16:9 wide format on a clean white background.

Layout: A horizontal 5-step process flow. Five equal-width rounded rectangle cards arranged in a single row from left to right, connected by bold rightward arrow icons between each card. Each card contains: a large icon at top center, a bold 2-word label in the middle, and a brief subtitle below. Cards have graduated blue-to-green color progression.

Style: Flat vector illustration. Clean geometric shapes, vibrant solid colors, minimal decoration, no shadows. Bold clean sans-serif typography throughout.

Content (left to right):
- Card 1 (indigo): icon of a person sketching on tablet, bold label "PRODUCT DESIGN", subtitle "AI as PM + Designer"
- Card 2 (blue): icon of three stacked document layers, bold label "SPEC LAYERS", subtitle "Rules + Templates + Visual"
- Card 3 (teal): icon of robot at keyboard with code stream, bold label "AI CODING", subtitle "Claude Code Spec"
- Card 4 (amber): icon of human and robot with dotted dividing line, bold label "TESTING", subtitle "Human Takes Limits"
- Card 5 (green): icon of rocket launching from phone, bold label "DELIVERY", subtitle "25K Lines · 36% Faster"

Bottom metrics strip (light gray background): bold text reading "10 Days · 25,000 Lines · 36% Efficiency Gain"
Top title: very large bold text "AI-Powered Development Workflow"

Typography: all labels short and bold, clean sans-serif, high contrast text on colored backgrounds. Professional infographic design, legible text, readable labels.
```

## 常见错误

| 错误 | 示例 | 改进 |
|------|------|------|
| 标签太长 | `"How AI Enables Full-Stack Product Development"` | `"AI CODING"` |
| 布局描述模糊 | `"some cards"` | `"five equal-width cards in a horizontal row"` |
| 忘记位置关系 | 没说"左到右"或"上到下" | 明确空间方向 |
| 忽略文字可读性声明 | 没有 `legible text` | 末尾加上可读性声明 |
| 中英文混用于同一标签 | `"AI编码"` | 统一用英文或中文 |
