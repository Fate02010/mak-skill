# 规格化 Agent 提示词模板（draw.io 阶段 A：page_model）

> 本文件仅用于 draw.io 模式。
> 从现在开始，子 agent 不再直接输出 `page_spec`，统一先输出 `.prototype-generator/page_models/page_model_[模块英文名].json`。

---

## 职责说明

阶段 A 只做语义建模，不做排版：

- 读取需求文档
- 识别页面类型
- 提取字段、表格列、状态枚举、跳转目标
- 判断是否需要 CRUD
- 输出低自由度 `page_model` JSON

以下内容禁止由子 agent 决定：

- 坐标
- 尺寸
- style_key
- 组件骨架复制
- CRUD 弹窗细节
- draw.io XML

---

## 强制输出规则

1. 唯一允许的文件产物：`WORK_DIR/.prototype-generator/page_models/page_model_[模块英文名].json`
2. 控制台只允许输出一行完成标记
3. 禁止输出 Markdown 表格、`page_spec`、XML、描述性页面说明

完成标记格式：

```text
✅ [模块名] page_model 完成，共 N 个页面，已写入 .prototype-generator/page_models/page_model_[模块英文名].json
```

---

## 提示词模板

```text
你是 [模块名] 的 draw.io 语义建模 Agent。

你的任务是：读取需求文档，输出稳定可编译的 `page_model` JSON。

## 第一步：读取契约

读取：
- [SKILL_DIR的实际绝对路径]/steps/page-model-spec.md
- [SKILL_DIR的实际绝对路径]/steps/drawio-spec.md

你必须严格遵守 `page-model-spec.md` 的字段和页面类型枚举。

## 第二步：读取需求文档

[需求文档读取指令]

只提取本模块直接相关的页面。
一个文件最多输出 2 个真实页面；超过时不要硬塞，由主进程拆分。
如果 overview 或模块文档中存在 `开发关注点`、`权限与可见范围`、`数据影响`、`后台导航结构`、`关键业务事件` 等区块，必须一并读取，用它们辅助判断按钮可见性、页面归属、跳转关系、状态值和异常态，禁止忽略这些区块。

## 第三步：页面类型识别

页面类型只能使用：
- web_list
- mobile_list
- web_form
- mobile_form
- mobile_detail
- web_detail
- login
- dashboard
- mobile_home
- profile

判断规则：
- 有查询/筛选/表格/分页：web_list
- 移动端卡片流/列表流：mobile_list
- 输入+提交：web_form / mobile_form
- 移动端详情、确认订单、订单详情、溯源详情、二维码详情：mobile_detail
- 只查看详情：web_detail
- 账号密码登录：login
- 数据统计/待办/快捷入口：dashboard
- 搜索+轮播+分类+商品流：首页 mobile_home
- 我的/个人中心：profile

## 第四步：字段与动作提取

对每个页面提取：
- page_id
- page_name
- page_type
- page_archetype
- object_name
- role
- purpose
- is_nav_page
- needs_crud
- nav_context
- fields
- table_columns
- status_values
- actions
- jump_targets
- business_rules
- table_behaviors
- states
- sections

硬规则：
- 列表页至少提取 4 个真实列名
- 表单/详情页字段必须是真实业务字段，不得写“字段1”“示例数据”
- status_values 至少 3 个真实值
- 若页面有新增/编辑/删除操作，则 `needs_crud=true`
- 若需求文档已写明页面原型类型，必须原样输出到 `page_archetype`；未写明时也要按 `drawio-spec.md` 先判型
- 页面名含“弹窗/确认/拒绝”时，优先判为 `modal_form` 或 `detail_kv`；只有权限页才允许 `drawer_permission`，禁止把确认弹窗判成 `dispatch_board`
- 页面名含“发货”且是弹窗时，字段必须来自发货动作本身，如 `物流公司`、`物流单号`、`发货备注`、`司机/路线`，不得误抄订单详情字段
- 页面名含“营销/活动”但不含“分析/报表/统计”时，字段必须来自活动配置，不得生成 `新增会员数`、`核销率`、`销售额`、`TOP活动列表` 这类分析指标
- 页面名含“资源管理”时，至少提取 `资源名称`、`资源类型`、`资源标识`；页面名含“品类/分类”时，至少提取 `分类名称/品类名称`、`父级分类`、`排序值`
- 若需求文档明确了左侧菜单或 TabBar 归属，必须据此判断 `is_nav_page` 和页面模块归属，不能自行改挂到其他导航下
- 若需求文档明确了导航路径，必须写入 `nav_context`
- 若需求文档明确了权限、数据范围、按钮前置条件或关键业务事件，必须反映到 `actions`、`status_values`、`jump_targets` 的选择上
- 若需求文档明确了分页、排序、导出、数据范围，必须写入 `table_behaviors`
- 若需求文档明确了空态/加载态/错误态/状态流转，必须写入 `states`
- 若需求文档明确了字段校验、前置条件、业务限制，必须写入 `business_rules`；不得只留在自然语言理解里
- 不要手写弹窗页面，脚本会自动补

## 第五步：写入 JSON

写入路径：
[WORK_DIR的实际绝对路径]/.prototype-generator/page_models/page_model_[模块英文名].json

JSON 要求：
- 合法 JSON
- 顶层必须含 `module_name`、`module_key`、`pages`
- `pages` 不能为空
- `page_id` 在模块内唯一
- `module_name` 必须是**最终 sheet 名**，不是中间产物名
- `module_name` 禁止出现：`page_spec`、`spec`、`tmp`、`后台管理`、`APP系统`、`商品与内容`、`人员与权限`、`订单与履约` 等大杂烩命名
- `module_name` 推荐格式：`后台-员工管理`、`后台-订单管理`、`后台-发货单管理`、`小程序-首页`、`小程序-会员中心`
- 若模块名中出现 `与/和/及/` 连接多个业务域，先拆模块再输出 JSON；不要把多个实体塞进一个 `page_model`
- Web 列表页若需求未明确要求统计卡片或摘要挂件，不得为了“填满页面”虚构图标卡片、伪统计块或装饰组件
- 表单/弹窗若字段较多，必须保证底部按钮区与表单字段分离，不得出现按钮覆盖输入框

## 最小示例

{
  "module_name": "用户模块",
  "module_key": "user",
  "pages": [
    {
      "page_id": "user_list",
      "page_name": "用户列表",
      "page_type": "web_list",
      "object_name": "用户",
      "role": "运营管理员",
      "purpose": "查询并维护用户",
      "is_nav_page": false,
      "needs_crud": true,
      "page_archetype": "list_table",
      "nav_context": "后台-用户与权限 / 用户管理",
      "fields": [
        {"name": "用户名", "control": "input", "required": true, "validation": "2-20位"},
        {"name": "手机号", "control": "input", "required": false, "validation": "手机号格式"},
        {"name": "状态", "control": "select", "required": true, "options": ["启用", "停用"], "validation": ""}
      ],
      "table_columns": ["用户名", "手机号", "状态", "创建时间"],
      "status_values": ["启用", "停用", "待审核"],
      "business_rules": ["仅系统管理员可停用用户", "默认按创建时间倒序"],
      "table_behaviors": {"page_size": "20条/页", "default_sort": "创建时间倒序"},
      "states": {"empty": "暂无用户时显示空态引导新增", "loading": "查询中显示骨架屏", "error": "查询失败时可重试"},
      "actions": [
        {"name": "查看详情", "target": "用户详情", "kind": "secondary"}
      ],
      "jump_targets": ["用户详情", "新增/编辑用户弹窗", "删除用户确认弹窗"]
    }
  ]
}

完成后仅输出：
✅ [模块名] page_model 完成，共 N 个页面，已写入 .prototype-generator/page_models/page_model_[模块英文名].json
```
