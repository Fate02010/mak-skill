# mak-skill

A collection of Claude Code / Codex skills for product development workflows. These skills automate repetitive design and engineering tasks — database modeling, API documentation, prototyping, image prompt generation — so you can go from product brief to deliverable in minutes.

> 中文文档：[README.zh.md](./README.zh.md)

---

## Skills

### 🗄️ data-module-design

**Database schema design from product requirements.**

Give it a PRD or product description and it generates production-ready SQL with proper indexing, naming conventions, and an ER diagram.

| What it does | Output files |
|---|---|
| Reads product docs, identifies domain entities | `RountMap.md` — resource index |
| Models domain with DDD aggregate thinking | `领域模型.md` — domain model |
| Generates normalized SQL with `t_` prefixed tables | `[product].sql` — DDL |
| Draws ER relationships | `ER关系图.md` |
| Writes detailed data design doc | `数据详细设计文档.md` |

**Trigger phrases:** "设计数据库", "生成建表SQL", "数据建模", "ER图", "DDD建模", "给XX表加个字段"

---

### 📡 restful-api-design

**RESTful API documentation from product requirements.**

Reads your product docs and generates complete, consistent API specs with request/response schemas, idempotency annotations, and error codes.

| What it does | Output files |
|---|---|
| Scans product materials | `RountMap.md` |
| Designs URL structure (`/api/v1/mobile/*`, `/api/v1/admin/*`) | `接口文档.md` — full API spec |
| Marks idempotent operations, defines error codes | `api_task_list.md` |
| Dual format per endpoint: table + JSON example | |

**Trigger phrases:** "设计接口", "生成接口文档", "API设计", "API文档", "接口规范"

---

### 🖼️ prototype-generator

**Interactive HTML prototypes or draw.io wireframes from product requirements.**

The most comprehensive skill. Reads product materials, runs competitor analysis, generates detailed requirements, then produces click-through HTML prototypes or draw.io diagrams — in parallel across modules.

| What it does | Output |
|---|---|
| Scans all product materials | `RountMap.md` |
| Web-searches 3–5 competitors, extracts insights | `竞品分析报告.md` |
| Generates detailed requirements with field specs | `requirements/` |
| Splits work across parallel subagents | `prototypes/*.html` or `[product].drawio` |
| Self-reviews (7-dimension audit) and iterates | Final polished prototype |

**Supports:**
- **HTML mode** — browser-ready interactive prototype with click-through navigation
- **draw.io mode** — two-phase architecture (Spec Agent → Render Agent), outputs a single `.drawio` file

**Trigger phrases:** "生成原型", "做线框图", "生成HTML原型图", "生成drawio", "界面设计", "新增XX功能的原型"

---

### 🎨 image-prompt-gen

**AI image prompts for Midjourney, DALL-E, Stable Diffusion, Flux, and DashScope.**

Analyzes your visual intent, recommends style combinations, and generates a structured English prompt with Chinese explanation. Covers 20 visual styles across 5 categories.

| Option | Values |
|---|---|
| `--style` | 20 styles (see Style Gallery), default: auto |
| `--ar` | `1:1` `16:9` `9:16` `4:3` `3:4` etc. |
| `--model` | `midjourney` `dalle` `flux` `dashscope` `sd` |
| `--lang` | `en` (default) or `zh` (bilingual) |

**Style Gallery:**

| Category | Styles |
|---|---|
| Photography | `portrait-photo` · `landscape-photo` · `product-photo` · `street-photo` · `cinematic-photo` |
| Illustration | `watercolor` · `digital-illustration` · `anime` · `storybook` · `concept-art` |
| Fine Art | `oil-painting` · `impressionism` · `art-nouveau` |
| Chinese Art | `chinese-ink` · `gongbi` · `new-chinese` |
| Digital & 3D | `cinematic-3d` · `flat-vector` · `pixel-art` · `cyberpunk` |

**Trigger phrases:** "帮我写个画图提示词", "Midjourney prompt", "SD提示词", "水墨风格", "电影感", "anime"

---

## Installation

Skills run inside **Claude Code** (default) or **Codex**. Each skill auto-detects its runtime environment.

### Claude Code

```bash
# Clone this repo
git clone https://github.com/your-org/mak-skill.git

# Sync all skills to Claude Code
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

## Quick Start

Once installed, just describe what you want in natural language. Claude will automatically select the right skill.

```
# Database design
"帮我根据这个PRD设计数据库表结构"

# API documentation
"根据需求文档生成RESTful接口文档"

# Prototype
"把这个产品资料文件夹生成一套HTML原型图"

# Image prompt
"帮我写一个赛博朋克女战士的Midjourney提示词，16:9比例"
"一张新中式风格的茶道场景，9:16竖图"
```

---

## Project Structure

```
mak-skill/
├── README.md
├── README.zh.md
└── skills/
    ├── data-module-design/
    │   ├── SKILL.md
    │   └── steps/
    ├── restful-api-design/
    │   ├── SKILL.md
    │   └── steps/
    ├── prototype-generator/
    │   ├── SKILL.md
    │   └── steps/
    └── image-prompt-gen/
        ├── SKILL.md
        └── references/
            ├── prompt-formula.md
            ├── model-formats.md
            └── styles/          (20 style files)
```

---

## How Skills Work

Each skill is a `SKILL.md` file with YAML frontmatter that tells Claude:
- **When to trigger** — the `description` field contains natural language patterns
- **What to do** — the body contains step-by-step workflow instructions
- **Where to find details** — heavy content is split into `steps/` or `references/` files loaded on demand (progressive disclosure)

Skills that involve parallel generation (prototype-generator, data-module-design, restful-api-design) spawn multiple subagents simultaneously to process different modules at once, dramatically reducing total time on large projects.

---

## License

MIT
