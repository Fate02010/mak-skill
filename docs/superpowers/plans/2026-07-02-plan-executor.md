# Plan Executor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `plan-executor` skill that executes existing implementation plans by orchestrating Superpowers execution, review, feedback repair, verification, and finishing workflows.

**Architecture:** Add one focused skill folder under `skills/plan-executor/`. Validate it with a static unittest file that checks discovery metadata, thin-orchestrator behavior, plan/isolation gates, execution-mode selection, TDD evidence requirements, repair limits, review routing, final verification, and the Codex symlink.

**Tech Stack:** Markdown skill files, YAML UI metadata, Python `unittest`, existing system skill-creator validation scripts.

## Global Constraints

- Do not write or revise requirements specs from this skill.
- Do not write implementation plans from this skill.
- Require an explicit plan file or pasted plan content; stop when no plan exists.
- Require isolated branch or worktree execution; stop on `main` or `master`.
- Ask the user to choose between `subagent-driven-development` and `executing-plans`, with a recommended option and reasoning.
- Ask only one question per message; when asking, provide 3-5 concrete options and mark the recommended option.
- Reference original Superpowers skills instead of copying their full content.
- Require task-level testing or verification before moving to the next task.
- Require code review after every task.
- Require `receiving-code-review` before implementing review feedback.
- Enforce a maximum of three repair rounds per task.
- Require strict TDD for feature development, software development, and script development.
- Strict TDD means `write failing test -> verify RED -> implement -> verify GREEN -> refactor while green`.
- Reject TDD-required task completion reports that lack RED and GREEN evidence.
- Use `verification-before-completion` before any completion claim.
- Enter `finishing-a-development-branch` after final verification passes.
- Create `~/.codex/skills/plan-executor` as a symlink to the repository skill directory.

---

### Task 1: Add Static Skill Tests

**Files:**
- Create: `tests/test_plan_executor_skill.py`

**Interfaces:**
- Consumes: Repository root at `Path(__file__).resolve().parents[1]`.
- Produces: `PlanExecutorSkillFileTests` for skill file checks and `PlanExecutorCodexSymlinkTests` for the Codex symlink check.

- [ ] **Step 1: Write the failing test file**

Create `tests/test_plan_executor_skill.py` with this complete content:

