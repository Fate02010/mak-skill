# Plan Executor Without Model Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all model and reasoning selection from Plan Executor while keeping execution-mode confirmation and model-independent token controls.

**Architecture:** Replace the current model preflight and cost-controlled model-routing sections with one execution-mode selector that explicitly preserves the runtime's current model and reasoning effort. Replace model-routing tests with a negative/positive contract that forbids catalog inspection and model decisions, while preserving all existing plan, TDD, review, verification, and finishing gates.

**Tech Stack:** Markdown skill instructions, Python `unittest`, existing `skill-creator` validator.

## Global Constraints

- Always keep the current runtime model and reasoning effort unchanged.
- Never inspect, fetch, or require a model catalog.
- Never recommend, select, switch, or compare models.
- Never recommend or change reasoning effort.
- Never produce model-price or model-quality analysis.
- Never create task-level model or reasoning overrides.
- Never block execution because exact model IDs are unavailable.
- Do not restrict `max`, `ultra`, or any other reasoning level.
- Pre-execution output contains only the recommended execution mode and reason, alternative mode and tradeoff, and an execution-mode confirmation.
- Preserve model-independent token controls and all plan, isolation, TDD, review, repair, final-verification, and branch-finishing behavior.
- Do not modify `skills/plan-executor/agents/openai.yaml`.
- Keep the skill body at or below 1,200 words.
- Preserve the pre-existing unstaged `test_frontend_tasks_have_token_budget_rules` hunk in `tests/test_plan_executor_skill.py`; do not stage or commit it.

---

### Task 1: Remove Model Selection and Preserve Mode-Only Execution

**Files:**
- Modify: `tests/test_plan_executor_skill.py:90-202`
- Modify: `skills/plan-executor/SKILL.md:44-150`
- Reference: `docs/superpowers/specs/2026-07-21-plan-executor-no-model-selection-design.md`

**Interfaces:**
- Consumes: Existing Plan Executor plan/isolation gates, execution-mode selection, token-budget rules, TDD/review/verification workflow, and current runtime-selected model/reasoning effort.
- Produces: `test_execution_keeps_current_model_without_selection`, an execution-mode-only three-field contract, and no model-catalog, recommendation, override, or model-related stop behavior.

- [ ] **Step 1: Record the overlapping user-owned test hunk**

Run:

```bash
git diff -- tests/test_plan_executor_skill.py
```

Expected: the unstaged diff contains only `test_frontend_tasks_have_token_budget_rules`. Leave that hunk unstaged throughout this task.

- [ ] **Step 2: Replace model-routing tests with the no-selection contract**

In `tests/test_plan_executor_skill.py`, replace `test_execution_preflight_controls_cost_and_plan_detail_risk` with:

```python
    def test_execution_preflight_controls_plan_detail_and_token_cost(self):
        _, body = _frontmatter_and_body()
        required_phrases = [
            "Execution Preflight",
            "requirement-to-task coverage checklist",
            "Token Budget Rules",
            "Executing-Plans Detail Safeguards",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, body)
```

Replace `test_model_routing_is_runtime_agnostic` with:

```python
    def test_execution_keeps_current_model_without_selection(self):
        _, body = _frontmatter_and_body()
        required_phrases = [
            "Keep the current runtime model and reasoning effort unchanged",
            "Do not inspect or require a model catalog",
            "Do not recommend, select, switch, or compare models",
            "Do not recommend or change reasoning effort",
            "Do not create task-level model or reasoning overrides",
            "Do not restrict `max`, `ultra`, or any other reasoning level",
            "Wait for the user to confirm the execution mode",
            "- The execution mode is unconfirmed.",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, body)

        forbidden_phrases = [
            "## Model and Reasoning Preflight",
            "## Cost-Controlled SDD",
            "`Overall model`",
            "`Reasoning effort`",
            "`Why this is the best value`",
            "token-cost and completion-quality rationale",
            "`Task overrides`",
            "`cheap`:",
            "`standard`:",
            "`high`:",
            "- Exact runtime model IDs are unavailable.",
            "model package is unconfirmed",
        ]
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, body)
        self.assertNotRegex(body, r"\bgpt-\d")

        expected_contract = "\n".join(
            [
                "1. Recommended option and reason.",
                "2. Alternative option and tradeoff.",
                "3. A confirmation request for the execution mode.",
            ]
        )
        self.assertIn(expected_contract, body)
```

