# Step 5 阶段 5-3：并行启动 subagent（draw.io 两阶段架构）

本文件仅在 OUTPUT_FORMAT=drawio 时加载。
draw.io 生成分为两个独立阶段：
- 阶段 A（规格化）：业务决策层
- 阶段 B（渲染）：格式转换层

---

**架构说明：**
- 阶段 A（规格化）：业务决策层——读取需求文档，确定每个页面的 UI 元素、字段内容、坐标，输出结构化的 `page_spec_[模块英文名].md`
- 阶段 B（渲染）：格式转换层——读取 page_spec + 样式字典，纯机械地将每行转换为 `<mxCell>` XML，输出 `drawio_[模块英文名]_tmp.xml`

**优势：** 规格化和渲染职责分离，渲染 Agent 不做任何业务判断，消除坐标计算错误和占位符内容问题。

---

## 阶段 5-3A：并行启动规格化 Agent

Read `SKILL_DIR/steps/step5-spec-agent-prompt.md` 获取规格化 Agent 提示词模板。

**分模块规则：**
- 一个功能模块 → 一个规格化 Agent
- **模块粒度必须符合 step5-common.md 的硬限制**：每模块 ≤ 2 个业务实体，≤ 6 个 swimlane，≤ 2 个列表页
- ⚠️ 若阶段 5-1 分组结果中存在 > 2 个列表页的模块，**必须在启动 Agent 前先拆分模块**
- 单模块页面数（含 CRUD 弹窗 swimlane）> 4 时拆分为 2 个 Agent（每个负责 ≤ 4 页，Codex 建议 ≤ 2 页）
- 最多同时启动 **6 个并行 Agent**

**占位符替换清单：**

| 占位符 | 替换为 |
|--------|--------|
| `[SKILL_DIR]` | `/Users/xxx/.claude/skills/prototype-generator` |
| `[WORK_DIR]` | 用户确认的工作目录绝对路径 |
| `[模块名]` / `[模块英文名]` | 当前模块的中文名 / 英文名 |
| `[页面名称N]` / `[章节名]` | 具体页面名 / 对应需求文档章节 |
| `[对象名]` | 该模块管理的业务对象（如「用户」「订单」） |
| `[CRUD 页面清单]` | 从阶段 5-2 CRUD 完整性检查结果中提取，格式：`- [列表页名] → 需要：新增/编辑[对象名]弹窗 + 删除确认弹窗`；若该模块无 CRUD 操作则填 `无 CRUD 操作` |
| `[需求文档读取指令]` | **单文件模式**：`Read [WORK_DIR]/requirements/详细需求文档.md 中以下章节`<br>**分拆模式**：`先 Read [WORK_DIR]/requirements/详细需求文档_overview.md（获取用户角色 §2 和枚举值字典 §5.5）；再 Read [WORK_DIR]/requirements/详细需求文档_[模块中文名].md 中以下章节` |

**Claude Code：**

```
# 所有规格化 Agent 必须在同一响应中并行启动
Agent(prompt="...模块1 规格化 prompt（所有占位符已替换）...", run_in_background=True)
Agent(prompt="...模块2 规格化 prompt（所有占位符已替换）...", run_in_background=True)
...  # 所有规格化 Agent 在同一响应中并行启动
```

> Codex 环境请参考 `SKILL_DIR/steps/codex-rules.md`。

**熔断规则（同后续渲染阶段）：** 失败 Agent 数 > 50% → 停止，告警用户选择重试/忽略/中止。

---

## ⚠️ page_spec 格式验证（Spec 冻结确认前必须通过）

所有规格化 Agent 完成、熔断检查通过后，**在展示规格摘要前，必须先验证所有 page_spec 文件的格式和元素数量**：

### 格式完整性检查

逐一读取所有 `page_spec_*.md` 文件，验证：

1. **必需表格标题存在：**
   ```bash
   grep -q "## swimlane 布局" page_spec_*.md
   grep -q "## 元素列表" page_spec_*.md
   ```

2. **元素列表行数统计：**
   ```bash
   grep -c "^| [0-9]" page_spec_*.md
   ```

3. **最低元素数量要求：**
   - 移动端列表页：≥ 35 行
   - 移动端表单页：≥ 30 行
   - Web 列表页：≥ 50 行
   - Web 表单页：≥ 35 行
   - Dashboard/数据看板：≥ 40 行
   - 移动端首页/商城首页：≥ 45 行

