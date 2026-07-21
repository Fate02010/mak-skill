# Plan Executor Model Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Plan Executor name the exact runtime model and reasoning effort that offer the best token-cost/completion-quality balance before any implementation begins.

**Architecture:** Extend the existing thin-orchestrator Markdown skill with one runtime-aware model preflight integrated into its execution-mode selector and cost-controlled SDD routing. Lock the required output shape with a focused static unittest, preserve runtime-agnostic model selection, and forward-test the resulting behavior across five plan-risk scenarios.

**Tech Stack:** Markdown skill instructions, Python `unittest`, Codex runtime model catalog, existing `skill-creator` validator.

## Global Constraints

- Present one overall exact model ID and exact supported reasoning effort before execution.
- Add task overrides only for tasks materially cheaper or riskier than the overall plan.
- Select the cheapest available model and lowest reasoning effort expected to complete the work reliably.
- Use an everyday coding workhorse with medium reasoning for a normal implementation plan.
- Reserve lower-cost/low reasoning for clear mechanical exceptions and strongest-suitable/high reasoning for security, concurrency, migration, architecture, or ambiguous integration.
- Do not recommend `xhigh`, `max`, or `ultra` without exceptional, explicit justification.
- Stop when exact runtime model IDs are unavailable; do not fall back to only `cheap`, `standard`, or `high` labels.
- Ask for one confirmation covering both execution mode and model package.
- Do not hard-code any `gpt-*` model name in `skills/plan-executor/SKILL.md`.
- Keep the skill body at or below the existing 1,200-word thin-orchestrator limit.
- Do not modify `skills/plan-executor/agents/openai.yaml`.
- Preserve the pre-existing unstaged `test_frontend_tasks_have_token_budget_rules` change in `tests/test_plan_executor_skill.py`; do not stage or commit that hunk.

---

### Task 1: Require and Implement the Exact Model Package Preflight

**Files:**
- Modify: `tests/test_plan_executor_skill.py:142`
- Modify: `skills/plan-executor/SKILL.md:52`
- Reference: `docs/superpowers/specs/2026-07-21-plan-executor-model-routing-design.md`

**Interfaces:**
- Consumes: Existing `PlanExecutorSkillFileTests`, execution-mode selector, `cheap`/`standard`/`high` task tiers, and the current runtime's visible model IDs and supported reasoning values.
- Produces: `test_model_preflight_requires_exact_runtime_package` and a pre-execution output contract containing `Execution mode`, `Overall model`, `Reasoning effort`, `Why this is the best value`, `Task overrides`, `Alternative`, and `Confirmation` in that order.

- [ ] **Step 1: Record the pre-existing overlapping test change**

Run:

```bash
git diff -- tests/test_plan_executor_skill.py
```

Expected: the unstaged diff contains `test_frontend_tasks_have_token_budget_rules`. Treat that hunk as user-owned and leave it unstaged throughout this task.

- [ ] **Step 2: Add the failing output-contract test**

Insert this method after `test_final_verification_and_finishing_are_required` and before `PlanExecutorCodexSymlinkTests`, keeping it far enough from the pre-existing frontend-test hunk to stage separately:

```python
    def test_model_preflight_requires_exact_runtime_package(self):
        _, body = _frontmatter_and_body()
        required_phrases = [
            "Model and Reasoning Preflight",
            "exact model ID",
            "exact supported reasoning effort",
            "cheapest currently available model",
            "everyday coding workhorse with medium reasoning",
            "lower-cost model with low reasoning",
            "strongest suitable coding model with high reasoning",
            "If exact model IDs are unavailable, stop",
            "Do not continue with tier-only routing",
            "`xhigh`, `max`, or `ultra`",
            "one user confirmation",
            "task, exact model ID, effort, and reason",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, body)

        ordered_fields = [
            "`Execution mode`",
            "`Overall model`",
            "`Reasoning effort`",
            "`Why this is the best value`",
            "`Task overrides`",
            "`Alternative`",
            "`Confirmation`",
        ]
        positions = [body.index(field) for field in ordered_fields]
        self.assertEqual(sorted(positions), positions)
```

- [ ] **Step 3: Run the focused test and verify RED**

Run:

```bash
python -m unittest tests.test_plan_executor_skill.PlanExecutorSkillFileTests.test_model_preflight_requires_exact_runtime_package -v
```

Expected: FAIL because `Model and Reasoning Preflight` is absent from the current skill. Confirm the failure is an assertion failure for missing contract text, not a Python import or syntax error.

- [ ] **Step 4: Replace the mode and cost-routing sections with the model-aware contract**

In `skills/plan-executor/SKILL.md`, replace everything from `## Execution Mode Selector` through the end of `## Cost-Controlled SDD`, stopping immediately before `### Token Budget Rules`, with exactly:

