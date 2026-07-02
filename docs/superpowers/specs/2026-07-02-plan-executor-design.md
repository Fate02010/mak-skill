# Plan Executor Skill Design

## Purpose

Create a `plan-executor` skill that acts as the execution entry point after a requirement spec and implementation plan already exist.

The skill must not perform requirement analysis, write specs, or create implementation plans. It only coordinates execution, verification, code review, review feedback handling, and branch finishing by orchestrating existing Superpowers workflow skills.

## Scope

### In Scope

- Create `skills/plan-executor/SKILL.md`.
- Create `skills/plan-executor/agents/openai.yaml`.
- Create a symlink at `~/.codex/skills/plan-executor` pointing to the repository skill directory.
- Define a plan-only entry gate: execution requires an explicit plan file or plan content.
- Define an isolation gate: execution requires an isolated branch or worktree.
- Provide an execution mode selector that recommends either `subagent-driven-development` or `executing-plans` and waits for user confirmation.
- Enforce per-task testing, code review, review feedback handling, and final verification.
- Enforce a maximum of three repair rounds per task.
- Route completion to `finishing-a-development-branch` after successful final verification.

### Out of Scope

- Writing requirement specs.
- Writing implementation plans.
- Replacing the source Superpowers skills with copied full instructions.
- Building a standalone execution engine.
- Implementing automatic multi-task parallel editing in the same worktree.

## Skill Identity

Name: `plan-executor`

Location:

```text
skills/plan-executor/
├── SKILL.md
└── agents/
    └── openai.yaml
```

Codex discovery symlink:

```text
~/.codex/skills/plan-executor -> <repo>/skills/plan-executor
```

The skill should be a thin orchestrator. It may name and require other skills, but it must not duplicate their full bodies.

## Trigger Conditions

Use `plan-executor` when the user has an existing implementation plan and wants Codex to execute it through implementation, testing, code review, review feedback repair, final verification, and branch finishing.

Example trigger situations:

- "Execute this implementation plan."
- "Run the plan with review and verification."
- "Use plan-executor for this plan."
- "Implement the plan and handle tests, review, fixes, and completion."

Do not use it for:

- Brainstorming requirements.
- Writing a spec.
- Writing or revising an implementation plan.
- Starting development without a plan.

## Startup Gates

### Plan Gate

At startup, the skill must verify that a concrete plan exists.

Accepted plan inputs:

- A plan file path.
- Plan content pasted in the current user request.

If no plan exists, stop and ask the user to provide a plan or create one first. Do not infer a plan from a spec or free-form request.

### Isolation Gate

Before implementation starts, the skill must confirm work is happening on an isolated branch or worktree.

Rules:

- If the current branch is `main` or `master`, stop.
- If branch or worktree isolation cannot be determined, stop.
- If isolation is missing, instruct the user to create or switch to an isolated branch/worktree before execution.
- Use `superpowers:using-git-worktrees` when a workflow needs to create or verify an isolated worktree.

## Execution Mode Selector

After reading and reviewing the plan, the skill must recommend an execution mode and wait for the user to confirm.

Supported modes:

1. `subagent-driven-development`
2. `executing-plans`

Recommendation logic:

- Recommend `subagent-driven-development` when subagents are available and plan tasks are mostly independent, task-scoped, and suitable for fresh context per task.
- Recommend `executing-plans` when tasks are tightly coupled, require continuous main-session context, or are not suitable for implementation subagents.
- If plan structure is not clear enough to recommend confidently, stop and ask the user to choose.

The choice prompt must include:

- Recommended mode.
- Reason for the recommendation.
- The alternative mode.
- A concise tradeoff statement.

The skill must wait for user confirmation before executing.

## Per-Task Workflow

For every plan task:

1. Mark the task in progress.
2. Execute the task using the confirmed execution mode.
3. For feature development, software development, and script development, require strict TDD by invoking or following `superpowers:test-driven-development`.
4. Strict TDD requires this exact order:
   - Write the failing test first.
   - Run the test and verify RED: it fails for the expected reason.
   - Write the minimal implementation.
   - Run the test and verify GREEN: it passes.
   - Refactor only after GREEN, keeping tests green.