4. **CRUD 弹窗 swimlane 检查：**
   对每个 page_spec 文件，检查列表类 swimlane 是否有对应的 modal swimlane：
   - 从元素列表中查找含 btn_sm（编辑按钮）或 btn_sm_danger（删除按钮）的 swimlane
   - 检查同一 page_spec 中是否存在对应的 type=modal swimlane（新增/编辑弹窗 + 删除确认弹窗）
   - 若列表 swimlane 有编辑/删除按钮但无对应 modal swimlane → 标记 CRUD_INCOMPLETE

### 格式错误判定

若文件满足以下任一条件，标记为 ❌ SPEC_INVALID：
- 不包含 "## 元素列表" 标题
- 元素列表行数不足最低要求
- 文件内容为描述性文字（如 `- 顶部：标题"xxx"，右侧消息图标`）而非表格
- 标记为 CRUD_INCOMPLETE（列表页有编辑/删除按钮但缺少弹窗 swimlane）

### 重试策略

标记为 SPEC_INVALID 的模块，**不进入 Spec 冻结确认**，立即重新启动该模块的规格化 Agent，在 prompt 末尾追加：

```
⚠️ 警告：上次输出格式错误（描述性文字而非坐标表格）。

本次必须严格按照 page_spec 表格格式输出：
- 必须包含 "## swimlane 布局" 和 "## 元素列表" 两个表格
- 每行一个 mxCell 元素，包含 id/parent/value/x/y/w/h/style_key 列
- 禁止输出描述性文字（如"- 轮播区：3张图"）
- 移动端列表页最少 25 行，Web 列表页最少 35 行

参考正确格式示例（见 step5-spec-agent-prompt.md 中的"完整业务示例"）。
```

### 验证通过标准

仅当所有模块 page_spec 均为 ✅ VALID 时，才进入下一步 Spec 冻结确认流程。

---

## ⚠️ Spec 冻结确认（5-3A 与 5-3B 之间的强制等待）

所有规格化 Agent 完成、熔断检查通过、**page_spec 格式验证通过**后，**必须向用户展示规格摘要并等待确认，禁止自动进入渲染阶段**：

```
=== Spec 冻结确认 ===
规格化已完成，共 N 个模块，M 个 swimlane：

| 模块     | swimlane 清单                          | 类型   | 预计元素数 | page_spec 文件           |
|----------|----------------------------------------|--------|-----------|--------------------------|
| 用户模块 | 登录页、用户列表页、新增/编辑弹窗、删除确认弹窗 | 移动端 | ~45       | page_spec_user.md        |
| 商品模块 | 商品列表页、商品详情页、新增/编辑弹窗           | 移动端 | ~38       | page_spec_product.md     |

请确认规格后，启动渲染：
- 回复"确认"：开始并行渲染（启动 N 个渲染 Agent）
- 回复"查看 [模块名]"：展示对应 page_spec 文件内容
- 回复"修改 [模块名] [说明]"：先修改 page_spec，再渲染
- 回复"取消"：停止流程
```

**收到用户明确回复"确认"后，才能进入阶段 5-3B。**

同时将此次规格摘要写入 `WORK_DIR/执行状态.md` 的"Spec 版本记录"表格（格式见 SKILL.md 中的执行状态文件格式）。

---

## 阶段 5-3B：渲染（脚本自动化）

所有规格化 Agent 完成后，确认每个模块的 `page_spec_[模块英文名].md` 均已写入 `WORK_DIR`，然后用脚本渲染。

**⚠️ 渲染不再使用 subagent，改为调用 Python 脚本，零 token 消耗。**

**执行方式：** 所有模块的渲染命令**必须在同一响应中并行启动**（`run_in_background=true`），禁止逐个串行等待：

```bash
python3 SKILL_DIR/scripts/render.py \
  SKILL_DIR/steps/step5-component-styles.md \
  WORK_DIR/page_spec_[模块英文名].md \
  WORK_DIR/drawio_[模块英文名]_tmp.xml
```

**Claude Code 示例（并行启动）：**
```
# 所有 Bash 调用在同一响应中发出，并行执行
Bash("python3 .../render.py ... page_spec_user.md ... drawio_user_tmp.xml", run_in_background=True)
Bash("python3 .../render.py ... page_spec_order.md ... drawio_order_tmp.xml", run_in_background=True)
Bash("python3 .../render.py ... page_spec_product.md ... drawio_product_tmp.xml", run_in_background=True)
# 然后用 TaskOutput 等待所有完成
```

> 脚本自动完成：样式字典查找 → XML 生成 → 坐标 8 倍数校验修正 → 特殊字符转义。
> 若 page_spec 中有未知 style_key，脚本会输出警告并降级为 `text_default`。
