# Step 5：工作流——并行生成 HTML 原型图

分六个阶段执行。

## 阶段 5-1：读取需求，功能划分

1. 读取 `详细需求文档.md` 中的"原型图清单"
2. 将所有页面按功能模块分组，估算每页复杂度（简单/中等/复杂）
3. **绘制页面跳转地图**：梳理所有页面间跳转关系，确保每条路径都有目标页面。发现断头路立即补充到任务清单。
4. Read `SKILL_DIR/steps/step5-tasklist-format.md` 获取格式规范，输出 `原型任务清单.md` 到 `WORK_DIR`

## 阶段 5-2：拆分生成任务

将原型页面拆分为独立任务，每个任务记录：页面名/文件名、需求文档对应章节标题、完整进出跳转关系、视觉风格。写入 `原型任务清单.md`。

## 阶段 5-3：并行启动 subagent 生成原型图

> 根据 OUTPUT_FORMAT 选择规范文件：HTML → `html-spec.md`；draw.io → `drawio-spec.md`

### 启动前：向用户展示执行计划

列出每个 Agent 负责的模块、页面列表、页面数量，告知输出目录和预计文件数，**等待用户确认后**再启动。

### 分模块规则

- 一个功能模块 → 一个 Agent
- 单模块超过 6 页时拆分为 2 个 Agent
- 最多同时启动 **6 个并行 Agent**

### 启动方式

Read `SKILL_DIR/steps/step5-agent-prompt.md` 获取提示词模板（含 HTML 和 draw.io 两套模板），按 OUTPUT_FORMAT 选择对应模板。

**启动前必须完成的占位符替换（两种运行环境均强制要求）：**

| 占位符 | Claude Code 替换为 | Codex 替换为 |
|--------|-------------------|-------------|
| `[SKILL_DIR]` | `/Users/xxx/.claude/skills/prototype-generator` | `/Users/xxx/.codex/skills/prototype-generator` |
| `[WORK_DIR]` | 用户确认的工作目录绝对路径 | 同左，必须是绝对路径 |
| `[模块名]` / `[模块英文名]` | 当前模块的中文名 / 英文名 | 同左 |
| `[模块名称]` | diagram 的 name 值（如 `用户模块`） | 同左 |
| `[页面名称N]` | 该模块负责的具体页面名 | 同左 |
| `[章节名]` | 需求文档中对应章节标题 | 同左 |
| `[画布宽]` / `[画布高]` | 移动端 595/860；Web 1700/960 | 同左 |
| `[风格]` / `[颜色]` | 实际设计风格和主色调 | 同左 |

> **替换前必须自检**：在发送任何 prompt 前，搜索 prompt 文本中是否还有 `[` 字符——若有则说明有占位符未替换，必须先补全再发送。

**Claude Code（Agent 工具）：** 单次响应内同时调用所有 Agent：

```
Agent(prompt="...模块1 完整 prompt（所有占位符已替换）...")
Agent(prompt="...模块2 完整 prompt（所有占位符已替换）...")
...  # 所有调用在同一响应中发出，并行执行
```

**Codex（Task 工具）：**

```python
# 步骤1：批量创建后台任务（所有 Task 在同一轮创建，实现真正并行）
# Codex 每个 Task 建议最多 4 页（避免单 Task 超时）
task_1 = Task(prompt="...模块1 完整 prompt...", run_in_background=True)
task_2 = Task(prompt="...模块2 完整 prompt...", run_in_background=True)
task_3 = Task(prompt="...模块3 完整 prompt...", run_in_background=True)

# 步骤2：阻塞等待所有任务完成，逐一检查输出
result_1 = TaskOutput(task_id=task_1.id, block=True, timeout=300000)
result_2 = TaskOutput(task_id=task_2.id, block=True, timeout=300000)
result_3 = TaskOutput(task_id=task_3.id, block=True, timeout=300000)

# 步骤3：检测每个任务的成功/失败
# 成功标志：输出包含 "✅ [模块名] 完成"
# 失败标志：输出包含 "❌" 或不包含 "✅"
```

**Codex 特别注意事项：**
- Task prompt 完全自包含，不继承父会话任何变量，所有路径必须是实际字符串
- SKILL_DIR 使用 `~/.codex/skills/prototype-generator`（不是 `.claude`）
- 如果 spec 文件 Read 失败，Task 应用 prompt 内联的 R1-R5 规则继续执行，并在输出中标注 `⚠️ spec文件读取失败，已用内联规则`
- 每个 Task 建议负责 ≤ 4 页；超过 4 页的模块在 Codex 环境下拆分为 2 个 Task

### 启动后进度

每个 Agent 完成时，同步更新 `WORK_DIR/执行状态.md` 的"Step 5 Agent 状态"表格。

展示每个 Agent 状态，等待全部完成后进入下一阶段：
```
  ⏳ Agent 1 │ [模块名]（生成中...含三轮精修）
  ✅ Agent 2 │ [模块名]（已完成，N 个文件，含三轮精修）
```

