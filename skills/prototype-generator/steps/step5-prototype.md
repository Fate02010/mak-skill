# Step 5：工作流——并行生成 HTML 原型图

分六个阶段执行。

## 阶段 5-1：读取需求，功能划分

**⚠️ 功能模块定义（draw.io 模式 sheet 命名强制规则）：**

"功能模块"= **业务域**，以产品功能命名，**不是系统层或技术层**。

| ✅ 正确（业务域）| ❌ 错误（系统层/技术层）|
|----------------|------------------------|
| 用户模块 | APP系统 |
| 商品模块 | 后台管理 |
| 订单模块 | 移动端 |
| 支付模块 | Web端 |
| 营销模块 | 前台 |

> "APP系统"不是一个功能模块，它包含多个功能模块（用户、商品、订单等），必须继续拆分。
> "后台管理"同理，必须拆分为具体的功能模块（权限管理、内容管理、数据统计等）。
> **每个 draw.io sheet 只对应一个具体业务域，sheet 名 = 模块名（如"订单模块"）。**

**需求文档读取模式检测（必须最先执行）：**

```
检查 WORK_DIR/requirements/index.md 是否存在：
  存在 → 分拆模式（DOC_MODE = split）：
    - Read WORK_DIR/requirements/index.md，获取所有模块文件路径列表
    - 原型图清单来自：requirements/详细需求文档_overview.md §7
    - 用户角色/枚举值来自：requirements/详细需求文档_overview.md §2 / §5.5
    - 各模块功能细节来自：index.md 中对应模块的文件路径
  不存在 → 单文件模式（DOC_MODE = single）：
    - 所有信息来自：requirements/详细需求文档.md
```

> **分拆模式下，启动每个 subagent 前，从 index.md 查找该模块的文件路径，填入 `[需求文档读取指令]` 占位符；不得硬编码猜测文件名。**

1. 读取原型图清单（分拆模式：`requirements/详细需求文档_overview.md` §7；单文件模式：`requirements/详细需求文档.md` §7）
2. 将所有页面按**业务域**功能模块分组，估算每页复杂度（简单/中等/复杂）
3. **绘制页面跳转地图**：梳理所有页面间跳转关系，确保每条路径都有目标页面。发现断头路立即补充到任务清单。
4. **CRUD 完整性检查**：对任务清单中每个"列表页/管理页"，检查是否已包含以下四个关联元素。缺少任何一项立即补充到任务清单：

   | 必须存在的元素 | 说明 |
   |--------------|------|
   | 列表页（含操作列） | 筛选区 + 表格 + 分页；行操作列包含"编辑"和"删除"按钮；页面右上角有"新增"主按钮 |
   | 新增表单（页面或弹窗） | 独立页面 or 在列表页内绘制的 Modal；字段来自需求文档 |
   | 编辑表单（页面或弹窗） | 与新增相同字段，但带初始数据；通常复用同一个页面/弹窗（"新增/编辑"合并） |
   | 删除确认弹窗 | 必须是弹窗（禁止直接删除），显示被删项名称，"确认删除"（红色）+ "取消"按钮 |

   > 若需求文档明确说明使用弹窗（Modal）方式，则新增/编辑弹窗在列表页 swimlane 内绘制；若为独立页面，则单独列为任务项。

5. Read `SKILL_DIR/steps/step5-tasklist-format.md` 获取格式规范，输出 `原型任务清单.md` 到 `WORK_DIR`

## 阶段 5-2：拆分生成任务

将原型页面拆分为独立任务，每个任务记录：页面名/文件名、需求文档对应章节标题、完整进出跳转关系、视觉风格。写入 `原型任务清单.md`。

## 阶段 5-3：并行启动 subagent 生成原型图

> - **HTML 模式**：直接启动生成 Agent，使用 `step5-agent-prompt.md` 中的 HTML 模板。
> - **draw.io 模式**：两阶段架构——先并行启动规格化 Agent（阶段 5-3A），再并行启动渲染 Agent（阶段 5-3B）。

### 启动前：向用户展示执行计划

列出每个 Agent 负责的模块、页面列表、页面数量，告知输出目录和预计文件数，**等待用户确认后**再启动。

---

### HTML 模式

#### 分模块规则

- 一个功能模块 → 一个 Agent
- 单模块超过 6 页时拆分为 2 个 Agent
- 最多同时启动 **6 个并行 Agent**
- 每个 Task（Codex）建议负责 ≤ 4 页

