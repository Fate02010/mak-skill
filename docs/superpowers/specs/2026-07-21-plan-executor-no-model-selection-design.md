# Plan Executor Without Model Selection Design

## Purpose

Remove model evaluation and model selection from Plan Executor. Execute plans with the model and reasoning effort already selected in the current runtime, while preserving execution-mode selection, verification, review, and token-efficient prompting.

## Current Problem

Plan Executor currently inspects the runtime model catalog, recommends an exact model and reasoning effort, creates task-level model overrides, and blocks execution when exact model IDs are unavailable. The user no longer wants Plan Executor to make model decisions.

The previously proposed optional-evaluation gate is also unnecessary: there is no model-evaluation branch to choose.

## Decision

Always keep the current runtime model and reasoning effort unchanged.

Plan Executor must not:

- Inspect, fetch, or require a model catalog.
- Recommend, select, switch, or compare models.
- Recommend or change reasoning effort.
- Produce model-price or model-quality analysis.
- Create task-level model or reasoning overrides.
- Block execution because exact model IDs are unavailable.

Do not restrict `max`, `ultra`, or any other reasoning level. The skill neither recommends nor rejects the current runtime selection.

## Execution Flow

After the existing plan, isolation, and execution-quality gates pass:

1. Keep the current runtime model and reasoning effort unchanged.
2. Select an execution mode from plan structure and coupling.
3. Present:
   - Recommended execution mode and reason.
   - Alternative execution mode and tradeoff.
   - One confirmation request for the execution mode.
4. Wait for confirmation before implementation.

Recommend `superpowers:subagent-driven-development` for independent, task-scoped work when subagents are available. Recommend `superpowers:executing-plans` for tightly coupled work needing continuous context.

No model-related field appears in the pre-execution response. In particular, do not output `Overall model`, `Reasoning effort`, `Why this is the best value`, or task-level model overrides.

## Token Control

Keep token-control rules that do not depend on model routing:

- Pass task briefs and file paths instead of full plans, histories, or large diffs.
- Return compact status, test summaries, and concerns instead of raw logs.
- Keep frontend prompts bounded to relevant files, screenshots, excerpts, and assertions.
- Avoid unnecessary subagents when tasks are tightly coupled or a single continuous context costs less.

Remove the `cheap`/`standard`/`high` model-routing table because it no longer changes model or reasoning selection.

## Stop Conditions

Retain existing plan, isolation, repair, review, verification, and source-skill stop conditions.

Replace model-related stops with one execution-mode stop:

- Stop when the user has not confirmed the execution mode.

Missing model IDs, an unavailable model catalog, and an unconfirmed model package are not stop conditions.

## Scope of Changes

- Remove `Model and Reasoning Preflight` and model-routing instructions from `skills/plan-executor/SKILL.md`.
- Simplify `Execution Mode Selector` to mode recommendation, alternative, and confirmation.
- Preserve non-model token-budget rules.
- Replace model-routing assertions in `tests/test_plan_executor_skill.py` with no-model-selection assertions.
- Keep `skills/plan-executor/agents/openai.yaml` unchanged.
- Keep the skill body at or below the existing 1,200-word thin-orchestrator limit.
- Preserve all unrelated unstaged work, including the frontend-budget test hunk.

This design supersedes the optional model-evaluation-choice design and the model-selection behavior implemented from the earlier model-routing design. Earlier commits and the implemented routing design remain historical context; this specification defines the new required behavior.

## Validation

1. Add or revise a static test so it fails while model preflight and model-routing content remain.
2. Remove model selection minimally and confirm the focused test passes.
3. Run the complete Plan Executor unittest suite.
4. Run the skill validator and verify the body is at or below 1,200 words.
5. Forward-test independent, tightly coupled, unavailable-catalog, and high-current-reasoning scenarios.

Each forward test must recommend an execution mode without inspecting or naming a model, changing reasoning effort, creating model overrides, or stopping for missing model IDs.

## Acceptance Criteria

- Plan Executor never inspects or requires a model catalog.
- Plan Executor never recommends, selects, switches, or compares models.
- Plan Executor never recommends or changes reasoning effort.
- The current model and reasoning effort remain unchanged.
- No reasoning level, including `max` and `ultra`, is restricted.
- Pre-execution output contains only the recommended execution mode, its reason, the alternative and tradeoff, and an execution-mode confirmation.
- Missing model IDs never block execution.
- No task-level model or reasoning overrides are generated.
- Non-model token-control rules remain active.
- Existing plan, isolation, TDD, review, repair, final-verification, and branch-finishing behavior remains intact.
- `agents/openai.yaml` remains unchanged.
- The skill body remains at or below 1,200 words.

## Out of Scope

- Changing the model or reasoning effort selected by the runtime or user.
- Validating whether the current model is suitable for the plan.
- Estimating model-specific token prices or completion quality.
- Adding restrictions for any reasoning level.
