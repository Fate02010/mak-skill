# 接口设计规范

## 1. URL 规范

- **必须含版本号**：`/api/v1/mobile/*` 或 `/api/v1/admin/*`
- 路径全小写，使用小写下划线或连字符
- 资源集合用复数：`/products`、`/orders`
- 详情资源用 path 参数：`/products/{id}`
- 禁止在路径中堆叠动词，禁止 `/getProduct`、`/deleteOrder`

**端侧前缀：**
| 端侧 | 前缀 | 示例 |
|------|------|------|
| 移动端 | `/api/v1/mobile/` | `/api/v1/mobile/products` |
| 管理后台 | `/api/v1/admin/` | `/api/v1/admin/products` |

## 2. HTTP Method

| Method | 用途 | 幂等 |
|--------|------|------|
| GET | 查询 | ✅ 是 |
| POST | 新增、提交、复杂查询 | ❌ 否（新增）/ ✅ 是（复杂查询） |
| PUT | 整体更新 | ✅ 是 |
| PATCH | 局部更新、状态变更 | ✅ 是（状态变更需业务保障） |
| DELETE | 删除 | ✅ 是 |

## 3. 请求参数规则

| 位置 | 适用场景 | 示例 |
|------|---------|------|
| Path | 资源主键标识 | `/orders/{id}` |
| Query | 列表筛选、排序、分页 | `?pageNum=1&pageSize=20&status=ACTIVE` |
| Header | 认证、语言 | `Authorization: Bearer {token}` |
| Body | 新增/修改/复杂查询 | JSON 对象 |

**分页参数（统一）：**
```
pageNum    整数，从 1 开始，默认 1
pageSize   整数，默认 20，最大 100
sortBy     字符串，排序字段（可选）
sortOrder  ASC / DESC（可选）
```

## 4. 统一响应结构

```json
{
  "code": "200",
  "message": "success",
  "traceId": "6d85e3b88b7642b9",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | String | "200"=成功；业务错误时返回错误码如 "ORDER_0001" |
| message | String | 可读提示，支持国际化 |
| traceId | String | 链路追踪 ID，必须返回 |
| data | Any | 业务数据，无数据时为 null 或 {} |

**HTTP 状态码：** 所有接口协议层统一返回 `200 OK`，业务结果通过响应体 `code` 判断。

**分页响应结构（data 内）：**
```json
{
  "total": 100,
  "pageNum": 1,
  "pageSize": 20,
  "list": []
}
```

## 5. 错误码规范

格式：`[模块前缀]_[4位数字]`，例如：
- `ORDER_0001`：订单不存在
- `PRODUCT_0002`：商品库存不足
- `AUTH_0001`：未登录或 Token 失效

每个接口必须列出常见错误码（至少 2-3 个）。

## 6. 幂等性标注规则

| 场景 | 幂等 | 说明 |
|------|------|------|
| GET 查询 | ✅ 是 | 天然幂等 |
| DELETE 删除 | ✅ 是 | 重复删除同一资源结果一致 |
| PUT 整体更新 | ✅ 是 | 重复提交同一数据结果一致 |
| PATCH 状态变更 | ✅ 是（需业务保障） | 如重复取消订单需做防重处理 |
| POST 新增 | ❌ 否 | 重复调用会创建多条记录 |
| POST 复杂查询 | ✅ 是 | 只读操作 |

## 7. 接口设计原则

- 边界清晰：移动端接口与后台管理接口分离
- 职责单一：一个接口只承载一个明确职责
- 风格统一：路径、请求、响应、错误码、分页风格统一
- 对象分层：接口层 Request/Response 对象与业务层 Command/Query 分离