> 每个 subagent 内部已执行三轮精修（字段完整性 → 内容真实性 → 交互闭环），汇报行包含"含三轮精修"字样时说明精修已完成。

**熔断规则：** 所有 Agent 完成后统计失败数量：
- 失败 Agent 数 ≤ 总数 50%：记录失败项，继续后续流程，最后统一补充生成
- 失败 Agent 数 > 总数 50%：**立即停止**，向用户告警：

```
⚠️ 熔断警告：[N] 个 Agent 中有 [M] 个失败（超过 50%），流程已暂停。
失败模块：[模块1]、[模块2]、...

请选择：
1. 重试失败的 Agent（推荐）
2. 忽略失败，继续生成已完成部分
3. 中止流程
```

## 阶段 5-4：收集需求变更，更新需求文档

所有并行任务完成后：

1. 读取所有原型文件（HTML 模式：`.html` 文件；draw.io 模式：`drawio_*_tmp.xml` 临时文件），提取 `<!-- REQUIREMENT_CHANGES ... -->` 注释
2. 判断哪些需要同步回需求文档：
   - **假设性决策**：合理则固化为正式需求
   - **需求遗漏**：补充到需求文档对应章节
   - **主动新增**：在原型图清单中补充新增页面
3. 编辑 `详细需求文档.md`，末尾追加"变更记录"章节
4. 将变更汇总记录到 `原型任务清单.md` 末尾的"需求变更汇总"区块

## 阶段 5-5：强制自查（质量校验）

生成导航首页之前，**必须完成以下校验**，发现问题立即修复，不得跳过。

> draw.io 模式：Read `SKILL_DIR/steps/drawio-design-rules.md` 获取输出文件规则和校验标准。

### 1. 文件完整性校验

- **HTML 模式**：用 `Glob` 扫描 `WORK_DIR/prototypes/` 目录，对比原型任务清单，列出缺失的 `.html` 文件，重新生成
- **draw.io 模式**：用 `Glob` 扫描 `WORK_DIR/` 下的 `drawio_*_tmp.xml` 临时文件，对比模块任务列表，列出缺失的模块临时文件，重新生成对应 Agent

### 2. 跳转标注校验

- **HTML 模式**：逐一读取所有 HTML 文件，提取 `href` / `onclick` 跳转目标，检查目标文件是否实际存在，修复断链
- **draw.io 模式**：
  - 逐一读取所有 `drawio_*_tmp.xml`，提取 `tooltip` 属性中的跳转目标 diagram name，检查是否在任务清单中存在，修复缺失引用
  - **跨模块跳转完整性校验**：汇总所有模块 tooltip 中引用的跨模块目标（格式"→ 目标模块/目标页面"），对照导航 diagram 中的连线（edge），检查每条跨模块引用是否在导航图中有对应箭头；缺失的连线直接用 Edit 工具追加到导航 diagram XML 中

### 3. 内容有效性校验

逐一读取生成的文件，检查基本结构完整性：

**HTML 模式** — 每个文件必须包含：
- `<html>`、`<head>`、`<body>` 标签
- `<title>` 标签（页面名称）
- 至少一个可交互元素（`<a>`、`<button>` 或带 `onclick` 的元素）
- 无明显截断（文件末尾含 `</html>`）

**draw.io 模式** — 每个 `drawio_*_tmp.xml` 临时文件必须包含：
- 至少一个 `<diagram>` 标签（含 `id` 和 `name` 属性）
- `<mxGraphModel>` 和 `<root>` 标签
- 至少 3 个 `<mxCell>` 元素（id=0、id=1 基础层 + 至少一个 UI 元素）
- **XML 合法性校验**：用 Grep 检查 mxCell `value=""` 属性中是否含有未转义的特殊字符：
  - 搜索 `value="[^"]*&[^a-z#][^"]*"` 形式（裸 `&` 未转义为 `&amp;`）
  - 搜索 `value="[^"]*<[^/!][^"]*"` 形式（裸 `<` 未转义为 `&lt;`）
  - 发现则用 Edit 工具修复对应 value（替换为正确转义），不重新生成整个 Agent
- **swimlane parent 校验**：文件中每个 swimlane 容器（style 含 `swimlane`）都有一个 `id`（设为 `S`），其内部 UI 元素的 `parent` 必须等于 `S`，而不是 `"1"`。用 Grep 检查是否存在 `parent="1"` 的非 swimlane 元素混在 swimlane 内部——若存在，说明 subagent 未正确设置 parent，需重新生成该模块

**draw.io 模式禁止内容检测**：用 Grep 在所有 `drawio_*_tmp.xml` 中搜索以下关键词，发现则标记该文件并要求修复（删除或移至独立文档）：
- `关键规则`、`验收线`、`开发注意`、`测试用例`、`TODO`、`待定`、`待补充`
这些内容不属于原型，不得出现在 mxCell value 中。

