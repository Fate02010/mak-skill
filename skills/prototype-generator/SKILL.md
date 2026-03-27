---
name: prototype-generator
description: |
  从产品资料、PRD、需求文档或产品文件夹生成 HTML 交互原型或 draw.io 线框图，也支持在已有原型上增量补充页面/模块。Use when user asks to "生成原型", "生成 HTML 原型图", "生成 draw.io/drawio", "根据资料做原型", "根据 PRD 出线框图", or "新增XX功能的原型". Best for end-to-end prototype workflows with real product materials, requirements parsing, page specs, rendering, and validation. Do not use for纯视觉润色、泛 UI 灵感讨论或与原型无关的编码任务。
compatibility: Claude Code / Codex skill with local filesystem access and Python 3. Draw.io mode uses bundled scripts; competitor-analysis steps may require network when the runtime allows it.
metadata:
  author: mak-skill
  version: 1.1.0
  category: prototype-workflow
  outputs: html, drawio
  repo_source: skills/prototype-generator
---

# Prototype Generator

这是一个面向“产品资料 -> 可交付原型”的流水线 skill。
对 Codex 内部，必须拆成可门禁、可回退的阶段，禁止 `原始资料 -> 直接画图`。

## 触发条件

当用户要求以下任一任务时使用本 Skill：
- 根据资料生成 HTML 原型
- 根据资料生成 draw.io 原型
- 根据 PRD / 需求文档 / 产品文件夹生成线框图、交互稿
- 在现有原型上增量新增页面或功能

以下情况默认**不**使用本 Skill：
- 只想讨论界面风格、视觉趋势、品牌调性
- 只要单个页面的创意文案或营销图
- 与产品原型无关的编码、测试、运维任务

## 先读哪些文件

优先只加载当前阶段需要的内容，遵守渐进式披露：
- 入口与门禁：本文件
- 终端边界与命名：`references/terminal-model.md`
- 输出模式差异：`references/output-modes.md`
- 适用场景与非适用场景：`references/skill-positioning.md`
- 质量门禁与回退策略：`references/quality-gates.md`
- 具体执行步骤：按需读取 `steps/`

## 阶段顺序

### 全量模式

1. **资料提炼**：扫描资料并生成 `.prototype-generator/RountMap.md`
2. **产品语境**：生成产品经理视角角色与系统边界
3. **竞品分析**：生成 `.prototype-generator/竞品分析报告.md`
4. **需求文档**：生成 `requirements/` 下的详细需求文档
5. **页面清单**：生成 `.prototype-generator/原型任务清单.md` 和 `.prototype-generator/原型DoD.md`
6. **页面规格冻结**：统一写入 `.prototype-generator/page_specs/page_spec_*.md`
7. **原型渲染**：
   - draw.io：`page_model -> build_page_spec.py -> render.py -> validate.py -> merge.py`
   - HTML：`page_spec -> body_slots(body_spec/body_prompt/body_html) -> shell compose -> validate`
8. **一致性校验**：覆盖率、一致性、缺页、缺字段检查
9. **最终交付**：输出 `prototypes/` 下最终原型

### 增量模式

1. 理解新增需求
2. 更新需求文档
3. 更新页面清单
4. 冻结新增页面规格到 `.prototype-generator/page_specs/`
5. 渲染与校验
6. 更新最终原型

## 上下文压缩模式

本 Skill 默认将“上下文压缩”视为正式门禁，不允许依赖长上下文持续记住全部原始资料。

### Codex 5.4 Medium 上下文预算

本 Skill 现在默认按 **Codex 5.4 Medium / 200K 上下文窗口** 设计。

硬规则：
- 不把 `200K` 视为可用满额；主流程必须保留 `30%~40%` 余量给推理、工具输出、修复指令和回归结果
- 任何 Step 5 / Step 6 子任务的默认输入只能是：`index.md -> overview -> module_brief -> 1 个模块详细文档 -> page_spec`
- 单个子任务禁止同时加载多个模块详细文档；跨模块信息优先从 `overview` 和 `module_brief` 提取
- 一旦某轮需要回读的详细文档章节超过 2 段，必须先把关键信息压缩回 `module_brief` 或 `page_spec`，再继续
- 若需求资料、需求文档或原型清单已经接近 200K 可用预算，必须在 Step 4 进入分拆模式，不得继续走单文件大 PRD

