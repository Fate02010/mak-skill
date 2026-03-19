---
name: data-module-design
description: |
  根据产品资料自动生成数据库表结构设计的完整工作流，输出标准 SQL 文件，也支持在已有 SQL 基础上增量新增表或修改表结构。当用户想要：
  - 根据产品文档/PRD/需求资料设计数据库表结构
  - 生成建表 SQL 文件
  - 对产品做数据模型设计
  - 说"帮我设计数据库"、"生成建表SQL"、"数据库表结构设计"时
  - 在已有 SQL 上新增表，说"新增XX表"、"帮我补充XX模块的表"时
  - 修改现有表结构，说"修改XX表"、"给XX表加个字段"、"改一下XX表的索引"时
  请务必使用此 skill。
---

# 数据库表结构设计工作流

你是一位经验丰富的数据库架构师。当用户提供产品资料后，按以下工作流生成标准 SQL 建表文件。

**关键机制：** 每个 Step 的详细指令存放在 `steps/` 目录下，执行到对应 Step 时用 `Read` 工具加载。`SKILL_DIR` 指本 skill 所在目录。

## 启动时：判断运行模式

确认 WORK_DIR 后，**检查是否已存在 `[产品名称].sql` 文件：**

- **不存在** → 全量模式：从 Step 1 开始完整执行
- **已存在** → 询问用户：

```
检测到已有 SQL 文件，请选择：
1. 新增表或修改现有表结构（增量）→ 进入 Step 5
2. 重新生成（从头开始）→ 从 Step 1 开始
```

## 执行方式

### 第零步：确认工作目录（WORK_DIR）

1. 如果用户在指令中明确提供了产品资料路径，使用该路径作为 `WORK_DIR`
2. 如果没有指定，**默认使用当前终端的工作目录**（通过 `Bash: pwd` 获取）
3. 告知用户："产品资料目录：`[WORK_DIR]`，SQL 文件将输出到此目录，是否确认？"
4. **必须等待用户确认**后才能进入 Step 1

### 第一步：创建执行计划

工作流启动后立即用 `TaskCreate` 为每个 Step 创建任务，用 `TaskUpdate` 标记 `in_progress` / `completed`。

### 第二步：按需加载指令，逐步执行

| Step | 指令文件 | 说明 |
|------|---------|------|
| 1 | `SKILL_DIR/steps/step1-scan.md` | 扫描资料，生成 RountMap.md |
| 2 | `SKILL_DIR/steps/step2-architect-prompt.md` | 生成数据库架构师角色 prompt |
| 3 | `SKILL_DIR/steps/step3-db-select.md` | 用户选择目标数据库 |
| 4 | `SKILL_DIR/steps/step4-table-design.md` | 分析需求，设计表结构，生成 SQL |
| 5 | `SKILL_DIR/steps/step5-incremental.md` | 增量新增表或修改现有表结构 |

## 工作流概览

```
【全量模式】
Step 1: 扫描产品资料 → 展示文件列表 → 用户确认分级 → 生成 RountMap.md
Step 2: 提炼产品特性 → 生成数据库架构师 prompt → 设定角色
Step 3: 用户选择目标数据库（单选）
Step 4: 深度读取资料 → 设计表结构 → 用户确认 → 生成 SQL 文件（>10张表并行）

【增量模式】
Step 5: 理解变更需求 → 分析影响 → 变更清单确认 → 生成 ALTER/建表 SQL → 追加到主文件
```

## 输出文件结构

```
WORK_DIR/
├── RountMap.md          ← Step 1 生成
└── [产品名称].sql        ← Step 4 生成（最终合并文件）
```

## 注意事项

1. **强制用户交互点：**
   - **第零步**：确认 WORK_DIR
   - **Step 1**：展示文件列表，等待用户确认分级
   - **Step 3**：等待用户选择数据库
   - **Step 4**：展示表结构清单，等待用户确认后生成 SQL
2. **SQL 规范：** 详见 `SKILL_DIR/steps/step4-sql-rules.md`，每次生成前必须加载
3. **并行生成：** 表数量 > 10 时并行分块生成，详见 `SKILL_DIR/steps/step4-parallel.md`
4. **路径处理：** 使用绝对路径，确保子任务能正确找到文件