**draw.io 模式尺寸合规抽查**：对每个 `drawio_*_tmp.xml`，用 Grep 抽查 `height=` 属性值，检测是否出现明显不合规的尺寸：
- 按钮/输入框类组件（style 含 `fillColor` 且非背景）height 应在 32–56px 范围内；发现 height > 80 或 height < 24 的非背景组件需标记
- 表格行高应在 44–56px；发现 height > 80px 的 list row 需标记
- 记录到自查报告，提示"检测到 N 个组件高度不符合规范，建议检查 [文件名]"；不强制重新生成，由人工复核

发现不合格文件 → 记录并重新生成对应 Agent。

### 4. 需求覆盖校验

对照 `详细需求文档.md` 的"原型图清单"，确认每一行对应的文件均已生成，输出校验结果：

```
=== 自查报告 ===

✅ 文件完整性：N 个文件全部生成
✅ 内容有效性：N 个文件结构校验通过（⚠️ X 个文件已重新生成）
⚠️ 断链修复：发现 X 处断链，已修复
❌ 缺失页面：[页面名] 未生成，已补充生成

自查通过，进入下一阶段。
```

> 若存在无法自动修复的问题，向用户说明后继续。

## 阶段 5-6：合并文件 / 生成导航首页

更新需求文档后，根据 OUTPUT_FORMAT 处理：

**HTML 模式** → 生成 `prototypes/index.html`：
- 列出所有原型页面及功能说明，提供跳转链接
- 显示产品名称和版本信息
- 可视化展示页面跳转地图（箭头连线）

**draw.io 模式** → 合并为单一文件 `prototypes/[产品名称].drawio`：

1. **生成导航 diagram**：创建一个 `<diagram name="导航-页面跳转地图">`，规则如下：
   - **按模块分组**：为每个功能模块创建一个 group 容器（style=`swimlane;startSize=30;fillColor=#f5f5f5;strokeColor=#bdbdbd;fontStyle=1;fontSize=13;`），所有页面节点的 `parent` 指向该 group 的 id，不得全部平铺在 `parent="1"`
   - **模块 group 布局**：各 group 水平排列，间距 60px；group 内页面节点**垂直排列**，节点间距 24px；group 宽度 = 节点宽 + 40，高度 = 节点数 × (节点高+24) + 60
   - **节点规格（必须够大，禁止文字溢出）**：每个页面矩形 **width=160，height=48**，圆角 style=`rounded=1;whiteSpace=wrap;html=1;fillColor=#e3f2fd;strokeColor=#1e88e5;fontSize=12;`；节点文字只写页面名称，不写"进入""跳转"等前缀
   - **跳转连线标签（必须简短）**：连线上的 value 只写触发动作（如"点击下单"、"返回"、"提交"），**禁止**写"进入 目标页面名"——目标已由箭头指向表达，无需重复
   - **边距与间距**：group 之间水平间距 ≥ 60px，避免箭头穿越 group 框；优先使用正交折线（orthogonalEdgeStyle）减少交叉
   - **禁止**：页面节点全部 `parent="1"` 平铺（无分组）；箭头标签写"进入 XXX页"导致与节点文字重叠
2. **合并前 ID 重新编号（必须执行，防止冲突）**：

   每个 subagent 生成的 diagram 内部 mxCell id 都从 0 开始，直接合并会大量重复。合并前逐个 diagram 做 id 偏移：
   - 导航 diagram：id 从 `0` 开始（保持 id=0、id=1 基础层）
   - 第 1 个模块 diagram：所有 mxCell id（除 0、1）加偏移量 `1000`
   - 第 2 个模块 diagram：所有 mxCell id（除 0、1）加偏移量 `2000`
   - 第 N 个模块 diagram：所有 mxCell id（除 0、1）加偏移量 `N×1000`
   - 同时更新该 diagram 内所有 `source`、`target`、`parent`（非 0、1）引用为偏移后的值

3. **合并所有 diagram**：按模块顺序读取所有 `drawio_*_tmp.xml`，提取其中的 `<diagram>` 元素，连同导航 diagram 一起写入最终文件：

```xml
<mxfile host="app.diagrams.net" modified="[时间]" agent="Claude Code" version="24.0.0" type="device">
  <!-- 第一个 sheet：导航跳转地图 -->
  <diagram id="..." name="导航-页面跳转地图">...</diagram>
  <!-- 后续按模块顺序，每个模块一个 sheet，模块内各页面用 swimlane 并排 -->
  <diagram id="..." name="用户模块">...</diagram>
  <diagram id="..." name="订单模块">...</diagram>
  <diagram id="..." name="商品模块">...</diagram>
  ...
</mxfile>
```

4. **清理临时文件**：合并完成后删除所有 `drawio_*_tmp.xml` 文件
5. 在文件第一个 diagram（导航图）的标题区域注明产品名称、生成时间、页面总数
