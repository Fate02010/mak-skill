---
name: image-prompt-gen
description: |
  专业信息图提示词生成器：分析内容，推荐布局×风格组合，生成可直接用于 AI 图片生成（nano-banana、DALL-E/GPT-Image、Midjourney、Stable Diffusion、Flux、通义万象）的结构化信息图提示词。当用户想要：
  - 把文章/数据/流程/概念生成信息图
  - 说"生成信息图提示词"、"把这个内容做成信息图"时
  - 说"帮我生成一张可以展示流程的图"、"做个数据可视化图"时
  - 说"帮我写个信息图 prompt"、"infographic prompt"时
  - 把文章/PRD/报告/笔记转化为可视化图片时
  - 说"用 AI 生成信息图"、"AI 画信息图"时
  请务必使用此 skill。即使用户没说"信息图"，只要是把结构化内容转化为可视化图片，都应触发此 skill。
---

# 信息图提示词生成器

两个维度：**布局**（信息结构）× **风格**（视觉美学）。自由组合。

**关键机制：** 每种布局/风格的详细定义存放在 `references/` 目录下，按需加载。`SKILL_DIR` 指本 skill 所在目录。

## 用法

```bash
/image-prompt-gen path/to/article.md
/image-prompt-gen --layout linear-flow --style flat-vector --ar 16:9 --model nano-banana
/image-prompt-gen  # 然后粘贴内容
```

## 选项

| 选项 | 值 |
|------|-----|
| `--layout` | 10 种布局（见布局库），默认 auto |
| `--style` | 20 种风格（见风格库），默认 auto |
| `--ar` | `16:9`（默认）`9:16` `1:1` `4:3` `3:4` 等 |
| `--model` | `nano-banana` `dalle` `midjourney` `flux` `dashscope` `sd`，默认 `generic` |
| `--lang` | `zh`（默认）`en` |

## 布局库（Layout Gallery）

| 布局 | 最适合 |
|------|--------|
| `linear-flow` | 流程、步骤、教程、操作指南 |
| `timeline` | 时间线、历史演变、里程碑 |
| `comparison` | A vs B、优缺点、对比分析 |
| `pyramid` | 层级、优先级、马斯洛式结构 |
| `hub-spoke` | 一个核心概念辐射多个关联点 |
| `funnel` | 转化漏斗、筛选流程、递进关系 |
| `circular-flow` | 循环过程、迭代流程、生命周期 |
| `bento-grid` | 多主题总览、特性展示、摘要面板 |
| `dashboard` | 数据指标、KPI、统计数据 |
| `magazine` | 单主题深度、文章封面、视觉叙事 |

完整定义：`references/layouts/<layout>.md`

## 风格库（Style Gallery）

### 摄影类
| 风格 | 描述 |
|------|------|
| `portrait-photo` | 人像摄影感，散景背景 |
| `cinematic-photo` | 电影感，宽幅，色调分级 |
| `product-photo` | 产品摄影，纯净背景 |

### 插画类
| 风格 | 描述 |
|------|------|
| `flat-vector` | 扁平矢量，现代简洁（信息图首选） |
| `digital-illustration` | 数字插画，干净线条 |
| `watercolor` | 水彩，柔和流动 |
| `storybook` | 绘本风，温柔可爱 |
| `concept-art` | 概念艺术，暗黑精细 |
| `anime` | 日系动漫 |

### 传统艺术类
| 风格 | 描述 |
|------|------|
| `oil-painting` | 油画，厚重质感 |
| `impressionism` | 印象派，笔触松散 |
| `art-nouveau` | 新艺术运动，装饰线条 |

### 中国风格类
| 风格 | 描述 |
|------|------|
| `chinese-ink` | 水墨画，留白意境 |
| `gongbi` | 工笔画，精细雅致 |
| `new-chinese` | 新中式，东方现代美学 |

### 数字/3D 类
| 风格 | 描述 |
|------|------|
| `cinematic-3d` | 电影级 CGI |
| `pixel-art` | 像素艺术，复古感 |
| `cyberpunk` | 赛博朋克，霓虹未来 |

完整定义：`references/styles/<style>.md`

## 推荐组合

| 内容类型 | 布局 | 风格 |
|----------|------|------|
| 流程/教程 | `linear-flow` | `flat-vector` |
| 技术架构 | `linear-flow` / `hub-spoke` | `concept-art` |
| 数据报告 | `dashboard` | `flat-vector` |
| 历史演变 | `timeline` | `watercolor` / `flat-vector` |
| 功能对比 | `comparison` | `flat-vector` |
| 层级体系 | `pyramid` | `flat-vector` |
| 生命周期 | `circular-flow` | `flat-vector` |
| 多主题总览 | `bento-grid` | `flat-vector` |
| 概念辐射 | `hub-spoke` | `flat-vector` |
| 文章封面 | `magazine` | `cinematic-photo` |

默认：`bento-grid` + `flat-vector`

## 输出结构

```
image-prompts/{topic-slug}/
├── analysis.md           ← Step 1 内容分析
├── structured-content.md ← Step 2 结构化提炼
├── prompt.md             ← Step 5 最终信息图提示词（主输出）
└── infographic.png       ← Step 6 生成的图片（可选）
```

