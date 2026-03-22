# 执行状态文件格式

写入 `WORK_DIR/执行状态.md` 时使用以下格式：

```markdown
# 执行状态

| 项目 | 内容 |
|------|------|
| 产品名称 | [产品名称] |
| OUTPUT_FORMAT | html / drawio |
| DOC_MODE | single（单文件）/ split（分拆，模块数>3） |
| WORK_DIR | [绝对路径] |
| 整体状态 | 进行中 / 已完成 |
| 最后更新 | [时间] |

## Step 完成状态

| Step | 状态 | 输出文件 |
|------|------|----------|
| Step 1 | ✅ 完成 | RountMap.md |
| Step 2 | ✅ 完成 | 角色设定 |
| Step 3 | ✅ 完成 | 竞品分析报告.md |
| Step 4 | 🔄 进行中 | 单文件：requirements/详细需求文档.md / 分拆：requirements/index.md + requirements/详细需求文档_overview.md + requirements/详细需求文档_[模块名].md |
| Step 5 | ⏳ 待执行 | - |
| Step 6 | ⏳ 待执行 | - |

## Step 5 Agent 状态（Step 5 开始后填写）

| Agent | 模块 | 状态 | 输出文件 |
|-------|------|------|----------|
| Agent 1 | [模块名] | ✅ 完成 | [文件列表] |
| Agent 2 | [模块名] | ❌ 失败 | - |

## Spec 版本记录（draw.io 模式，5-3A 完成后填写）

| 版本 | 时间 | 模块 | swimlane 数 | 变更原因 | page_spec 文件 |
|------|------|------|------------|---------|---------------|
| v1 | [时间] | [模块名] | [N] | 初始生成 | page_spec_[英文名].md |
| v2 | [时间] | [模块名] | [N] | [修复原因，如：缺失字段] | page_spec_[英文名].md |

## Step 6 迭代记录

| 轮次 | 改进内容摘要 |
|------|-------------|
| 第 1 轮 | [摘要] |
```
