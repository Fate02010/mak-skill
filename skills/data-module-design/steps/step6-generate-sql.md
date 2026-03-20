# Step 6：并行生成 SQL 文件

**目标：** 按 Step 5 拆分的任务，并行生成各聚合的 SQL 建表文件，最后合并为完整 SQL 文件。

## 阶段 6-1：判断生成方式

读取 `WORK_DIR/db_task_list.md`：

- **表数 ≤ 10（单任务）**：顺序生成，直接写入最终 SQL 文件
- **表数 > 10（多任务）**：并行生成，每个任务生成独立临时文件后合并

## 阶段 6-2A：顺序生成（表数 ≤ 10）

1. Read `SKILL_DIR/steps/step4-sql-rules.md` 获取 SQL 规范
2. 读取 `WORK_DIR/领域模型.md` 和相关资料
3. 按聚合顺序生成全部建表 SQL
4. 直接写入 `WORK_DIR/[产品名称].sql`

> **输出约束：** SQL 内容只写入文件，禁止在控制台输出 SQL 正文。每完成一张表只输出一行进度：`✅ t_表名 完成`

## 阶段 6-2B：并行生成（表数 > 10）

### 步骤一：展示并行执行计划，等待用户确认

**启动任何 Agent 之前，必须先向用户展示完整的任务分配计划，等待确认后才能启动：**

```
=== 并行生成执行计划 ===

共 [N] 张表，拆分为 [M] 个并行任务同时执行：

Agent 1 │ 用户聚合
        │ 负责表：t_user、t_user_address、t_user_profile
        │ 输出：sql_user.sql

Agent 2 │ 商品聚合
        │ 负责表：t_product、t_product_sku、t_product_category、t_product_image
        │ 输出：sql_product.sql

Agent 3 │ 订单聚合
        │ 负责表：t_order、t_order_item、t_order_payment、t_order_log
        │ 输出：sql_order.sql

Agent 4 │ 关系与基础表
        │ 负责表：t_user_product_favorite、t_sys_dict、t_sys_config
        │ 输出：sql_base.sql

输出目录：[WORK_DIR]/
是否确认并启动并行生成？（回复"确认"或提出调整）
```

### 步骤二：启动并行 Agent

用户确认后，按以下方式启动，所有 Agent 同时发起（单次响应内完成）。

每个 Agent 使用以下 prompt 模板（填入具体参数）：

```
你是 [产品名称] 的数据库架构师。

任务：生成 [聚合名称] 的建表 SQL（共 [N] 张表）

请按顺序执行：
1. Read `[SKILL_DIR]/steps/step4-sql-rules.md`（必须，获取 SQL 规范）
2. Read `[WORK_DIR]/领域模型.md`（获取实体定义）
3. Read `[WORK_DIR]/RountMap.md`（找到相关资料文件路径后读取）
4. 生成以下表的完整建表 SQL：
   - [t_表名1]：[职责描述]
   - [t_表名2]：[职责描述]
   ...
5. 将 SQL 写入 `[WORK_DIR]/sql_[聚合英文名].sql`

约束：
- 严禁写入 /private/tmp 等系统临时目录
- 所有表名必须以 t_ 开头
- 每个字段必须有 COMMENT，主键使用 BIGINT
- SQL 内容只写入文件，禁止在控制台输出 SQL 正文，只输出进度：✅ [聚合名] 完成，共 N 张表
- 如发现领域模型有误或遗漏，在文件末尾追加：
  -- [领域模型反馈] 发现 XXX，建议 YYY
```

**Claude Code 启动方式（Agent 工具）：**

在单次响应中同时调用多个 `Agent` 工具，每个 Agent 对应一个任务，所有调用并行执行：

```
# 示例：同时调用 Agent 工具 M 次（对应 M 个任务）
Agent(prompt="...Agent 1 的完整 prompt...")
Agent(prompt="...Agent 2 的完整 prompt...")
Agent(prompt="...Agent 3 的完整 prompt...")
...
```

**Codex 启动方式（Task 工具 + run_in_background）：**

```
# 步骤 1：依次创建后台任务（每个 Task 立即返回 task_id）
task_1 = Task(prompt="...Agent 1 的完整 prompt...", run_in_background=true)
task_2 = Task(prompt="...Agent 2 的完整 prompt...", run_in_background=true)
task_3 = Task(prompt="...Agent 3 的完整 prompt...", run_in_background=true)
...

# 步骤 2：等待并收集所有任务结果
result_1 = TaskOutput(task_id=task_1.id, block=true)
result_2 = TaskOutput(task_id=task_2.id, block=true)
result_3 = TaskOutput(task_id=task_3.id, block=true)
...
```

### 步骤三：跟踪进度

每个 Agent 完成时，同步更新 `WORK_DIR/执行状态.md` 的"Step 6 Agent 状态"表格。

