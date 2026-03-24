# Step 5 阶段 5-3：并行启动 subagent（HTML 模式）

本文件仅在 OUTPUT_FORMAT=html 时加载。

---

### 前置准备：复制共享 CSS 到 prototypes 目录

启动 subagent 之前，先将共享样式文件复制到输出目录：

```bash
mkdir -p WORK_DIR/prototypes
cp SKILL_DIR/templates/common.css WORK_DIR/prototypes/common.css
```

> 所有 HTML 页面通过 `<link rel="stylesheet" href="common.css">` 引用此文件。
> subagent 生成的 HTML 中**禁止在 `<style>` 中重复定义 `:root` 变量和通用组件样式**。

### 分模块规则

- 一个功能模块 → 一个 Agent
- 单模块超过 6 页时拆分为 2 个 Agent
- 最多同时启动 **6 个并行 Agent**
- 每个 Task（Codex）建议负责 ≤ 4 页

### 启动方式

Read `SKILL_DIR/steps/step5-agent-prompt.md` 获取提示词模板，使用 HTML 模板。

**占位符替换清单（两种运行环境均强制要求）：**

| 占位符 | 替换为 |
|--------|--------|
| `[SKILL_DIR]` | `/Users/xxx/.claude/skills/prototype-generator` |
| `[WORK_DIR]` | 用户确认的工作目录绝对路径 |
| `[模块名]` / `[模块英文名]` | 当前模块的中文名 / 英文名 |
| `[页面名称N]` | 该模块负责的具体页面名 |
| `[章节名]` | 需求文档中对应章节标题 |
| `[风格]` / `[颜色]` | 实际设计风格和主色调 |
| `[需求文档读取指令]` | **单文件模式**：`Read [WORK_DIR]/requirements/详细需求文档.md 中以下章节`<br>**分拆模式**：`先 Read [WORK_DIR]/requirements/详细需求文档_overview.md（获取用户角色 §2 和枚举值字典 §5.5）；再 Read [WORK_DIR]/requirements/详细需求文档_[模块中文名].md 中以下章节` |

> **替换前必须自检**：搜索 prompt 文本中是否还有 `[` 字符——若有则先补全再发送。

**Claude Code（Agent 工具）：**

```
Agent(prompt="...模块1 完整 prompt（所有占位符已替换）...")
Agent(prompt="...模块2 完整 prompt（所有占位符已替换）...")
...  # 所有调用在同一响应中发出，并行执行
```

> Codex 环境请参考 `SKILL_DIR/steps/codex-rules.md`。