```python
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "plan-executor"
SKILL_MD = SKILL_DIR / "SKILL.md"
OPENAI_YAML = SKILL_DIR / "agents" / "openai.yaml"


def _read_skill() -> str:
    return SKILL_MD.read_text(encoding="utf-8")


def _frontmatter_and_body() -> tuple[str, str]:
    text = _read_skill()
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not match:
        raise AssertionError("SKILL.md frontmatter must be closed with ---")
    return match.group(1), match.group(2)


class PlanExecutorSkillFileTests(unittest.TestCase):
    def test_skill_frontmatter_is_discoverable(self):
        self.assertTrue(SKILL_MD.exists(), "skills/plan-executor/SKILL.md must exist")
        frontmatter, _ = _frontmatter_and_body()
        keys = [line.split(":", 1)[0] for line in frontmatter.splitlines() if line.strip()]
        self.assertEqual(["name", "description"], keys)
        self.assertIn("name: plan-executor", frontmatter)
        description_line = next(line for line in frontmatter.splitlines() if line.startswith("description:"))
        description = description_line.split(":", 1)[1].strip().strip('"')
        self.assertTrue(description.startswith("Use when"), description)
        self.assertIn("implementation plan", description)
        self.assertLessEqual(len(description), 1024)

    def test_openai_yaml_metadata_exists(self):
        self.assertTrue(OPENAI_YAML.exists(), "agents/openai.yaml must exist")
        text = OPENAI_YAML.read_text(encoding="utf-8")
        self.assertIn('display_name: "Plan Executor"', text)
        self.assertIn('short_description: "Execute plans with review and verification"', text)
        self.assertIn('default_prompt: "Use $plan-executor to execute an existing implementation plan with review and verification."', text)

    def test_skill_is_a_thin_orchestrator(self):
        _, body = _frontmatter_and_body()
        required_skill_names = [
            "superpowers:using-git-worktrees",
            "superpowers:subagent-driven-development",
            "superpowers:executing-plans",
            "superpowers:test-driven-development",
            "superpowers:requesting-code-review",
            "superpowers:receiving-code-review",
            "superpowers:verification-before-completion",
            "superpowers:finishing-a-development-branch",
        ]
        for skill_name in required_skill_names:
            self.assertIn(skill_name, body)
        self.assertLessEqual(len(body.split()), 1200, "plan-executor should orchestrate, not duplicate source skills")

    def test_startup_gates_are_explicit(self):
        _, body = _frontmatter_and_body()
        required_phrases = [
            "If no plan is provided, stop",
            "Do not infer a plan",
            "If the current branch is `main` or `master`, stop",
            "If branch or worktree isolation cannot be confirmed, stop",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, body)

    def test_execution_mode_selector_requires_user_choice(self):
        _, body = _frontmatter_and_body()
        required_phrases = [
            "Recommend `superpowers:subagent-driven-development`",
            "Recommend `superpowers:executing-plans`",
            "wait for the user to choose",
            "Recommended option",
            "3-5 concrete options",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, body)

    def test_task_loop_enforces_tdd_review_and_repair_limits(self):
        _, body = _frontmatter_and_body()
        required_phrases = [
            "write failing test -> verify RED -> implement -> verify GREEN -> refactor while green",
            "RED evidence and GREEN evidence",
            "three repair rounds",
            "Do not enter the next task",
            "Every task requires review",
            "Use `superpowers:receiving-code-review` before acting on review feedback",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, body)

    def test_final_verification_and_finishing_are_required(self):
        _, body = _frontmatter_and_body()
        required_phrases = [
            "Use `superpowers:verification-before-completion`",
            "fresh verification evidence",
            "Use `superpowers:finishing-a-development-branch`",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, body)


class PlanExecutorCodexSymlinkTests(unittest.TestCase):
    def test_codex_skill_symlink_points_to_repo_skill(self):
        link = Path.home() / ".codex" / "skills" / "plan-executor"
        self.assertTrue(link.is_symlink(), f"{link} must be a symlink")
        self.assertEqual(SKILL_DIR.resolve(), link.resolve())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify RED**

Run:

```bash
python -m unittest tests.test_plan_executor_skill -v
```

Expected: FAIL because `skills/plan-executor/SKILL.md` and `agents/openai.yaml` do not exist yet.

- [ ] **Step 3: Commit the failing tests**

Run:

```bash
git add tests/test_plan_executor_skill.py
git commit -m "test: add plan executor skill checks"
```

Expected: commit succeeds and only `tests/test_plan_executor_skill.py` is included.

---

### Task 2: Create the Plan Executor Skill Files

**Files:**
- Create: `skills/plan-executor/SKILL.md`
- Create: `skills/plan-executor/agents/openai.yaml`

**Interfaces:**
- Consumes: Failing tests from `tests/test_plan_executor_skill.py`.
- Produces: A discoverable `plan-executor` skill and UI metadata.

- [ ] **Step 1: Initialize the skill directory**

Run:

```bash
python /Users/maijinchao/.codex/skills/.system/skill-creator/scripts/init_skill.py plan-executor --path skills --interface 'display_name=Plan Executor' --interface 'short_description=Execute plans with review and verification' --interface 'default_prompt=Use $plan-executor to execute an existing implementation plan with review and verification.'
```

Expected: `skills/plan-executor/SKILL.md` and `skills/plan-executor/agents/openai.yaml` are created.

- [ ] **Step 2: Replace `SKILL.md` with the final skill content**

Replace `skills/plan-executor/SKILL.md` with this complete content:

```markdown
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
```

- [ ] **Step 3: Confirm `agents/openai.yaml` content**

Ensure `skills/plan-executor/agents/openai.yaml` contains exactly:

```yaml
interface:
  display_name: "Plan Executor"
  short_description: "Execute plans with review and verification"
  default_prompt: "Use $plan-executor to execute an existing implementation plan with review and verification."