#### 启动方式

Read `SKILL_DIR/steps/step5-agent-prompt.md` 获取提示词模板，使用 HTML 模板。

**占位符替换清单（两种运行环境均强制要求）：**

| 占位符 | Claude Code 替换为 | Codex 替换为 |
|--------|-------------------|-------------|
| `[SKILL_DIR]` | `/Users/xxx/.claude/skills/prototype-generator` | `/Users/xxx/.codex/skills/prototype-generator` |
| `[WORK_DIR]` | 用户确认的工作目录绝对路径 | 同左，必须是绝对路径 |
| `[模块名]` / `[模块英文名]` | 当前模块的中文名 / 英文名 | 同左 |
| `[页面名称N]` | 该模块负责的具体页面名 | 同左 |
| `[章节名]` | 需求文档中对应章节标题 | 同左 |
| `[风格]` / `[颜色]` | 实际设计风格和主色调 | 同左 |
| `[需求文档读取指令]` | **单文件模式**：`Read [WORK_DIR]/requirements/详细需求文档.md 中以下章节`<br>**分拆模式**：`先 Read [WORK_DIR]/requirements/详细需求文档_overview.md（获取用户角色 §2 和枚举值字典 §5.5）；再 Read [WORK_DIR]/requirements/详细需求文档_[模块中文名].md 中以下章节` | 同左 |

> **替换前必须自检**：搜索 prompt 文本中是否还有 `[` 字符——若有则先补全再发送。

**Claude Code（Agent 工具）：**

```
Agent(prompt="...模块1 完整 prompt（所有占位符已替换）...")
Agent(prompt="...模块2 完整 prompt（所有占位符已替换）...")
...  # 所有调用在同一响应中发出，并行执行
```

**Codex（Task 工具）：**

```python
task_1 = Task(prompt="...模块1 完整 prompt...", run_in_background=True)
task_2 = Task(prompt="...模块2 完整 prompt...", run_in_background=True)

result_1 = TaskOutput(task_id=task_1.id, block=True, timeout=300000)
result_2 = TaskOutput(task_id=task_2.id, block=True, timeout=300000)
# 成功标志：输出包含 "✅ [模块名] 完成"
```

---

### draw.io 模式（两阶段架构）

draw.io 生成分为两个独立阶段：

**架构说明：**
- 阶段 A（规格化）：业务决策层——读取需求文档，确定每个页面的 UI 元素、字段内容、坐标，输出结构化的 `page_spec_[模块英文名].md`
- 阶段 B（渲染）：格式转换层——读取 page_spec + 样式字典，纯机械地将每行转换为 `<mxCell>` XML，输出 `drawio_[模块英文名]_tmp.xml`

**优势：** 规格化和渲染职责分离，渲染 Agent 不做任何业务判断，消除坐标计算错误和占位符内容问题。

---

#### 阶段 5-3A：并行启动规格化 Agent

Read `SKILL_DIR/steps/step5-spec-agent-prompt.md` 获取规格化 Agent 提示词模板。

**分模块规则：**
- 一个功能模块 → 一个规格化 Agent
- 单模块超过 4 页时拆分为 2 个 Agent（每个负责 ≤ 4 页，Codex 建议 ≤ 2 页）
- 最多同时启动 **6 个并行 Agent**

**占位符替换清单：**

| 占位符 | Claude Code 替换为 | Codex 替换为 |
|--------|-------------------|-------------|
| `[SKILL_DIR]` | `/Users/xxx/.claude/skills/prototype-generator` | `/Users/xxx/.codex/skills/prototype-generator` |
| `[WORK_DIR]` | 用户确认的工作目录绝对路径 | 同左 |
| `[模块名]` / `[模块英文名]` | 当前模块的中文名 / 英文名 | 同左 |
| `[页面名称N]` / `[章节名]` | 具体页面名 / 对应需求文档章节 | 同左 |
| `[对象名]` | 该模块管理的业务对象（如「用户」「订单」） | 同左 |
| `[需求文档读取指令]` | **单文件模式**：`Read [WORK_DIR]/requirements/详细需求文档.md 中以下章节`<br>**分拆模式**：`先 Read [WORK_DIR]/requirements/详细需求文档_overview.md（获取用户角色 §2 和枚举值字典 §5.5）；再 Read [WORK_DIR]/requirements/详细需求文档_[模块中文名].md 中以下章节` | 同左 |

**Claude Code：**

