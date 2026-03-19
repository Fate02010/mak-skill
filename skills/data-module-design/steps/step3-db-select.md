# Step 3：选择目标数据库

**目标：** 确认本次 SQL 输出的目标数据库类型，后续所有 DDL 语法严格遵循所选数据库规范。

## 执行步骤

向用户展示选择菜单，**单选，必须等待用户回复后继续**：

```
=== 请选择目标数据库 ===

支持以下关系型数据库（单选）：

1. MySQL / MariaDB
2. PostgreSQL
3. Microsoft SQL Server
4. Oracle Database
5. IBM Db2

请回复数字（1-5）选择数据库：
```

## 各数据库关键语法差异备忘

选定后记录所选数据库，后续生成 SQL 时参照以下规范：

| 特性 | MySQL/MariaDB | PostgreSQL | SQL Server | Oracle | Db2 |
|------|--------------|------------|------------|--------|-----|
| 自增主键 | `AUTO_INCREMENT` | `SERIAL` / `GENERATED ALWAYS AS IDENTITY` | `IDENTITY(1,1)` | `GENERATED ALWAYS AS IDENTITY` | `GENERATED ALWAYS AS IDENTITY` |
| 字段注释 | `COMMENT '...'` | `COMMENT ON COLUMN` | 无原生，用扩展属性 | `COMMENT ON COLUMN` | `COMMENT ON COLUMN` |
| 字符串类型 | `VARCHAR` | `VARCHAR` | `NVARCHAR` | `VARCHAR2` | `VARCHAR` |
| 当前时间默认值 | `CURRENT_TIMESTAMP` | `CURRENT_TIMESTAMP` | `GETDATE()` | `SYSDATE` | `CURRENT_TIMESTAMP` |
| 布尔/标志位 | `TINYINT(1)` | `BOOLEAN` | `BIT` | `NUMBER(1)` | `SMALLINT` |
| 表注释 | `COMMENT='...'` | `COMMENT ON TABLE` | 无原生 | `COMMENT ON TABLE` | `COMMENT ON TABLE` |
