# 接口文档格式规范

每个接口按以下固定格式输出，所有字段必须填写完整。

---

## 单个接口文档模板

```markdown
### [序号]. [接口说明]

| 项目 | 内容 |
|------|------|
| **接口地址** | `[METHOD] [URL]` |
| **接口说明** | [一句话描述接口职责] |
| **端侧** | mobile / admin |
| **是否幂等** | ✅ 是 / ❌ 否 |

---

#### 请求参数

**Header**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | String | 是 | Bearer {token} |

**Path 参数**（如有）

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | Long | 是 | 资源 ID |

**Query 参数**（如有）

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| pageNum | Integer | 否 | 1 | 页码，从 1 开始 |
| pageSize | Integer | 否 | 20 | 每页数量，最大 100 |
| status | String | 否 | — | 状态筛选（ACTIVE / INACTIVE） |

**Body 参数**（如有，POST/PUT/PATCH）

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| name | String | 是 | 商品名称，最大 128 字符 |
| price | Decimal | 是 | 售价，单位：元，精度 2 位小数 |
| category_id | Long | 是 | 分类 ID |
| description | String | 否 | 商品描述 |

**请求示例**

```json
{
  "name": "精品草鱼",
  "price": 29.90,
  "category_id": 101,
  "description": "新鲜活鱼，当日现捕"
}
```

---

#### 响应参数

| 参数名 | 类型 | 说明 |
|--------|------|------|
| code | String | "200"=成功，其他为业务错误码 |
| message | String | 提示信息 |
| traceId | String | 链路追踪 ID |
| data.id | Long | 创建的资源 ID |
| data.name | String | 商品名称 |
| data.status | String | 状态（ACTIVE=上架，INACTIVE=下架） |
| data.created_at | String | 创建时间（ISO 8601：2024-01-01T12:00:00+08:00） |

**（列表接口的 data 结构）**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| data.total | Integer | 总记录数 |
| data.pageNum | Integer | 当前页码 |
| data.pageSize | Integer | 每页数量 |
| data.list | Array | 数据列表 |
| data.list[].id | Long | 资源 ID |
| data.list[].name | String | 名称 |

**响应示例（成功）**

```json
{
  "code": "200",
  "message": "success",
  "traceId": "6d85e3b88b7642b9",
  "data": {
    "id": 2001,
    "name": "精品草鱼",
    "status": "ACTIVE",
    "created_at": "2024-01-01T12:00:00+08:00"
  }
}
```

**响应示例（失败）**

```json
{
  "code": "PRODUCT_0003",
  "message": "商品分类不存在",
  "traceId": "b4e1d7fca4b34567",
  "data": null
}
```

---

#### 错误码

| 错误码 | HTTP状态 | 说明 |
|--------|---------|------|
| AUTH_0001 | 200 | 未登录或 Token 失效 |
| PRODUCT_0001 | 200 | 商品不存在 |
| PRODUCT_0003 | 200 | 商品分类不存在 |

---
```

## 格式注意事项

1. **出入参双格式**：参数表格 + JSON 示例**都必须输出**，缺一不可
2. **参数说明要完整**：字符串需注明最大长度；数值需注明范围/精度；枚举需列出所有可选值
3. **数组嵌套展开**：`data.list[].field` 逐级展开，不用 Object 类型一笔带过
4. **时间格式统一**：ISO 8601 格式 `2024-01-01T12:00:00+08:00`
5. **金额字段**：类型写 `Decimal`，注明精度和单位
6. **错误码**：HTTP 状态码统一写 `200`（业务层判断），列出该接口常见业务错误码
7. **模块标题**：每个模块用二级标题 `## [模块名]（[端侧]端）`，接口用三级标题