```
Agent(prompt="...模块1 规格化 prompt（所有占位符已替换）...")
Agent(prompt="...模块2 规格化 prompt（所有占位符已替换）...")
...  # 所有规格化 Agent 在同一响应中并行启动
```

**Codex：**

```python
spec_1 = Task(prompt="...模块1 规格化 prompt...", run_in_background=True)
spec_2 = Task(prompt="...模块2 规格化 prompt...", run_in_background=True)

result_spec_1 = TaskOutput(task_id=spec_1.id, block=True, timeout=300000)
result_spec_2 = TaskOutput(task_id=spec_2.id, block=True, timeout=300000)
# 成功标志：输出包含 "✅ [模块名] page_spec 完成"
```

**熔断规则（同后续渲染阶段）：** 失败 Agent 数 > 50% → 停止，告警用户选择重试/忽略/中止。

---

#### ⚠️ Spec 冻结确认（5-3A 与 5-3B 之间的强制等待）

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

#### 阶段 5-3B：并行启动渲染 Agent

所有规格化 Agent 完成后，确认每个模块的 `page_spec_[模块英文名].md` 均已写入 `WORK_DIR`，然后启动渲染 Agent。

Read `SKILL_DIR/steps/step5-render-agent-prompt.md` 获取渲染 Agent 提示词模板。

**分模块规则：**
- 一个模块的 page_spec → 一个渲染 Agent（与规格化 Agent 一一对应）
- Codex：每个渲染 Task 对应一个 page_spec 文件（包含 ≤ 2 页的规格）

**占位符替换清单：**

| 占位符 | Claude Code 替换为 | Codex 替换为 |
|--------|-------------------|-------------|
| `[SKILL_DIR]` | `/Users/xxx/.claude/skills/prototype-generator` | `/Users/xxx/.codex/skills/prototype-generator` |
| `[WORK_DIR]` | 用户确认的工作目录绝对路径 | 同左 |
| `[模块名]` / `[模块英文名]` | 当前模块的中文名 / 英文名 | 同左 |

**Claude Code：**

```
Agent(prompt="...模块1 渲染 prompt（所有占位符已替换）...")
Agent(prompt="...模块2 渲染 prompt（所有占位符已替换）...")
...  # 所有渲染 Agent 在同一响应中并行启动
```

**Codex：**

```python
render_1 = Task(prompt="...模块1 渲染 prompt...", run_in_background=True)
render_2 = Task(prompt="...模块2 渲染 prompt...", run_in_background=True)

result_render_1 = TaskOutput(task_id=render_1.id, block=True, timeout=300000)
result_render_2 = TaskOutput(task_id=render_2.id, block=True, timeout=300000)
# 成功标志：输出包含 "✅ [模块名] 渲染完成"
```

**Codex 特别注意事项：**
- Task prompt 完全自包含，所有路径必须是实际字符串
- SKILL_DIR 使用 `~/.codex/skills/prototype-generator`（不是 `.claude`）
- 如果 styles 文件 Read 失败，渲染 Agent 使用 prompt 内联的兜底样式继续执行，标注 `⚠️ styles文件读取失败`
- draw.io 渲染 Task：每个 Task 对应 ≤ 2 页的 page_spec（规格化阶段已按此拆分）
- **HTML 模式**：每个 Task 建议负责 ≤ 4 页

### 启动后进度

每个 Agent 完成时，同步更新 `WORK_DIR/执行状态.md` 的"Step 5 Agent 状态"表格。

**HTML 模式** — 展示每个生成 Agent 状态：
```
  ⏳ Agent 1 │ [模块名]（生成中...含三轮精修）
  ✅ Agent 2 │ [模块名]（已完成，N 个文件，含三轮精修）
```

**draw.io 模式（两阶段）** — 分阶段展示：
```
【阶段 A — 规格化】
  ⏳ 规格化 1 │ [模块名]（page_spec 生成中...）
  ✅ 规格化 2 │ [模块名]（page_spec 完成，M 个 swimlane，N 个元素）

【阶段 B — 渲染】（规格化全部完成后启动）
  ⏳ 渲染 1 │ [模块名]（XML 渲染中...）
  ✅ 渲染 2 │ [模块名]（渲染完成，M 个 swimlane，N 个 mxCell）
```

> HTML 模式：每个 subagent 内部已执行三轮精修（字段完整性 → 内容真实性 → 交互闭环）。
> draw.io 模式：规格化 Agent 负责业务决策与坐标计算；渲染 Agent 只做格式转换，不做业务判断。

