# Step 5 阶段 5-3：并行启动 subagent（draw.io 两阶段架构）

本文件仅在 OUTPUT_FORMAT=drawio 时加载。
draw.io 生成分为两个独立阶段：
- 阶段 A（规格化）：业务决策层
- 阶段 B（渲染）：格式转换层

---

**架构说明：**
- 阶段 A（规格化）：业务决策层——读取需求文档，确定每个页面的 UI 元素、字段内容、坐标，输出结构化的 `page_spec_[模块英文名].md`
- 阶段 B（渲染）：格式转换层——读取 page_spec + 样式字典，纯机械地将每行转换为 `<mxCell>` XML，输出 `drawio_[模块英文名]_tmp.xml`

**优势：** 规格化和渲染职责分离，渲染 Agent 不做任何业务判断，消除坐标计算错误和占位符内容问题。

---

## 阶段 5-3A：并行启动规格化 Agent

Read `SKILL_DIR/steps/step5-spec-agent-prompt.md` 获取规格化 Agent 提示词模板。

**分模块规则：**
- 一个功能模块 → 一个规格化 Agent
- 单模块超过 4 页时拆分为 2 个 Agent（每个负责 ≤ 4 页，Codex 建议 ≤ 2 页）
- 最多同时启动 **6 个并行 Agent**

**占位符替换清单：**

| 占位符 | 替换为 |
|--------|--------|
| `[SKILL_DIR]` | `/Users/xxx/.claude/skills/prototype-generator` |
| `[WORK_DIR]` | 用户确认的工作目录绝对路径 |
| `[模块名]` / `[模块英文名]` | 当前模块的中文名 / 英文名 |
| `[页面名称N]` / `[章节名]` | 具体页面名 / 对应需求文档章节 |
| `[对象名]` | 该模块管理的业务对象（如「用户」「订单」） |
| `[需求文档读取指令]` | **单文件模式**：`Read [WORK_DIR]/requirements/详细需求文档.md 中以下章节`<br>**分拆模式**：`先 Read [WORK_DIR]/requirements/详细需求文档_overview.md（获取用户角色 §2 和枚举值字典 §5.5）；再 Read [WORK_DIR]/requirements/详细需求文档_[模块中文名].md 中以下章节` |

**Claude Code：**

```
Agent(prompt="...模块1 规格化 prompt（所有占位符已替换）...")
Agent(prompt="...模块2 规格化 prompt（所有占位符已替换）...")
...  # 所有规格化 Agent 在同一响应中并行启动
```

> Codex 环境请参考 `SKILL_DIR/steps/codex-rules.md`。

**熔断规则（同后续渲染阶段）：** 失败 Agent 数 > 50% → 停止，告警用户选择重试/忽略/中止。

---

## ⚠️ Spec 冻结确认（5-3A 与 5-3B 之间的强制等待）

所有规格化 Agent 完成、熔断检查通过后，**必须向用户展示规格摘要并等待确认，禁止自动进入渲染阶段**：

```
=== Spec 冻结确认 ===
规格化已完成，共 N 个模块，M 个 swimlane：

| 模块     | swimlane 清单                          | 类型   | 预计元素数 | page_spec 文件           |
|----------|----------------------------------------|--------|-----------|--------------------------|
| 用户模块 | 登录页、用户列表页、新增/编辑弹窗、删除确认弹窗 | 移动端 | ~45       | page_spec_user.md        |
| 商品模块 | 商品列表页、商品详情页、新增/编辑弹窗           | 移动端 | ~38       | page_spec_product.md     |

请确认规格后，启动渲染：
- 回复"确认"：开始并行渲染（启动 N 个渲染 Agent）
- 回复"查看 [模块名]"：展示对应 page_spec 文件内容
- 回复"修改 [模块名] [说明]"：先修改 page_spec，再渲染
- 回复"取消"：停止流程
```

**收到用户明确回复"确认"后，才能进入阶段 5-3B。**

同时将此次规格摘要写入 `WORK_DIR/执行状态.md` 的"Spec 版本记录"表格（格式见 SKILL.md 中的执行状态文件格式）。

---

## 阶段 5-3B：并行启动渲染 Agent

所有规格化 Agent 完成后，确认每个模块的 `page_spec_[模块英文名].md` 均已写入 `WORK_DIR`，然后启动渲染 Agent。

Read `SKILL_DIR/steps/step5-render-agent-prompt.md` 获取渲染 Agent 提示词模板。

**分模块规则：**
- 一个模块的 page_spec → 一个渲染 Agent（与规格化 Agent 一一对应）
- Codex：每个渲染 Task 对应一个 page_spec 文件（包含 ≤ 2 页的规格）

**占位符替换清单：**

| 占位符 | 替换为 |
|--------|--------|
| `[SKILL_DIR]` | `/Users/xxx/.claude/skills/prototype-generator` |
| `[WORK_DIR]` | 用户确认的工作目录绝对路径 |
| `[模块名]` / `[模块英文名]` | 当前模块的中文名 / 英文名 |

**Claude Code：**

```
Agent(prompt="...模块1 渲染 prompt（所有占位符已替换）...")
Agent(prompt="...模块2 渲染 prompt（所有占位符已替换）...")
...  # 所有渲染 Agent 在同一响应中并行启动
```

> Codex 环境请参考 `SKILL_DIR/steps/codex-rules.md`。
