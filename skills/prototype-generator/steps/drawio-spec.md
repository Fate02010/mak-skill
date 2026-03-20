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

文件名与 HTML 模式一致，仅扩展名改为 `.drawio`：

| HTML 模式 | draw.io 模式 |
|-----------|-------------|
| `login.html` | `login.drawio` |
| `home.html` | `home.drawio` |
| `order-list.html` | `order-list.drawio` |
| `index.html` | `index.drawio`（跳转地图目录页） |
