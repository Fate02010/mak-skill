# Codex 环境专有规则

> 本文件仅在 Codex 环境中加载，Claude Code 环境无需读取。

---

## 运行环境声明

| 项目 | Codex |
|------|-------|
| 识别方式 | 可用工具中有 `Task` |
| SKILL_DIR | `~/.codex/skills/prototype-generator` |
| 并行生成方式 | `Task(prompt="...", run_in_background=True)` + `TaskOutput(task_id=..., block=True)` |
| 等待结果 | 必须用 `TaskOutput(task_id=..., block=True, timeout=300000)` 阻塞等待 |
| 成功标志 | TaskOutput 输出含 `✅` |
| 失败标志 | TaskOutput 输出含 `❌` 或不含 `✅` |

---

## Codex 必须遵守的并行规则

1. **Step 5 并行生成原型时，必须使用 Task 工具**：将每个模块的完整 prompt 作为独立 Task 启动，所有 Task 在同一轮创建以实现真正并行
2. **Task prompt 必须完全自包含**：不继承父会话的任何变量，所有路径（SKILL_DIR、WORK_DIR）必须是实际的绝对路径字符串，不能用变量引用
3. **draw.io 模式两阶段**：先并行创建所有规格化 Task（阶段 A），全部完成后再并行创建所有渲染 Task（阶段 B）
4. **Task 容量限制**：draw.io 模式每个 Task ≤ 2 页（XML 坐标计算复杂）；HTML 模式每个 Task ≤ 4 页
5. **超过容量时拆分**：单模块超过容量上限时，拆为多个 Task，每个 Task 负责部分页面
6. **熔断规则**：所有 Task 完成后统计失败数，失败 > 50% 时停止并告警用户

---

## Step 5 HTML 模式：Task 启动示例

```python
task_1 = Task(prompt="...模块1 完整 prompt...", run_in_background=True)
task_2 = Task(prompt="...模块2 完整 prompt...", run_in_background=True)

result_1 = TaskOutput(task_id=task_1.id, block=True, timeout=300000)
result_2 = TaskOutput(task_id=task_2.id, block=True, timeout=300000)
# 成功标志：输出包含 "✅ [模块名] 完成"
```

## Step 5 占位符替换差异

Codex 环境下，占位符替换规则与 Claude Code 相同，唯一差异：

| 占位符 | Codex 替换为 |
|--------|-------------|
| `[SKILL_DIR]` | `/Users/xxx/.codex/skills/prototype-generator`（注意是 `.codex` 不是 `.claude`） |

其余占位符（`[WORK_DIR]`、`[模块名]`、`[模块英文名]`、`[页面名称N]`、`[章节名]`、`[风格]`/`[颜色]`、`[需求文档读取指令]`）替换规则与 Claude Code 完全一致。

---

## Step 5 draw.io 阶段 A（规格化）：Task 启动示例

```python
spec_1 = Task(prompt="...模块1 规格化 prompt...", run_in_background=True)
spec_2 = Task(prompt="...模块2 规格化 prompt...", run_in_background=True)

result_spec_1 = TaskOutput(task_id=spec_1.id, block=True, timeout=300000)
result_spec_2 = TaskOutput(task_id=spec_2.id, block=True, timeout=300000)
# 成功标志：输出包含 "✅ [模块名] page_spec 完成"
```

## Step 5 draw.io 阶段 B（渲染）：Task 启动示例

```python
render_1 = Task(prompt="...模块1 渲染 prompt...", run_in_background=True)
render_2 = Task(prompt="...模块2 渲染 prompt...", run_in_background=True)

result_render_1 = TaskOutput(task_id=render_1.id, block=True, timeout=300000)
result_render_2 = TaskOutput(task_id=render_2.id, block=True, timeout=300000)
# 成功标志：输出包含 "✅ [模块名] 渲染完成"
```

## Codex 特别注意事项

- Task prompt 完全自包含，所有路径必须是实际字符串
- SKILL_DIR 使用 `~/.codex/skills/prototype-generator`（不是 `.claude`）
- 如果 styles 文件 Read 失败，渲染 Agent 使用 prompt 内联的兜底样式继续执行，标注 `⚠️ styles文件读取失败`
- draw.io 渲染 Task：每个 Task 对应 ≤ 2 页的 page_spec（规格化阶段已按此拆分）
- **HTML 模式**：每个 Task 建议负责 ≤ 4 页

---

## ⚠️ Codex 强制：TaskOutput 收集后的主进程验收（不可跳过）

> 所有 Task 的 TaskOutput 返回后，Codex 主进程在进入阶段 5-5 之前，必须完成以下快速验收，发现问题立即重跑对应 Task：

### 1. 模块产出统计验收

逐模块读取 TaskOutput 内容，提取 `✅ [模块名] 完成` 行中的 swimlane 数量，与原型任务清单对照：

```
模块 [X]：任务清单要求 N 个 swimlane，Task 报告 M 个 →
  M < N：缺少 swimlane，必须重跑该模块 Task
  M ≥ N：通过
```

### 2. Tab 页拆分验收

对每个已生成的 drawio_*_tmp.xml 文件（或 HTML 文件），检查是否存在以下情况：

```
Grep 搜索 "部门管理|角色管理|权限管理|管理员" 等同属一个 Tab 的功能点是否出现在同一个 swimlane 标题 (name=) 中
```

- 若多个 Tab 功能点在同一个 swimlane 内 → 说明 Tab 未拆分，重新生成该模块 Task，要求每个 Tab 独立 swimlane
- 每个 swimlane 应只包含一个功能点的内容

### 3. 关键按钮缺失验收

对每个详情页/表单页（HTML 模式：`.html` 文件；draw.io 模式：`page_spec_*.md` 或 `drawio_*_tmp.xml`），检查需求文档中标注的"主操作"按钮是否在 UI 区存在：

```
读取 WORK_DIR/原型任务清单.md，找到每个页面的"主操作"字段
对照原型文件中是否有对应按钮（Grep 搜索按钮名称）
缺失 → 用 Edit 工具直接追加对应按钮 mxCell 或 HTML 元素，不重跑整个 Task
```

验收通过后，才进入阶段 5-5 执行全量质量校验。

---

## Step 4 需求文档并行生成：Task 启动示例

```python
task_1 = Task(prompt="...模块1 完整 prompt...", run_in_background=True)
task_2 = Task(prompt="...模块2 完整 prompt...", run_in_background=True)

result_1 = TaskOutput(task_id=task_1.id, block=True, timeout=300000)
result_2 = TaskOutput(task_id=task_2.id, block=True, timeout=300000)
# 成功标志：输出包含 "✅ 详细需求文档_[模块中文名].md 完成"
```

---

## Step 7 增量模式：Task 启动方式

新增页面并行生成时，使用 `Task` + `run_in_background=true`，启动方式同 Step 5。