Delete the complete `test_model_preflight_requires_exact_runtime_package` method. Do not alter `test_frontend_tasks_have_token_budget_rules`.

- [ ] **Step 3: Run the new focused test and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_plan_executor_skill.PlanExecutorSkillFileTests.test_execution_keeps_current_model_without_selection -v
```

Expected: FAIL because the current skill does not contain `Keep the current runtime model and reasoning effort unchanged` and still contains `Model and Reasoning Preflight`.

- [ ] **Step 4: Replace model preflight and routing with mode-only selection**

In `skills/plan-executor/SKILL.md`, replace everything from `## Model and Reasoning Preflight` through the end of `## Cost-Controlled SDD`, stopping immediately before `### Token Budget Rules`, with exactly:

```markdown
## Execution Mode Selector

Keep the current runtime model and reasoning effort unchanged. Do not inspect or require a model catalog. Do not recommend, select, switch, or compare models. Do not recommend or change reasoning effort. Do not create task-level model or reasoning overrides. Do not restrict `max`, `ultra`, or any other reasoning level.

Recommend `superpowers:subagent-driven-development` for independent, task-scoped work when subagents are available. Recommend `superpowers:executing-plans` for tightly coupled work needing continuous context.

The mode prompt must contain only:

1. Recommended option and reason.
2. Alternative option and tradeoff.
3. A confirmation request for the execution mode.

Wait for the user to confirm the execution mode before implementation.
```

Change the following heading from:

```markdown
### Token Budget Rules
```

to:

```markdown
## Token Budget Rules
```

In `## Stop Conditions`, replace:

```markdown
- Exact runtime model IDs are unavailable.
- The execution mode or model package is unconfirmed.
```

with:

```markdown
- The execution mode is unconfirmed.
```

- [ ] **Step 5: Run focused and complete tests to verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_plan_executor_skill.PlanExecutorSkillFileTests.test_execution_keeps_current_model_without_selection -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_plan_executor_skill -v
```

Expected: the focused test passes; then all Plan Executor tests pass, including the existing frontend-budget test from the user-owned working-tree hunk.

- [ ] **Step 6: Validate structure, size, and scoped diff**

Run:

```bash
/usr/bin/python3 /Users/maijinchao/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/plan-executor
tail -n +5 skills/plan-executor/SKILL.md | wc -w
git diff --check -- skills/plan-executor/SKILL.md tests/test_plan_executor_skill.py
git diff -- skills/plan-executor/agents/openai.yaml
```

Expected: `Skill is valid!`; body word count is at most `1200`; both diff commands print no errors or metadata changes.

- [ ] **Step 7: Forward-test mode-only behavior**

Use fresh read-only agent contexts for these four valid-plan scenarios. Allow plan and repository inspection, but do not provide a model catalog and do not permit implementation:

```text
Scenario 1: Independent multi-task feature plan with subagents available.
Scenario 2: Tightly coupled parser refactor requiring continuous context.
Scenario 3: Runtime model catalog is unavailable.
Scenario 4: Current reasoning effort is max or ultra.
```

Expected for every scenario: the response recommends an execution mode, gives an alternative and tradeoff, and asks for one execution-mode confirmation. It does not inspect or name a model, evaluate or change reasoning effort, create model overrides, restrict `max`/`ultra`, or stop because model IDs are unavailable.

- [ ] **Step 8: Stage only task-owned hunks**

Run:

```bash
git add skills/plan-executor/SKILL.md
git add -p tests/test_plan_executor_skill.py
```

At the interactive prompts, stage the renamed/rewritten preflight and no-selection test hunks plus deletion of the old model-preflight test. Leave `test_frontend_tasks_have_token_budget_rules` unstaged.

Then run:

```bash
git diff --cached --check
git diff --cached -- skills/plan-executor/SKILL.md tests/test_plan_executor_skill.py
git diff -- tests/test_plan_executor_skill.py
```

Expected: the cached diff contains only the skill and no-selection test changes; the unstaged test diff still contains only `test_frontend_tasks_have_token_budget_rules`.

- [ ] **Step 9: Commit the verified change**

Run:

```bash
git commit -m "feat: remove plan executor model selection"
```

Expected: commit succeeds with only `skills/plan-executor/SKILL.md` and task-owned hunks from `tests/test_plan_executor_skill.py`. All unrelated working-tree changes remain uncommitted.