5. If an implementation subagent reports completion for a TDD-required task, its report must include RED evidence and GREEN evidence before the task can proceed to review.
6. For documentation, configuration, release, cleanup, or organizational tasks, decide whether TDD applies based on risk and testability.
7. Run the task-specific tests or verification commands defined by the plan.
8. If tests or verification fail, repair and re-run within the task repair limit.
9. Request code review with `superpowers:requesting-code-review`.
10. Handle review feedback with `superpowers:receiving-code-review`.
11. Repair and re-review until the task's tests, verification, and review feedback are clear, or until the repair limit is reached.
12. Mark the task complete only after task verification and review are clear.

The skill must not enter the next task while the current task has failing tests, failing verification, unclear review feedback, or unresolved review findings.

## Repair Round Limit

The repair limit is counted per plan task.

One repair round means:

```text
repair attempt -> re-run required verification and/or re-review
```

Rules:

- Each task gets at most three repair rounds.
- Test failures, verification failures, and review feedback repairs all count toward the same task-level limit.
- If the third repair round still does not clear the task, stop execution.
- When stopping, report:
  - Current task.
  - Commands run.
  - Remaining failures or review findings.
  - Repairs already attempted.
  - Why execution cannot safely continue.

This limit prevents infinite fix loops and forces a human decision when the plan, implementation approach, or context is insufficient.

## Code Review Rules

Every task requires code review, even if the task is small.

The skill must use `superpowers:requesting-code-review` for review requests and `superpowers:receiving-code-review` before acting on review feedback.

Review feedback handling rules:

- Verify feedback against the codebase before implementing.
- Ask for clarification if feedback is unclear.
- Push back with technical reasoning when feedback is incorrect.
- Fix blocking issues before proceeding.
- Re-run relevant tests after fixes.
- Re-request review when fixes affect the reviewed task.

## Final Verification and Finishing

After all tasks are complete:

1. Use `superpowers:verification-before-completion`.
2. Identify and run the commands that prove the whole plan is complete.
3. Read outputs and confirm results before making completion claims.
4. If final verification fails, repair within the current task or final verification context when appropriate. If the failure reveals an earlier task is not actually complete, return to that task's repair logic and limit.
5. After final verification passes, use `superpowers:finishing-a-development-branch`.

The skill must not claim completion before fresh verification evidence exists.

## Parallelism Policy

The skill does not default to parallel implementation in a shared worktree.

Parallel work is allowed only through existing Superpowers workflows:

- `subagent-driven-development` may use task-scoped subagents according to its own rules.
- `dispatching-parallel-agents` may be used for independent problem domains such as unrelated test failures, when that skill's conditions are met.

The skill must not dispatch multiple implementation agents that edit the same worktree concurrently unless a future plan explicitly defines safe isolated worktrees and merge order.

## Error and Stop Conditions

Stop immediately when:

- No plan is provided.
- The current branch is `main` or `master`.
- Worktree or branch isolation cannot be confirmed.
- The plan has contradictions or gaps that prevent safe execution.
- The user has not confirmed the execution mode.
- A task exceeds three repair rounds.
- Review feedback is unclear and cannot be resolved from local context.
- Required verification cannot be run.
- A source skill required for the selected mode is unavailable.

When stopping, report the blocker concretely and avoid claiming progress beyond verified evidence.

## Acceptance Criteria

- `skills/plan-executor/SKILL.md` exists.
- `skills/plan-executor/agents/openai.yaml` exists.
- The skill frontmatter has only `name` and `description`.
- The description starts with "Use when" and describes triggering conditions rather than summarizing the full workflow.
- The skill requires an explicit plan and stops when none is provided.
- The skill requires isolated branch or worktree execution and stops on `main` or `master`.
- The skill asks the user to choose between `subagent-driven-development` and `executing-plans`, with a recommended option and reasoning.
- The skill references the original Superpowers skills instead of copying their full content.
- The skill requires task-level testing or verification before moving to the next task.
- The skill requires code review after every task.
- The skill requires `receiving-code-review` before implementing review feedback.
- The skill enforces a maximum of three repair rounds per task.
- The skill requires strict TDD for feature development, software development, and script development.
- The strict TDD requirement explicitly enforces `write failing test -> verify RED -> implement -> verify GREEN -> refactor while green`.
- The skill rejects TDD-required task completion reports that lack RED and GREEN evidence.
- The skill uses `verification-before-completion` before any completion claim.
- The skill enters `finishing-a-development-branch` after final verification passes.
- `~/.codex/skills/plan-executor` points to the repository skill directory.
- Skill validation is run if available; otherwise frontmatter, directory structure, and symlink are checked manually.

## Open Decisions

None. The design choices above were confirmed by the user.
