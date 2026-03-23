# timeline — 时间线

按时间顺序展示事件、历史或里程碑的线性排列。

## 结构

- 一条横贯全图的主线（或竖线）
- 节点标记关键时间点
- 节点上/下交替排列事件描述
- 年份/日期标注在主线上

## 最适合

- 历史演变、发展史
- 产品迭代路线图
- 人物/公司成长历程
- 项目时间规划

## Image Prompt 空间描述语言

```
A horizontal timeline infographic on white background. A thick horizontal line runs across the center of the image. N circular or diamond-shaped nodes marked at equal intervals along the line, each labeled with a year or date below the line. Above each even-numbered node: a small icon + 2-line text (title + description). Below each odd-numbered node: a small icon + 2-line text. Bold timeline line with directional arrows at the right end.
```

## 节点结构（提示词写法）

```
- Node 1 at left: date "[年份/日期]", above line, icon of [图标], label "[事件名]", subtitle "[简短描述]"
- Node 2: date "[年份/日期]", below line, icon of [图标], label "[事件名]"
...
```

## 文字标签建议

- 日期：年份数字（如"2020"、"Q3 2024"）
- 事件名：≤ 4 汉字 / 3 词
- 描述：≤ 8 汉字（可省略）

## 推荐配对风格

- `flat-vector`：现代科技感
- `watercolor`：历史/人文内容
- `aged-academia`：学术/历史主题（如有此风格）
