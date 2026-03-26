# Step 5 阶段 5-3：并行启动 subagent（draw.io 强约束架构）

本文件仅在 `OUTPUT_FORMAT=drawio` 时加载。

draw.io 统一改为四段链路：

`page_model -> build_page_spec.py -> render.py -> validate.py`

目标是压缩模型自由度，缩小 Claude 与 Codex 的结构差异。

> **200K 预算规则：** 面向 `Codex 5.4 Medium / 200K`，draw.io 阶段默认只允许把 `overview` 关键章节、当前模块 `module_brief`、当前模块详细文档必要章节放进同一个子任务。若 prompt 还想附带第二个模块文档，必须拆任务。

---

## 启动前完成标准确认（不可跳过）

在任何 draw.io 子任务启动前，主进程必须先完成以下动作：

1. 读取 `WORK_DIR/.prototype-generator/原型DoD.md`
2. 读取 `WORK_DIR/.prototype-generator/drawio-完成标准.md`
3. 若处于分拆模式，读取 `WORK_DIR/requirements/index.md`、`WORK_DIR/requirements/详细需求文档_overview.md` 与 `WORK_DIR/requirements/module_briefs/模块摘要_[模块中文名].md`
3. 用简洁摘要向用户确认本次 draw.io 任务的完成定义：
   - 最终交付物路径
   - 模块数 / 预计 swimlane 数
   - validate.py 通过门槛
   - merge.py 合并成功门槛
   - “发现问题即修复并重新验收”这一条是否已纳入完成标准

**如果以上任一项还没定义清楚，禁止启动生成。**
**如果已触发默认强制压缩模式但缺少 `module_brief`，禁止启动生成。**

若用户已授权自治模式：
- 无需在本阶段再次等待确认
- 主进程必须将完成标准写入 `WORK_DIR/.prototype-generator/drawio-完成标准.md`
- 后续默认进入“真实产物自迭代闭环”，直到通过或达到 5 轮熔断

> 判断原则：draw.io 任务不是“产出 XML 就算完成”，而是“脚本链路跑通、校验通过、DoD 通过、最终文件可交付”才算完成。

---

## 阶段 A：page_model 语义建模

读取：
- `SKILL_DIR/steps/page-model-spec.md`
- `SKILL_DIR/steps/step5-spec-agent-prompt.md`
- 分拆模式下按 `index.md -> overview -> module_brief -> 模块详细文档` 顺序读取；优先用 `module_brief` 完成页面语义建模，仅在需要字段明细、复杂校验或状态流转时再回读模块详细文档

### 子任务输出

- `WORK_DIR/.prototype-generator/page_models/page_model_[模块英文名].json`

### 硬约束

1. 一个子任务最多 2 个真实页面
2. 子任务禁止输出 `page_spec`
3. 子任务禁止输出 XML
4. 子任务不负责坐标、骨架、CRUD 弹窗细节

### 新增强约束：先判 `page_archetype`

在输出 `page_model` 之前，子任务必须先为每个页面确定 `page_archetype`，类型集合以 `drawio-spec.md` 为准。

禁止：
- 不写 `page_archetype`
- 一个页面同时使用多个 archetype
- 将 `dashboard`、`detail_kv`、`drawer_permission`、`dispatch_board` 偷换成 `list_table`

若页面类型无法明确，必须回读需求文档补判断，禁止直接生成通用列表页。

### 并行规则

- 一个功能模块拆成若干 `page_model` 子任务
- 子任务按批次并行启动，每批最多 3 个，再统一等待本批结果
- 若某模块页面 > 2，必须先拆分后再启动
- 该并发上限 3 是 draw.io 全链路统一上限；后续 render / validate / merge 前检查也不得突破

### 成功标准

- JSON 可解析
- 顶层包含 `module_name`、`module_key`、`pages`
- `pages` 数组非空
- 页面类型全部合法
- 子任务读取集合仍符合 `index -> overview -> module_brief -> 1 个模块详细文档` 的预算上限

---

## 阶段 B：构建标准 page_spec

先确保目录存在：

```bash
mkdir -p WORK_DIR/.prototype-generator/page_models WORK_DIR/.prototype-generator/page_specs WORK_DIR/.prototype-generator/tmp
```

**固定目录规则：**

