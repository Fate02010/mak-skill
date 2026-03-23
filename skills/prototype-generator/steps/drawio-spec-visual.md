# draw.io 原型规范（视觉层参考）

本文件供 Render Agent 和需要坐标精修的场景使用。
包含 ASCII 布局参照图、坐标计算公式和尺寸标准。
Spec Agent 通常不需要加载本文件（已有核心规范）。

---

## 视觉层参照（生成前对照，减少布局错误）

> **约束 + 示范 + 视觉**三层体系的视觉层。生成每类页面前，先对照下方 ASCII 布局图，确认骨架结构正确后再填充业务字段。

### 移动端列表页（宽375）

```
swimlane [页面名] width=595
┌─────────────────────┬────────────────┐  y=0
│ ████ 页面标题 ████  │  (标注区)       │
├─────────────────────┤  角色/操作/跳转 │  y=38 nav h=56
│░░░░░░░░░░░░░░░░░░░░░│                │
│  搜索框   [筛选]  │                │  y=110 input h=44
│ ┌─────────────────┐ │                │
│ │主字段值   [状态]│ │                │  y=170 card h=96
│ │次要信息   ¥金额 │ │                │
│ └─────────────────┘ │                │
│ ┌─────────────────┐ │                │  y=274 card
│ └─────────────────┘ │                │
│ ┌─────────────────┐ │                │  y=378 card
│ └─────────────────┘ │                │
│                     │                │
│                     │                │  y=748（bg 结束）
├─────────────────────┤                │
│ 首页 商品 我的│                │  y=804 bottom_bar h=56
└─────────────────────┴────────────────┘  y=860
  ←— UI区(0~375) —→←标注区(395~595)→
```

### 移动端个人中心页（我的，宽375）

```
swimlane [我的] width=595
┌─────────────────────┬────────────────┐  y=0
│ ████ 我的 ████      │  (标注区)       │
├─────────────────────┤                │  y=38 nav h=56
│ ┌────────────────┐  │                │
│ │[头像]  用户名  │  │                │  y=110 card h=96
│ │       手机号   │  │                │
│ └────────────────┘  │                │
│ ─────────────────── │                │
│ 菜单项1         >   │                │  y=222 list_row h=56
│ ─────────────────── │                │
│ 菜单项2         >   │                │  y=278
│ ─────────────────── │                │
│ 菜单项3         >   │                │  y=334
│ ─────────────────── │                │
│                     │                │  y=748（bg 结束）
├─────────────────────┤                │
│ 首页 商品 我的│                │  y=804 bottom_bar h=56
└─────────────────────┴────────────────┘  y=860
```

### Web 后台列表页（宽1440）

```
swimlane [页面名] width=1700
┌────────────────────────────────────────┬──────────────┐  y=0
│ ██████████ 系统名 ██████████            │  (标注区)    │
├────────────────────────────────────────┤              │  y=38 nav h=56
│ 首页 / 模块名 / 页面名（面包屑）          │              │  y=110 h=32
│ [关键词搜索] [状态▼] [类型▼] [查询][重置] [新增] │     │  y=158 h=44
│ ┌──────┬────────┬──────┬────┬──────┬──┐│              │
│ │列名1 │ 列名2  │列名3 │状态│创建时│操│              │  y=218 thead h=44
│ ├──────┼────────┼──────┼────┼──────┼──┤│              │
│ │数据1 │ 数据2  │数据3 │[标]│日期  │编删│             │  y=262 row h=52
│ │数据1 │ 数据2  │数据3 │[标]│日期  │编删│             │  y=314
│ │数据1 │ 数据2  │数据3 │[标]│日期  │编删│             │  y=366
│ └──────┴────────┴──────┴────┴──────┴──┘│              │
│ 共N条  第1/5页  [上一页][下一页]          │              │  y=434 pagination
└────────────────────────────────────────┴──────────────┘
  ←─────────── UI区(0~1440) ─────────────→←标注区→
```