满足以下任一条件时，**必须进入压缩模式**：
- 原始资料总内容 `> 3000` 行
- 原始资料或需求文档累计内容已接近 `200K` 上下文预算
- 模块数 `> 3`
- 功能点数 `> 12`
- 预计原型页面 / swimlane 数 `> 8`
- 终端数 `> 1`（如小程序 + 后台、App + Web）
- 关键用户角色数 `> 3`

压缩模式下：
- Step 4 必须生成 `requirements/详细需求文档_overview.md`
- Step 4 必须生成 `requirements/module_briefs/模块摘要_[模块中文名].md`
- Step 4 必须生成 `requirements/index.md`
- Step 4 可继续生成 `requirements/详细需求文档_[模块中文名].md`，但**不再合并回单一大文档**
- 若后续阶段发现缺少 `overview/module_briefs/index`、`module_brief` 覆盖不足，或上下文预算门禁失败，必须自动重写这些压缩产物，而不是只报错退出
- Step 5 / Step 6 必须按 `index.md -> overview -> module_brief -> 模块详细文档 -> page_spec` 的顺序读取
- Step 5 / Step 6 每个子任务默认只允许回读 **一个** 模块详细文档；若一个模块文档仍过大，必须先压缩到对应 `module_brief`
- render 阶段与审视阶段禁止把最终原型或原始资料当作主记忆源；若发现问题，必须回退到 `requirements/` 或 `.prototype-generator/page_specs/`

## 输入与输出

### 输入

- 产品资料目录
- 输出格式：`html` 或 `drawio`
- 工作目录 `WORK_DIR`
- 终端类型统一使用：`admin` / `miniapp` / `app` / `h5` / `bigscreen` / `portal` / `industrial`

### 输出

- `WORK_DIR/.prototype-generator/RountMap.md`
- `WORK_DIR/.prototype-generator/竞品分析报告.md`
- `WORK_DIR/requirements/`
- `WORK_DIR/requirements/module_briefs/模块摘要_*.md`
- `WORK_DIR/.prototype-generator/原型任务清单.md`
- `WORK_DIR/.prototype-generator/原型DoD.md`
- `WORK_DIR/.prototype-generator/reference_pack/`
- `WORK_DIR/.prototype-generator/page_models/page_model_*.json`
- `WORK_DIR/.prototype-generator/page_specs/page_spec_*.md`
- `WORK_DIR/.prototype-generator/body_slots/`
- `WORK_DIR/.prototype-generator/tmp/drawio_*_tmp.xml`
- `WORK_DIR/prototypes/`

## 自治模式

当用户明确表达以下意图之一时，视为授权进入自治模式：
- “不要来回交互”
- “自己检查”
- “自己迭代到可以”
- “一次生成尽量到位”

自治模式下：
- draw.io 主流程默认最多自迭代 5 轮；每轮都必须生成真实 `WORK_DIR/prototypes/[产品名称].drawio`
- 自治主控器统一入口：`scripts/run_autonomous_pipeline.py <work_dir> <product_name> --format drawio|html`
- 若 CLI / 网络中断后要继续，只能显式执行 `scripts/run_autonomous_pipeline.py <work_dir> <product_name> --format drawio|html --resume`
- `--resume` 只恢复已落盘的 checkpoint、中间产物和轮次账本；不恢复已退出的 agent / subprocess / 网络会话
- 任一时刻最多只允许 3 个并行 agent 或并行模块任务
- 每轮都必须执行：`check_prototype_consistency.py` → 模块级 `validate.py` → `merge.py` → 最终 `validate.py`
- 最终 `.drawio` 未通过前，禁止宣告完成
- 仅在输出格式、工作目录、资料范围本身不明确时才向用户追问；已获授权后，禁止在每一轮修复前再次等待确认
- 测试、review、对比产生的临时文件统一放到 `WORK_DIR/.prototype-generator/`，通过后清理无用中间物

## 门禁规则

### 全局门禁

