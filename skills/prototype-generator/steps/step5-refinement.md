# 三轮精修规则

> subagent 生成所有页面后必须自动执行三轮精修，不得跳过。汇报行含「含三轮精修」字样表示完成。

---

## HTML 模式精修

▶ 第一轮 — 字段完整性精修
逐页重新对照需求文档对应章节，用 Edit 工具修复：
- 表单页缺少的字段：补充 `<label>真实字段名</label><input>` 行
- 详情页缺少的键值对：补充 `<span class="label">字段名</span><span class="value">示例数据</span>`
- 列表页缺少的表格列：在 `<thead>` 和每行 `<td>` 中补充

▶ 第二轮 — 内容真实性精修
逐页检查并修复：
- 多条数据行的规格/价格/时间是否完全相同 → 修改为各不相同的真实示例（如价格差异 ¥20-¥200）
- 是否仍有"字段一/字段二"等序号 label → 替换为需求文档中的真实字段名
- 是否有 class="card" 但内部无实质内容的空容器 → 补充内容或删除容器

▶ 第三轮 — 交互闭环精修
逐页检查并修复：
- 每个 `<a>` 和带 `onclick` 的按钮是否有明确目标（href 或 location.href）
- 列表页是否有空态 HTML（无数据时的引导文案 + 引导按钮）
- 表单页提交按钮是否有"处理中..."加载态和成功/失败反馈

---

## draw.io 模式精修

### 写入后质量验收（必须通过，不通过先修复再进入三轮精修）

文件写入后立即执行以下 Grep 检查，发现问题用 Edit 修复：

1. **占位内容检测**：
   Grep 搜索以下模式（任意命中 → 立即替换为需求文档中的真实业务内容）：
   `搜索框|主按钮|状态标签|列表项\d|数据项\d|卡片\d|示例数据|业务卡片|真实字段|字段一|字段二|InputA|选项\d`

2. **内容丰富度检测**：
   统计每个页面 swimlane 内的 mxCell 数量，不足则补充元素：
   - 列表页 swimlane：mxCell ≥ 20（导航+筛选+表头+3行数据各列+分页+标注）
   - 表单页 swimlane：mxCell ≥ 15（导航+每字段Label+Input+提交取消按钮+标注）
   - 详情页 swimlane：mxCell ≥ 12（导航+各字段键值对+操作按钮+标注）

3. **parent 层级检测**：
   Grep `parent="1"` → 若有非 swimlane 容器本身使用 parent="1"，说明 UI 元素层级错误，需将其 parent 改为所属 swimlane 的 id

4. **暗色背景检测**：
   Grep `fillColor=#[01][0-9a-fA-F]` → 若命中元素为 bg 类组件（component_type=bg 或 style 含 `strokeColor=none` 且 width≥300），说明背景色过深会遮盖内容，用 Edit 将 fillColor 替换为 `#f5f5f5`

5. **移动端主导航页底栏检测**：
   对需求文档中标注为"主导航页"的每个移动端 swimlane，Grep `bottom_bar` 是否存在于该 swimlane 的元素中：
   - 缺失 → 在该 swimlane 末尾追加：`<mxCell id="N" value="{{Tab1}} · {{Tab2}} · {{Tab3}} · {{Tab4}}" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor=#e0e0e0;fontSize=11;" vertex="1" parent="SWIMLANE_ID"><mxGeometry x="0" y="804" width="375" height="56" as="geometry" /></mxCell>`
   - 并将该 swimlane 的 bg 元素 height 改为 654（确保不覆盖底栏区域）

### 三轮精修（文件写入后自动执行，不得跳过）

▶ 第一轮 — 字段完整性精修
Read 已写入的 drawio_[模块英文名]_tmp.xml，逐 swimlane 对照需求文档对应章节：
- 用 Grep 搜索 `字段一\|字段二\|字段三\|InputA\|选项1\|列表项\d\|搜索框\|主按钮` → 发现则用 Edit 替换为真实字段名
- 表单 swimlane：检查每个字段是否有对应 Label mxCell + Input mxCell，缺少则 Edit 追加
- 列表 swimlane：检查是否有 ≥3 行数据行且每行每列是独立 mxCell，不足则 Edit 补充

▶ 第二轮 — 内容真实性精修
继续读取文件，检查并修复：
- 用 Grep 抽查 value 属性，检查是否有多条完全相同的数据行（如价格/规格完全一致）→ 用 Edit 修改为各不相同的真实示例数据
- 检查是否有 style 含 `rounded=1` 但内部无子 mxCell 的空容器 → 删除空容器或补充内容 mxCell
- 检查标注区文字（style 含 `fontColor=#9e9e9e`）的 x 坐标是否进入 UI 区 → 修正 x 坐标

▶ 第三轮 — tooltip 和跳转完整性精修
- Grep 提取所有 style 含 `fillColor=#1e88e5`（主按钮）的 mxCell，检查是否有 tooltip 属性
- 缺少 tooltip 的主按钮：根据【页面跳转关系】用 Edit 追加 `tooltip="→ 目标模块/目标页面"` 属性
- 检查每个 swimlane 标注区顶部是否有页面说明卡片（含页面/用途/角色/主操作/跳转去向）→ 缺少则追加
