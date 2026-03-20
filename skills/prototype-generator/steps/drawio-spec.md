# draw.io 原型图规范

生成的每个 `.drawio` 文件必须是**可直接在 draw.io / Diagrams.net 中打开**的合法 XML 文件。

---

## 完整文件结构（必须严格遵守）

```xml
<mxfile host="app.diagrams.net" modified="2024-01-01T00:00:00.000Z" agent="Claude Code" version="24.0.0" type="device">
  <diagram id="[8位随机字母数字，如 aB3dEf7g]" name="[页面中文名]">
    <mxGraphModel dx="1034" dy="546" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="[画布宽]" pageHeight="[画布高]" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- 所有 UI 元素从 id="2" 开始，必须有 parent="1" -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**关键属性说明：**
- `mxfile` 必须包含 `host`、`modified`、`agent`、`version`、`type` 五个属性
- `diagram` 的 `id` 必须唯一，`name` 为页面显示名称
- `mxGraphModel` 必须包含 `dx`、`dy`、`grid`、`gridSize`、`guides`、`tooltips`、`connect`、`arrows`、`fold`、`page`、`pageScale`、`pageWidth`、`pageHeight`、`math`、`shadow` 全部属性
- `root` 下前两个 `mxCell`（id=0 和 id=1）是固定基础层，**不可省略**
- 所有 UI 元素的 `parent` 必须为 `"1"`

**画布尺寸：**
- 移动端页面：`pageWidth="375" pageHeight="812"`（iPhone 标准）
- 后台/Web 页面：`pageWidth="1440" pageHeight="900"`

---

## XML 特殊字符转义规则

| 原字符 | 转义写法 | 使用场景 |
|--------|----------|----------|
| `&` | `&amp;` | value 中出现 & 符号 |
| `<` | `&lt;` | value 中出现小于号 |
| `>` | `&gt;` | value 中出现大于号 |
| 换行 | `&#xa;` | value 中需要换行 |
| `"` | `&quot;` | value 中出现双引号 |

---

## 形状（vertex）写法

所有形状必须包含 `vertex="1"` 和 `parent="1"`：

```xml
<mxCell id="[数字]" value="[显示文字]" style="[样式]" vertex="1" parent="1">
  <mxGeometry x="[X坐标]" y="[Y坐标]" width="[宽]" height="[高]" as="geometry" />
</mxCell>
```

> **`<mxGeometry>` 必须有 `as="geometry"` 属性，不可省略。**

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
| 跳转说明框 | `text;html=1;strokeColor=#e0e0e0;fillColor=#fafafa;align=left;verticalAlign=top;fontSize=11;fontColor=#9e9e9e;spacingLeft=8;` |

---

## 完整单页示例（移动端登录页）

```xml
<mxfile host="app.diagrams.net" modified="2024-01-01T00:00:00.000Z" agent="Claude Code" version="24.0.0" type="device">
  <diagram id="kR2mNp4q" name="登录页">
    <mxGraphModel dx="1034" dy="546" grid="0" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="375" pageHeight="812" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- 页面背景 -->
        <mxCell id="2" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;" vertex="1" parent="1">
          <mxGeometry x="0" y="0" width="375" height="812" as="geometry" />
        </mxCell>
        <!-- 顶部导航栏 -->
        <mxCell id="3" value="登录" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;verticalAlign=middle;" vertex="1" parent="1">
          <mxGeometry x="0" y="0" width="375" height="48" as="geometry" />
        </mxCell>
        <!-- Logo 占位 -->
        <mxCell id="4" value="🐟 鲜渔到家" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=24;fontStyle=1;" vertex="1" parent="1">
          <mxGeometry x="0" y="100" width="375" height="60" as="geometry" />
        </mxCell>
        <!-- 手机号输入框 -->
        <mxCell id="5" value="请输入手机号" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=12;fontSize=13;fontColor=#9e9e9e;" vertex="1" parent="1">
          <mxGeometry x="24" y="200" width="327" height="48" as="geometry" />
        </mxCell>
        <!-- 密码输入框 -->
        <mxCell id="6" value="请输入密码" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#bdbdbd;align=left;spacingLeft=12;fontSize=13;fontColor=#9e9e9e;" vertex="1" parent="1">
          <mxGeometry x="24" y="264" width="327" height="48" as="geometry" />
        </mxCell>
        <!-- 登录按钮 -->
        <mxCell id="7" value="登录" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=15;fontStyle=1;" vertex="1" parent="1" tooltip="→ home.drawio">
          <mxGeometry x="24" y="340" width="327" height="48" as="geometry" />
        </mxCell>
        <!-- 注册链接 -->
        <mxCell id="8" value="还没有账号？立即注册" style="text;html=1;strokeColor=none;fillColor=none;align=center;verticalAlign=middle;fontSize=13;fontColor=#1e88e5;" vertex="1" parent="1" tooltip="→ register.drawio">
          <mxGeometry x="0" y="408" width="375" height="32" as="geometry" />
        </mxCell>
        <!-- 跳转说明 -->
        <mxCell id="9" value="跳转说明：&#xa;• 登录按钮 → home.drawio&#xa;• 立即注册 → register.drawio" style="text;html=1;strokeColor=#e0e0e0;fillColor=#fafafa;align=left;verticalAlign=top;fontSize=11;fontColor=#9e9e9e;spacingLeft=8;" vertex="1" parent="1">
          <mxGeometry x="0" y="760" width="375" height="52" as="geometry" />
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

---

## 连线（edge）写法（用于 index.drawio 跳转地图）

```xml
<mxCell id="[数字]" value="[标注文字，可为空]" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;" edge="1" source="[来源节点id]" target="[目标节点id]" parent="1">
  <mxGeometry relative="1" as="geometry" />
