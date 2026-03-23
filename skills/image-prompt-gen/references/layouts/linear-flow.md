# linear-flow — 横向流程步骤

横向排列的步骤序列，用箭头连接，展示有序流程或过程。

## 结构

- 3-6 个等宽卡片从左到右水平排列
- 卡片之间有粗体向右箭头
- 每个卡片：顶部图标 + 中央标签 + 底部副标签
- 明确的起点和终点
- 可选：底部添加数据汇总条

## 最适合

- 操作流程、步骤指南（how-to）
- 项目阶段、工作流
- 算法/决策过程
- 产品功能演示

## Image Prompt 空间描述语言

```
A horizontal N-step process flow on a [background] background. N equal-width rounded rectangle cards arranged in a single row from left to right, connected by bold rightward arrow icons between each card. Each card contains: a large icon at top center, a bold 2-3 word label in the middle, and a brief 4-word subtitle below the label. Cards have alternating or graduated colors. A bold title at the very top spanning full width.
```

替换变量：N=步骤数，background=white/light gray

## 卡片结构（提示词写法）

```
- Card 1 ([颜色]): icon of [图标描述], label "[2-3词标签]", subtitle "[≤4词说明]"
- Card 2 ([颜色]): icon of [图标描述], label "[2-3词标签]", subtitle "[≤4词说明]"
...
```

## 文字标签建议

- 主标题：≤ 6 汉字
- 步骤标签：≤ 4 汉字 / 3 英文词（如"产品设计"、"SPEC LAYERS"）
- 副标签：≤ 8 汉字 / 5 英文词
- 底部汇总：数字 + 短词（如"36% 提效"）

## 推荐配对风格

- `flat-vector`：最常用，干净专业
- `digital-illustration`：更有趣味感
- `concept-art`：技术/工程主题
