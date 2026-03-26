# Codex 环境专有规则

> 本文件仅在 Codex 环境中加载，Claude Code 环境无需读取。

---

## 运行环境声明

当前 Codex 环境以实际可用工具为准，不再使用历史文档中的 `Task` / `TaskOutput` / `Read` / `Glob` / `Edit` / `Bash` 术语。

### Codex 5.4 Medium 上下文预算

默认按 `Codex 5.4 Medium / 200K` 设计：
- 不按 200K 满额拼 prompt；主流程必须保留 `30%~40%` 余量给链式推理、工具输出和修复回合
- 单个子任务的默认读取上限是：`requirements/index.md + overview 关键章节 + 1 个 module_brief + 1 个模块详细文档 + 当前 page_spec`
- 若一个 prompt 需要第二个模块详细文档，先停止并把跨模块依赖压缩回 `overview` 或 `module_brief`，再继续
- 禁止把“整份 requirements 目录逐文件读一遍”当常规做法；读取必须基于当前模块和当前阶段最小化

| 能力 | Codex 当前做法 |
|------|----------------|
| 文件读取 | 用 `exec_command` 执行 `sed` / `rg` / `ls` / `find` 等命令读取文件与目录 |
| 并行子任务 | 用 `spawn_agent` 启动子 agent，必要时用 `wait_agent` 收集结果 |
| 并行 shell | 用 `multi_tool_use.parallel` 并行发出多个 `exec_command` |
| 文件编辑 | 用 `apply_patch` 修改文件 |
| 进度计划 | 用 `update_plan` 维护步骤状态 |

**识别方式：**
- 当前会话可用 `spawn_agent`、`wait_agent`、`exec_command`
- 不要假设存在 `Task` / `TaskOutput`

---

## Codex 必须遵守的并行规则

1. **独立写作任务优先使用 `spawn_agent`**：Step 4 模块需求文档、Step 5 HTML 页面、Step 5 draw.io 规格化，均可按模块拆给子 agent。
2. **子 agent prompt 必须自包含**：所有路径都写成绝对路径，不依赖父会话变量。
3. **并发上限**：任一时刻最多只允许 3 个子 agent 同时运行；任务数超过 3 时必须分批启动。
4. **等待策略**：每批子任务全部启动后统一 `wait_agent`，不要边启动边等待；上一批完成后再启动下一批。
5. **shell 并行只用于互不写同一文件的命令**：例如多个 `render.py` 渲染命令可以并行；同一文件的连续修改不可并行。
6. **熔断规则**：并行子任务失败数超过 50% 时暂停，并提示用户选择重试或中止。
7. **模块粒度预检**：创建子任务前，先按 `step5-common.md` 的业务域限制拆好模块，避免单个子任务承担过多页面。
8. **上下文预算预检**：发起子任务前先判断该 prompt 是否已经包含 `overview + module_brief + detail` 的必要最小集合；若还能再删文件或删章节，必须先删再发。

---

## Step 4 需求文档并行生成

大型项目需求文档拆分时：

1. 主进程先生成 `requirements/详细需求文档_overview.md`
2. 再按模块用 `spawn_agent` 分批并行生成各模块文档，每批最多 3 个
3. 每个模块文档完成后，必须继续生成 `requirements/module_briefs/模块摘要_[模块中文名].md`
4. 所有 agent 完成后，由主进程汇总并写入 `requirements/index.md`

**默认强制压缩模式触发条件：**
- 原始资料总内容 `> 3000` 行
- 模块数 `> 3`
- 功能点数 `> 12`
- 预计页面 / swimlane 数 `> 8`
- 终端数 `> 1`
- 关键角色数 `> 3`

一旦命中任一项，Step 4 不得继续生成单一合并大 PRD，必须改走 `overview + module_brief + 模块详细文档 + index`。
对 `Codex 5.4 Medium / 200K`，即便未明显命中阈值，只要判断单文件 PRD 会压缩掉后续推理空间，也必须提前走分拆模式。

**Codex 示例：**

```text
spawn_agent(agent_type="worker", message="负责 用户模块 需求文档 ...")
spawn_agent(agent_type="worker", message="负责 商品模块 需求文档 ...")
spawn_agent(agent_type="worker", message="负责 订单模块 需求文档 ...")
wait_agent(ids=[...], timeout_ms=300000)
# 若仍有剩余模块，再启动下一批，确保同时运行数不超过 3
```

成功标志统一为子 agent 最终输出含 `✅ [文件名] 完成`。

---

## Step 5 HTML 模式

HTML 模式按模块拆分为独立子任务：

1. 先由主进程准备共享文件，例如 `prototypes/common.css`
2. 每个子任务必须先冻结 `page_specs/page_spec_[模块英文名].md`
3. 再从 `page_spec` 渲染 HTML 页面，render 阶段不得回读原始资料或需求文档原文
4. 全部完成后，主进程执行 `check_prototype_consistency.py`、冒烟检查和缺失修复

分拆模式下，HTML 子任务的读取顺序必须是：
- 先读 `requirements/index.md`
- 再读 `requirements/详细需求文档_overview.md`
- 再读 `requirements/module_briefs/模块摘要_[模块中文名].md`
- 仅在需要字段明细、复杂校验、状态流转或失败处理时再读模块详细文档
- 单个 HTML 子任务禁止同时读两个模块详细文档；跨模块跳转信息优先从 `overview` 和 `module_brief` 提取

