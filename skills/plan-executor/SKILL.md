---
name: plan-executor
description: Use when the user has an explicit implementation plan and asks Codex to execute that plan after requirements/spec and write-plan work are complete; especially requests to run a plan, implement a plan, or execute planned tasks with review and verification.
---

# Plan Executor

## Overview

Execute an existing implementation plan by coordinating the existing Superpowers execution, review, feedback, verification, and finishing workflows.

This skill is a thin orchestrator. It does not replace the source skills and does not copy their full instructions.

## Required Sub-Skills

- **REQUIRED SUB-SKILL:** Use `superpowers:using-git-worktrees` when branch or worktree isolation must be created or verified.
- **REQUIRED SUB-SKILL:** Use either `superpowers:subagent-driven-development` or `superpowers:executing-plans` after the user chooses the execution mode.
- **REQUIRED SUB-SKILL:** Use `superpowers:test-driven-development` for feature development, software development, and script development tasks.
- **REQUIRED SUB-SKILL:** Use `superpowers:requesting-code-review` for review requests that are not already covered by the selected execution workflow.
- **REQUIRED SUB-SKILL:** Use `superpowers:receiving-code-review` before acting on review feedback.
- **REQUIRED SUB-SKILL:** Use `superpowers:verification-before-completion` before claiming completion.
- **REQUIRED SUB-SKILL:** Use `superpowers:finishing-a-development-branch` after final verification passes.

## Question Rule

Ask only one question per message. For execution-mode confirmation, provide exactly the two supported modes and mark the Recommended option. For other choices or clarifications, provide 3-5 concrete options and mark the Recommended option.

## Startup Gates

### Plan Gate

If no plan is provided, stop. Accept only a plan file path or plan content pasted by the user.

Do not infer a plan from a spec, requirement, issue, or loose request. Ask the user to provide a plan or create one first.

### Isolation Gate

Before implementation starts, confirm branch or worktree isolation.

Run the normal git checks for the current repository. If the current branch is `main` or `master`, stop. If branch or worktree isolation cannot be confirmed, stop.

If isolation is missing, use `superpowers:using-git-worktrees` or ask the user to create or switch to an isolated branch/worktree.

## Execution Preflight

Before mode selection, read the plan and audit execution risk.

Stop if the plan has placeholders, vague instructions such as "handle edge cases", missing file targets, missing interfaces, missing verification commands, missing expected results, contradictions, or tasks without independently testable deliverables.

Create a short requirement-to-task coverage checklist from the plan goal, global constraints, acceptance criteria, and task headings. If any requirement has no task, stop and report the gap instead of guessing during execution.

## Execution Mode Selector

Keep the current runtime model and reasoning effort unchanged. Do not inspect, fetch, or require a model catalog. Do not evaluate the current model or its suitability. Do not recommend, select, switch, or compare models. Do not recommend or change reasoning effort. Do not produce model-price or model-quality analysis. Do not create task-level model or reasoning overrides. Do not block execution because exact model IDs are unavailable. Do not restrict `max`, `ultra`, or any other reasoning level.

Recommend `superpowers:subagent-driven-development` for independent, task-scoped work when subagents are available. Recommend `superpowers:executing-plans` for tightly coupled work needing continuous context.

The mode prompt must contain only:

1. Recommended option and reason.
2. Alternative option and tradeoff.
3. A confirmation request for the execution mode.

Wait for the user to confirm the execution mode before implementation.

## Token Budget Rules

Use task briefs and file paths for reports, diffs, and review packages. Do not paste the full plan, accumulated task history, or large diffs into prompts. Require subagents to return only status, commits, test summary, and concerns in chat. Group adjacent trivial tasks only when grouping does not change the plan's deliverables or review boundary.

## Frontend Task Budget Rules

For frontend tasks, require a frontend surface brief: target screen or component, affected files, existing design source, states to implement, and exact acceptance checks.

Do not paste full component trees, full CSS bundles, large screenshots, large DOM dumps, or full browser/test logs into prompts. Pass screenshot paths, bounded DOM/CSS excerpts, relevant file paths, and exact failing assertions instead.

## Executing-Plans Detail Safeguards

Use `superpowers:executing-plans` only after the preflight audit passes.

Before marking each task complete, confirm planned files, interfaces, verification commands, expected results, and acceptance criteria were satisfied. For each task review under `superpowers:executing-plans`, include the task text, coverage checklist, verification output, and diff reference.

## Per-Task Gate

For every plan task:

1. Mark the task in progress.
2. Execute through the selected execution mode.
3. For feature development, software development, and script development, enforce `write failing test -> verify RED -> implement -> verify GREEN -> refactor while green`.
4. If an implementation subagent reports completion for a TDD-required task, require RED evidence and GREEN evidence before the task can proceed to review.
5. Run the task-specific verification commands from the plan.
6. Every task requires review. For `superpowers:subagent-driven-development`, its task reviewer is the task review gate. For `superpowers:executing-plans`, use `superpowers:requesting-code-review` after each task.
7. Use `superpowers:receiving-code-review` before acting on review feedback.
8. Repair, re-run verification, and re-review until the task is clear or the task reaches the repair limit.
9. Do not enter the next task while tests, verification, review feedback, or review findings remain unresolved.

## Repair Limit

Each task gets at most three repair rounds.

One repair round is `repair attempt -> re-run required verification and/or re-review`.

Test failures, verification failures, missing TDD evidence, and review feedback repairs all count toward the same task-level limit.

If the third repair round still does not clear the task, stop. Report the current task, commands run, remaining failures or findings, repairs attempted, and why execution cannot safely continue.

## Final Verification and Finishing

After all tasks are complete, use `superpowers:verification-before-completion`.

Run fresh verification commands, read the output, and only then make completion claims. If fresh verification evidence is missing, do not claim completion.

After final verification passes, use `superpowers:finishing-a-development-branch`.

## Stop Conditions

Stop immediately when:

- No plan is provided.
- Current branch is `main` or `master`.
- Branch or worktree isolation cannot be confirmed.
- The plan has contradictions or blocking gaps.
- The execution mode is unconfirmed.
- A task exceeds three repair rounds.
- Review feedback is unclear and cannot be resolved locally.
- Required verification cannot be run.
- A required source skill is unavailable.

Report the blocker concretely and avoid claims beyond verified evidence.

## Parallelism Policy

Do not dispatch multiple implementation agents editing the same worktree concurrently.

Parallel work is allowed only through the selected Superpowers workflow or through `superpowers:dispatching-parallel-agents` for independent problem domains such as unrelated test failures.
