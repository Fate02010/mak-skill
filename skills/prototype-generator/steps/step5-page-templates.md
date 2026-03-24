# 页面骨架模板库（脚本参数化版）

本文件描述 `build_page_spec.py` 使用的固定模板与坐标 token。  
子 agent 不再逐行复制模板，只输出 `page_model`。

---

## 统一坐标 token

### Web

| token | 值 |
|---|---|
| `web_ui_w` | `1440` |
| `web_nav_y` | `40` |
| `web_nav_h` | `56` |
| `web_content_y` | `104` |
| `web_annotation_x` | `1464` |
| `web_annotation_w` | `216` |
| `web_swimlane_w` | `1680` |
| `web_swimlane_h` | `960` |

### Mobile

| token | 值 |
|---|---|
| `mobile_ui_w` | `376` |
| `mobile_nav_y` | `40` |
| `mobile_nav_h` | `56` |
| `mobile_content_y` | `104` |
| `mobile_annotation_x` | `400` |
| `mobile_annotation_w` | `176` |
| `mobile_swimlane_w` | `592` |
| `mobile_swimlane_h` | `856` |

---

## 页面类型与固定骨架

| page_type | 固定骨架 |
|---|---|
| `web_list` | nav + bg + breadcrumb + 搜索/筛选 + 新增按钮 + 表头 + 5 行数据 + 分页 + annotation |
| `mobile_list` | nav + bg + 搜索/筛选 + 5 张卡片 + annotation + 可选 bottom_bar |
| `web_form` | nav + bg + breadcrumb + card + label/input 列表 + 提交/取消 + annotation |
| `mobile_form` | nav + nav_back + bg + 字段列表 + 提交按钮 + annotation |
| `web_detail` | nav + bg + breadcrumb + card + 键值对 + 状态标签 + 操作按钮 + annotation |
| `login` | bg + 居中 card + 账号/密码 + 登录按钮 + annotation |
| `dashboard` | nav + bg + 4 个指标卡 + 待办卡 + 快捷入口卡 + annotation |
| `mobile_home` | nav + search_input + banner + 分类 icon + 商品卡片 + bottom_bar + annotation |
| `profile` | header_bg + avatar + 用户信息 + list_row 菜单 + bottom_bar + annotation |

---

## 自动补全规则

脚本统一负责以下补全：

1. `needs_crud=true`
   - 自动补 `新增/编辑弹窗`
   - 自动补 `删除确认弹窗`
   - 自动补列表页新增按钮
   - 自动补每行编辑/删除按钮

2. 列表页
   - 自动生成 5 行数据
   - 自动按 `status_values` 轮换状态

3. annotation
   - 每页自动生成 1 个 `annotation_card`

4. 主导航页
   - `is_nav_page=true` 时自动补 `bottom_bar`

---

## 禁止事项

- 禁止继续使用旧模板里的 `38/94/110/158`
- 禁止 agent 手工排坐标
- 禁止 agent 手工复制大段 page_spec 骨架
- 禁止 agent 为 CRUD 列表手工写 modal swimlane
