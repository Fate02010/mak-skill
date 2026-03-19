# SQL 编写规范

## 1. 固定字段（所有表必须包含）

```sql
id          -- 主键，见下方主键规范
create_by   VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '创建人',
create_time DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
update_by   VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '更新人',
update_time DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
delete_flag TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '删除标志（0=未删除，1=已删除）'
```

> **中间表例外：** 纯关联中间表（仅含两个外键的多对多关系表）不需要 `delete_flag`，其余固定字段保留。

## 2. 主键规范

主键字段名统一为 `id`，**同时兼容自增和雪花算法**：

**MySQL / MariaDB：**
```sql
id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
PRIMARY KEY (id)
```

**PostgreSQL：**
```sql
id BIGINT NOT NULL GENERATED ALWAYS AS IDENTITY COMMENT '主键ID',
PRIMARY KEY (id)
```

**SQL Server：**
```sql
id BIGINT NOT NULL IDENTITY(1,1),  -- 主键ID
PRIMARY KEY (id)
```

**Oracle / Db2：**
```sql
id NUMBER(19) NOT NULL GENERATED ALWAYS AS IDENTITY,  -- 主键ID
PRIMARY KEY (id)
```

> **雪花算法兼容：** 字段类型统一使用 `BIGINT`（MySQL）或对应数据库的64位整型，确保能容纳雪花算法生成的18位数字 ID。使用雪花 ID 时，移除 `AUTO_INCREMENT` / `IDENTITY` 约束，由应用层赋值。

## 3. 字段注释规范

- **每个字段必须添加 COMMENT**，不得省略
- 注释内容：字段含义 + 枚举说明（如有）
- 枚举格式：`COMMENT '状态（0=禁用，1=启用）'`
- 外键字段注释注明关联表：`COMMENT '关联 user 表 id'`

## 4. 索引设计规范

根据需求资料中的查询场景，在建表时同步设计索引：

| 场景 | 索引类型 | 示例 |
|------|---------|------|
| 高频等值查询字段 | 普通索引 | `INDEX idx_user_id (user_id)` |
| 唯一约束字段 | 唯一索引 | `UNIQUE INDEX uniq_email (email)` |
| 多字段组合查询 | 联合索引 | `INDEX idx_status_time (status, create_time)` |
| 全文搜索字段 | 全文索引 | `FULLTEXT INDEX ft_content (content)` |

索引命名规范：
- 普通索引：`idx_[字段名]` 或 `idx_[字段1]_[字段2]`
- 唯一索引：`uniq_[字段名]`
- 全文索引：`ft_[字段名]`

## 5. 表级规范

- **表名前缀：所有表名必须以 `t_` 开头**，例如 `t_user`、`t_order`、`t_order_item`
- 表名：`t_` + 小写下划线命名，见名知意
- 表必须有表级注释说明业务含义
- 字符集（MySQL）：`CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`
- 存储引擎（MySQL）：`ENGINE=InnoDB`

## 6. SQL 文件头部模板

```sql
-- ============================================================
-- 产品名称：[产品名]
-- 数据库：[所选数据库]
-- 生成时间：[日期]
-- 说明：[简要说明]
-- ============================================================

-- 使用数据库（按需修改）
-- USE [database_name];

SET NAMES utf8mb4;  -- MySQL/MariaDB
```