</mxCell>
```

> **连线必须包含 `edge="1"`、`source`、`target`、`parent="1"`，`<mxGeometry>` 必须有 `relative="1" as="geometry"`。**

---

## 页面跳转标注规范

draw.io 无法实现真实文件跳转，统一用以下两种方式标注：

1. **按钮/链接元素加 `tooltip` 属性**：`tooltip="→ 目标文件名.drawio"`
2. **页面底部跳转说明框**：用 `&#xa;` 换行，列出所有跳转关系（见上方示例 id=9）

---

## 内容规范

- **真实数据**：使用符合业务场景的示例文字，不用"文字1"/"按钮A"等占位符
- **完整界面**：包含背景层、导航栏、主内容区、操作按钮、跳转说明框
- **id 连续递增**：从 2 开始，按从上到下、从左到右顺序，不可跳号或重复
- **XML 合法性**：value 中出现 `&`、`<`、`>` 必须转义；文件必须是合法闭合 XML

---

## 命名规范

### 文件命名

draw.io 模式**整个系统只输出一个文件**：`[产品名称].drawio`（如 `鲜渔到家.drawio`）。

每个页面对应文件内的一个 `<diagram>`，用 `name` 属性标注页面名称：

| 页面 | diagram name |
|------|-------------|
| 登录页 | `用户-登录页` |
| 首页 | `用户-首页` |
| 订单列表 | `订单-列表页` |
| 跳转地图 | `导航-页面跳转地图` |

**subagent 输出约定：** 每个 subagent 将负责的所有 `<diagram>` 写入临时片段文件 `WORK_DIR/drawio_[模块英文名]_tmp.xml`（仅含 `<diagram>` 元素，无 `<mxfile>` 包裹）。主流程等所有 subagent 完成后，将全部 `<diagram>` 合并写入 `WORK_DIR/prototypes/[产品名称].drawio`。

### 页面/组件/连线命名规则

| 类型 | 命名格式 | 示例 |
|------|----------|------|
| **页面** | `系统-模块-页面` | `订单-列表页`、`用户-个人中心` |
| **组件** | `类型-业务名` | `按钮-提交订单`、`弹窗-删除确认` |
| **连线** | `动作-目标页面` | `点击提交-订单详情`、`取消-返回列表` |

---

## 页面结构规则（每页必须包含）

### 通用必备区块

每个页面顶部必须有**页面说明卡片**（用跳转说明框样式），包含以下信息：

```
页面：[系统-模块-页面名]
用途：[一句话描述页面职责]
用户角色：[买家 / 商家 / 管理员 / ...]
主操作：[该页面最核心的一个操作]
跳转去向：[操作A → 目标页, 操作B → 目标页]
```

### 列表页必须包含四个区块

| 区块 | 说明 |
|------|------|
| **筛选区** | 搜索框 + 筛选条件（状态/时间/分类等），含"查询"和"重置"按钮 |
| **表格区** | 列标题行 + 至少 3 行示例数据，含复选框（如需批量操作） |
| **分页区** | 当前页/总页数、每页条数、上一页/下一页按钮 |
| **行操作区** | 每行右侧操作列：查看/编辑/删除等，危险操作用红色标注 |

### 表单页必须包含四个区块

| 区块 | 说明 |
|------|------|
| **字段区** | 所有输入字段，必填字段标注 `*`，每个字段旁注明校验规则 |
| **校验规则** | 在字段下方或右侧用灰色小字注明：如"最多 50 字"、"手机号格式" |
| **提交按钮** | 主按钮，注明点击后动作（tooltip 指向成功页或结果反馈） |
| **取消按钮** | 次要按钮，tooltip 指向来源页 |

### 详情页必须包含四个区块

| 区块 | 说明 |
|------|------|
| **基础信息区** | 核心字段展示（编号、名称、时间等键值对布局） |
| **状态区** | 当前状态标签 + 状态流转说明（如：待支付 → 已支付 → 已发货） |
| **操作区** | 该状态下可执行的操作按钮，不可用的按钮置灰并注明原因 |
| **日志/记录区** | 操作历史或流转记录列表（时间、操作人、操作内容） |

