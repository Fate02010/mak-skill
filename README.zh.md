# mak-skill

一套用于产品开发工作流的 Claude Code / Codex skill 集合。这些 skill 将数据库设计、接口文档、原型图生成、图片提示词等重复性设计与工程任务自动化，让你从产品需求到可交付成果只需几分钟。

> English docs: [README.md](./README.md)

---

## Skill 列表

### 🗄️ data-module-design — 数据库表结构设计

**根据产品需求自动生成数据库表结构。**

给它一份 PRD 或产品描述，它会生成符合规范的 SQL 建表文件，包含合理的索引设计、命名规范（`t_` 前缀）和 ER 图。

| 做什么 | 输出文件 |
|---|---|
| 读取产品资料，识别业务实体 | `RountMap.md` — 资料导航索引 |
| 以 DDD 聚合思维进行领域建模 | `领域模型.md` — 领域模型图 |
| 生成规范化 SQL（`t_` 前缀表名） | `[产品名].sql` — DDL 建表文件 |
| 绘制 ER 关系图 | `ER关系图.md` |
| 编写详细数据设计文档 | `数据详细设计文档.md` |

**触发关键词：** "设计数据库"、"生成建表SQL"、"数据建模"、"画ER图"、"DDD建模"、"给XX表加个字段"

---

### 📡 restful-api-design — RESTful 接口文档生成

**根据产品需求自动生成 RESTful 接口文档。**

读取产品资料，生成完整、规范的接口文档，包含出入参定义、幂等性标注和错误码规范。

| 做什么 | 输出文件 |
|---|---|
| 扫描产品资料 | `RountMap.md` |
| 设计 URL 结构（`/api/v1/mobile/*`、`/api/v1/admin/*`） | `接口文档.md` — 完整接口规范 |
| 标注幂等操作，定义错误码 | `api_task_list.md` |
| 每个接口双格式输出：表格 + JSON 示例 | |

**触发关键词：** "设计接口"、"生成接口文档"、"API设计"、"API文档"、"接口规范"

---

### 🖼️ prototype-generator — 原型图生成器

**把产品资料收敛成可评审、可交付的原型，而不是零散页面草图。**

它会读取 PRD、需求文档和产品资料文件夹，经过门禁化流水线生成需求文档、任务清单、页面规格，再输出 HTML 交互原型或 draw.io 线框图。

| 做什么 | 输出 |
|---|---|
| 扫描全部产品资料 | `RountMap.md` |
| 网络搜索 3–5 个竞品，提炼洞察 | `竞品分析报告.md` + `竞品亮点摘要.md` |
| 生成含字段规格的详细需求文档 | `requirements/` |
| 并行启动多个 subagent 分模块生成 | `prototypes/*.html` 或 `[产品名].drawio` |
| 校验、一致性审视与回退重建 | 可评审的最终原型 |

**支持两种输出格式：**
- **HTML 模式** — 浏览器可直接预览的交互式原型，支持页面跳转
- **draw.io 模式** — 两阶段架构（规格化 Agent → 渲染 Agent），输出单个 `.drawio` 文件

**触发关键词：** "生成原型"、"根据资料做原型"、"生成HTML原型图"、"生成drawio"、"根据 PRD 出线框图"、"新增XX功能的原型"

---

### 🎨 image-prompt-gen — AI 图片提示词生成器

**为 Midjourney、DALL-E、Stable Diffusion、Flux、通义万象等模型生成高质量提示词。**

分析你的画面意图，推荐风格组合，输出结构化英文提示词并附中文说明。覆盖 5 大类 20 种视觉风格。

| 选项 | 可选值 |
|---|---|
| `--style` | 20 种风格（见风格库），默认 auto 自动推荐 |
| `--ar` | `1:1` `16:9` `9:16` `4:3` `3:4` 等 |
| `--model` | `midjourney` `dalle` `flux` `dashscope` `sd` |
| `--lang` | `en`（默认）或 `zh`（中英双语） |

**风格库：**

