# draw.io 原型图规范

生成的每个 .drawio 文件必须符合以下规范。

## 文件结构

每个页面生成一个独立 `.drawio` 文件，存放于 `WORK_DIR/prototypes/` 下：

```xml
<mxfile host="app.diagrams.net">
  <diagram id="[唯一ID]" name="[页面名称]">
    <mxGraphModel width="[画布宽]" height="[画布高]" grid="0" guides="1" tooltips="1" page="1" pageWidth="[画布宽]" pageHeight="[画布高]">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
        <!-- UI 元素从 id="2" 开始 -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

**画布尺寸：**
- 移动端页面：`width="375" height="812"`（iPhone 标准尺寸）
- 后台/Web 页面：`width="1440" height="900"`

## 常用 UI 元素样式

| 元素 | style 值 |
|------|----------|
| 顶部导航栏 | `rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;verticalAlign=middle;` |
| 主容器/背景 | `rounded=0;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=none;` |
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

## mxCell 写法示例

```xml
<!-- 顶部导航栏 -->
<mxCell id="2" value="页面标题" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=14;fontStyle=1;verticalAlign=middle;" vertex="1" parent="1">
  <mxGeometry x="0" y="0" width="375" height="48" as="geometry" />
</mxCell>

<!-- 卡片 -->
<mxCell id="3" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e0e0e0;shadow=1;" vertex="1" parent="1">
  <mxGeometry x="12" y="64" width="351" height="80" as="geometry" />
</mxCell>

<!-- 文字标签 -->
<mxCell id="4" value="用户名称" style="text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;fontSize=13;" vertex="1" parent="1">
  <mxGeometry x="20" y="72" width="200" height="24" as="geometry" />
</mxCell>

<!-- 主按钮（带跳转链接） -->
<mxCell id="5" value="立即下单" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#1e88e5;strokeColor=none;fontColor=#ffffff;fontSize=13;fontStyle=1;" vertex="1" parent="1" tooltip="→ order-confirm.drawio">
  <mxGeometry x="12" y="740" width="351" height="44" as="geometry" />
</mxCell>
```

## 页面跳转标注规范

draw.io 没有真实超链接跳转，使用以下两种方式标注跳转关系：

1. **tooltip 属性**：在按钮/链接元素上加 `tooltip="→ 目标文件名.drawio"`
2. **跳转说明文字框**：在页面底部添加灰色说明框，列出所有跳转关系：

```xml
<mxCell id="99" value="跳转说明：&#xa;• [按钮A] → order-confirm.drawio&#xa;• [返回] → home.drawio"
  style="text;html=1;strokeColor=#e0e0e0;fillColor=#fafafa;align=left;verticalAlign=top;fontSize=11;fontColor=#9e9e9e;spacingLeft=8;"
  vertex="1" parent="1">
  <mxGeometry x="0" y="760" width="375" height="52" as="geometry" />
</mxCell>
```

## 内容规范

- **真实数据**：使用符合业务场景的示例数据，不用"文字1"/"按钮A"等占位符
- **完整界面**：包含导航栏、主要内容区、操作按钮、底部标签栏（移动端）
- **状态展示**：展示最常见状态（有数据状态优先于空状态）
- **层级清晰**：id 按从上到下、从左到右的顺序递增，便于阅读

## 命名规范

文件名与 HTML 模式保持一致（仅扩展名改为 `.drawio`）：

| HTML 模式 | draw.io 模式 |
|-----------|-------------|
| `login.html` | `login.drawio` |
| `home.html` | `home.drawio` |
| `order-list.html` | `order-list.drawio` |
| `index.html`（导航首页） | `index.drawio`（目录页） |
