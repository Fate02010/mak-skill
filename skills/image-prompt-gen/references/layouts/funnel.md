# funnel — 漏斗

从宽到窄的漏斗形状，展示递进筛选或转化过程。

## 结构

- 顶部最宽，逐层变窄
- 3-5 层，每层有标签和数字
- 箭头向下表示流向
- 可在右侧显示各层数量/百分比

## 最适合

- 转化率漏斗
- 筛选/过滤过程
- 从宏观到微观的递进
- 用户旅程各阶段

## Image Prompt 空间描述语言

```
A funnel diagram on white background. A large inverted trapezoid shape divided into N horizontal layers from top (widest) to bottom (narrowest). Each layer has a distinct [颜色] fill and a bold centered label. The right side of each layer shows a percentage or number value. Downward arrows between layers indicate flow. The overall shape resembles a funnel or inverted pyramid.
```

## 层级结构（提示词写法）

```
Funnel layers from top to bottom:
- Layer 1 (widest, [颜色]): bold label "[层名]", right-side value "[数值]"
- Layer 2 ([颜色]): bold label "[层名]", right-side value "[数值]"
...
- Layer N (narrowest, [颜色]): bold label "[层名]", right-side value "[数值]"
```

## 推荐配对风格

- `flat-vector`：标准商业漏斗
- `corporate-memphis`（如有）：活泼版本
