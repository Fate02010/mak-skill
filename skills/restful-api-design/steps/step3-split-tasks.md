# Step 3：识别接口清单，拆分任务

**目标：** 从资料中识别全部接口，展示给用户确认，再按模块拆分为可并行执行的生成任务。

## 阶段 3-1：识别全部接口

读取 `WORK_DIR/RountMap.md`，参考标注的核心文件，识别所有接口需求：

- 每个列表页 → GET 列表接口 + 可能的筛选参数
- 每个详情页 → GET 详情接口
- 每个表单提交 → POST/PUT/PATCH 接口
- 每个删除操作 → DELETE 接口
- 状态变更操作 → PATCH 接口
- 复杂查询 → POST 接口（GET 参数过多时）

## 阶段 3-2：展示接口清单，等待用户确认

**必须展示所有接口，等待用户确认后才能继续：**

```
=== 接口清单确认（共 N 个接口）===

请确认以下接口是否满足业务需求，可提出调整（新增/删除/修改）：

| # | Method | URL | 说明 | 端侧 | 幂等 |
|---|--------|-----|------|------|------|
| 1 | GET | /api/v1/mobile/products | 商品列表 | mobile | ✅ |
| 2 | GET | /api/v1/mobile/products/{id} | 商品详情 | mobile | ✅ |
| 3 | POST | /api/v1/mobile/orders | 创建订单 | mobile | ❌ |
| 4 | GET | /api/v1/mobile/orders | 我的订单列表 | mobile | ✅ |
| 5 | GET | /api/v1/mobile/orders/{id} | 订单详情 | mobile | ✅ |
| 6 | PATCH | /api/v1/mobile/orders/{id}/cancel | 取消订单 | mobile | ✅ |
| 7 | GET | /api/v1/admin/products | 商品管理列表 | admin | ✅ |
| 8 | POST | /api/v1/admin/products | 新增商品 | admin | ❌ |
...

回复"确认"开始生成，或提出调整（如"删除第3条"/"新增XX接口"/"把第5条改为..."）
```

## 阶段 3-3：处理用户调整

用户提出调整时更新清单，调整完毕后重新展示，再次等待确认。

## 阶段 3-4：按模块拆分并行任务

用户确认后，按业务模块分组（每个模块为一个并行任务）：

- 每个模块为一个子任务（≤5 个接口可合并）
- 接口数 ≤ 8 时单任务顺序生成（不并行）
- 最多同时 6 个并行任务

## 阶段 3-5：写入任务清单

将确认后的接口清单和分组写入 `WORK_DIR/api_task_list.md`：

```markdown
# 接口文档生成任务清单
生成时间：[日期]  产品：[产品名称]

## 接口清单（共 N 个）
| # | Method | URL | 说明 | 端侧 | 幂等 |
...

## 任务分组
| 任务 | 模块 | 接口数 | 涉及 URL | 临时文件 |
|------|------|--------|---------|---------|
| 1 | 商品模块 | 4 | /products/* | api_product.md |
| 2 | 订单模块 | 5 | /orders/* | api_order.md |
| 3 | 用户模块 | 3 | /users/* | api_user.md |

接口规范：见 SKILL_DIR/steps/api-spec.md（子任务必须 Read）
文档格式：见 SKILL_DIR/steps/api-doc-format.md（子任务必须 Read）
```