---

## 交互规则（所有页面强制执行）

| 规则 | 要求 |
|------|------|
| **主按钮动作说明** | 所有主按钮必须通过 `tooltip` 或旁注说明点击后的动作和跳转目标 |
| **危险操作确认弹窗** | 删除、清空、注销、强制操作等必须绘制确认弹窗，挂载到来源页面 |
| **表单反馈** | 每个表单页必须标注：成功态（提示文字 + 跳转）和失败态（错误提示位置） |
| **可回退** | 每个页面必须有明确的返回/取消路径，连线标注 `返回-[上级页面]` |

---

## 状态规则（必须补充，不得只画 happy path）

每个核心页面必须补充以下状态的示意（可在同一画布内并排展示）：

| 状态 | 说明 |
|------|------|
| **默认态** | 正常有数据的主流程状态 |
| **空态** | 无数据时的展示（引导文案 + 引导操作按钮） |
| **异常态** | 加载失败 / 网络错误（错误提示 + 重试按钮） |
| **无权限态** | 无访问权限时的提示（说明原因 + 返回操作） |
| **处理中态** | 提交/加载中的按钮禁用状态（按钮文字变"处理中..."） |
| **结果态** | 操作成功/失败的结果页或 Toast 提示 |

> 关键操作（提交、支付、删除）必须补充**处理中态**和**结果态**，其他页面至少补充**空态**和**异常态**。

---

## UI 渲染质量规则（禁止违反）

### 首要原则：输出结果必须首先像界面，其次才是说明图

在生成任何页面前，明确以下两点：
1. **界面 ≠ 文档截图**：不能把 PRD 章节标题、业务说明直接画成界面主体
2. **组件优先**：需求信息必须映射为真实 UI 组件，禁止用大文本框平铺说明文字

---

### 规则一：先识别页面类型，再套用对应骨架

生成前必须判断页面类型，并强制套用对应骨架：

| 页面类型 | 识别特征 | 对应骨架 |
|----------|----------|----------|
| **列表页** | 有查询/筛选/表格/分页 | 顶部筛选区 + 表格 + 分页 + 行操作 |
| **表单页** | 有填写/提交/新增/编辑 | 字段分组 + 校验提示 + 提交/取消按钮 |
| **详情页** | 有查看/详情/信息展示 | 基础信息卡 + 状态标签 + 操作按钮 + 日志区 |
| **登录/注册页** | 有账号/密码/验证码输入 | 居中卡片 + 输入框组 + 主按钮 + 辅助链接 |
| **首页/Dashboard** | 有汇总数据/快捷入口 | 顶部统计卡 + 图表区 + 快捷操作入口 |
| **设置页** | 有配置项/开关/保存 | 左侧导航 + 右侧设置分组 + 保存按钮 |

---

### 规则二：需求信息映射为 UI 组件

| 需求内容 | 正确做法 | 禁止做法 |
|----------|----------|----------|
| 状态字段（待支付/已支付/...） | Tag 标签组件，不同颜色区分状态 | 大文本框写"状态：待支付" |
| 列表数据 | Table 组件，列标题 + 3 行示例数据 | 竖排文字列出数据项 |
| 筛选条件 | Input + Select + DatePicker + Button | 说明框写"筛选区：支持按状态筛选" |
| 操作按钮组 | Button 组件，主次样式区分 | 文字写"操作：查看、编辑、删除" |
| 弹窗/确认框 | Modal 浮层组件（绘制在主页面旁） | 大框写"此处弹出确认弹窗" |
| 分页 | Pagination 组件（含页码 + 条数） | 文字写"底部有分页" |
| Tab 切换 | Tab 组件，多个 Tab 标签 | 说明框写"支持按Tab切换" |

---

### 规则三：主次层级与视觉中心

- **主操作区**（核心按钮、主要输入框）占据最显眼位置，使用蓝色填充主按钮突出
- **次要信息**（页面说明卡、跳转说明框、业务规则注释）统一放置在页面右侧或底部，字号 ≤ 11，颜色 `#9e9e9e`
- **页面说明卡片**尺寸不超过页面宽度的 30%，绝不占据页面上半部分核心区域
- **状态流程图**（如：待支付→已支付→已发货）用小型流程图或状态标签行排列，不用大文本框

---

### 规则四：布局对齐与间距规格

| 规格项 | 标准值 |
|--------|--------|
| 页面边距 | 左右各 24px |
| 组件间垂直间距 | 16px（紧凑布局 8px） |
| 同行组件水平间距 | 12px |
| 输入框高度 | 36–48px |
| 主按钮高度 | 36–48px，宽度 ≥ 80px |
| 行操作小按钮 | 高度 28px，宽度 60px |
| 表格列标题行高度 | 40px |
| 表格数据行高度 | 48px |
| 卡片内边距 | 16px |

所有同类组件尺寸必须一致，同列元素 x 坐标对齐，同行元素 y 坐标对齐。

