# 信息图提示词基础模板

Step 5 使用此模板，将布局 + 风格 + 结构化内容合并为完整的 AI 图片生成提示词。

## 基础模板

```
Create a professional infographic with the following specifications:

**Format**: Infographic, {{ASPECT_RATIO}} aspect ratio, white or light background
**Layout**: {{LAYOUT}} — {{LAYOUT_SUMMARY}}
**Style**: {{STYLE}} — {{STYLE_SUMMARY}}

**Layout Structure**:
{{LAYOUT_GUIDELINES}}

**Visual Style**:
{{STYLE_GUIDELINES}}

**Content to Include**:
{{STRUCTURED_CONTENT_LABELS}}

**Typography Rules** (critical for readability):
- Main title: large bold text at top, prominent
- Section labels: medium bold, 2-3 words maximum each
- Data values: oversized numerals, high contrast
- All text: clean sans-serif font, legible at small size
- Avoid full sentences as labels — use keywords only

**Design Rules**:
- Clean professional infographic aesthetic
- High contrast between text and background
- Each section visually distinct with clear boundaries
- Consistent icon style throughout
- Ample white space between sections
- No decorative clutter that reduces readability
```

## 语言版本模板

根据用户选择的 `--lang`，切换对应模板：

### 英文版（lang=en，推荐 nano-banana / Midjourney / DALL-E / Flux）

> 上方基础模板即为英文版，直接使用。
> 图中所有标签（卡片标题、副标签、数据值说明）全部使用英文。

### 中文版（lang=zh，推荐通义万象 DashScope）

```
创作一张专业信息图，规格如下：

**格式**：信息图，{{ASPECT_RATIO}} 比例，白色或浅色背景
**布局**：{{LAYOUT}} — {{LAYOUT_SUMMARY}}
**风格**：{{STYLE}} — {{STYLE_SUMMARY}}

**布局结构**：
{{LAYOUT_GUIDELINES_ZH}}

**视觉风格**：
{{STYLE_GUIDELINES_ZH}}

**图中需要展示的文字内容**：
{{STRUCTURED_CONTENT_LABELS_ZH}}

**排版规则**（影响可读性，务必遵守）：
- 主标题：大字加粗，顶部居中，最多 8 个汉字
- 各区块标签：中等加粗，每个标签最多 4 个汉字
- 数据数值：超大字体，高对比度，数字+单位格式
- 全图字体：清晰无衬线字体，小尺寸下仍可辨读
- 禁止在标签中使用完整句子，只用关键词

**设计规则**：
- 专业干净的信息图风格
- 文字与背景高度对比
- 每个区块视觉上清晰区分，有明确边界
- 全图图标风格统一
- 留白充足，区块间不拥挤
- 无多余装饰，以可读性为第一优先
```

> 使用中文模板时，在提示词末尾加注：
> `请使用清晰的中文字体，确保所有汉字标签准确渲染，不要出现乱码或英文替代。`

## 变量说明

| 变量 | 来源 | 说明 |
|------|------|------|
| `{{ASPECT_RATIO}}` | `--ar` 参数 | 如 `16:9`, `9:16`, `1:1` |
| `{{LAYOUT}}` | 用户选择 | 布局名称 |
| `{{LAYOUT_SUMMARY}}` | 布局文件首行 | 一句话布局描述 |
| `{{LAYOUT_GUIDELINES}}` | 布局文件 Image Prompt 章节 | 布局的空间描述语言 |
| `{{STYLE}}` | 用户选择 | 风格名称 |
| `{{STYLE_SUMMARY}}` | 风格文件首行 | 一句话风格描述 |
| `{{STYLE_GUIDELINES}}` | 风格文件核心关键词 | 风格的视觉描述语言 |
| `{{STRUCTURED_CONTENT_LABELS}}` | Step 4 输出 | 全局文字标签清单 |

## 模型特定调整

### nano-banana / Replicate（Google 模型）
- 自然语言段落效果好
- 支持详细的空间描述
- 文字渲染相对准确，但仍建议每标签 ≤ 4 词

### DALL-E / GPT-Image
- 长句描述效果优于碎片关键词
- 不需要堆砌质量词
- 文字渲染在简单标签（1-3词）时较准确

### Midjourney
- 在提示词后追加：`--ar {{AR}} --v 7 --style raw`
- 复杂布局可加 `--chaos 5`（减少随机性）

### Flux
- 接近自然语言，结构描述 + 简单质量词

### 通义万象（DashScope）
- 中文标签效果最好，推荐使用中文
- 对信息图类内容布局遵循较好

## 文字渲染提示（通用）

在所有模型中，以下策略可提高文字准确率：
1. 把所有要显示的文字按顺序列出，用引号标注
2. 强调"legible text"、"readable labels"
3. 说明字体风格（bold sans-serif, clean typeface）
4. 避免要求渲染中文长句——用数字+短词代替

## 示例输出

以 `linear-flow` + `flat-vector` + `16:9` + `nano-banana` 为例：

```
Create a professional infographic in 16:9 wide format on a clean white background.

Layout: A horizontal 5-step process flow. Five equal-width rounded rectangle cards arranged in a single row from left to right, connected by bold rightward arrows. Each card contains: a large icon at top, a bold 2-word label in the center, and a short 4-word subtitle below.

Style: Flat vector illustration. Clean geometric shapes, vibrant solid colors (indigo, cyan, amber, coral, emerald), no shadows, minimal decoration. Bold sans-serif typography throughout.

Content cards (left to right):
- Card 1 (indigo): icon of pencil + tablet, label "PRODUCT DESIGN", subtitle "AI as PM + Designer"
- Card 2 (cyan): icon of stacked documents, label "SPEC LAYERS", subtitle "Rules + Templates + Visual"
- Card 3 (teal): icon of robot at keyboard, label "AI CODING", subtitle "Claude Code Workflow"
- Card 4 (amber): icon of human + robot divided by dotted line, label "TESTING", subtitle "Human Takes the Wheel"
- Card 5 (emerald): icon of rocket + phone, label "DELIVERY", subtitle "25K Lines · 36% Faster"

Bottom metrics bar (light gray strip): bold text "10 Days · 25,000 Lines of Code · 36% Efficiency Gain"
Title at very top: large bold text "AI-Powered Full Development Workflow"

Legible text, readable labels, clean sans-serif font, professional infographic design.
```
