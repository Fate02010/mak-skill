---
name: image-prompt-gen
description: |
  为 AI 图片生成（Midjourney、DALL-E/GPT-Image、Stable Diffusion、Flux、通义万象等）生成高质量、结构化的提示词。分析用户意图，推荐风格组合，输出精准的英文提示词（可附中文说明）。当用户想要：
  - 生成 AI 图片提示词 / image prompt / prompt词
  - 说"帮我写个画图提示词"、"生成 Midjourney prompt"、"SD 提示词"时
  - 说"我想生成一张图，帮我写提示词"、"写个绘图描述"时
  - 根据描述或参考内容生成风格化图片
  - 说"照片风格"、"插画风格"、"水墨风格"、"anime"、"电影感"、"国风"等风格关键词时
  请务必使用此 skill。即使用户没有明确说"提示词"，只要他们想生成任何类型的 AI 图片，都应触发此 skill。
---

# 图片提示词生成器

两个维度：**主题**（画面内容）× **风格**（视觉美学）。任意组合。

## 用法

```bash
/image-prompt-gen 一只在雨中行走的猫咪，电影感
/image-prompt-gen --style cinematic-photography --ar 16:9 --model midjourney
/image-prompt-gen path/to/reference.md --style chinese-ink --lang zh
```

## 选项

| 选项 | 值 |
|------|-----|
| `--style` | 20 种风格（见风格库），默认 auto（自动推荐） |
| `--ar` | 比例：`1:1` `16:9` `9:16` `4:3` `3:4` `2:1` 等 |
| `--model` | `midjourney` `dalle` `flux` `dashscope` `sd`，默认 `generic` |
| `--lang` | 输出语言：`en`（默认）`zh`（中英双语） |

## 风格库

### 摄影类（Photography）

| 风格 | 描述 | 适合主题 |
|------|------|----------|
| `portrait-photo` | 人像摄影，散景背景，自然光 | 人物、肖像 |
| `landscape-photo` | 风光摄影，广角，黄金时刻 | 自然、建筑、城市 |
| `product-photo` | 产品摄影，纯净背景，戏剧光影 | 产品、物品展示 |
| `street-photo` | 街拍，纪实，黑白或胶片感 | 城市、人文 |
| `cinematic-photo` | 电影感，宽幅，色调分级 | 叙事性场景 |

### 插画类（Illustration）

| 风格 | 描述 | 适合主题 |
|------|------|----------|
| `watercolor` | 水彩插画，柔和流动，纸张纹理 | 花卉、童话、自然 |
| `digital-illustration` | 数字插画，干净线条，鲜艳配色 | 角色设计、概念图 |
| `anime` | 日系动漫风格，细腻线稿 | 人物、奇幻场景 |
| `storybook` | 绘本插画，温柔，儿童感 | 儿童内容、温情故事 |
| `concept-art` | 概念艺术，暗黑细致，专业感 | 游戏、电影场景 |

### 传统艺术类（Fine Art）

| 风格 | 描述 | 适合主题 |
|------|------|----------|
| `oil-painting` | 油画，厚重质感，古典构图 | 人物、静物、风景 |
| `impressionism` | 印象派，笔触松散，光影变化 | 户外场景、自然光 |
| `art-nouveau` | 新艺术运动，装饰性线条，花卉元素 | 装饰图案、人物 |

### 中国风格类（Chinese Art）

| 风格 | 描述 | 适合主题 |
|------|------|----------|
| `chinese-ink` | 水墨画，留白，意境深远 | 山水、花鸟、禅意 |
| `gongbi` | 工笔画，细致精工，色彩雅致 | 花卉、人物、工笔重彩 |
| `new-chinese` | 新中式，东方美学与现代设计结合 | 品牌、空间、人文 |

### 数字/3D 类（Digital & 3D）

