# Plan Executor Model Evaluation Choice Design

## Purpose

Let the user decide whether Plan Executor should evaluate and recommend a model and reasoning effort before execution. Preserve the current model-selection workflow when evaluation is requested, while allowing users to keep the runtime's current model and reasoning effort without extra catalog inspection.

## Current Problem

Plan Executor currently performs model and reasoning preflight for every valid plan. It requires exact runtime model IDs, builds a cost/quality recommendation, and blocks execution when the catalog is unavailable. This is useful when users want optimization, but adds an unnecessary decision and model lookup when they prefer to keep their current runtime selection.

## Decision

Add a model-evaluation choice gate after plan audit and before any model-catalog inspection or execution-mode confirmation.

The gate must offer three choices:

1. Evaluate and recommend a model and reasoning effort.
2. Skip evaluation and keep the current model and reasoning effort unchanged.
3. Pause execution.

Mark one option Recommended. Recommend evaluation for normal or high-risk plans and whenever the user explicitly asks to optimize cost, token usage, or completion quality. The skill may recommend skipping evaluation for a clear, mechanical, low-risk plan when avoiding an extra lookup or decision is more valuable.

The choice applies to the current plan execution. Ask again if the plan changes materially before implementation starts.

## Interaction Flow

### Shared Preflight

Both branches require the existing plan gate, isolation gate, plan-quality audit, and requirement-to-task coverage checklist. Model choice does not weaken plan validation or execution safety.

After those checks pass, ask only the model-evaluation question. Do not combine it with execution-mode selection; the existing one-question-per-message rule remains in force.

### Evaluation Branch

When the user chooses evaluation:

1. Inspect exact model IDs and supported reasoning levels in the current runtime.
2. Apply the existing balanced, lower-cost, and high-risk routing rules.
3. Produce the existing seven-field recommendation in order:
   - `Execution mode`
   - `Overall model`
   - `Reasoning effort`
   - `Why this is the best value`
   - `Task overrides`
   - `Alternative`
   - `Confirmation`
4. Wait for one confirmation covering the execution mode and model package.

If exact model IDs are unavailable, stop and ask the user to select from the visible model list. Do not continue with tier-only routing.

### Skip-Evaluation Branch

When the user skips evaluation:

1. Do not inspect or fetch the runtime model catalog.
2. Do not recommend a model, reasoning effort, or task-level model overrides.
3. Keep the runtime's current model and reasoning effort unchanged.
4. Present only:
   - Recommended execution mode and reason.
   - Alternative execution mode and tradeoff.
   - A confirmation request for the execution mode.
5. Wait for execution-mode confirmation before starting any task.

The skill may state once that model evaluation was skipped, but must not turn that statement into an inferred model recommendation.

Missing exact model IDs do not block this branch because no model selection is being performed.

### Pause Branch

When the user pauses, stop before model inspection, mode selection, or implementation. Report that execution has not started.

## State and Stop Conditions

Track the model-evaluation choice as one of `evaluate`, `skip`, or `pause` for the current plan.

- No implementation task may start before the choice is recorded.
- The `evaluate` branch stops when exact model IDs are unavailable or the combined mode/model package is unconfirmed.
- The `skip` branch stops only when the execution mode is unconfirmed; unavailable model IDs are irrelevant.
- The `pause` branch always stops.
- A material plan change invalidates the prior choice and returns to the choice gate.

## Scope of Changes

- Update `skills/plan-executor/SKILL.md` with the choice gate and conditional model/mode confirmation rules.
- Refactor the existing model preflight instead of creating a second model-routing section.
- Update `tests/test_plan_executor_skill.py` with static assertions for all three branches and conditional stop behavior.
- Keep `skills/plan-executor/agents/openai.yaml` unchanged.
- Preserve the 1,200-word thin-orchestrator limit by removing duplicated unconditional wording.
- Preserve all unrelated unstaged changes, including the existing frontend-budget test hunk.

## Validation

1. Add a failing static test for the choice gate and conditional branches.
2. Confirm RED because the current skill has no choice gate.
3. Update the skill minimally and confirm the focused and full Plan Executor tests pass.
4. Run the skill validator and verify the body remains at or below 1,200 words.
5. Forward-test at least these scenarios:
   - Evaluation selected with a visible catalog.
   - Evaluation selected without exact model IDs.
   - Evaluation skipped with no catalog lookup.
   - Pause selected.
   - Material plan change after an earlier choice.

## Acceptance Criteria

- Every valid execution reaches a model-evaluation choice before model lookup or mode confirmation.
- The choice offers evaluate, skip-and-keep-current, and pause options.
- One option is marked Recommended using plan risk and the user's optimization request.
- Evaluation preserves the existing exact-model seven-field contract.
- Skipping performs no model-catalog inspection and produces no model recommendation or overrides.
- Skipping keeps the current model and reasoning effort unchanged.
- Missing model IDs block only the evaluation branch.
- Both active branches require the appropriate confirmation before implementation.
- Pausing starts no model inspection, mode selection, or implementation.
- A material plan change returns to the choice gate.
- The skill contains no hard-coded `gpt-*` model name and remains at or below 1,200 words.
- Existing Plan Executor behavior outside this choice remains intact.

## Out of Scope

- Changing the currently selected runtime model or reasoning effort when evaluation is skipped.
- Persisting the choice across unrelated plans or sessions.
- Changing model providers, account entitlements, pricing, or global Codex defaults.
- Combining the choice gate with execution-mode confirmation.
