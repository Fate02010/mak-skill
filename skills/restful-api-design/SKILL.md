---
name: restful-api-design
description: |
  根据产品资料自动生成 RESTful 接口文档的完整工作流，输出包含出入参、幂等性标注、错误码的标准接口文档。当用户想要：
  - 根据产品文档/PRD/需求资料设计 REST 接口
  - 生成接口文档 / API 文档 / 接口设计文档
  - 设计 API / 设计接口 / 接口规范
  - 说"帮我设计接口"、"生成接口文档"、"API设计"、"接口设计"时
  - 说"生成REST接口"、"生成RESTful文档"、"接口规范文档"时
  - 说"API文档"、"接口说明"、"接口清单"、"接口列表"时
  请务必使用此 skill。
---

# RESTful 接口文档生成工作流

你是一位经验丰富的后端架构师。当用户提供产品资料后，按以下工作流生成标准 RESTful 接口文档。

**关键机制：** 每个 Step 的详细指令存放在 `steps/` 目录下，执行到对应 Step 时用 `Read` 工具加载。`SKILL_DIR` 指本 skill 所在目录。

## 第零步：确认工作目录（WORK_DIR）

**必须主动询问用户：**

```
所有生成文件（RountMap.md、接口文档.md、临时模块文件等）将保存在同一目录下。
请指定保存目录，或直接回复"当前目录"使用默认路径。
```

- 用户指定路径 → 使用该路径
- 用户回复"当前目录"或未指定 → `Bash: pwd` 获取，再告知用户实际路径

**确认后** 将路径记为 `WORK_DIR`，**所有后续步骤和子 Agent 必须使用此绝对路径，严禁写入 `/private/tmp` 或任何系统临时目录。**

确认后检查是否已存在 `接口文档.md`：不存在 → 全量模式从 Step 1 开始；已存在 → 询问用户选择增量（Step 6）或重新生成。

## 执行计划与进度

启动后**立即**用 `TaskCreate` 为 Step 1-5 各创建一个任务，展示：

```
=== RESTful 接口设计执行计划 ===  工作目录：[WORK_DIR]
[ ] Step 1 扫描资料 → RountMap.md
[ ] Step 2 生成架构师 prompt → 设定角色
[ ] Step 3 识别接口清单 → 拆分任务 → 用户确认
[ ] Step 4 并行生成接口文档
[ ] Step 5 汇总审视 → 改进建议
即将开始，按任意内容继续，或回复"取消"退出。
```

每个 Step 开始时 `TaskUpdate` 标记 `in_progress`，完成后标记 `completed`。

## 按需加载指令

| Step | 指令文件 | 说明 |
|------|---------|------|
| 1 | `SKILL_DIR/steps/step1-scan.md` | 扫描资料，生成 RountMap.md |
| 2 | `SKILL_DIR/steps/step2-api-prompt.md` | 生成 API 架构师 prompt，设定角色 |
| 3 | `SKILL_DIR/steps/step3-split-tasks.md` | 识别全部接口，拆分模块任务 |
| 4 | `SKILL_DIR/steps/step4-generate-docs.md` | 并行生成各模块接口文档 |
| 5 | `SKILL_DIR/steps/step5-review.md` | 汇总、审视、改进建议 |
| 6 | `SKILL_DIR/steps/step6-incremental.md` | 增量新增或修改接口 |

接口规范（每个生成子任务必须加载）：`SKILL_DIR/steps/api-spec.md`
接口文档格式（每个生成子任务必须加载）：`SKILL_DIR/steps/api-doc-format.md`

## 输出文件

```
WORK_DIR/
├── RountMap.md       ← Step 1
├── 接口文档.md       ← Step 4 生成，Step 5/6 按需更新
└── api_task_list.md  ← Step 3 生成（任务清单，临时文件）
```

## 强制交互点（每处必须等待用户回复）

第零步确认 WORK_DIR → Step 1 确认文件分级 → Step 2 确认架构师角色 → Step 3 确认接口清单和任务分组 → Step 5 确认改进建议

> **接口规范是基准：** URL 必须含版本号（`/api/v1/mobile/*` 或 `/api/v1/admin/*`），所有接口必须标注幂等性，出入参使用表格 + JSON 示例双格式展示。