- 所有 `page_spec_*.md` 必须写入 `WORK_DIR/.prototype-generator/page_specs/`
- `WORK_DIR` 根目录或 `WORK_DIR/page_specs/` 下出现新的 `page_spec_*.md` 视为流程错误，不得继续进入 render
- 即使脚本调用者误把输出路径写成 `WORK_DIR/page_spec_xxx.md` 或 `WORK_DIR/page_specs/page_spec_xxx.md`，也必须自动收敛到 `WORK_DIR/.prototype-generator/page_specs/page_spec_xxx.md`

对每个模块执行：

```bash
python3 SKILL_DIR/scripts/build_page_spec.py \
  WORK_DIR/.prototype-generator/page_models/page_model_[模块英文名].json \
  WORK_DIR/.prototype-generator/page_specs/page_spec_[模块英文名].md
```

### 脚本负责

- 套统一页面骨架
- 应用统一 8pt 坐标
- 自动补 CRUD 弹窗
- 自动补新增/编辑/删除按钮
- 自动展开 5 行列表数据
- 自动补 annotation_card
- 按 `page_archetype` 选择页面模板，而不是按页面名自由发挥

### 页面模板选择规则

- `dashboard`：必须套工作台模板
- `detail_kv`：必须套详情模板
- `modal_form`：必须套表单弹窗模板
- `drawer_permission`：必须套授权抽屉模板
- `dispatch_board`：必须套发货/调度模板
- `tree_manage`：必须套树/层级管理模板

禁止：
- 用通用列表模板兜底所有后台页面
- 用“新增/编辑通用弹窗”兜底角色授权、复杂商品编辑、订单详情

### 不通过即中断

若 `build_page_spec.py` 报错，该模块不得进入 render 阶段。

---

## 阶段 C：render 渲染

render 阶段只允许读取：

- `WORK_DIR/.prototype-generator/page_specs/page_spec_[模块英文名].md`
- `SKILL_DIR/steps/step5-component-styles.md`
- `WORK_DIR/.prototype-generator/原型任务清单.md`
- 导航/跳转映射

禁止回读原始资料、PRD、竞品文档、需求文档原文。

```bash
python3 SKILL_DIR/scripts/render.py \
  SKILL_DIR/steps/step5-component-styles.md \
  WORK_DIR/.prototype-generator/page_specs/page_spec_[模块英文名].md \
  WORK_DIR/.prototype-generator/tmp/drawio_[模块英文名]_tmp.xml
```

规则：

- 所有模块渲染命令按批次发出，每批最多 3 个
- render 报错的模块不得进入 merge

---

## 阶段 C.5：规格覆盖率与一致性门禁

在任何模块进入 merge 之前，主进程必须执行：

```bash
python3 SKILL_DIR/scripts/check_prototype_consistency.py \
  WORK_DIR/requirements \
  WORK_DIR/.prototype-generator/page_specs \
  --json
```

门禁规则：

- `missing_pages` 非空：必须回退到 `page_model` 或更上游补页
- `missing_field_pages` 非空：必须回退到 `page_specs` 补字段
- `low_coverage_pages` 非空：不得进入最终交付
- 只有脚本返回 0，才允许继续 merge

---

## 阶段 D：自动验收与重建

对每个模块执行：

```bash
python3 SKILL_DIR/scripts/validate.py WORK_DIR/.prototype-generator/tmp/drawio_[模块英文名]_tmp.xml --json
```

### 通过门槛

- `FAIL = 0`
- 不允许触发 `C10 CRUD闭环`
- 不允许触发 `C11 占位词残留`
- 通过结果必须回写到 `WORK_DIR/.prototype-generator/drawio-完成标准.md` 或 `WORK_DIR/.prototype-generator/原型DoD.md` 的对应勾选项

### 自动重建规则

遇到以下问题，禁止直接 patch XML，必须回到 `page_model` 重建：

- 页面缺失
- 页面类型错误
- `C13 页面类型降级`
- `C10 CRUD闭环`
- `C11 占位词残留`
- 明显骨架错误

仅以下问题允许保留 `page_model`，重跑构建或轻微调 `page_spec`：

- `C5 坐标对齐`
- 少量 annotation 偏移
- 分页/按钮间距轻微不齐

---

## 自治模式：真实产物自迭代闭环

当用户已授权自治模式时，draw.io 主流程必须按以下顺序执行，且每轮都基于真实 `WORK_DIR/prototypes/[产品名称].drawio` 复测：

