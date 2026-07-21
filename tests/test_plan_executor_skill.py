import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "skills" / "plan-executor"
SKILL_MD = SKILL_DIR / "SKILL.md"
OPENAI_YAML = SKILL_DIR / "agents" / "openai.yaml"


def _read_skill() -> str:
    if not SKILL_MD.exists():
        raise AssertionError("skills/plan-executor/SKILL.md must exist")
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
        self.assertIn(
            'default_prompt: "Use $plan-executor to execute an existing implementation plan with review and verification."',
            text,
        )

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
            "Wait for the user to confirm the execution mode",
            "Recommended option",
            "For execution-mode confirmation, provide exactly the two supported modes",
            "For other choices or clarifications, provide 3-5 concrete options",
        ]
        for phrase in required_phrases:
            self.assertIn(phrase, body)

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
