# page_model 契约（draw.io 共用）

draw.io 模式下，子 agent 统一先输出 `page_model_[模块英文名].json`，再由 `build_page_spec.py` 生成 `page_specs/page_spec_[模块英文名].md`。

---

## 顶层结构

```json
{
  "terminal_type": "portal",
  "terminal_name": "官网门户",
  "module_name": "官网门户-产品官网",
  "module_key": "user",
  "product_name": "示例产品",
  "pages": []
}
```

要求：
- 必须是合法 JSON
- `terminal_type` 必填，固定枚举：`admin` / `miniapp` / `app` / `h5` / `bigscreen` / `portal` / `industrial`
- `terminal_name` 必填，必须与 `terminal_type` 对应：`后台` / `小程序` / `App` / `H5` / `大屏` / `官网门户` / `工控机`
- `module_name` 必填
- `module_name` 必须使用 `[terminal_name]-[业务模块]` 格式，如 `后台-订单管理`、`小程序-首页`、`App-会员中心`、`H5-活动报名`、`大屏-指挥中心`、`官网门户-产品官网`、`工控机-产线监控`
- `module_key` 建议英文
- `pages` 必须为非空数组

---

## pages 数组字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `page_id` | 是 | 模块内唯一英文 id |
| `page_name` | 是 | 页面中文名 |
| `canonical_page_name` | 否 | 推荐输出的标准页面名，用于别名归并 |
| `page_type` | 是 | 固定枚举 |
| `page_archetype` | 否 | draw.io 页面原型类型，建议显式输出 |
| `page_kind` | 否 | 推荐输出：`list/detail/form_modal/confirm_modal/tree_list/login/dashboard/landing/content/hub/console` |
| `layout_mode` | 否 | 推荐输出：`web/mobile/modal/tree/drawer/login/h5/portal/bigscreen/industrial` |
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
- `portal_home`
- `portal_content`
- `portal_hub`
- `bigscreen_dashboard`
- `industrial_console`

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
- `portal_landing`
- `portal_content`
- `portal_hub`
- `bigscreen_board`
- `industrial_hmi`

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
6. 登录页必须输出真实登录字段；后台登录仍使用 `page_type=login`，但页面语义必须是 Web 后台登录，不得按移动端登录页理解
7. 名称含“发货”且为弹窗/确认页时，字段必须优先来自需求中的发货动作本身，如 `物流公司`、`物流单号`、`发货备注`、`司机/路线`；禁止偷用订单详情字段
8. 营销活动页只能提取活动配置字段；除非页面明确是分析/报表，否则禁止写入 `新增会员数`、`核销率`、`销售额`、`TOP活动列表` 等分析指标
9. 资源管理页必须覆盖 `资源名称`、`资源类型`、`资源标识`；分类/品类页必须覆盖 `分类名称/品类名称`、`父级分类`、`排序值`
10. 页面名含“弹窗/确认/拒绝”时，`page_archetype` 只能是 `modal_form`、`detail_kv` 或 `drawer_permission`；不得把确认弹窗标成 `dispatch_board`
11. 订单列表页必须覆盖 `订单编号`、`用户信息`、`商品摘要`、`实付金额`、`订单状态`、`售后状态`、`下单时间`，并显式体现 `详情/发货/关闭/备注`
12. 订单详情页必须覆盖 `支付信息`、`售后信息`、`操作区`，且动作必须体现 `发货/关闭/备注/确认收货/查看售后` 中的适用项
13. 关闭订单确认弹窗必须包含 `关闭原因` 和风险提示；若只有确认文案没有关闭原因，视为不合格
14. 资源管理页优先使用树形资源结构；若出现 `时间范围`、`更新时间`、`创建人`、分页等通用列表字段，视为语义漂移
15. `terminal_type=admin` 时，`terminal_name` 必须为 `后台`；`miniapp` 时必须为 `小程序`；`app` 时必须为 `App`；`h5` 时必须为 `H5`；`bigscreen` 时必须为 `大屏`；`portal` 时必须为 `官网门户`；`industrial` 时必须为 `工控机`
16. `module_name` 必须和终端前缀一致，禁止 `terminal_type=portal` 却输出 `后台-产品官网`
17. `H5` 继续复用移动端 page_type，但导航语义必须是 `H5页面栈`，不得写成 `小程序主导航`
18. `portal_home / portal_content / portal_hub` 只能用于官网门户终端；`bigscreen_dashboard` 只能用于大屏；`industrial_console` 只能用于工控机
