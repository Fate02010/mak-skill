# Step 5：拆分设计任务

**目标：** 基于领域模型，将数据库设计工作拆分为可并行执行的子任务，并展示给用户确认后启动生成。

## 执行步骤

### 阶段 5-1：规划任务分组

读取 `WORK_DIR/领域模型.md`，按**聚合**为单位拆分任务：

- 每个聚合为一个子任务（包含聚合根表 + 从属实体表）
- 单个聚合涉及 >5 张表时，可进一步拆分为子聚合
- 公共/基础表（如字典表、日志表、配置表）单独作为一个任务

**分组原则：**
- 同一聚合内的表放在同一子任务（保证 FK 关系一致）
- 跨聚合的关联表（中间表）归入"关系表"任务
- 预计总表数 ≤ 10 时，单任务顺序生成（不并行）

### 阶段 5-2：向用户展示任务清单，等待确认

```
=== 数据库设计任务拆分 ===

共识别 [N] 张表，拆分为 [M] 个子任务：

任务 1：用户聚合（user、user_address、user_profile）
任务 2：商品聚合（product、product_sku、product_category、product_image）
任务 3：订单聚合（order、order_item、order_payment、order_log）
任务 4：关系与基础表（user_product_favorite、sys_dict、sys_config）

生成方式：[并行生成 / 顺序生成（表数 ≤ 10）]
输出目录：WORK_DIR/

是否确认并开始生成？（回复"确认"或提出调整）
```

**必须等待用户确认后，才能进入 Step 6。**

### 阶段 5-3：记录任务元数据

将任务清单写入 `WORK_DIR/db_task_list.md`，供 Step 6 子任务读取：

```markdown
# 数据库设计任务清单

生成时间：[日期]
目标数据库：[所选数据库]
领域模型版本：v[X]

## 任务列表

| 任务 | 聚合 | 涉及表 | 临时文件 | 状态 |
|------|------|-------|---------|------|
| 1 | 用户聚合 | user, user_address | sql_user.sql | 待生成 |
| 2 | 商品聚合 | product, product_sku... | sql_product.sql | 待生成 |
| 3 | 订单聚合 | order, order_item... | sql_order.sql | 待生成 |
| 4 | 关系与基础表 | ... | sql_base.sql | 待生成 |

## SQL 规范

见 `SKILL_DIR/steps/step4-sql-rules.md`（每个子任务生成前必须 Read）
```
