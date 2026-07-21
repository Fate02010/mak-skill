# Plan Executor Model Routing Design

## Purpose

Require Plan Executor to present an exact model and reasoning-effort recommendation before implementation starts. Optimize the recommendation for low token cost without sacrificing completion quality, and wait for user confirmation before executing the plan.

## Current Problem

The current skill classifies subagent tasks as `cheap`, `standard`, or `high`, but its pre-execution response does not require an exact model ID or reasoning effort. Three baseline scenarios all selected an execution mode while omitting the concrete model and effort, so the user could not verify the intended cost/quality combination before execution.

## Decision

Use runtime-aware routing with one overall recommendation plus task-specific exceptions.

Do not hard-code model names in `SKILL.md`. Resolve the exact model IDs from the models exposed by the current Codex runtime or model picker. This keeps the skill useful as model catalogs, access, and pricing change.

At the time of this design, the local Codex catalog illustrates the intended roles:

- `gpt-5.6-terra` with `medium` reasoning is the balanced overall choice for a normal implementation plan.
- `gpt-5.6-luna` with `low` reasoning suits clear, repeatable, low-risk tasks.
- `gpt-5.6-sol` with `high` reasoning suits security, concurrency, migration, architecture, or similarly high-risk exceptions.

These names are examples of the runtime roles, not constants to embed in the skill.

## Pre-Execution Flow

After plan validation and before mode confirmation, Plan Executor must:

1. Inspect the models and reasoning levels available in the current runtime.
2. Classify the plan's overall risk, ambiguity, coupling, and verification burden.
3. Select the cheapest model and lowest reasoning effort expected to complete the full plan reliably.
4. Add task-level overrides only where a task is materially cheaper or riskier than the plan default.
5. Present the execution mode and model package together.
6. Wait for one user confirmation before implementation.

If the runtime cannot expose exact model IDs, stop and ask the user to select from the model list visible in their Codex surface. Do not substitute only `cheap`, `standard`, or `high` tiers for the required exact values.

## Selection Policy

Use these capability roles rather than fixed model names:

| Plan or task class | Model role | Reasoning | Rationale |
| --- | --- | --- | --- |
| Clear, mechanical, repeatable | Lowest-cost capable implementation model | `low` | Minimize tokens where success criteria are exact |
| Normal multi-file implementation | Everyday coding workhorse | `medium` | Default price/quality balance |
| Security, concurrency, migration, architecture, ambiguous integration | Strongest suitable coding model | `high` | Spend extra tokens only where failure cost is high |

Do not recommend `xhigh`, `max`, or `ultra` by default. Use one only when the plan contains an exceptional reasoning or parallelism requirement, and state why the expected quality gain justifies the additional usage.

Authentication and available model metadata determine the selectable catalog. The recommendation must use a model that is actually available in the current runtime.

## Output Contract

The pre-execution recommendation must contain, in this order:

1. `Execution mode`: the recommended Superpowers execution workflow.
2. `Overall model`: the exact runtime model ID.
3. `Reasoning effort`: the exact supported effort value.
4. `Why this is the best value`: a concise token-cost and completion-quality justification.
5. `Task overrides`: only exceptions, each with task, exact model ID, effort, and reason; use `None` when no override is needed.
6. `Alternative`: one lower-cost or higher-quality package and its tradeoff.
7. A single confirmation request covering both execution mode and model package.

No implementation task may start before the user confirms this package.

## Scope of Changes

- Add the model-and-reasoning preflight and output contract to `skills/plan-executor/SKILL.md`.
- Refine the existing cost-controlled routing rules rather than adding a parallel routing system.
- Add static tests to `tests/test_plan_executor_skill.py` for required fields, exact-value language, runtime availability, exception routing, and confirmation.
- Preserve the existing runtime-agnostic test that rejects hard-coded `gpt-*` names in `SKILL.md`.
- Keep `agents/openai.yaml` unchanged because the skill identity and trigger remain the same.

## Validation

1. Run the focused Plan Executor unittest and confirm the new assertions fail before the skill edit.
2. Update the skill minimally and confirm the focused unittest passes.
3. Run the skill validator.
4. Forward-test normal, tightly coupled, and high-risk plan scenarios. Each response must name an exact model and reasoning effort before requesting confirmation.
5. Confirm no unrelated dirty-worktree changes are included.

## Acceptance Criteria

- Every pre-execution recommendation names an exact available model and reasoning effort.
- The normal recommendation optimizes for the balanced runtime role with medium reasoning.
- Only materially cheaper or riskier tasks receive overrides.
- The recommendation explains the token-cost and quality tradeoff.
- `xhigh`, `max`, and `ultra` require exceptional justification.
- Missing runtime model information stops execution instead of producing a vague tier-only recommendation.
- One user confirmation approves both the execution mode and model package.
- No model name is hard-coded in `SKILL.md`.
- Existing Plan Executor behavior and user-owned worktree changes remain intact.

## Out of Scope

- Changing Codex account entitlements, pricing, or global model defaults.
- Installing or configuring model providers.
- Guaranteeing an absolute currency price when the runtime exposes only relative cost or usage information.
- Replacing the existing execution-mode selector or per-task review workflow.