**熔断规则：** 每阶段所有 Agent 完成后统计失败数量：
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
3. **按文档模式回写：**
   - **单文件模式**：编辑 `requirements/详细需求文档.md`，末尾追加"变更记录"章节
   - **分拆模式**：功能点变更 → 编辑对应 `requirements/详细需求文档_[模块中文名].md`；原型图清单变更（新增页面）→ 编辑 `requirements/详细需求文档_overview.md` §7
4. 将变更汇总记录到 `原型任务清单.md` 末尾的"需求变更汇总"区块

## ⚠️ Codex 强制：TaskOutput 收集后的主进程验收（不可跳过）

> **仅 Codex 环境适用。** 所有 Task 的 TaskOutput 返回后，Codex 主进程在进入阶段 5-5 之前，必须完成以下快速验收，发现问题立即重跑对应 Task：

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

## 阶段 5-5：强制自查（质量校验）

生成导航首页之前，**必须完成以下校验**，发现问题立即修复，不得跳过。

> **Codex 特别注意：** 阶段5-5 是 Codex 主进程必须亲自执行的步骤，不得以"Task 已完成三轮精修"为由跳过。Task 的三轮精修是模块内自检，5-5 是跨模块全局校验，二者不可替代。

> draw.io 模式：Read `SKILL_DIR/steps/drawio-design-rules.md` 获取输出文件规则和校验标准。
> 通用：Read `SKILL_DIR/steps/step5-acceptance-rules.md` 获取 A/B/C 三类验收规则。

### 1. 文件完整性校验

- **HTML 模式**：用 `Glob` 扫描 `WORK_DIR/prototypes/` 目录，对比原型任务清单，列出缺失的 `.html` 文件，重新生成
- **draw.io 模式**：用 `Glob` 扫描 `WORK_DIR/` 下的 `drawio_*_tmp.xml` 临时文件，对比模块任务列表，列出缺失的模块临时文件，重新生成对应 Agent

### 2. 跳转标注校验

- **HTML 模式**：逐一读取所有 HTML 文件，提取 `href` / `onclick` 跳转目标，检查目标文件是否实际存在，修复断链
- **draw.io 模式**：
  - 逐一读取所有 `drawio_*_tmp.xml`，提取 `tooltip` 属性中的跳转目标 diagram name，检查是否在任务清单中存在，修复缺失引用
  - **跨模块跳转完整性校验**：汇总所有模块 tooltip 中引用的跨模块目标（格式"→ 目标模块/目标页面"），对照导航 diagram 中的连线（edge），检查每条跨模块引用是否在导航图中有对应箭头；缺失的连线直接用 Edit 工具追加到导航 diagram XML 中

### 2.5 主流程闭环校验（规则 A5）

按 `step5-acceptance-rules.md` 中 A5 的检查方法执行：读取需求文档「核心业务流程」，逐条验证跳转链路可达性，覆盖 CRUD 闭环、查看闭环、登录闭环。输出闭环校验结果，缺失跳转立即修复。

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

### 3.5 模板合规校验（规则 B1/B2/B4，draw.io 两阶段模式执行）

按 `step5-acceptance-rules.md` 中 B 类规则执行：

- **B1 页面类型校验**：对照需求文档中页面功能描述，确认 page_spec 的类型标注和模板选择正确（列表页不能用表单模板，登录页不能带侧边栏）
- **B2 骨架完整性校验**：逐页统计骨架必备元素（nav/筛选区/表格/分页/提交取消等），输出骨架完整度百分比
- **B4 布局顺序校验**：按 y 坐标排列所有元素，检查 style_key 出现顺序是否符合模板定义（筛选区在表格上方、提交按钮在字段下方等）

不通过 → 用 Edit 修改 page_spec 后重新渲染。

### 4. 需求覆盖校验

对照原型图清单，确认每一行对应的文件均已生成：
- **单文件模式**：读取 `requirements/详细需求文档.md` §7 原型图清单
- **分拆模式**：读取 `requirements/详细需求文档_overview.md` §7 原型图清单

### 5. 字段级 coverage 校验（逐页强制执行，含 A3/A4）

> 本校验检查的不是"文件是否存在"，而是"每个页面内的字段是否与需求文档一一对应"。

**执行流程：**

