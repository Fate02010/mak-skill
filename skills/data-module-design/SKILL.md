---
name: data-module-design
description: |
  根据产品资料自动生成数据库表结构设计的完整工作流，输出标准 SQL 文件，也支持在已有 SQL 基础上增量新增表或修改表结构。当用户想要：
  - 根据产品文档/PRD/需求资料设计数据库表结构
  - 生成建表 SQL 文件 / DDL
  - 对产品做数据模型设计 / 数据建模
  - 设计 ER 图 / ER 模型 / 实体关系图
  - 说"帮我设计数据库"、"生成建表SQL"、"数据库表结构设计"、"表结构设计"、"数据库schema"时
  - 说"数据建模"、"数据模型设计"、"画ER图"、"生成DDL"时
  - 说"领域模型"、"DDD建模"、"聚合设计"、"实体设计"时
  - 在已有 SQL 上新增表，说"新增XX表"、"帮我补充XX模块的表"时
  - 修改现有表结构，说"修改XX表"、"给XX表加个字段"、"改一下XX表的索引"时
  请务必使用此 skill。
---

# 数据库表结构设计工作流

你是一位经验丰富的数据库架构师。当用户提供产品资料后，按以下工作流生成标准 SQL 建表文件。

**关键机制：** 每个 Step 的详细指令存放在 `steps/` 目录下，执行到对应 Step 时用 `Read` 工具加载。`SKILL_DIR` 指本 skill 所在目录。

## 运行环境声明

本 skill 在两种环境中运行，启动时必须识别当前环境并遵循对应规则：

| 项目 | Claude Code | Codex |
|------|------------|-------|
| 识别方式 | 可用工具中有 `Agent` | 可用工具中有 `Task` |
| SKILL_DIR | `~/.claude/skills/data-module-design` | `~/.codex/skills/data-module-design` |
| 并行生成方式 | `Agent(prompt="...", run_in_background=True)` | `Task(prompt="...", run_in_background=True)` + `TaskOutput(task_id=..., block=True)` |
| 等待结果 | Agent 自动返回结果 | 必须用 `TaskOutput(task_id=..., block=True, timeout=300000)` 阻塞等待 |
| 成功标志 | Agent 返回含 `✅` | TaskOutput 输出含 `✅` |
| 失败标志 | Agent 返回含 `❌` 或异常 | TaskOutput 输出含 `❌` 或不含 `✅` |

**Codex 必须遵守的并行规则：**

1. **Step 6 并行生成 SQL 时，必须使用 Task 工具**：将每个模块的完整 prompt 作为独立 Task 启动，所有 Task 在同一轮创建以实现真正并行
2. **Task prompt 必须完全自包含**：不继承父会话的任何变量，所有路径（SKILL_DIR、WORK_DIR）必须是实际的绝对路径字符串
3. **熔断规则**：所有 Task 完成后统计失败数，失败 > 50% 时停止并告警用户

## 第零步：确认工作目录（WORK_DIR）

**必须主动询问用户：**

```
所有生成文件（RountMap.md、SQL 文件、设计文档等）将保存在同一目录下。
请指定保存目录，或直接回复"当前目录"使用默认路径。
```

- 用户指定路径 → 使用该路径
- 用户回复"当前目录"或未指定 → `Bash: pwd` 获取，再告知用户实际路径

**确认后** 将路径记为 `WORK_DIR`，**所有后续步骤和子 Agent 必须使用此绝对路径，严禁写入 `/private/tmp` 或任何系统临时目录。**

确认 WORK_DIR 后，**检查是否存在 `执行状态.md`**：

- **存在且状态为"进行中"** → 检测到中断，询问用户：

```
检测到上次执行未完成：
  当前进度：Step [X]（[Step 名称]）
  工作目录：[WORK_DIR]

请选择：
1. 从断点继续（跳过已完成的 Step，继续未完成部分）
2. 重新生成（从头开始，覆盖已有文件）
3. 取消
```

- **存在且状态为"已完成"** → 询问用户选择增量（Step 8）或重新生成
- **不存在** → 全量模式从 Step 1 开始

## 执行计划与进度

