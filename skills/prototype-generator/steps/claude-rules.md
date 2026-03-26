# Claude Code 环境专有规则

> 本文件仅在 Claude Code 环境中加载，Codex 环境无需读取。

---

## 运行环境声明

Claude Code 环境以实际可用工具为准，默认使用 `Agent`、文件读取能力和 shell 能力完成工作流。

| 能力 | Claude Code 当前做法 |
|------|----------------------|
| 文件读取 | 用 `Read` / `Glob` / 目录扫描能力按需读取文件 |
| 并行子任务 | 用 `Agent(prompt="...", run_in_background=True)` 并行启动子 agent |
| 并行 shell | 用 `Bash(..., run_in_background=True)` 发出互不冲突的独立命令 |
| 文件编辑 | 用 `Edit` 修改文件 |
| 进度跟踪 | 用 Claude Code 自身任务能力或执行状态文件跟踪 |

**识别方式：**
- 当前会话可用 `Agent`
- `SKILL_DIR` 通常为 `~/.claude/skills/prototype-generator`

---

## Claude 必须遵守的并行规则

1. **独立写作任务优先使用 `Agent`**：Step 4 模块需求文档、Step 5 HTML 页面、Step 5 draw.io 规格化，均按模块拆分。
2. **Agent prompt 必须自包含**：所有路径都替换为绝对路径。
3. **并发上限**：任一时刻最多只允许 3 个子 agent 同时运行；任务数超过 3 时必须分批启动。
4. **等待策略**：先发出当前批独立 Agent，再统一等待当前批结果；上一批完成后再启动下一批。
5. **shell 并行只用于互不写同一文件的命令**：例如多个 `render.py` 命令可以并行；同一文件不可并行修改。
6. **熔断规则**：并行 Agent 失败数超过 50% 时暂停，并提示用户选择重试或中止。

---

## Step 4 需求文档并行生成

大型项目需求文档拆分时：

1. 主进程先生成 `requirements/详细需求文档_overview.md`
2. 再按模块用 `Agent` 分批并行生成各模块文档，每批最多 3 个
3. 每个模块文档完成后，必须继续生成 `requirements/module_briefs/模块摘要_[模块中文名].md`
4. 全部完成后由主进程汇总并写入 `requirements/index.md`

**默认强制压缩模式触发条件：**
- 原始资料总内容 `> 3000` 行
- 模块数 `> 3`
- 功能点数 `> 12`
- 预计页面 / swimlane 数 `> 8`
- 终端数 `> 1`
- 关键角色数 `> 3`

一旦命中任一项，Step 4 不得继续生成单一合并大 PRD，必须改走 `overview + module_brief + 模块详细文档 + index`。

**Claude 示例：**

```text
Agent(prompt="负责 用户模块 需求文档 ...", run_in_background=True)
Agent(prompt="负责 商品模块 需求文档 ...", run_in_background=True)
Agent(prompt="负责 订单模块 需求文档 ...", run_in_background=True)
# 若仍有剩余模块，再启动下一批，确保同时运行数不超过 3
```

成功标志统一为 Agent 最终输出含 `✅ [文件名] 完成`。

---

## Step 5 HTML 模式

1. 主进程先准备共享文件，例如 `prototypes/common.css`
2. 用 `Agent` 按模块分批并行生成 HTML 页面，每批最多 3 个子 agent
3. 全部完成后，主进程执行冒烟检查和缺失修复

分拆模式下，HTML 子任务默认先读 `index.md`，再读 `overview`，再读 `module_brief`，只有必要时才回读模块详细文档。

**建议容量：**
- 单个 Agent 负责 ≤ 4 页
- 单模块超过 6 页时拆分为多个 Agent

---

## Step 5 draw.io 模式

### 阶段 A：语义建模

- 用 `Agent` 按模块分批并行生成 `.prototype-generator/page_models/page_model_[模块英文名].json`，每批最多 3 个子 agent
- 每个 Agent 负责 ≤ 2 个真实页面时最稳定；超过则拆分
- 子任务只负责页面类型、字段、列表列、状态枚举、跳转、CRUD 标记
- 分拆模式下，page_model 子任务必须先按 `index.md -> overview -> module_brief -> 模块详细文档` 的顺序读取；优先依赖模块摘要完成语义建模

### 阶段 B：渲染

- 主进程先调用 `build_page_spec.py`
- 再调用 `render.py`
- 多个模块的 `build_page_spec.py` / `render.py` 命令可并行发出

**Claude shell 示例：**

```text
Bash("mkdir -p .../.prototype-generator/page_models .../.prototype-generator/page_specs .../.prototype-generator/tmp")
Bash("python3 .../build_page_spec.py .../.prototype-generator/page_models/page_model_user.json .../.prototype-generator/page_specs/page_spec_user.md", run_in_background=True)
Bash("python3 .../render.py .../step5-component-styles.md .../.prototype-generator/page_specs/page_spec_user.md .../.prototype-generator/tmp/drawio_user_tmp.xml", run_in_background=True)
```

补充强约束：

- `page_spec_*.md` 只能写入 `WORK_DIR/.prototype-generator/page_specs/`
- 如果 `WORK_DIR` 根目录出现新的 `page_spec_*.md`，说明流程仍在走旧路径，必须修正后重跑
- render 只允许读取 `.prototype-generator/page_specs/` 目录内的 page_spec

---

## page_model 契约

Claude draw.io 模式与 Codex 使用同一套 `page_model` JSON 契约：

- 契约文件：`SKILL_DIR/steps/page-model-spec.md`
- 新生成内容统一写 `WORK_DIR/.prototype-generator/page_models/page_model_[模块英文名].json`
- `page_spec` 由 `build_page_spec.py` 自动生成

---

## 特别注意事项

- 新文档和新示例必须使用统一 `page_model` 契约
- 渲染阶段出现 `style_key` 缺失、空 `swimlane_label`、缺表头时，应直接报错，不要静默降级
- 与 Codex 的差异只在工具调用方式，不在输出契约