1. 读取需求文档字段规格（**分拆模式**：按模块逐一读取 `requirements/详细需求文档_[模块中文名].md`；**单文件模式**：读取 `requirements/详细需求文档.md`），对每个有字段规格的功能点，提取以下信息：
   - 列表页：筛选条件列表 + 列表展示列名列表
   - 表单页：表单字段名列表（含控件类型、是否必填）
   - 详情页：展示字段名列表
   - **主操作列表（A3）**：每个页面的核心操作按钮（新增/编辑/删除/提交/导出等）
   - **状态枚举（A4）**：每个模块定义的状态值（待支付/已支付/已发货等）

2. 逐页对照原型文件中实际包含的字段：
   - **draw.io 模式**：读取 `page_spec_*.md`（若两阶段架构）或 `drawio_*_tmp.xml`，提取所有 mxCell 的 value 值，与需求文档字段列表逐一比对
   - **HTML 模式**：读取 `.html` 文件，提取所有 `<label>`、`<th>`、`<input placeholder>`、键值对的 label 文字，与需求文档字段列表逐一比对

3. 输出 coverage 报告：

```
=== 字段 coverage 校验 ===

[页面名1]（列表页）
  筛选条件：✅ 关键词 | ✅ 状态 | ❌ 时间范围（缺失）
  列表列名：✅ 订单编号 | ✅ 客户名称 | ✅ 金额 | ✅ 状态 | ❌ 创建时间（缺失）
  coverage: 7/9 = 78%

[页面名2]（表单页）
  表单字段：✅ 用户名 | ✅ 手机号 | ✅ 邮箱 | ❌ 所属角色（缺失）| ❌ 备注（缺失）
  coverage: 3/5 = 60%

[页面名3]（详情页）
  展示字段：✅ 订单编号 | ✅ 客户名称 | ✅ 金额 | ✅ 状态
  coverage: 4/4 = 100%

=== 总体字段 coverage: 14/18 = 78%，缺失 4 个字段 ===

=== 主操作 coverage（A3）===
[页面名1]：✅ 新增 | ✅ 编辑 | ✅ 删除 | ❌ 导出（缺失）
[页面名2]：✅ 提交 | ✅ 取消

=== 状态 coverage（A4）===
[模块名]：需求定义 5 种状态，原型展示 3 种，覆盖率 60%
  ✅ 待支付 | ✅ 已发货 | ❌ 已完成 | ❌ 已取消 | ✅ 已支付
```

4. **修复缺失项：**
   - 缺失字段：用 Edit 补充到对应文件
   - 缺失主操作（A3）：补充操作按钮（含 tooltip 跳转标注）
   - 缺失状态（A4）：在列表页数据行中补充缺失状态的示例行，在详情页标注区补充状态流转
   - draw.io 两阶段架构：优先修改 `page_spec_*.md`，然后重新运行对应模块的渲染 Agent
   - HTML 模式：直接 Edit 对应 `.html` 文件
   - 修复后重新执行 coverage 计算，确认达到 100%

**质量门禁：**
- 字段 coverage < 80% 的页面 → 必须修复
- 主操作 coverage < 100% → 必须修复（每个主操作按钮都不可缺）
- 状态 coverage < 80% → 必须修复

---

### 校验总结报告

```
=== 自查报告 ===

1. ✅ 文件完整性：N 个文件全部生成
2. ✅ 跳转标注：N 处跳转全部可达（⚠️ 修复了 X 处断链）
3. ✅ 主流程闭环（A5）：N 条核心流程全部闭环
4. ✅ 内容有效性：N 个文件结构校验通过（⚠️ X 个已重新生成）
5. ✅ 模板合规（B1/B2/B4）：所有页面类型正确、骨架完整、布局有序
6. ✅ 需求覆盖：原型图清单 N 项全部对应
7. ✅ 字段 coverage：所有页面 100%
8. ✅ 主操作 coverage（A3）：所有主操作按钮已就位
9. ✅ 状态 coverage（A4）：所有状态枚举覆盖率 ≥ 80%

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
   - 第 1 个模块 diagram：所有 mxCell id（除 0、1）加偏移量 `10000`
   - 第 2 个模块 diagram：所有 mxCell id（除 0、1）加偏移量 `20000`
   - 第 N 个模块 diagram：所有 mxCell id（除 0、1）加偏移量 `N×10000`
   > 偏移量使用 10000 而非 1000，确保单个模块 diagram 内有最多 9999 个元素时也不会产生 id 冲突。
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
