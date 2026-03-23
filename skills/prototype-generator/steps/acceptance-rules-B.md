# B 类模板验收规则

本文件定义 B 类模板验收规则，仅 draw.io 两阶段架构适用。
检查 page_spec 和最终 XML 是否遵循页面模板库。

---

### B1 — 页面类型是否正确

**定义：** page_spec 中标注的页面类型必须与需求文档中该页面的实际功能一致。

**检查方法：**

1. 读取 `原型任务清单.md` 中每个页面的类型标注（列表页/表单页/详情页/登录页）
2. 读取 `page_spec_*.md` 中 swimlane 布局表的 type 列
3. 对照检查：
   - 需求文档说「管理列表」→ page_spec type 应为 web，骨架应为列表页模板
   - 需求文档说「新增表单」→ page_spec type 应为 web/mobile，骨架应为表单页模板
   - 需求文档说「查看详情」→ 骨架应为详情页模板
   - 需求文档说「登录」→ 骨架应为登录页模板，**swimlane 内不得有 sidebar/nav 导航**

**常见错误：**
- 列表页用了表单页模板（没有表格，只有输入框）
- 详情页用了表单页模板（出现空白 input 而非键值对）
- 登录页用了后台页面模板（带侧边栏）

**不通过修复：** 重新生成该页面的 page_spec（套用正确模板）+ 重新渲染。

---

### B2 — 骨架是否正确

**定义：** 每个页面必须包含其类型模板中定义的所有固定骨架元素，不得缺失。

**检查方法：**

读取 page_spec 或最终 XML，检查以下骨架必备元素：

| 页面类型 | 必须存在的骨架元素 | 检查方式 |
|----------|------------------|----------|
| 列表页（Web） | nav + breadcrumb + ≥1 input/select（筛选）+ btn「查询」+ btn「新增」+ ≥3 table_header + ≥3 table_row + pagination + annotation_card | Grep 统计各 style_key 出现次数 |
| 表单页 | nav + ≥2 label + ≥2 input + btn「提交」+ btn「取消」+ annotation_card | 同上 |
| 详情页 | nav + breadcrumb + ≥2 label + ≥2 text_value + ≥1 tag + btn「返回」+ annotation_card | 同上 |
| 登录页 | bg + card + text_title + ≥2 input + btn_primary「登录」+ annotation_card；**不得有** sidebar/nav/breadcrumb | 同上 + 反向 Grep 确认无 sidebar |

**输出格式：**
```
[页面名]（列表页）骨架校验：
  ✅ nav | ✅ breadcrumb | ✅ 筛选区（2 input + 1 select + 查询 + 重置）
  ✅ 新增按钮 | ✅ 表格（5列×3行）| ✅ pagination | ✅ annotation_card
  骨架完整度：10/10 = 100%
```

**不通过修复：** 用 Edit 在 page_spec 中补充缺失的骨架元素行，然后重新渲染。

---

### B3 — 主区是否突出

**定义：** 每个页面必须有一个视觉上占据最大面积的「主内容区」，该区域面积必须 ≥ 页面可用面积的 50%。

**检查方法（draw.io 模式）：**

1. 计算页面可用面积 = UI 区宽 × (swimlane 高 - 导航栏高 - 底部栏高)
   - Web：1440 × (960 - 56 - 0) = 1,301,760 px²
   - 移动端：375 × (860 - 56 - 56) = 280,500 px²

2. 识别主内容区：
   - 列表页：主内容区 = 表格区（从 table_header 第一行 y 到最后一个 table_row 的 y+height）
   - 表单页：主内容区 = 字段区 card 容器
   - 详情页：主内容区 = 基础信息 card 容器
   - 登录页：主内容区 = 居中 card

3. 计算主内容区面积占比：
   - 主内容区面积 = width × height（从 page_spec 读取）
   - 占比 = 主内容区面积 / 页面可用面积

4. 判定：
   - ≥ 50%：✅ 主区突出
   - 30%–50%：⚠️ 主区偏小，建议扩大
   - < 30%：❌ 主区不突出，页面重心不明确

**常见问题：**
- 列表页表格只有 2 行数据，表格区占比过小
- 表单页字段 card 宽度不足（只用了 400px，实际可用 1392px）
- 大量标注文字挤占了 UI 区（标注区元素 x 坐标进入 UI 区）

**不通过修复：** 扩大主内容区尺寸（增加表格行数、扩大 card 宽度），或删除挤占主区的多余元素。

---

### B4 — 是否出现模板外乱布局

**定义：** 页面元素的 y 坐标顺序必须符合其类型模板的区块排列逻辑，禁止出现"筛选区跑到表格下方"、"提交按钮出现在导航栏上方"等乱序。

**检查方法：**

1. 对每个页面，按 y 坐标从小到大排列所有元素
2. 检查元素 style_key 的出现顺序是否符合模板定义：

| 页面类型 | 正确的 y 坐标递增顺序 |
|----------|---------------------|
| 列表页 | nav → breadcrumb → 筛选区(input/select/btn) → 新增btn → table_header → table_row×3 → pagination → annotation_card(标注区) |
| 表单页 | nav → breadcrumb → text_subtitle(分组) → label+input(×N) → btn_primary+btn_secondary → annotation_card |
| 详情页 | nav → breadcrumb → card → label+text_value(×N) → tag → btn → annotation_card |
| 登录页 | bg → card → text_title → input(×N) → btn_primary → text_hint |

3. 检测乱序：
   - 若 pagination 的 y < table_header 的 y → 分页跑到表头上方 ❌
   - 若 btn_primary（提交）的 y < 任何 input 的 y → 按钮在输入框上方 ❌
   - 若 annotation_card 的 x < 标注区起点 → 标注卡片进入 UI 区 ❌
   - 若 sidebar 或 nav 出现在登录页 → 骨架隔离违规 ❌

**输出格式：**
```
[页面名] 布局顺序校验：
  ✅ 元素 y 坐标递增顺序与模板一致
  ❌ pagination(y=170) 出现在 table_header(y=218) 之前 → 分页乱序
```

**不通过修复：** 用 Edit 修正元素的 y 坐标，使其符合模板顺序。

---

## 验收执行时机汇总

| 规则 | Step 5-5 | Step 6-0 |
|------|----------|----------|
| B1 页面类型正确 | ✅ draw.io 模式执行 | — |
| B2 骨架正确 | ✅ draw.io 模式执行 | — |
| B3 主区突出 | — | ✅ 维度三执行 |
| B4 模板外乱布局 | ✅ draw.io 模式执行 | — |
