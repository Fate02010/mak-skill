# 大规模表结构并行生成流程

> 触发条件：表数量 > 10 时加载本文件。

## 步骤一：分组规划

将所有表按业务模块分组，每组 3-6 张表，生成对应的分块任务：
- 分块文件命名：`sql_[模块名].sql`（如 `sql_user.sql`、`sql_order.sql`）

## 步骤二：并行生成各分块

- **Claude Code**：使用 `Agent` 工具在单次响应中同时启动所有写作 Agent
- **Codex**：使用 `Task` 工具并设置 `run_in_background=true`，用 `TaskOutput` 收集结果

每个 Agent / Task 提示词模板：

```
你是数据库架构师，负责生成以下业务模块的建表 SQL。

【目标数据库】[所选数据库]
【输出文件】[WORK_DIR]/sql_[模块名].sql
所有文件必须保存在 WORK_DIR 下，严禁写入 /private/tmp 或其他系统临时目录。

【负责的表】
- [表名1]：[业务说明]
- [表名2]：[业务说明]
- [表名3]：[业务说明]

【需求参考】
Read [WORK_DIR/RountMap.md] 中 [相关场景] 指定的文件获取需求细节。

【SQL 规范】
Read [SKILL_DIR]/steps/step4-sql-rules.md 严格遵循所有规范（固定字段、主键、注释、索引）。

完成后输出：✅ sql_[模块名].sql 完成，包含 N 张表。
```

## 步骤三：合并为最终文件

所有分块完成后合并：

```
1. 写入 SQL 文件头部（Read step4-sql-rules.md 获取模板）
2. 按模块顺序依次拼接各 sql_*.sql 内容
3. 删除所有分块临时文件（sql_*.sql）
4. 输出最终文件：[产品名称].sql
5. 报告：✅ 合并完成，共 N 张表，约 X 行
```