展示每个任务状态，待全部完成后进入下一阶段：

```
并行任务进度：
  ⏳ Agent 1 │ 用户聚合（生成中...）
  ✅ Agent 2 │ 商品聚合（已完成，sql_product.sql）
  ✅ Agent 3 │ 订单聚合（已完成，sql_order.sql）
  ⏳ Agent 4 │ 关系与基础表（生成中...）
```

**熔断规则：** 所有 Agent 完成后统计失败数量：
- 失败 Agent 数 ≤ 总数 50%：记录失败项，继续后续流程，最后统一补充生成
- 失败 Agent 数 > 总数 50%：**立即停止**，向用户告警：

```
⚠️ 熔断警告：[N] 个 Agent 中有 [M] 个失败（超过 50%），流程已暂停。
失败聚合：[聚合1]、[聚合2]、...

请选择：
1. 重试失败的 Agent（推荐）
2. 忽略失败，继续合并已完成部分
3. 中止流程
```

**SQL 内容有效性校验：** 所有成功的临时 SQL 文件，逐一读取并检查：
- 包含至少一条 `CREATE TABLE` 语句
- 表名以 `t_` 开头
- 至少一个字段含 `COMMENT`
- 文件未被截断（末尾含完整的 `)` 或 `ENGINE=` 结束行）

发现不合格文件 → 记录后重新生成该 Agent 对应的 SQL。

## 阶段 6-3：合并 SQL 文件

所有子任务完成后：

1. 按聚合依赖顺序读取各临时文件（被依赖的聚合先写入）
2. 合并顺序：基础字典表 → 用户聚合 → 商品聚合 → 订单聚合 → 关系表 → 其他
3. 写入 `WORK_DIR/[产品名称].sql`，文件头：

```sql
-- ============================================================
-- [产品名称] 数据库建表脚本
-- 目标数据库：[所选数据库]  生成时间：[日期]  领域模型版本：v[X]
-- ============================================================
```

4. 合并完成后删除临时文件（`sql_*.sql`）

## 阶段 6-4：并行生成 ER 文档 + 详细设计文档

> **为什么用 subagent：** 这两个文档都需要读取完整 SQL 文件（10K-15K tokens），在主线程执行会大量消耗上下文。改用 subagent 隔离，主线程只追踪进度。

展示计划并**等待用户确认后**启动两个并行 subagent：

```
=== 文档生成计划 ===

Doc-Agent 1 │ 生成 ER关系图.md
            │ 输入：[产品名称].sql + 领域模型.md
            │ 输出：WORK_DIR/ER关系图.md

Doc-Agent 2 │ 生成 数据详细设计文档.md
            │ 输入：[产品名称].sql + 领域模型.md + ER关系图.md
            │ 输出：WORK_DIR/数据详细设计文档.md

是否确认并启动？（回复"确认"）
```

**Doc-Agent 1 prompt（ER 文档）：**
```
任务：生成 ER 关系说明文档

1. Read `[SKILL_DIR]/steps/step6-er-doc.md` 获取格式规范
2. Read `[WORK_DIR]/[产品名称].sql` 提取表结构
3. Read `[WORK_DIR]/领域模型.md` 获取聚合分组
4. 按规范生成，写入 `[WORK_DIR]/ER关系图.md`
5. 完成后输出：✅ ER关系图.md 已生成（禁止在控制台输出文档正文）
```

**Doc-Agent 2 prompt（详细设计文档）：**
```
任务：生成数据详细设计文档

1. Read `[SKILL_DIR]/steps/step6-design-doc.md` 获取格式规范
2. Read `[WORK_DIR]/[产品名称].sql` 提取所有表和字段
3. Read `[WORK_DIR]/领域模型.md` 获取实体职责和业务规则
4. 等待 ER关系图.md 存在后 Read 以引用关系说明
5. 按规范生成，写入 `[WORK_DIR]/数据详细设计文档.md`
6. 完成后输出：✅ 数据详细设计文档.md 已生成（共 N 张表）（禁止在控制台输出文档正文）
```

**Claude Code**：单次响应同时调用两个 `Agent` 工具并行执行
**Codex**：`Task(run_in_background=true)` × 2，再 `TaskOutput(block=true)` 收集

## 阶段 6-6：收集领域模型反馈

扫描各临时文件中的 `[领域模型反馈]` 注释，汇总后告知用户：

```
=== SQL 生成完成 ===

输出文件：
  - [WORK_DIR]/[产品名称].sql      （共 [N] 张表）
  - [WORK_DIR]/ER关系图.md
  - [WORK_DIR]/数据详细设计文档.md

[如有领域模型反馈]
⚠️  发现以下领域模型问题，Step 7 将评估是否更新：
- 订单聚合：发现缺少退款表，建议新增 t_order_refund
```

进入 Step 7 进行审视与改进。
