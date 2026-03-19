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

## 第零步：确认工作目录（WORK_DIR）

1. 用户提供了路径则使用，否则 `Bash: pwd` 获取当前目录
2. 告知用户路径并**等待确认**后才能继续
3. **所有文件必须保存在 `WORK_DIR` 下，严禁写入 `/private/tmp`**

确认 WORK_DIR 后，检查是否已存在 `[产品名称].sql`：不存在 → 全量模式从 Step 1 开始；已存在 → 询问用户选择增量（Step 8）或重新生成。

## 执行计划与进度

启动后**立即**用 `TaskCreate` 为 Step 1-7 各创建一个任务，展示：

```
=== 数据库设计执行计划 ===  工作目录：[WORK_DIR]
[ ] Step 1 选择数据库  [ ] Step 2 扫描资料  [ ] Step 3 架构师角色
[ ] Step 4 领域模型    [ ] Step 5 拆分任务  [ ] Step 6 生成 SQL
[ ] Step 7 审视改进
即将开始，按任意内容继续，或回复"取消"退出。
```

每个 Step 开始时 `TaskUpdate` 标记 `in_progress`，完成后标记 `completed`。

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
├── RountMap.md       ← Step 2
├── 领域模型.md       ← Step 4，Step 7/8 按需更新
├── [产品名称].sql    ← Step 6（含 t_ 前缀表名）
└── ER关系图.md       ← Step 6（Mermaid + 关系表 + 索引说明）
```

## 强制交互点（每处必须等待用户回复）

第零步确认 WORK_DIR → Step 1 选择数据库 → Step 2 确认文件分级 → Step 3 确认架构师角色 → Step 4 确认领域模型 → Step 5 确认任务分组 → Step 7 确认改进建议

> **领域模型是基准：** Step 7/8 发现任何影响领域模型的设计，必须同步更新 `领域模型.md` 并记录变更。
