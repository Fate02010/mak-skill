# comparison — 左右对比

将两个对象/方案并排展示，突出差异和共同点。

## 结构

- 左右两栏，中间可有分割线或 VS 标志
- 顶部各有标题标识
- 对应行展示相同维度的对比值
- 可有底部结论区

## 最适合

- A vs B 方案比较
- 优缺点分析
- 前后对比（before/after）
- 产品功能对比

## Image Prompt 空间描述语言

```
A split-screen comparison infographic on white background. Two equal columns side by side. Left column has [左侧颜色] header with title "[左标题]". Right column has [右侧颜色] header with title "[右标题]". A bold "VS" badge or vertical dividing line in the center. N rows of comparison items, each row showing the same attribute for both sides. Each row: attribute icon on the far left, left value in the left column, right value in the right column.
```

## 对比行结构（提示词写法）

```
Comparison rows from top to bottom:
- Row 1: attribute "[维度1]", left value "[左值]", right value "[右值]"
- Row 2: attribute "[维度2]", left value "[左值]", right value "[右值]"
...
Bottom summary: "[结论文字]"
```

## 文字标签建议

- 两侧标题：≤ 4 汉字 / 3 词
- 维度名：≤ 4 汉字
- 对比值：数字或 1-3 词

## 推荐配对风格

- `flat-vector`：最常用
- `corporate-memphis`（如有）：商业报告风格