`page_model -> build_page_spec.py -> render.py -> check_prototype_consistency.py -> validate(tmp) -> merge.py -> validate(final) -> visual review -> failure routing -> next round`

默认不要手工拼装这条链路，直接运行：

```bash
python3 SKILL_DIR/scripts/run_autonomous_pipeline.py WORK_DIR [产品名称] --format drawio --json
```

### 每轮固定动作

1. 用 `scripts/run_drawio_pipeline.py` 或等价主进程脚本生成真实 `.drawio`
2. 读取一致性报告与模块级 / 最终级 `validate.py` 结果
3. 对最终 `.drawio` 做视觉分析，至少检查：
   - 登录页是否有越界或骨架混入
   - 列表页是否缺少操作列按钮、分页是否只在底部
   - 详情页 / 授权页是否有状态区、记录区、规则区
4. 将失败页映射回上游责任层级：
   - `page_model`：缺页、错误 archetype、按钮语义缺失、字段遗漏、状态遗漏
   - `page_spec`：骨架错位、分组顺序、分页位置、局部间距
   - `render/merge`：重复 ID、XML 结构、合并后 diagram 丢失
5. 仅重建受影响模块；禁止整包无差别重跑，除非 merge 或全局规则损坏

### 熔断与收敛

- 最大自迭代轮次：5
- 任一轮只要最终 `.drawio` 仍有 FAIL，即视为本轮未完成，必须继续回到上游修复
- 连续 2 轮命中同一失败页且同一规则不下降时，必须上提一个回退层级
  - 例如：先改 `page_spec` 无效，则回退到 `page_model`
- 达到第 5 轮仍未通过时，输出剩余阻塞项与当前最小复现路径，再结束

### 临时文件

- 中间文件统一放在 `WORK_DIR/.prototype-generator/`
- 每轮结束后清理本轮无用的 `tmp` / `review_tmp` / 临时 HTML 对比稿
- 最终只保留：
  - 最新 `page_models/`
  - 最新 `page_specs/`
  - 必要的 `执行状态.md`、`drawio-完成标准.md`
  - 最终 `prototypes/[产品名称].drawio`

---

## Claude / Codex 差异量化

若存在 Claude 基线文件，可执行：

```bash
python3 SKILL_DIR/scripts/compare_drawio.py \
  WORK_DIR/prototypes/claude_baseline.drawio \
  WORK_DIR/prototypes/[产品名称].drawio \
  --json
```

解释：

- `diff_score <= 5`：达到目标
- `diff_score > 5`：继续拆小模块，或修订 page_model

## 无 Claude 基线时的完成定义

如果项目中没有 Claude 或其他高质量基线文件，draw.io 阶段必须改用以下门槛：

1. `validate.py` 最终结果 `FAIL = 0`
2. 不允许触发：
   - `C10 CRUD闭环`
   - `C11 占位词残留`
   - `C13 页面类型降级`
3. `原型DoD.md` 中页面完整性、闭环、内容真实性全部满足
4. 至少人工抽查 3 类不同 archetype 页面：
   - `dashboard`
   - `list_table`
   - `detail_kv` 或 `drawer_permission`

> 没有外部基线时，`drawio-spec.md + validate.py + 原型DoD.md` 就是唯一完成标准。

---

## 合并

全部模块通过验收后：

```bash
python3 SKILL_DIR/scripts/merge.py \
  WORK_DIR/prototypes/[产品名称].drawio \
  [产品名称] \
  --glob WORK_DIR/.prototype-generator/tmp/drawio_*_tmp.xml
```

合并完成后，必须立刻再对最终文件执行一次：

```bash
python3 SKILL_DIR/scripts/validate.py WORK_DIR/prototypes/[产品名称].drawio --json
```

只有当最终 `.drawio` 文件也满足以下条件时，任务才算真正完成：
- validate 结果 `FAIL = 0`
- `C13 页面类型降级 = 0`
- `WORK_DIR/.prototype-generator/原型DoD.md` 全部条目通过
- `WORK_DIR/.prototype-generator/drawio-完成标准.md` 全部条目通过
- 已向用户报告最终产物路径和复测结果
- 若本轮同时修改了 skill 脚本或模板，还必须补充并运行 `python3 -m unittest discover -s tests -p 'test_*.py' -v`；任一测试失败都必须返回脚本层继续修复
