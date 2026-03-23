# bento-grid — 信息方格

不同尺寸的方格拼合，像便当盒一样展示多个并列主题。

## 结构

- 4-9 个矩形方格，尺寸不等
- 有主格（更大，放最重要内容）
- 支撑方格环绕主格排列
- 每格有标题+图标+简短内容

## 最适合

- 多个并列特性/功能展示
- 总览/摘要类信息
- 产品特性矩阵
- 知识点集合

## Image Prompt 空间描述语言

```
A bento-box grid infographic on white background. A collection of N rounded rectangle cards of varied sizes arranged in a tight grid layout. One large "hero" card (2x width or 2x height) for the main point, surrounded by smaller cards. Each card has a distinct [颜色] background, a bold short title at top, a large icon or number in the center, and a brief 3-word subtitle at bottom. Clean consistent border radius on all cards, uniform padding inside.
```

## 方格结构（提示词写法）

```
Grid layout:
- Hero card (large, [颜色]): icon of [图标], bold title "[主题名]", subtitle "[≤4词]"
- Supporting card 2 ([颜色]): bold number "[数值]", label "[指标名]"
- Supporting card 3 ([颜色]): icon of [图标], label "[特性名]", subtitle "[≤4词]"
...（最多9格）
```

## 推荐配对风格

- `flat-vector`：最常用（默认）
- `digital-illustration`：更有个性
- `cyberpunk`：科技/暗色主题
