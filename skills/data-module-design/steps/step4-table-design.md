# Step 4：设计表结构，生成 SQL

**目标：** 综合产品资料和架构师视角，设计完整的数据库表结构并输出标准 SQL 文件。

> **首先执行：** Read `SKILL_DIR/steps/step4-sql-rules.md`，后续所有 SQL 严格遵循其规范。

## 阶段 4-1：分析需求，识别实体与关系

1. 参考 `RountMap.md`，按优先级读取核心资料文件
2. 识别所有业务实体，梳理实体间关系：
   - 一对一（One-to-One）
   - 一对多（One-to-Many）
   - 多对多（Many-to-Many）→ 需要中间表
3. 识别每个实体的关键属性、枚举值、业务规则和约束

## 阶段 4-2：输出表清单，用户确认

向用户展示识别出的表结构清单，**等待用户确认后再生成 SQL**：

```
=== 数据库表结构清单确认 ===

共识别出 N 张表，请确认后开始生成 SQL：

📋 模块一：[模块名]
  • [表名]（[中文说明]）：[核心字段摘要] | 索引：[关键索引]
  • [表名]（[中文说明]）：[核心字段摘要] | 索引：[关键索引]

📋 模块二：[模块名]
  • [表名]（[中文说明]）：[核心字段摘要] | 索引：[关键索引]
  • [中间表名]（[中文说明]）⚡中间表，无 delete_flag

📋 模块三：...

请确认：
- 回复"确认"：按以上清单生成 SQL
- 回复"调整"：说明需要修改的表或字段
```

## 阶段 4-3：生成 SQL

用户确认后，根据表数量选择生成方式：

- **表数量 ≤ 10**：直接生成单一 `[产品名称].sql`
- **表数量 > 10**：Read `SKILL_DIR/steps/step4-parallel.md`，并行分块生成后合并

### 每张表的生成要求

1. 包含所有业务字段（类型、NOT NULL、默认值、COMMENT）
2. 固定字段按规范追加（中间表跳过 delete_flag）
3. 主键按所选数据库规范生成（兼容雪花算法）
4. 根据查询场景同步创建索引
5. 表级 COMMENT 说明业务含义

### 输出示例（MySQL）

```sql
-- ----------------------------
-- 用户表
-- ----------------------------
DROP TABLE IF EXISTS `sys_user`;
CREATE TABLE `sys_user` (
  `id`          BIGINT UNSIGNED   NOT NULL AUTO_INCREMENT                    COMMENT '主键ID',
  `username`    VARCHAR(64)       NOT NULL DEFAULT ''                        COMMENT '用户名',
  `password`    VARCHAR(128)      NOT NULL DEFAULT ''                        COMMENT '密码（加密存储）',
  `email`       VARCHAR(128)      NOT NULL DEFAULT ''                        COMMENT '邮箱',
  `phone`       VARCHAR(20)       NOT NULL DEFAULT ''                        COMMENT '手机号',
  `status`      TINYINT(1)        NOT NULL DEFAULT 1                         COMMENT '状态（0=禁用，1=启用）',
  `create_by`   VARCHAR(64)       NOT NULL DEFAULT ''                        COMMENT '创建人',
  `create_time` DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP         COMMENT '创建时间',
  `update_by`   VARCHAR(64)       NOT NULL DEFAULT ''                        COMMENT '更新人',
  `update_time` DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP
                                           ON UPDATE CURRENT_TIMESTAMP       COMMENT '更新时间',
  `delete_flag` TINYINT(1)        NOT NULL DEFAULT 0                         COMMENT '删除标志（0=未删除，1=已删除）',
  PRIMARY KEY (`id`),
  UNIQUE INDEX `uniq_username` (`username`),
  INDEX `idx_email` (`email`),
  INDEX `idx_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';
```

## 阶段 4-4：自查与输出

SQL 生成完毕后执行自查：
1. 确认每张表的所有字段都有 COMMENT
2. 确认固定字段齐全（中间表核查是否正确跳过 delete_flag）
3. 确认主键类型为 BIGINT，与雪花算法兼容
4. 确认索引命名规范，无重复索引

输出最终文件 `WORK_DIR/[产品名称].sql`，并向用户汇报：

```
✅ SQL 生成完成

输出文件：[WORK_DIR]/[产品名称].sql
共生成：N 张表（其中中间表 M 张）
总行数：约 X 行
索引：共 Y 个索引

请检查并按需调整。
```