> **对照要点：**
> - 移动端主导航页：bg 高度 = 654（y=94→748），bottom_bar 固定 y=804
> - Web 列表页：筛选区 y=158，表头 y=218，首行数据 y=262
> - 标注区必须在 UI 区右侧（移动端 x≥395，Web x≥1460）

---

## 坐标计算规则

### UI 区画布尺寸（页面实际设备宽度）

- 移动端：UI 区宽 `375`，高 `812`（iPhone 标准）
- 后台/Web：UI 区宽 `1440`，高 `900`

### swimlane 总宽度（含右侧标注区）

- 移动端 swimlane：宽 `595`（375 UI区 + 20 间隔 + 200 标注区），高 `860`
- Web swimlane：宽 `1700`（1440 UI区 + 20 间隔 + 240 标注区），高 `960`

> **标注区 x 起点 = UI 区宽 + 20**（移动端 x=395，Web x=1460）

### 混合系统画布尺寸规则（App + 后台同系统）

同一 diagram 内可以同时包含移动端页面和 Web 页面，每个 swimlane 根据其所属页面类型**独立选择宽度**：
- App/移动端页面 swimlane：宽 `595`，高 `860`
- 后台/Web 页面 swimlane：宽 `1700`，高 `960`
- 同一 diagram 中允许不同宽度的 swimlane 并排，只需确保 x 坐标正确累加（后一个 swimlane 的 x = 前一个 x + 前一个宽 + 40）

### pageWidth 动态计算（必须按 swimlane 数量计算，禁止使用固定值）

```
pageWidth = Σ(每个swimlane宽) + (N-1)×40间距 + 左右边距80
```
示例：3个移动端页面 → pageWidth = 3×595 + 2×40 + 80 = 1945
示例：4个Web页面 → pageWidth = 4×1700 + 3×40 + 80 = 7000
> 若不计算，多 swimlane 并排时内容会溢出画布边界，draw.io 无法完整显示。

### swimlane 内组件 y 坐标起点规则

- swimlane 标题栏高度固定 `startSize=30`（标题占用 y:0~30）
- swimlane 内第一个组件 **y 坐标必须 ≥ 38**（30标题 + 8间距）
- 推荐：顶部导航栏 y=30，正文第一个组件 y=86（30+56导航高）
- **禁止**：组件 y=0，会被标题栏完全遮挡

### swimlane 并排排列坐标

- 第一个 swimlane x=20，y=20
- 后续 x = 前一个 x + swimlane宽 + 40（间距）

---

## 区域分离详细规则

每个页面 swimlane 内部划分为两个水平区域，**二者绝不重叠**：

```
swimlane 内部
┌─────────────────────────────┬──┬───────────────────┐
│                             │  │                   │
│         UI 区               │  │    标注区          │
│   （仅放真实 UI 组件）        │间│  （业务说明专区）  │
│                             │隔│                   │
│  x: 0 ~ UI宽               │  │  x: UI宽+20 起    │
│  移动端：0~375               │  │  移动端：395~595   │
│  Web：0~1440                │  │  Web：1460~1700    │
└─────────────────────────────┴──┴───────────────────┘
```

**标注元素尺寸限制（防止溢出相邻 swimlane）：**
- 移动端标注区宽度 = 200px（595 - 375 - 20），所有标注元素 `width ≤ 180`
- Web 标注区宽度 = 240px（1700 - 1440 - 20），所有标注元素 `width ≤ 220`
- 页面说明卡片 x + width 不得超过 swimlane 右边界（移动端不超过 595，Web 不超过 1700）
- **禁止**：标注卡片宽度超出标注区范围，导致溢出覆盖相邻 swimlane 的 UI 区

**禁止**：标注元素的 x 坐标进入 UI 区（x < UI宽），不得与任何 UI 组件重叠

所有标注元素样式：`text;html=1;strokeColor=none;fillColor=none;fontSize=10;fontColor=#9e9e9e;align=left;verticalAlign=top;`

