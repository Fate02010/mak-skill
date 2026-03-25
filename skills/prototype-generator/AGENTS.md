# Prototype Generator Agents Rules

1. 任何输出格式都必须先生成 `WORK_DIR/.prototype-generator/page_specs/page_spec_*.md`，再进入渲染。
2. 渲染阶段禁止回读原始资料；只允许读取 `.prototype-generator/page_specs/`、样式规范、`.prototype-generator/原型任务清单.md`、导航/跳转映射。
3. 最终产物输出前必须通过 `validate.py` 和 `check_prototype_consistency.py`。
4. 一致性或覆盖率检查失败时，必须回退到 `.prototype-generator/page_specs` 或更上游重建，禁止直接修补最终成品。