```markdown
## Model and Reasoning Preflight

Before mode selection, inspect exact model IDs and reasoning levels in the current runtime. Choose the cheapest currently available model and lowest exact supported reasoning effort expected to complete plan reliably. For normal plans, use the everyday coding workhorse with medium reasoning; use a lower-cost model with low reasoning for mechanical exceptions and the strongest suitable coding model with high reasoning for security, concurrency, migration, architecture, or ambiguous integration.

Do not hard-code model names. Do not recommend `xhigh`, `max`, or `ultra` by default. Use one only for exceptional reasoning or parallelism; justify extra usage.

If exact model IDs are unavailable, stop and ask the user to select from the current runtime's visible model list. Do not continue with tier-only routing.

Every pre-execution recommendation must contain, in order:

1. `Execution mode`: recommended workflow.
2. `Overall model`: exact model ID.
3. `Reasoning effort`: exact supported value.
4. `Why this is the best value`: token-cost and completion-quality rationale.
5. `Task overrides`: task, exact model ID, effort, and reason; write `None` when absent.
6. `Alternative`: one lower-cost or higher-quality package and its tradeoff.
7. `Confirmation`: one user confirmation covering the execution mode and model package.

No implementation task may start before that confirmation.

## Execution Mode Selector

Read the plan, recommend one mode, show the alternative, and wait for the user to choose.

Recommend `superpowers:subagent-driven-development` for independent, task-scoped work when subagents are available. Recommend `superpowers:executing-plans` for tightly coupled work needing continuous context.

Present the Recommended option, tradeoff, and model package together. Do not execute until confirmed.

## Cost-Controlled SDD

For `superpowers:subagent-driven-development`, use the confirmed overall model by default and route only exceptions:

- `cheap`: exact-code, single-file, doc/config/test-only, or mechanical edits.
- `standard`: normal multi-file implementation with clear interfaces.
- `high`: architecture, ambiguous integration, security, concurrency, performance risk, or final whole-branch review.

Every override must name an exact current-runtime model and supported reasoning effort.
```

- [ ] **Step 5: Run focused and complete static tests to verify GREEN**

Run:

```bash
python -m unittest tests.test_plan_executor_skill.PlanExecutorSkillFileTests.test_model_preflight_requires_exact_runtime_package -v
python -m unittest tests.test_plan_executor_skill -v
```

Expected: the focused test passes; then all Plan Executor tests pass, including the runtime-agnostic assertion that `SKILL.md` contains no hard-coded `gpt-*` name.

- [ ] **Step 6: Verify the thin-orchestrator limit and skill metadata**

Run:

```bash
tail -n +5 skills/plan-executor/SKILL.md | wc -w
python /Users/maijinchao/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/plan-executor
git diff --check -- skills/plan-executor/SKILL.md tests/test_plan_executor_skill.py
```

Expected: the body word count is at most `1200`; the validator exits successfully; `git diff --check` prints nothing.

- [ ] **Step 7: Forward-test five pre-execution scenarios**

Run each scenario in a fresh, read-only agent context with the updated `plan-executor` skill. Stop every scenario before implementation and capture only its pre-execution recommendation.

```text
Scenario 1: Execute a normal multi-file CRUD plan. Minimize token cost without reducing completion quality.
Scenario 2: Execute a tightly coupled parser refactor plan. Minimize context repetition and integration risk.
Scenario 3: Execute a plan covering authentication, concurrency, and a database migration. Keep cost low, but do not compromise safety.
Scenario 4: Execute a clear documentation and configuration-only plan with exact acceptance checks.
Scenario 5: Assume the Codex surface does not expose exact model IDs. Prepare to execute a valid plan.
```

Expected for Scenarios 1-4: each response lists all seven output fields in order, names an exact model ID and supported reasoning effort, explains the value tradeoff, limits overrides to genuine exceptions, and asks for one combined confirmation. Expected for Scenario 5: it stops and asks the user to choose from the visible model list; it does not offer only tier labels and does not start execution.

- [ ] **Step 8: Review the final diff and stage only task-owned hunks**

Run:

```bash
git diff -- skills/plan-executor/SKILL.md tests/test_plan_executor_skill.py
git add skills/plan-executor/SKILL.md
git add -p tests/test_plan_executor_skill.py
```

At the interactive prompt, leave the pre-existing `test_frontend_tasks_have_token_budget_rules` hunk unstaged and stage only `test_model_preflight_requires_exact_runtime_package`.

Then run:

```bash
git diff --cached --check
git diff --cached -- skills/plan-executor/SKILL.md tests/test_plan_executor_skill.py
git diff -- tests/test_plan_executor_skill.py
```

Expected: the cached diff contains the skill edit and only the new model-preflight test method; the unstaged test diff still contains the user-owned frontend-test method.

- [ ] **Step 9: Commit the verified change**

Run:

```bash
git commit -m "feat: add plan executor model preflight"
```

Expected: commit succeeds with only `skills/plan-executor/SKILL.md` and the new model-preflight test hunk. The pre-existing frontend-test hunk and all unrelated dirty-worktree changes remain uncommitted.
