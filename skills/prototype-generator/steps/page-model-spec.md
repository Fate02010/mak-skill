# page_model 契约（draw.io 共用）

draw.io 模式下，子 agent 统一先输出 `page_model_[模块英文名].json`，再由 `build_page_spec.py` 生成 `page_specs/page_spec_[模块英文名].md`。

---

## 顶层结构

```json
{
  "module_name": "用户模块",
  "module_key": "user",
  "product_name": "示例产品",
  "pages": []
}
```

要求：
- 必须是合法 JSON
- `module_name` 必填
- `module_key` 建议英文
- `pages` 必须为非空数组

---

## pages 数组字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `page_id` | 是 | 模块内唯一英文 id |
| `page_name` | 是 | 页面中文名 |
| `page_type` | 是 | 固定枚举 |
| `page_archetype` | 否 | draw.io 页面原型类型，建议显式输出 |
| `object_name` | 否 | 业务对象名 |
| `role` | 否 | 页面主要角色 |
| `purpose` | 否 | 页面用途 |
| `is_nav_page` | 否 | 是否主导航页 |
| `needs_crud` | 否 | 是否自动补 CRUD |
| `nav_context` | 否 | 导航归属，如“后台-权限审计 / 角色管理” |
| `fields` | 否 | 表单/详情字段 |
| `table_columns` | 否 | 列表页列定义 |
| `status_values` | 否 | 状态枚举 |
| `actions` | 否 | 主操作 |
| `jump_targets` | 否 | 跳转目标 |
| `business_rules` | 否 | 原型标注区必须展示的业务规则 |
| `table_behaviors` | 否 | 默认排序、分页、导出、数据范围等列表行为 |
| `states` | 否 | 空态/加载态/错误态/状态流转 |
| `sections` | 否 | dashboard / 首页业务分区 |

---

## page_type 固定枚举

- `web_list`
- `mobile_list`
- `web_form`
- `mobile_form`
- `mobile_detail`
- `web_detail`
- `login`
- `dashboard`
- `mobile_home`
- `profile`

禁止输出其他值。

## page_archetype 推荐枚举

- `dashboard`
- `list_table`
- `detail_kv`
- `form_page`
- `modal_form`
- `drawer_permission`
- `dispatch_board`
- `tree_manage`
- `content_manage`
- `audit_log`
- `mobile_home`
- `profile`
- `login`

建议显式输出，避免脚本按页面名兜底猜测。

---

## fields 示例

```json
{
  "name": "状态",
  "control": "select",
  "required": true,
  "options": ["启用", "停用"],
  "validation": ""
}
```

`control` 仅允许：
- `input`
- `select`
- `textarea`

---

## actions 示例

```json
{
  "name": "查看详情",
  "target": "用户详情",
  "kind": "secondary"
}
```

`kind` 允许：
- `primary`
- `secondary`
- `danger`

## 业务增强字段示例

```json
{
  "page_archetype": "drawer_permission",
  "nav_context": "后台-权限审计 / 角色管理",
  "business_rules": [
    "仅系统管理员可修改菜单权限",
    "禁用角色不可分配新增管理员"
  ],
  "table_behaviors": {
    "default_sort": "按更新时间倒序",
    "page_size": "默认20条/页",
    "data_scope": "仅显示所属组织数据"
  },
  "states": {
    "empty": "暂无角色时显示空态引导创建角色",
    "loading": "保存授权时按钮进入提交中",
    "error": "权限保存失败时保留勾选状态并提示重试",
    "transition": "待生效 → 已生效 → 已禁用"
  }
}
```

---

## 硬约束

1. 一个 `page_model` 文件最多 2 个真实页面
2. `needs_crud=true` 时，不要手写弹窗页面
3. 不要手写坐标、尺寸、style_key
4. 不要输出 Markdown 表格、XML、自然语言草图
5. 若需求文档已明确导航归属、业务规则、分页排序或三态，必须分别填入 `nav_context`、`business_rules`、`table_behaviors`、`states`
