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

Ask only one question per message. When asking the user to choose or clarify, provide 3-5 concrete options and mark the Recommended option.

## Startup Gates

### Plan Gate

If no plan is provided, stop. Accept only a plan file path or plan content pasted by the user.

Do not infer a plan from a spec, requirement, issue, or loose request. Ask the user to provide a plan or create one first.

### Isolation Gate

Before implementation starts, confirm branch or worktree isolation.

Run the normal git checks for the current repository. If the current branch is `main` or `master`, stop. If branch or worktree isolation cannot be confirmed, stop.

If isolation is missing, use `superpowers:using-git-worktrees` or ask the user to create or switch to an isolated branch/worktree.

## Execution Mode Selector

Read the plan before choosing a mode. Recommend one mode, explain why, show the alternative, and wait for the user to choose.

Recommend `superpowers:subagent-driven-development` when subagents are available and plan tasks are mostly independent, task-scoped, and suitable for fresh context per task.

Recommend `superpowers:executing-plans` when tasks are tightly coupled, require continuous main-session context, or are not suitable for implementation subagents.

The mode prompt must include:

1. Recommended option and reason.
2. Alternative option and tradeoff.
3. A clear request for the user to choose before execution.

Do not execute any task until the user confirms the mode.

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
- The user has not chosen an execution mode.
- A task exceeds three repair rounds.
- Review feedback is unclear and cannot be resolved locally.
- Required verification cannot be run.
- A required source skill is unavailable.

Report the blocker concretely and avoid claims beyond verified evidence.

## Parallelism Policy

Do not dispatch multiple implementation agents editing the same worktree concurrently.

Parallel work is allowed only through the selected Superpowers workflow or through `superpowers:dispatching-parallel-agents` for independent problem domains such as unrelated test failures.
