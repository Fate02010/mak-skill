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

Read `SKILL_DIR/steps/step5-agent-prompt.md` 获取提示词模板（含 HTML 和 draw.io 两套模板），按 OUTPUT_FORMAT 选择对应模板，填入模块数据后启动。

**Claude Code（Agent 工具）：** 单次响应内同时调用所有 Agent，每个 Agent 对应一个模块：
```
Agent(prompt="...模块1 完整 prompt...")
Agent(prompt="...模块2 完整 prompt...")
...  # 所有调用在同一响应中发出，并行执行
```

**Codex（Task 工具 + run_in_background）：**
```
# 步骤1：依次创建后台任务
task_1 = Task(prompt="...模块1 完整 prompt...", run_in_background=true)
task_2 = Task(prompt="...模块2 完整 prompt...", run_in_background=true)
...

# 步骤2：等待并收集结果
result_1 = TaskOutput(task_id=task_1.id, block=true)
result_2 = TaskOutput(task_id=task_2.id, block=true)
...
```

### 启动后进度

每个 Agent 完成时，同步更新 `WORK_DIR/执行状态.md` 的"Step 5 Agent 状态"表格。

展示每个 Agent 状态，等待全部完成后进入下一阶段：
```
  ⏳ Agent 1 │ [模块名]（生成中...）
  ✅ Agent 2 │ [模块名]（已完成，N 个文件）
```

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
- **draw.io 模式**：逐一读取所有 `drawio_*_tmp.xml`，提取 `tooltip` 属性中的跳转目标 diagram name，检查是否在任务清单中存在，修复缺失引用

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

1. **生成导航 diagram**：创建一个 `<diagram name="导航-页面跳转地图">` 用矩形 + 箭头绘制完整页面跳转地图，每个矩形节点标注页面名称和所属模块
2. **合并所有 diagram**：按模块顺序读取所有 `drawio_*_tmp.xml`，提取其中的 `<diagram>` 元素，连同导航 diagram 一起写入最终文件：

```xml
<mxfile host="app.diagrams.net" modified="[时间]" agent="Claude Code" version="24.0.0" type="device">
  <!-- 第一个 diagram 为导航跳转地图 -->
  <diagram id="..." name="导航-页面跳转地图">...</diagram>
  <!-- 后续按模块顺序排列各页面 diagram -->
  <diagram id="..." name="用户-登录页">...</diagram>
  <diagram id="..." name="用户-首页">...</diagram>
  ...
</mxfile>
```

3. **清理临时文件**：合并完成后删除所有 `drawio_*_tmp.xml` 文件
4. 在文件第一个 diagram（导航图）的标题区域注明产品名称、生成时间、页面总数