| 风格 | 描述 | 适合主题 |
|------|------|----------|
| `cinematic-3d` | 电影级 CGI，写实材质，戏剧光影 | 产品、角色、场景 |
| `flat-vector` | 扁平插画，鲜亮色块，简洁 | 图标、UI、品牌 |
| `pixel-art` | 像素艺术，复古 8-bit | 游戏、怀旧风格 |
| `cyberpunk` | 赛博朋克，霓虹灯，未来都市 | 科技、未来、城市 |

完整风格定义：`references/styles/<style>.md`

## 推荐组合

| 场景 | 主题类型 | 风格 |
|------|----------|------|
| 社交媒体封面 | 人物/品牌 | `portrait-photo` / `flat-vector` |
| 国风配图 | 自然/人文 | `chinese-ink` / `new-chinese` |
| 游戏概念图 | 角色/场景 | `concept-art` / `cinematic-3d` |
| 儿童内容 | 故事/角色 | `storybook` / `watercolor` |
| 产品展示 | 物品 | `product-photo` / `cinematic-3d` |
| 科技感 | 未来/城市 | `cyberpunk` / `cinematic-photo` |
| 艺术创作 | 自由主题 | `oil-painting` / `impressionism` |
| 动漫人物 | 人物/故事 | `anime` / `concept-art` |

## 输出结构

```
image-prompts/{topic-slug}/
├── brief.md          ← 意图分析
├── prompt.md         ← 最终提示词（主输出）
└── image.png         ← 生成的图片（如调用图片生成 skill）
```

## 工作流

### Step 1：理解用户意图

分析用户输入，提取：
- **主体**（Subject）：画面的核心描绘对象
- **动作/状态**（Action）：主体在做什么
- **环境/背景**（Setting）：场景在哪里
- **情绪/氛围**（Mood）：希望传递的情感
- **用途**（Purpose）：封面图、插画、头像、背景等

如果意图不够明确，用 `AskUserQuestion` 一次性询问关键缺失信息（不要分多次问）。

Read `references/prompt-formula.md` 了解提示词构建原则。

### Step 2：推荐风格

如果用户未指定 `--style`：
1. 根据主题类型和用途，推荐 2-3 个风格选项
2. 每个选项附简短理由
3. 如果用户输入包含明确风格关键词（如"水墨"→`chinese-ink`，"电影感"→`cinematic-photo`），直接自动选取

如果用户已指定 `--style`，Read `references/styles/<style>.md` 获取该风格的完整定义。

### Step 3：确认参数（可选）

若以下任一参数未确定，用单次 `AskUserQuestion` 同时确认：

| 参数 | 何时询问 |
|------|----------|
| **风格** | 未指定且推荐了多个 |
| **比例（--ar）** | 未指定且用途对比例有明显要求 |
| **目标模型** | 未指定（影响提示词语法） |

重要：不要拆成多次提问。

### Step 4：生成提示词 → `prompt.md`

Read 已选风格的 `references/styles/<style>.md`，结合 `references/prompt-formula.md`，按以下结构生成：

```markdown
# [图片主题]

## 提示词（Prompt）

[完整英文提示词]

## 负面提示词（Negative Prompt）
[仅 SD/Flux 模式输出；其他模型跳过]

## 参数
- 比例：[ar]
- 目标模型：[model]
- 风格：[style]

## 中文说明
[对提示词的简要中文解读，帮助用户理解和调整]
```

**提示词质量要求**：
- 英文输出，结构清晰（主体 → 风格 → 技术参数）
- 具体而不空泛：用"golden hour, soft diffused light"而非"good lighting"
- 避免空洞词：不用"beautiful"、"amazing"等形容词堆砌
- 根据目标模型调整语法（见 `references/model-formats.md`）

### Step 5：输出与选择

展示生成的提示词，询问用户：
1. 是否要**调整**（风格、细节、参数）
2. 是否要**直接生成图片**（调用可用的图片生成 skill）

如果用户要生成图片，调用 `baoyu-image-gen`（如可用），以 `prompt.md` 作为 `--promptfiles` 参数。

## 参考文件

- `references/prompt-formula.md` — 提示词构建原则
- `references/styles/<style>.md` — 20 种风格的完整定义
- `references/model-formats.md` — 不同模型的语法差异