---

## 组件尺寸参考表

### 布局对齐与间距规格（8pt 网格，所有坐标/尺寸必须是 8 的倍数）

**间距标准：**

| 规格项 | 标准值 |
|--------|--------|
| 页面左右边距 | 24px（x 起点 = 24） |
| 组件间垂直间距 | 16px（紧凑 8px） |
| 同行组件水平间距 | 12px |
| 卡片内边距 | 16px |

**组件精确尺寸（必须严格使用，禁止自行估算）：**

| 组件 | 高度 | 宽度 |
|------|------|------|
| 顶部导航栏 | 56px | 等于 UI 区宽 |
| 输入框 | 44px | 按列宽计算 |
| 主按钮 / 次要按钮 | 44px | ≥ 80px |
| 小按钮（行操作） | 32px | 60px |
| 超小按钮 | 24px | 48px |
| 表格列标题行 | 44px | — |
| 表格数据行 | 52px | — |
| 卡片头部 | 48px | — |
| Tag 状态标签 | 24px | 按文字 + 8px*2 |
| 底部标签栏（移动端） | 56px | 等于 UI 区宽 |
| 面包屑 / 分页栏 | 40px | — |

**8pt 网格强制要求：**
- 所有 `<mxGeometry>` 的 `x`、`y`、`width`、`height` 必须是 **8 的倍数**
- 导航栏固定 y=0；第一个内容组件 y=56+16=72（导航高+上边距）
- 同列所有输入框/按钮 x 坐标必须一致；同行组件 y 坐标必须一致
- 同类组件（如所有输入框、所有主按钮）尺寸必须完全相同

---

## 常用 UI 元素样式表

| 元素 | style 值 |
|------|----------|
| 顶部导航栏 | `rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;verticalAlign=middle;` |
| 页面背景 | `rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;` |
| 卡片 | `rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e0e0e0;shadow=1;` |
| 主按钮 | `rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;` |
| 次要按钮 | `rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#1e88e5;fontColor=#1e88e5;fontSize=13;` |
| 输入框 | `rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=8;` |
| 文字标签 | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=13;` |
| 标题文字 | `text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=16;fontStyle=1;` |
| 底部标签栏 | `rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e0e0e0;fontSize=11;` |
| 分割线 | `line;strokeColor=#e0e0e0;fillColor=none;` |
| 列表行 | `rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#eeeeee;align=left;spacingLeft=12;` |
| 图片占位 | `rounded=1;whiteSpace=wrap;html=1;fillColor=#e3f2fd;strokeColor=#90caf9;fontColor=#1565c0;` |
| 状态标签（成功） | `rounded=1;whiteSpace=wrap;html=1;fillColor=#e8f5e9;strokeColor=none;fontColor=#2e7d32;fontSize=11;` |
| 状态标签（警告） | `rounded=1;whiteSpace=wrap;html=1;fillColor=#fff8e1;strokeColor=none;fontColor=#f57f17;fontSize=11;` |
| 标注区文字（说明/规则/跳转） | `text;html=1;strokeColor=none;fillColor=none;fontSize=10;fontColor=#9e9e9e;align=left;verticalAlign=top;` |

---

## 视觉层级规则

### Tab 组件规格

- Tab 栏高度 40px，每个 Tab 标签宽度等分，激活态用主色底色 + 白色文字
- 同一 swimlane 内绘制默认激活的第一个 Tab 的内容，其余 Tab 内容在标注区注明"切换后显示 [字段列表]"

### 后台侧边栏视觉规格

- 深色矩形 `w=200 fillColor=#263238`，内含菜单项（每项 h=48，激活项 fillColor=#1e88e5）

### 登录页视觉规格

- 居中卡片 `w=360（移动端320）`，内含输入框组 + 主按钮
- 第一个元素：Logo 或产品名文字（h=60），然后输入框，最后按钮
