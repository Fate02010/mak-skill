# 组件样式字典

规格化 agent 在 page_spec 中写入 `style_key`，渲染 agent 通过此字典将 `style_key` 转换为 draw.io `style` 属性。

---

## 查找规则

渲染 agent 读取 page_spec 的每行 `style_key`，在下表中查找对应的 `style` 字符串，直接写入 `<mxCell style="...">` 属性。
若 style_key 不在表中，使用 `text_default` 作为兜底。

---

## 样式字典

| style_key | draw.io style 字符串 |
|-----------|---------------------|
| `swimlane` | `swimlane;startSize=30;fillColor=#f0f4ff;strokeColor=#1e88e5;fontStyle=1;fontSize=13;` |
| `swimlane_modal` | `swimlane;startSize=30;fillColor=#fff3e0;strokeColor=#ef6c00;fontStyle=1;fontSize=12;` |
| `nav` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;verticalAlign=middle;` |
| `nav_back` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#1565c0;strokeColor=none;fontColor=#ffffff;fontSize=13;align=left;spacingLeft=12;` |
| `bg` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;` |
| `card` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e0e0e0;shadow=1;` |
| `input` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;fontSize=13;` |
| `select` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;fontSize=13;` |
| `textarea` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;verticalAlign=top;fontSize=13;` |
| `label` | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=13;` |
| `label_required` | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=13;fontColor=#d32f2f;` |
| `text_title` | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=16;fontStyle=1;` |
| `text_subtitle` | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=14;fontStyle=1;` |
| `text_body` | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=13;` |
| `text_hint` | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=11;fontColor=#9e9e9e;` |
| `text_value` | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=13;fontColor=#212121;` |
| `text_default` | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=13;` |
| `btn_primary` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;` |
| `btn_secondary` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1e88e5;fontColor=#1e88e5;fontSize=13;` |
| `btn_danger` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#f44336;fontColor=#f44336;fontSize=13;` |
| `btn_danger_filled` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#f44336;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;` |
| `btn_sm` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1e88e5;fontColor=#1e88e5;fontSize=12;` |
| `btn_sm_danger` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#f44336;fontColor=#f44336;fontSize=12;` |
| `btn_disabled` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#e0e0e0;strokeColor=none;fontColor=#9e9e9e;fontSize=13;` |
| `table_header` | `text;html=1;strokeColor=none;fillColor=#f5f5f5;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;` |
| `table_row_odd` | `text;html=1;strokeColor=none;fillColor=#ffffff;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;` |
| `table_row_even` | `text;html=1;strokeColor=none;fillColor=#fafafa;align=left;verticalAlign=middle;fontSize=12;spacingLeft=8;` |
| `table_divider` | `line;strokeColor=#eeeeee;fillColor=none;` |
| `tag_success` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#e8f5e9;strokeColor=none;fontColor=#2e7d32;fontSize=11;` |
| `tag_warning` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#fff8e1;strokeColor=none;fontColor=#f57f17;fontSize=11;` |
| `tag_error` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#ffebee;strokeColor=none;fontColor=#c62828;fontSize=11;` |
| `tag_info` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#e3f2fd;strokeColor=none;fontColor=#1565c0;fontSize=11;` |
| `tag_default` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;fontColor=#616161;fontSize=11;` |
| `tab_bar` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e0e0e0;fontSize=13;` |
| `tab_active` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;` |
| `tab_inactive` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=none;fontColor=#757575;fontSize=13;` |
| `bottom_bar` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e0e0e0;fontSize=11;` |
| `sidebar` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#263238;strokeColor=none;fontColor=#ffffff;fontSize=13;` |
| `sidebar_item` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#263238;strokeColor=none;fontColor=#b0bec5;fontSize=13;align=left;spacingLeft=16;` |
| `sidebar_active` | `rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;align=left;spacingLeft=16;` |
| `img_placeholder` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#e3f2fd;strokeColor=#90caf9;fontColor=#1565c0;fontSize=12;` |
| `divider` | `line;strokeColor=#e0e0e0;fillColor=none;` |
| `breadcrumb` | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=12;fontColor=#757575;` |
| `pagination` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e0e0e0;fontSize=12;` |
| `modal_bg` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e0e0e0;shadow=1;` |
| `modal_title` | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=15;fontStyle=1;` |
| `annotation` | `text;html=1;strokeColor=none;fillColor=none;fontSize=10;fontColor=#9e9e9e;align=left;verticalAlign=top;` |
| `annotation_card` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#fffde7;strokeColor=#f9a825;fontSize=10;fontColor=#5d4037;align=left;verticalAlign=top;spacingLeft=8;spacingTop=8;` |
| `edge_default` | `edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;` |
| `nav_node` | `rounded=1;whiteSpace=wrap;html=1;fillColor=#e3f2fd;strokeColor=#1e88e5;fontSize=12;` |
| `nav_group` | `swimlane;startSize=30;fillColor=#f5f5f5;strokeColor=#bdbdbd;fontStyle=1;fontSize=13;` |

---

## 标准组件尺寸（规格化 agent 写入坐标时遵守）

| 组件 | 高度 | 典型宽度 |
|------|------|----------|
| 顶部导航栏 nav | 56 | UI 区全宽（375 或 1440） |
| 输入框 input / select | 44 | 表单区 320；筛选区 140–200 |
| 多行文本 textarea | 88 | 320 |
| 主按钮 btn_primary | 44 | 120 |
| 次要按钮 btn_secondary | 44 | 80–120 |
| 小操作按钮 btn_sm / btn_sm_danger | 32 | 60 |
| 表格列标题行 table_header | 44 | 各列按比例分配 |
| 表格数据行 table_row_* | 52 | 各列按比例分配 |
| Tag 状态标签 | 24 | 56–80 |
| 底部标签栏 bottom_bar | 56 | UI 区全宽 |
| 面包屑 / 分页 breadcrumb / pagination | 40 | — |
| Modal 弹窗容器 modal_bg（Web） | 按内容 | 400–600 |
| Modal 弹窗容器 modal_bg（移动端） | 按内容 | 300–360 |

---

## 坐标系规则（规格化 agent 必须遵守）

- 所有坐标 x、y、width、height 必须是 **8 的倍数**
- swimlane 内组件坐标相对于 swimlane 内部（swimlane 本身 x/y 已描述位置）
- swimlane 标题栏高 30px，内部第一个组件 **y ≥ 38**
- 顶部导航栏 y = 38，height = 56
- 正文第一个组件 y = 38 + 56 + 16 = 110（导航 + 间距）
- label 与对应 input 在同一行：label x=24 w=80，input x=112 w=240，y 相同
- 行间距 16px（紧凑 8px）
- 页面左右边距 24px（Web 左右各 24，移动端左右各 16）
- 标注区 x 起点：移动端 395，Web 1460
- 标注元素 width：移动端 ≤ 180，Web ≤ 220
- 标注元素 x + width：移动端 ≤ 595，Web ≤ 1700
