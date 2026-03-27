# Prototype Generator Agents Rules

1. 任何输出格式都必须先生成 `WORK_DIR/.prototype-generator/page_specs/page_spec_*.md`，再进入渲染。
2. 若满足 `原始资料 > 3000 行 / 模块数 > 3 / 功能点数 > 12 / 页面或 swimlane > 8 / 终端数 > 1 / 关键角色数 > 3` 任一项，必须进入默认强制压缩模式。
3. 默认强制压缩模式下，Step 4 必须产出 `requirements/详细需求文档_overview.md`、`requirements/module_briefs/模块摘要_[模块中文名].md`、`requirements/index.md`，缺一不可。
3.1 若后续阶段发现这些压缩产物缺失、覆盖不足或上下文预算门禁失败，必须自动重写 `overview + module_briefs + index`，不得只返回错误。
4. 分拆模式下，子 agent 读取顺序必须是 `index.md -> overview -> module_brief -> 模块详细文档 -> page_spec`，禁止直接把整份大文档或原始资料塞进后续子任务。
5. 本 Skill 默认按 `Codex 5.4 Medium / 200K` 上下文窗口工作；主流程必须保留 `30%~40%` 余量，禁止按 200K 满额拼接输入。
6. 单个子 agent 默认只允许加载 `overview + 1 个 module_brief + 1 个模块详细文档`；禁止同时读取两个以上模块详细文档。
7. 渲染阶段禁止回读原始资料；只允许读取 `.prototype-generator/page_specs/`、样式规范、`.prototype-generator/原型任务清单.md`、导航/跳转映射。
8. HTML 模式渲染前必须先生成 `.prototype-generator/reference_pack/`；优先匹配用户资料中的截图/原型/竞品图，缺少页面参照物时允许触发外部检索补充行业案例。
9. HTML `page_spec` 需要显式包含 `page_archetype`、`reference_basis`、`layout_directives`、`visual_cues`、`interaction_patterns`，禁止只给字段表后让渲染器自由发挥。
9.1 HTML 默认走双层生成：先生成 `.prototype-generator/body_slots/body_spec_* / body_prompt_* / body_html_*`，模型仅输出 body slot，脚本负责 shell、导航、状态区和 metadata。
10. Step 6 审视优先对照 `module_brief + page_spec + 任务清单`；若存在 `reference_pack`，继续对照页面级参考摘要。只有这些结构化产物无法判定时才回读模块详细文档。
11. 最终产物输出前必须通过 `validate.py` 和 `check_prototype_consistency.py`。
12. 一致性或覆盖率检查失败时，必须回退到 `.prototype-generator/page_specs` 或更上游重建，禁止直接修补最终成品。
13. HTML findings 必须带上 `repair_action`、`root_cause_hint`、`expected_fix_scope`、`stop_category`；主控器禁止只靠 `repair_target` 猜修复面。
14. HTML 自治修复分流固定为：`MISSING_FIELDS/LOW_COVERAGE -> rewrite_page_spec`，`LAYOUT_MISMATCH -> rewrite_module_brief/rewrite_requirements`，`H1/H2/H4/H10/H11/RENDER/BODY_RENDER/BODY_CONTRACT/H8/H9 -> patch_renderer`，`H7/REFERENCE_POLICY -> rebuild_reference_pack`。
14.1 `rewrite_requirements` 必须生成真实可消费的压缩产物，不得只写空壳 overview。
15. `patch_renderer` 必须进入 skill patch + regression test 分支；回归测试失败时立即停机，并把原因写入 `autoloop_state.json` 与 `执行状态.md`。
16. `reference_pack` 禁止引用 `prototypes-html/`；若命中禁用来源，必须记录 `blocked_sources/policy_violations` 并中断当前 HTML pipeline。
17. 任一时刻最多只允许 3 个并行 agent、并行模块任务或并行渲染任务；超过 3 个必须分批。
18. 用户明确授权“自己检查/自己迭代/不要来回交互”后，默认进入自治模式：不再在每轮修复前等待确认，直到真实 `WORK_DIR/prototypes/[产品名称].drawio` 通过门禁或达到熔断轮次。
19. 每轮修复都必须重新生成真实 `.drawio`，并重新执行 `check_prototype_consistency.py`、模块级 `validate.py`、`merge.py`、最终 `validate.py`；只测单页 tmp XML 不算完成。
20. `C13/C10/C11/缺页/低覆盖率/明显功能缺失` 必须回退到 `page_model` 或 `page_spec` 修复；禁止直接改最终 `.drawio` XML 作为主修复方式。
21. 测试、review、对比中间物统一放到 `WORK_DIR/.prototype-generator/`；任务完成后删除无用途的临时文件，禁止泄漏到根目录。
22. 自治模式跨会话恢复必须使用 `scripts/run_autonomous_pipeline.py ... --resume`；不允许假设 CLI 重开后会自动接上旧任务。
23. `--resume` 只恢复 `autoloop_state.json`、`rounds/round_XX/` 和已落盘产物；不得宣称恢复了已退出的 agent 或网络连接。