| 类别 | 风格 |
|---|---|
| 摄影类 | `portrait-photo` 人像 · `landscape-photo` 风光 · `product-photo` 产品 · `street-photo` 街拍 · `cinematic-photo` 电影感 |
| 插画类 | `watercolor` 水彩 · `digital-illustration` 数字插画 · `anime` 日系动漫 · `storybook` 绘本 · `concept-art` 概念艺术 |
| 传统艺术 | `oil-painting` 油画 · `impressionism` 印象派 · `art-nouveau` 新艺术运动 |
| 中国风格 | `chinese-ink` 水墨画 · `gongbi` 工笔画 · `new-chinese` 新中式 |
| 数字/3D | `cinematic-3d` 电影级3D · `flat-vector` 扁平矢量 · `pixel-art` 像素艺术 · `cyberpunk` 赛博朋克 |

**触发关键词：** "帮我写个画图提示词"、"Midjourney prompt"、"SD提示词"、"水墨风格"、"电影感"、"anime"、"国风"

---

## 安装

Skill 在 **Claude Code**（默认）或 **Codex** 中运行，每个 skill 会自动识别当前运行环境。

这个仓库是 skill 的标准源。修改 skill 后，再用 `rsync` 将对应目录同步到 `~/.claude/skills/` 或 `~/.codex/skills/`。

### Claude Code

```bash
# 克隆仓库
git clone https://github.com/your-org/mak-skill.git

# 同步到 Claude Code
rsync -av --delete mak-skill/skills/data-module-design/     ~/.claude/skills/data-module-design/
rsync -av --delete mak-skill/skills/restful-api-design/      ~/.claude/skills/restful-api-design/
rsync -av --delete mak-skill/skills/prototype-generator/     ~/.claude/skills/prototype-generator/
rsync -av --delete mak-skill/skills/image-prompt-gen/        ~/.claude/skills/image-prompt-gen/
```

### Codex

```bash
rsync -av --delete mak-skill/skills/data-module-design/     ~/.codex/skills/data-module-design/
rsync -av --delete mak-skill/skills/restful-api-design/      ~/.codex/skills/restful-api-design/
rsync -av --delete mak-skill/skills/prototype-generator/     ~/.codex/skills/prototype-generator/
rsync -av --delete mak-skill/skills/image-prompt-gen/        ~/.codex/skills/image-prompt-gen/
```

---

## 快速开始

安装后，用自然语言描述你的需求，Claude 会自动选择合适的 skill。

```
# 数据库设计
"帮我根据这个PRD设计数据库表结构"

# 接口文档
"根据需求文档生成RESTful接口文档"

# 原型图
"把这个产品资料文件夹生成一套HTML原型图"
"根据需求做个draw.io线框图"

# 图片提示词
"帮我写一个赛博朋克女战士的Midjourney提示词，16:9比例"
"一张新中式风格的茶道场景，9:16竖图"
"水墨风格的山水画，给我写个SD提示词"
```

---

## 项目结构

```
mak-skill/
├── README.md              # 英文文档
├── README.zh.md           # 中文文档
└── skills/
    ├── data-module-design/     # 数据库表结构设计
    │   ├── SKILL.md
    │   └── steps/
    ├── restful-api-design/     # RESTful 接口文档
    │   ├── SKILL.md
    │   └── steps/
    ├── prototype-generator/    # 原型图生成器
    │   ├── SKILL.md
    │   └── steps/              (30+ 步骤和规范文件)
    └── image-prompt-gen/       # 图片提示词生成器
        ├── SKILL.md
        └── references/
            ├── prompt-formula.md   # 提示词构建原则
            ├── model-formats.md    # 各模型语法差异
            └── styles/             # 20 种风格定义文件
```

---

## Skill 工作原理

每个 skill 是一个带 YAML frontmatter 的 `SKILL.md` 文件，告诉 Claude：

- **何时触发** — `description` 字段包含自然语言触发模式
- **做什么** — 正文包含分步工作流指令
- **从哪加载细节** — 大量内容拆分到 `steps/` 或 `references/` 目录，按需加载（渐进式披露），避免一次性消耗大量 context

涉及并行生成的 skill（prototype-generator、data-module-design、restful-api-design）会同时启动多个 subagent 并行处理不同模块，大型项目的生成时间可以大幅缩短。

---

## License

MIT
