---
name: prototype-generator
description: |
  从产品资料自动生成原型图的完整工作流（支持 HTML 交互原型 或 draw.io 线框图），也支持在已有原型基础上增量新增功能。当用户想要：
  - 根据产品文档/PRD/需求资料生成原型图
  - 把产品文件夹里的资料转化成 HTML 原型或 draw.io 线框图
  - 生成需求文档并配套生成交互原型
  - 为产品功能快速制作线框图/原型图/交互稿
  - 说"帮我生成原型"、"根据资料做原型"、"生成 HTML 原型图"时
  - 说"生成 draw.io"、"生成 drawio"、"生成线框图"、"drawio 原型"时
  - 说"做线框图"、"做交互稿"、"界面设计"、"页面设计"、"产品界面"时
  - 在已有原型上新增功能，说"新增XX功能的原型"、"帮我补充XX模块"、"加一个XX页面"时
  请务必使用此 skill。即使用户没有明确说"原型图"，只要提到要把产品资料/需求文档转化为可视化界面、线框图、交互稿，或在现有原型上新增功能，也应触发此 skill。
---

# Prototype Generator

这是一个给产品经理提供“一键上传资料并生成原型”体验的门面 Skill。
对 Codex 内部，必须拆成可门禁、可回退的流水线，禁止 `原始资料 -> 直接画图`。

## 触发条件

当用户要求以下任一任务时使用本 Skill：
- 根据资料生成 HTML 原型
- 根据资料生成 draw.io 原型
- 生成线框图、交互稿、产品界面
- 在现有原型上增量新增页面或功能

## 阶段顺序

### 全量模式

1. **资料提炼**：扫描资料并生成 `RountMap.md`
2. **产品语境**：生成产品经理视角角色与系统边界
3. **竞品分析**：生成 `竞品分析报告.md`
4. **需求文档**：生成 `requirements/` 下的详细需求文档
5. **页面清单**：生成 `原型任务清单.md` 和 `原型DoD.md`
6. **页面规格冻结**：统一写入 `page_specs/page_spec_*.md`
7. **原型渲染**：
   - draw.io：`page_model -> build_page_spec.py -> render.py -> validate.py -> merge.py`
   - HTML：从 `page_specs/` 渲染页面文件
8. **一致性校验**：覆盖率、一致性、缺页、缺字段检查
9. **最终交付**：输出 `prototypes/` 下最终原型

### 增量模式

1. 理解新增需求
2. 更新需求文档
3. 更新页面清单
4. 冻结新增页面规格到 `page_specs/`
5. 渲染与校验
6. 更新最终原型

## 输入与输出

### 输入

- 产品资料目录
- 输出格式：`html` 或 `drawio`
- 工作目录 `WORK_DIR`

### 输出

- `WORK_DIR/RountMap.md`
- `WORK_DIR/竞品分析报告.md`
- `WORK_DIR/requirements/`
- `WORK_DIR/原型任务清单.md`
- `WORK_DIR/原型DoD.md`
- `WORK_DIR/page_model_*.json`
- `WORK_DIR/page_specs/page_spec_*.md`
- `WORK_DIR/prototypes/`

## 门禁规则

### 全局门禁

- 没有 `RountMap.md`，禁止进入需求文档阶段
- 没有 `requirements/`，禁止进入原型阶段
- 没有 `原型任务清单.md`，禁止进入渲染阶段
- 没有 `page_specs/`，禁止进入任何渲染阶段
- 渲染阶段禁止回读原始资料，只允许读取冻结后的 `page_specs/`、样式规范、任务清单、导航映射
- 最终输出前，必须通过 `validate.py` 与 `check_prototype_consistency.py`

### draw.io 专属门禁

- 必须先生成 `page_model_*.json`
- 必须再生成 `page_specs/page_spec_*.md`
- `validate.py` 或一致性检查失败时，必须回退到 `page_specs` 或更上游重建，禁止直接把最终 `.drawio` 当主修复面

### 用户交互门禁

以下节点必须等待用户确认：
- 输出格式
- 工作目录
- 文件优先级分类
- 系统与功能列表确认
- 原型完成标准确认
- Step 6 改进建议确认

## 详细规则位置

只在需要时按阶段读取：

- 运行环境规则：`steps/codex-rules.md` / `steps/claude-rules.md`
- Step 1：`steps/step1-scan.md`
- Step 4：`steps/step4-requirements.md`
- Step 5 通用：`steps/step5-common.md`
- Step 5 draw.io：`steps/step5-drawio.md`
- Step 5 HTML：`steps/step5-html.md`
- 页面规格冻结契约：`steps/page-spec-freeze.md`
- draw.io 规范：`steps/drawio-spec.md`
- 页面模型契约：`steps/page-model-spec.md`
- 校验脚本：`scripts/validate.py`、`scripts/check_prototype_consistency.py`
