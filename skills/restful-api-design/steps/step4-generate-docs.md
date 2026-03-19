# Step 4：并行生成接口文档

**目标：** 按任务清单分模块并行生成接口文档，最后合并为完整的 `接口文档.md`。

## 阶段 4-1：判断生成方式

读取 `WORK_DIR/api_task_list.md`：

- **接口数 ≤ 8（单任务）**：顺序生成，直接写入 `接口文档.md`
- **接口数 > 8（多任务）**：并行生成，每任务输出独立临时文件后合并

## 阶段 4-2A：顺序生成（接口数 ≤ 8）

1. Read `SKILL_DIR/steps/api-spec.md` 获取接口规范
2. Read `SKILL_DIR/steps/api-doc-format.md` 获取文档格式
3. 读取 `WORK_DIR/RountMap.md` 和核心资料
4. 按接口清单顺序逐个生成，写入 `WORK_DIR/接口文档.md`

> **输出约束：** 接口文档内容只写入文件，禁止在控制台输出文档正文。每完成一个接口只输出一行进度：`✅ [Method] [URL] 完成`

## 阶段 4-2B：并行生成（接口数 > 8）

### 步骤一：展示并行执行计划，等待用户确认

```
=== 接口文档并行生成计划 ===

共 [N] 个接口，拆分为 [M] 个并行任务同时执行：

Agent 1 │ 商品模块（mobile 端）
        │ 接口：GET /api/v1/mobile/products，GET /api/v1/mobile/products/{id}，...
        │ 共 4 个接口，输出：api_product_mobile.md

Agent 2 │ 商品模块（admin 端）
        │ 接口：GET /api/v1/admin/products，POST /api/v1/admin/products，...
        │ 共 3 个接口，输出：api_product_admin.md

Agent 3 │ 订单模块
        │ 接口：POST /api/v1/mobile/orders，GET /api/v1/mobile/orders，...
        │ 共 5 个接口，输出：api_order.md

是否确认并启动？（回复"确认"）
```

### 步骤二：启动并行 Agent

> **重要：** 启动前必须将 prompt 中的所有占位符替换为实际值：
> - `[SKILL_DIR]` → skill 所在绝对路径（如 `/Users/xxx/.claude/skills/restful-api-design`）
> - `[WORK_DIR]` → 第零步确认的绝对路径（如 `/Users/xxx/project`），**禁止使用 `/private/tmp` 或任何系统临时目录**
> - `[产品名称]`、`[模块名称]`、`[模块英文名]` → 实际名称
> - 接口列表 → 展开为具体的 `[Method] [URL]：[说明]` 列表

每个 Agent 使用以下 prompt 模板（替换所有占位符后启动）：

```
你是 [产品名称] 的 API 架构师（来自 Step 2 的角色设定）。

任务：生成 [模块名称] 的接口文档

工作目录（所有文件必须写入此路径）：[WORK_DIR 的实际绝对路径]

请按顺序执行：
1. Read `[SKILL_DIR 的实际绝对路径]/steps/api-spec.md`（必须，获取接口规范）
2. Read `[SKILL_DIR 的实际绝对路径]/steps/api-doc-format.md`（必须，获取文档格式）
3. Read `[WORK_DIR 的实际绝对路径]/RountMap.md`，找到 [模块名称] 相关核心资料文件路径
4. 读取相关资料文件，理解业务需求和数据对象
5. 按规范生成以下接口的完整文档：
   - [Method] [URL]：[说明]
   - [Method] [URL]：[说明]
   ...
6. 写入 `[WORK_DIR 的实际绝对路径]/api_[模块英文名].md`

约束：
- 所有文件只能写入上方指定的工作目录，严禁写入 /private/tmp 或任何系统临时目录
- URL 必须含版本号 /api/v1/
- 每个接口必须标注幂等性
- 出入参使用表格 + JSON 示例双格式
- 遵循统一响应结构 { code, message, traceId, data }
- 完成后输出：✅ [模块名] 完成，共 N 个接口
```

**Claude Code（Agent 工具）：** 单次响应内同时调用所有 Agent 工具

**Codex（Task 工具 + run_in_background）：**
```
task_1 = Task(prompt="...Agent 1 完整 prompt...", run_in_background=true)
task_2 = Task(prompt="...Agent 2 完整 prompt...", run_in_background=true)
...
result_1 = TaskOutput(task_id=task_1.id, block=true)
result_2 = TaskOutput(task_id=task_2.id, block=true)
...
```

### 步骤三：跟踪进度

```
  ⏳ Agent 1 │ 商品模块 mobile（生成中...）
  ✅ Agent 2 │ 商品模块 admin（已完成，3 个接口）
  ⏳ Agent 3 │ 订单模块（生成中...）
```

若某任务失败，记录后继续等待其他任务，最后统一补充。

## 阶段 4-3：合并接口文档

所有子任务完成后，按模块顺序合并为 `WORK_DIR/接口文档.md`：

**文件头：**
```markdown
# [产品名称] RESTful 接口文档

| 项目 | 内容 |
|------|------|
| 产品名称 | [产品名称] |
| 文档版本 | v1.0 |
| 生成时间 | [日期] |
| 接口总数 | [N] 个 |
| 基础 URL | /api/v1 |

---
```

合并顺序：移动端模块 → 管理端模块，模块内按功能重要性排序。

合并完成后删除临时文件（`api_*.md`，`api_task_list.md` 保留供参考）。