Slug：从主题取 2-4 个关键词，kebab-case。

## 工作流

### Step 1：扫描分析内容

Read `SKILL_DIR/references/analysis-framework.md` 获取分析框架，执行：

1. 读取用户提供的内容（文件/粘贴/URL）
2. 分析：主题、数据类型、复杂度、语气、受众
3. 提取关键数据点（原文原句，不改写）
4. 保存分析到 `analysis.md`

### Step 2：生成结构化内容提纲

Read `SKILL_DIR/references/structured-content-template.md` 获取格式规范，执行：

1. 将内容转化为信息图结构：标题、各节关键概念、视觉元素、文字标签
2. 提炼所有数字/统计数据（原文原句）
3. 输出 `structured-content.md`

**规则**：
- 只用来源内容，不新增信息
- 严格保留所有数字、引语、专有名词
- 文字标签精简：每个标签 ≤ 4 个汉字 / 3 个英文单词

### Step 3：推荐布局 × 风格组合

**优先检查关键词捷径**（见下方关键词映射表），命中则直接自动选取，跳过推荐步骤。

否则根据以下依据推荐 3 个组合：
- 内容数据结构 → 匹配布局
- 内容语气/受众 → 匹配风格
- 用户明确的设计指令

### Step 4：确认参数

用**单次 `AskUserQuestion`** 同时确认以下参数（不要分多次提问）：

| 参数 | 何时询问 |
|------|----------|
| 布局×风格 | 未指定且推荐了多个 |
| 比例（`--ar`） | 未指定 |
| 目标模型 | 未指定（影响提示词语法和文字限制） |
| **提示词语言** | 始终询问（每次都必须让用户选择） |

**语言选项说明**（在 AskUserQuestion 中展示给用户）：

| 选项 | 适用场景 | 文字渲染说明 |
|------|---------|------------|
| **英文（English）** | 大多数模型（nano-banana、Midjourney、DALL-E、Flux） | 英文标签渲染准确率更高，推荐首选 |
| **中文（Chinese）** | 通义万象（DashScope）、对中文排版有要求的场景 | 通义万象对中文渲染有专项优化，其他模型中文渲染不稳定 |

### Step 5：生成信息图提示词 → `prompt.md`

1. Read `SKILL_DIR/references/layouts/<layout>.md` 获取布局定义
2. Read `SKILL_DIR/references/styles/<style>.md` 获取风格定义
3. Read `SKILL_DIR/references/base-prompt.md` 获取基础提示词模板
4. 将布局定义 + 风格定义 + 结构化内容 + 模型优化 组合为完整提示词

**提示词质量要求**：
- 按 `--model` 调整语法（见 `references/model-formats.md`）
- 文字标签必须短（AI 图片生成文字渲染能力有限）
- 布局描述要明确空间关系（上/下/左/右/中心）
- 每个内容区域都有对应视觉元素描述

**语言输出规则（`--lang` 决定提示词中所有文字标签的语言）**：

| `--lang` | 提示词结构语言 | 图中文字标签 | 适用模型 |
|----------|-------------|------------|---------|
| `en`（英文） | 英文段落描述 | 全英文标签 | nano-banana / Midjourney / DALL-E / Flux |
| `zh`（中文） | 中文段落描述 | 全中文标签 | 通义万象（DashScope）为主 |

- `lang=en`：提示词整体用英文书写，图中所有卡片标签、副标题、数据标注全部用英文
- `lang=zh`：提示词整体用中文书写，图中所有卡片标签、副标题、数据标注全部用中文；同时在 `--model` 推荐或说明中注明"建议使用通义万象以获得最佳中文渲染效果"
- **混用禁止**：同一张图中不能中英混用（如标题中文但标签英文），保持统一

### Step 6：生成图片（可选）

询问用户是否直接生成图片。如果确认，调用可用的图片生成 skill（如 `baoyu-image-gen`），以 `prompt.md` 作为 `--promptfiles` 参数。

## 关键词捷径

| 用户关键词 | 自动选取布局 | 推荐风格 | 默认比例 |
|------------|------------|---------|---------|
| 流程图 / 步骤 / how-to | `linear-flow` | `flat-vector` | `16:9` |
| 对比 / vs / 比较 | `comparison` | `flat-vector` | `16:9` |
| 时间线 / 历史 / timeline | `timeline` | `flat-vector` / `watercolor` | `16:9` |
| 数据 / 报告 / 统计 | `dashboard` | `flat-vector` | `16:9` |
| 总览 / 概览 / overview | `bento-grid` | `flat-vector` | `16:9` |
| 循环 / 周期 / 生命周期 | `circular-flow` | `flat-vector` | `1:1` |
| 封面 / cover / 海报 | `magazine` | `cinematic-photo` | `9:16` |

## 参考文件

- `references/analysis-framework.md` — 内容分析方法论
- `references/structured-content-template.md` — 结构化内容格式
- `references/base-prompt.md` — 信息图提示词基础模板
- `references/layouts/<layout>.md` — 10 种布局定义
- `references/styles/<style>.md` — 20 种风格定义
- `references/model-formats.md` — 不同模型语法差异
