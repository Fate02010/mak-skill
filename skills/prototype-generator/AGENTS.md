# Prototype Generator Agents Rules

1. 任何输出格式都必须先生成 `WORK_DIR/.prototype-generator/page_specs/page_spec_*.md`，再进入渲染。
2. 渲染阶段禁止回读原始资料；只允许读取 `.prototype-generator/page_specs/`、样式规范、`.prototype-generator/原型任务清单.md`、导航/跳转映射。
3. 最终产物输出前必须通过 `validate.py` 和 `check_prototype_consistency.py`。
4. 一致性或覆盖率检查失败时，必须回退到 `.prototype-generator/page_specs` 或更上游重建，禁止直接修补最终成品。
5. 任一时刻最多只允许 3 个并行 agent、并行模块任务或并行渲染任务；超过 3 个必须分批。
6. 用户明确授权“自己检查/自己迭代/不要来回交互”后，默认进入自治模式：不再在每轮修复前等待确认，直到真实 `WORK_DIR/prototypes/[产品名称].drawio` 通过门禁或达到熔断轮次。
7. 每轮修复都必须重新生成真实 `.drawio`，并重新执行 `check_prototype_consistency.py`、模块级 `validate.py`、`merge.py`、最终 `validate.py`；只测单页 tmp XML 不算完成。
8. `C13/C10/C11/缺页/低覆盖率/明显功能缺失` 必须回退到 `page_model` 或 `page_spec` 修复；禁止直接改最终 `.drawio` XML 作为主修复方式。
9. 测试、review、对比中间物统一放到 `WORK_DIR/.prototype-generator/`；任务完成后删除无用途的临时文件，禁止泄漏到根目录。