**建议容量：**
- 单个子任务负责 ≤ 4 页
- 单模块超过 6 页时拆分为多个子任务

---

## Step 5 draw.io 模式

draw.io 统一走强约束链路：

### 启动前门禁

- 主进程必须先生成并检查 `WORK_DIR/.prototype-generator/原型DoD.md`
- 主进程必须先生成并检查 `WORK_DIR/.prototype-generator/drawio-完成标准.md`
- 主进程必须先检查每个 `page_model.module_name` 是否为**最终 sheet 名**，不得带 `page_spec:` 前缀，不得是“后台-商品与内容”这类聚合命名
- 若“完成定义 / 交付前检查清单 / 最终 validate 门槛”任一未明确，Codex 不得启动 draw.io 子 agent

### 阶段 A：语义建模

- 用 `spawn_agent` 按模块分批并行生成 `.prototype-generator/page_models/page_model_[模块英文名].json`，每批最多 3 个子 agent
- 每个子任务负责 ≤ 2 个真实页面；超过则强制拆分
- 子任务只负责页面类型、字段、列表列、状态枚举、跳转、CRUD 标记
- 子任务输出必须直接写入 `WORK_DIR/.prototype-generator/page_models/page_model_[模块英文名].json`
- 分拆模式下，page_model 子任务必须先按 `requirements/index.md -> requirements/详细需求文档_overview.md -> requirements/module_briefs/模块摘要_[模块中文名].md -> 模块详细文档` 的顺序读取；优先依赖模块摘要完成语义建模
- 对 `200K` 预算，page_model 子任务应优先依赖 `module_brief` 完成 80% 以上判断；模块详细文档只补字段明细和复杂状态，不得整篇通读

### 阶段 B：构建与渲染

- 主进程先调用 `build_page_spec.py`
- 再调用 `render.py`
- 多个模块的 `build_page_spec.py` / `render.py` 命令可通过 `multi_tool_use.parallel` 并行执行

**Codex shell 示例：**

```text
exec_command(cmd="mkdir -p .../.prototype-generator/page_models .../.prototype-generator/page_specs .../.prototype-generator/tmp")
exec_command(cmd="python3 .../build_page_spec.py .../.prototype-generator/page_models/page_model_user.json .../.prototype-generator/page_specs/page_spec_user.md")
exec_command(cmd="python3 .../render.py .../step5-component-styles.md .../.prototype-generator/page_specs/page_spec_user.md .../.prototype-generator/tmp/drawio_user_tmp.xml")
```

补充强约束：

- `build_page_spec.py` 的输出路径必须显式指向 `WORK_DIR/.prototype-generator/page_specs/page_spec_[模块英文名].md`
- 若发现新生成的 `WORK_DIR/page_spec_[模块英文名].md` 或 `WORK_DIR/page_specs/page_spec_[模块英文名].md` 落在根目录侧，视为流程错误，必须修正路径后重跑
- render 阶段只允许读取 `WORK_DIR/.prototype-generator/page_specs/` 下的 page_spec，不得读取根目录历史文件

---

## 文件读取策略

Codex 中凡是历史文档写着 “Read 某文件 / 某章节”，都按下面方式执行：

- 整文件读取：`exec_command(cmd="sed -n '1,220p' <file>")`
- 章节定位：先用 `rg -n "^## |^### " <file>` 找行号，再用 `sed -n '<start>,<end>p'`
- 文件存在性检查：`test -f` / `test -d` / `rg --files`

不要在 Codex 环境里继续输出 “Read 工具”、“Glob 工具” 这类不存在的工具名。

---

## page_model 契约

Codex draw.io 模式统一先输出 `.prototype-generator/page_models/page_model_[模块英文名].json`：

- 契约文件：`SKILL_DIR/steps/page-model-spec.md`
- 新内容统一写 JSON，不再让子任务直接输出 `page_spec`
- `page_spec` 仅作为脚本生成的中间产物保留，供 render/修复使用

---

## 主进程验收（不可跳过）

所有子任务完成后，主进程必须完成以下快速验收：

1. **产出完整性**：检查任务清单中的每个模块是否都有对应 `.prototype-generator/page_models/page_model_*.json`
2. **page_model 校验**：确认 JSON 合法且页面数 ≤ 2
3. **构建前校验**：对每个模型执行 `build_page_spec.py`；脚本报错则不进入 render
4. **渲染后校验**：对每个 `.prototype-generator/tmp/drawio_*_tmp.xml` 执行 `validate.py`
5. **一致性门禁**：执行 `check_prototype_consistency.py WORK_DIR/requirements WORK_DIR/.prototype-generator/page_specs --json`
6. **自动重建**：若触发 `C10/C11`、`FAIL`、缺页、缺字段或低覆盖率，必须回到 `.prototype-generator/page_specs` 或 `.prototype-generator/page_models` 重建
7. **失败熔断**：失败数超过 50% 时暂停流程

---

## 特别注意事项

- 不要继续使用 `TaskOutput`、`run_in_background=true` 这种旧接口描述
- 不要让 Codex 手工排坐标、复制骨架、补 CRUD 弹窗
- 渲染阶段出现 `style_key` 缺失、空 `swimlane_label`、缺表头时，应直接报错，不要静默降级
- 新链路统一使用 `page_model -> build_page_spec -> render`
