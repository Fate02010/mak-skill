# Step 5 阶段 5-3：并行启动 subagent（HTML 模式）

本文件仅在 OUTPUT_FORMAT=html 时加载。

---

## HTML 两段式规则

HTML 模式也必须走：

`requirements -> .prototype-generator/page_specs/page_spec_*.md -> HTML render`

禁止从需求文档直接生成最终 HTML。

> **200K 预算规则：** 面向 `Codex 5.4 Medium / 200K`，HTML 子任务默认只读 `index + overview 关键章节 + 1 个 module_brief`；只有字段不够时才补读当前模块详细文档，且不得再串读第二个模块的详细文档。

### 前置准备：复制共享 CSS 到 prototypes 目录

启动 subagent 之前，先将共享样式文件复制到输出目录：

```bash
mkdir -p WORK_DIR/prototypes
cp SKILL_DIR/templates/common.css WORK_DIR/prototypes/common.css
```

> 所有 HTML 页面通过 `<link rel="stylesheet" href="common.css">` 引用此文件。
> subagent 生成的 HTML 中**禁止在 `<style>` 中重复定义 `:root` 变量和通用组件样式**。

同时读取：

- `SKILL_DIR/steps/page-spec-freeze.md`

主进程必须先确认本轮 HTML 任务会为每个模块写出：

- `WORK_DIR/.prototype-generator/page_specs/page_spec_[模块英文名].md`

### 分模块规则

- 一个功能模块 → 一个 Agent
- 单模块超过 6 页时拆分为 2 个 Agent
- 最多同时启动 **3 个并行 Agent**
- 每个 Codex 子任务建议负责 ≤ 4 页

## 子任务职责

每个 HTML 子任务必须按顺序完成两件事：

1. 读取需求文档并冻结本模块 `page_spec`
2. 只基于 `page_spec` 渲染 HTML 页面

第二阶段禁止再次回读原始资料、PRD、竞品文档或需求文档原文。

### 启动方式

读取 `SKILL_DIR/steps/step5-agent-prompt.md` 获取提示词模板，使用 HTML 模板。

**占位符替换清单（两种运行环境均强制要求）：**

| 占位符 | 替换为 |
|--------|--------|
| `[SKILL_DIR]` | 当前环境下的实际 skill 绝对路径（如 Claude：`/Users/xxx/.claude/skills/prototype-generator`；Codex：`/Users/xxx/.codex/skills/prototype-generator`） |
| `[WORK_DIR]` | 用户确认的工作目录绝对路径 |
| `[模块名]` / `[模块英文名]` | 当前模块的中文名 / 英文名 |
| `[页面名称N]` | 该模块负责的具体页面名 |
| `[章节名]` | 需求文档中对应章节标题 |
| `[风格]` / `[颜色]` | 实际设计风格和主色调 |
| `[PAGE_SPEC_PATH]` | `WORK_DIR/.prototype-generator/page_specs/page_spec_[模块英文名].md` |
| `[CRUD 页面清单]` | 从阶段 5-2 CRUD 完整性检查结果中提取，格式：`- [列表页名] → 需要：新增/编辑[对象名]弹窗/页面 + 删除确认弹窗`；若该模块无 CRUD 操作则填 `无 CRUD 操作` |
| `[需求文档读取指令]` | **单文件模式**：`读取 [WORK_DIR]/requirements/详细需求文档.md 中以下章节`<br>**分拆模式**：`先读取 [WORK_DIR]/requirements/index.md 定位模块摘要和模块详细文档；再读取 [WORK_DIR]/requirements/详细需求文档_overview.md（至少获取用户角色 §2、系统边界 §2.5、模块职责 §2.8、导航结构 §3.5/§3.6、关键业务事件 §4.5、枚举值字典 §5.5、权限与数据口径 §5.8）；再读取 [WORK_DIR]/requirements/module_briefs/模块摘要_[模块中文名].md 作为最小执行上下文；仅在需要字段明细、复杂校验、状态流转或失败处理时，再读取 [WORK_DIR]/requirements/详细需求文档_[模块中文名].md 中以下章节` |

> **替换前必须自检**：搜索 prompt 文本中是否还有 `[` 字符——若有则先补全再发送。

**Claude Code（Agent 工具）— 分批并行启动，每批最多 3 个 Agent：**

```
# 每批最多 3 个，先并行发出本批，再等待本批完成
Agent(prompt="...模块1 完整 prompt（所有占位符已替换）...", run_in_background=True)
Agent(prompt="...模块2 完整 prompt（所有占位符已替换）...", run_in_background=True)
Agent(prompt="...模块3 完整 prompt（所有占位符已替换）...", run_in_background=True)
# 若还有剩余模块，下一批重复相同步骤
```

> Claude Code 请参考 `SKILL_DIR/steps/claude-rules.md`；Codex 请参考 `SKILL_DIR/steps/codex-rules.md`。

**Codex：**

```
# 用 spawn_agent 按模块分批并行启动 HTML 生成子任务，每批最多 3 个
spawn_agent(agent_type="worker", message="...模块1 完整 prompt（所有占位符已替换）...")
spawn_agent(agent_type="worker", message="...模块2 完整 prompt（所有占位符已替换）...")
spawn_agent(agent_type="worker", message="...模块3 完整 prompt（所有占位符已替换）...")
# wait 当前批完成后，再启动下一批
```