```

- [ ] **Step 4: Run file tests to verify GREEN for skill files**

Run:

```bash
python -m unittest tests.test_plan_executor_skill.PlanExecutorSkillFileTests -v
```

Expected: OK. If any assertion fails, fix only `skills/plan-executor/SKILL.md` or `skills/plan-executor/agents/openai.yaml`, then re-run this command.

- [ ] **Step 5: Run skill validator**

Run:

```bash
python /Users/maijinchao/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/plan-executor
```

Expected:

```text
Skill is valid!
```

- [ ] **Step 6: Commit the skill files**

Run:

```bash
git add skills/plan-executor/SKILL.md skills/plan-executor/agents/openai.yaml
git commit -m "feat: add plan executor skill"
```

Expected: commit succeeds and includes only the new skill files.

---

### Task 3: Create Codex Symlink and Run Final Verification

**Files:**
- No repository file changes required unless a correction is needed.
- External symlink: `~/.codex/skills/plan-executor`

**Interfaces:**
- Consumes: `skills/plan-executor/`.
- Produces: Codex-discoverable symlink and passing full validation.

- [ ] **Step 1: Inspect the target symlink path**

Run:

```bash
ls -ld "$HOME/.codex/skills/plan-executor" 2>/dev/null || true
```

Expected: either no output because the path does not exist, or a symlink that already points to the repository `skills/plan-executor` directory.

If the path exists and is not the correct symlink, stop and ask the user before changing it.

- [ ] **Step 2: Create the parent directory**

Run:

```bash
mkdir -p "$HOME/.codex/skills"
```

Expected: command exits 0. This may require elevated filesystem approval because it writes outside the repository.

- [ ] **Step 3: Create the symlink**

Run from the repository root:

```bash
target="$(pwd)/skills/plan-executor"
link="$HOME/.codex/skills/plan-executor"
if [ -L "$link" ] && [ "$(readlink "$link")" = "$target" ]; then
  printf 'Symlink already points to %s\n' "$target"
else
  ln -s "$target" "$link"
fi
```

Expected: command exits 0 and creates `~/.codex/skills/plan-executor` as a symlink, or reports that the correct symlink already exists.

- [ ] **Step 4: Run all plan-executor tests**

Run:

```bash
python -m unittest tests.test_plan_executor_skill -v
```

Expected: OK.

- [ ] **Step 5: Run skill validation again**

Run:

```bash
python /Users/maijinchao/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/plan-executor
```

Expected:

```text
Skill is valid!
```

- [ ] **Step 6: Check for accidental unfinished marker text**

Run:

```bash
python - <<'PY'
from pathlib import Path

needles = [
    "TB" + "D",
    "PLACE" + "HOLDER",
    "FIX" + "ME",
    "implement " + "later",
    "fill in " + "details",
]
paths = [Path("skills/plan-executor/SKILL.md"), Path("skills/plan-executor/agents/openai.yaml"), Path("tests/test_plan_executor_skill.py")]
matches = []
for path in paths:
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle in text:
            matches.append(f"{path}: contains {needle!r}")
if matches:
    print("\n".join(matches))
    raise SystemExit(1)
print("No unfinished marker text found.")
PY
```

Expected:

```text
No unfinished marker text found.
```

- [ ] **Step 7: Commit the symlink test if needed**

If Task 1's test file was not already committed after final edits, run:

```bash
git add tests/test_plan_executor_skill.py
git commit -m "test: cover plan executor codex symlink"
```

Expected: commit succeeds only if `tests/test_plan_executor_skill.py` has uncommitted changes. If there are no changes, skip this commit.

- [ ] **Step 8: Final implementation summary**

Run:

```bash
git status --short
```

Expected: only pre-existing unrelated worktree changes remain. Report the new commits, the validation commands run, and the symlink target.