启动后**立即**：
1. 用 `TaskCreate` 为 Step 1-7 各创建一个任务
2. 写入 `WORK_DIR/执行状态.md`（格式见下方），后续每个 Step 开始/完成时更新

展示：

```
=== 数据库设计执行计划 ===  工作目录：[WORK_DIR]
[ ] Step 1 选择数据库  [ ] Step 2 扫描资料  [ ] Step 3 架构师角色
[ ] Step 4 领域模型    [ ] Step 5 拆分任务  [ ] Step 6 生成 SQL
[ ] Step 7 审视改进
即将开始，按任意内容继续，或回复"取消"退出。
```

每个 Step 开始时 `TaskUpdate` 标记 `in_progress`，完成后标记 `completed`；同步更新 `执行状态.md`。

**执行状态文件格式：**

```markdown
# 执行状态

| 项目 | 内容 |
|------|------|
| 产品名称 | [产品名称] |
| 目标数据库 | [MySQL/PostgreSQL/...] |
| WORK_DIR | [绝对路径] |
| 整体状态 | 进行中 / 已完成 |
| 最后更新 | [时间] |

## Step 完成状态

| Step | 状态 | 输出文件 |
|------|------|----------|
| Step 1 DB选择 | ✅ 完成 | - |
| Step 2 扫描 | ✅ 完成 | RountMap.md |
| Step 3 架构师 | ✅ 完成 | 角色设定 |
| Step 4 领域模型 | 🔄 进行中 | - |
| Step 5 拆分任务 | ⏳ 待执行 | - |
| Step 6 生成SQL | ⏳ 待执行 | - |
| Step 7 审视 | ⏳ 待执行 | - |

## Step 6 Agent 状态（Step 6 开始后填写）

| Agent | 聚合 | 状态 | 输出文件 |
|-------|------|------|----------|
| Agent 1 | [聚合名] | ✅ 完成 | sql_xxx.sql |

## Step 7 迭代记录

| 轮次 | 改进内容摘要 |
|------|-------------|
| 第 1 轮 | [摘要] |
```

## 按需加载指令

| Step | 指令文件 | 说明 |
|------|---------|------|
| 1 | `SKILL_DIR/steps/step1-db-select.md` | 选择目标数据库 |
| 2 | `SKILL_DIR/steps/step2-scan.md` | 扫描资料，生成 RountMap.md |
| 3 | `SKILL_DIR/steps/step3-architect-prompt.md` | 生成架构师 prompt，设定角色 |
| 4 | `SKILL_DIR/steps/step4-domain-model.md` | 识别业务实体，生成 领域模型.md |
| 5 | `SKILL_DIR/steps/step5-split-tasks.md` | 按聚合拆分设计任务 |
| 6 | `SKILL_DIR/steps/step6-generate-sql.md` | 并行生成 SQL，生成 ER关系图.md |
| 7 | `SKILL_DIR/steps/step7-review.md` | 审视检查，改进建议 |
| 8 | `SKILL_DIR/steps/step8-incremental.md` | 增量新增表或修改表结构 |

SQL 规范（每个生成子任务必须加载）：`SKILL_DIR/steps/step4-sql-rules.md`

## 输出文件

```
WORK_DIR/
├── 执行状态.md           ← 第零步初始化，每步更新（支持断点恢复）
├── RountMap.md           ← Step 2
├── 领域模型.md           ← Step 4，Step 7/8 按需更新
├── [产品名称].sql        ← Step 6（含 t_ 前缀表名）
├── ER关系图.md           ← Step 6（Mermaid + 关系表 + 索引说明）
└── 数据详细设计文档.md   ← Step 6（字段明细、业务规则、流程说明、数据字典）
```

## 强制交互点（每处必须等待用户回复）

第零步确认 WORK_DIR → Step 1 选择数据库 → Step 2 确认文件分级 → Step 3 确认架构师角色 → Step 4 确认领域模型 → Step 5 确认任务分组 → Step 7 确认改进建议

> **领域模型是基准：** Step 7/8 发现任何影响领域模型的设计，必须同步更新 `领域模型.md` 并记录变更。