- 没有 `.prototype-generator/RountMap.md`，禁止进入需求文档阶段
- 没有 `requirements/`，禁止进入原型阶段
- 若已触发上下文压缩模式，缺少 `requirements/详细需求文档_overview.md`、`requirements/module_briefs/` 或 `requirements/index.md` 任一项，禁止进入原型阶段
- 没有 `.prototype-generator/原型任务清单.md`，禁止进入渲染阶段
- 没有 `.prototype-generator/page_specs/`，禁止进入任何渲染阶段
- `OUTPUT_FORMAT=html` 时，渲染前必须先生成或刷新 `.prototype-generator/reference_pack/`；优先使用内部截图/原型/竞品图，缺参照物时允许外部检索补充行业案例
- `reference_pack` 必须显式记录 `allowed_sources`、`blocked_sources`、`policy_violations`；命中 `prototypes-html/` 等禁用来源时，必须直接报错并重建参考包，禁止静默忽略
- HTML 渲染阶段禁止回读原始资料；只允许读取冻结后的 `.prototype-generator/page_specs/`、`.prototype-generator/body_slots/`、样式规范、任务清单、导航映射
- HTML 页面主体必须通过受控 `body slot` 生成；模型只生成 slot 片段，脚本负责 shell、导航、状态区和元数据拼装
- Step 5 / Step 6 子任务若处于分拆模式，必须先读取 `requirements/index.md`、`requirements/详细需求文档_overview.md` 和 `requirements/module_briefs/模块摘要_[模块中文名].md`，再按需读取模块详细文档
- 最终输出前，必须通过 `validate.py` 与 `check_prototype_consistency.py`
- 若本轮为修复原型质量而修改了 skill 自身脚本、模板或提示词，必须同步补充回归测试并执行 `python3 -m unittest discover -s tests -p 'test_*.py' -v`；测试不通过时必须继续修复，禁止直接宣布完成
- HTML 自治修复必须按 `repair_action` 分流：`MISSING_FIELDS/LOW_COVERAGE -> rewrite_page_spec`，`LAYOUT_MISMATCH -> rewrite_module_brief/rewrite_requirements`，`H1/H2/H4/H10/H11/RENDER/BODY_RENDER/BODY_CONTRACT -> patch_renderer`，`H7/参考污染 -> rebuild_reference_pack`
- `rewrite_requirements` 不得只生成占位文件；必须生成真实可消费的 `overview + module_briefs + index`
- `scripts/run_autonomous_pipeline.py` 写入的 `autoloop_state.json` 必须包含未收敛原因摘要：重复失败、已尝试修复层、最近未收敛原因、停机建议

### draw.io 专属门禁

- 必须先生成 `.prototype-generator/page_models/page_model_*.json`
- 必须再生成 `.prototype-generator/page_specs/page_spec_*.md`
- `validate.py` 或一致性检查失败时，必须回退到 `.prototype-generator/page_specs` 或更上游重建，禁止直接把最终 `.drawio` 当主修复面
- 所有中间产物必须收敛到 `WORK_DIR/.prototype-generator/`；`WORK_DIR` 根目录只允许保留 `requirements/`、`prototypes/` 和用户原始资料
- 登录页、弹窗、抽屉等容易出现错位的骨架页，若用户反馈布局异常，优先修改 `build_page_spec.py` 或对应模板，并补充几何回归测试覆盖该版式
- 推荐使用 `scripts/run_drawio_pipeline.py` 执行真实产物级门禁；该脚本负责编排 `build_page_spec.py -> render.py -> check_prototype_consistency.py -> validate.py -> merge.py -> validate.py`
- 若已进入自治模式，统一由 `scripts/run_autonomous_pipeline.py` 调 `run_drawio_pipeline.py` / `run_html_pipeline.py` 并记录轮次账本
- draw.io 最终交付前必须对真实 `.drawio` 做视觉分析；至少覆盖登录页、列表页、详情页/授权页三类 archetype

### 用户交互门禁

以下节点必须等待用户确认：
- 输出格式
- 工作目录
- 文件优先级分类
- 系统与功能列表确认
- 原型完成标准确认（仅未进入自治模式时）
- Step 6 改进建议确认（仅未进入自治模式时）

## 详细规则位置

只在需要时按阶段读取；不要一次性把全部步骤文件塞进上下文：

- 定位与终端：`references/skill-positioning.md`、`references/terminal-model.md`
- 输出模式与门禁：`references/output-modes.md`、`references/quality-gates.md`
- 运行环境规则：`steps/codex-rules.md` / `steps/claude-rules.md`
- Step 1：`steps/step1-scan.md`
- Step 4：`steps/step4-requirements.md`
- Step 5 通用：`steps/step5-common.md`
- Step 5 draw.io：`steps/step5-drawio.md`
- Step 5 HTML：`steps/step5-html.md`
- 页面规格冻结契约：`steps/page-spec-freeze.md`
- draw.io 规范：`steps/drawio-spec.md`
- 页面模型契约：`steps/page-model-spec.md`
- 校验脚本：`scripts/validate.py`、`scripts/check_prototype_consistency.py`、`scripts/check_module_brief_consistency.py`、`scripts/check_context_budget.py`
