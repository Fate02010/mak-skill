# SQL 编写规范

## 1. 固定字段（所有表必须包含）

```sql
id          -- 主键，见下方主键规范
create_by   VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '创建人',
create_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
update_by   VARCHAR(64)  NOT NULL DEFAULT '' COMMENT '更新人',
update_time DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
delete_flag TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '删除标志（0=未删除，1=已删除）'
```

> **中间表例外：** 纯关联中间表不需要 `delete_flag`，其余固定字段保留。

## 2. 主键规范

字段名统一为 `id`，类型 `BIGINT`（兼容雪花算法，使用雪花 ID 时由应用层赋值，移除自增约束）：

| 数据库 | 建表语法 |
|--------|---------|
| MySQL / MariaDB | `id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID'` |
| PostgreSQL | `id BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY` |
| SQL Server | `id BIGINT NOT NULL IDENTITY(1,1)` |
| Oracle / Db2 | `id NUMBER(19) NOT NULL GENERATED ALWAYS AS IDENTITY` |

## 3. 字段注释规范

- **每个字段必须有 COMMENT**，不得省略
- 枚举格式：`COMMENT '状态（0=禁用，1=启用）'`
- 外键字段：`COMMENT '关联 t_user 表 id'`

## 4. 索引设计规范

| 场景 | 命名 | 示例 |
|------|------|------|
| 高频等值/JOIN 字段 | `idx_[字段名]` | `INDEX idx_user_id (user_id)` |
| 唯一约束 | `uniq_[字段名]` | `UNIQUE INDEX uniq_email (email)` |
| 多字段组合查询 | `idx_[字段1]_[字段2]` | `INDEX idx_status_time (status, create_time)` |
| 全文搜索 | `ft_[字段名]` | `FULLTEXT INDEX ft_content (content)` |

## 5. 表级规范

- **表名前缀：所有表名必须以 `t_` 开头**（如 `t_user`、`t_order_item`）
- 表名：`t_` + 小写下划线命名，见名知意
- 表必须有表级注释
- MySQL：`CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci ENGINE=InnoDB`

## 6. SQL 文件头部模板

```sql
-- ============================================================
-- 产品名称：[产品名]  数据库：[所选数据库]  生成时间：[日期]
-- ============================================================
-- USE [database_name];
SET NAMES utf8mb4;  -- MySQL/MariaDB
```
