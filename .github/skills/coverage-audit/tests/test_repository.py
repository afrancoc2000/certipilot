from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location(
    "coverage_audit_repository", ROOT / ".github" / "skills" / "coverage-audit" / "scripts" / "coverage.py",
)
coverage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coverage)


class RepositoryTests(unittest.TestCase):
    def test_study_turn_fast_path_is_wired_without_relaxing_safety(self):
        policy = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        fast_path = policy.split("## Efficient study turns", 1)[1].split("\n## ", 1)[0]
        for required in (
            "execution-subagent", "direct", "same pending item",
            "successful `record --json`", "ledger hash", "as-of date",
            "genuine-turn", "before presentation", "No latency promise",
        ):
            with self.subTest(required=required):
                self.assertIn(required, fast_path)
        for path in (
            ROOT / ".github" / "agents" / "quiz-agent.agent.md",
            *[ROOT / ".github" / "skills" / name / "SKILL.md"
              for name in ("grade-answer", "select-next-question", "update-progress", "follow-plan")],
        ):
            with self.subTest(path=path):
                self.assertIn("AGENTS.md#efficient-study-turns", path.read_text(encoding="utf-8"))
        progress = (ROOT / ".github" / "skills" / "update-progress" / "SKILL.md").read_text(
            encoding="utf-8",
        )
        self.assertNotIn("After successful recording, audit again", progress)
        record_command = next(line for line in progress.splitlines()
                              if "coverage.py record --exam" in line)
        self.assertIn("--json", record_command)
        self.assertIn("complete successful", progress)
        for name in ("quiz-agent", "tutor-agent", "study-planner-agent"):
            agent = (ROOT / ".github" / "agents" / f"{name}.agent.md").read_text(encoding="utf-8")
            self.assertNotIn("\nmodel:", agent.split("---", 2)[1])

    def test_ci_uses_one_python_version_and_initializes_runner_paths_at_step_scope(self):
        workflow = (ROOT / ".github" / "workflows" / "ci-python.yml").read_text(encoding="utf-8")
        self.assertIn("os: [ubuntu-latest, windows-latest]", workflow)
        self.assertIn("python-version: ['3.13']", workflow)
        environment = workflow.split("    env:\n", 1)[1].split("    steps:\n", 1)[0]
        self.assertNotIn("runner.", environment)
        self.assertIn('$reportDir = Join-Path $env:RUNNER_TEMP "python-ci"', workflow)
        self.assertIn('"CI_REPORT_DIR=$reportDir"', workflow)
        self.assertIn("$env:GITHUB_ENV", workflow)
        self.assertLess(workflow.index("- name: Prepare report directory"),
                        workflow.index("- name: Run unittest"))

    def test_every_configured_exam_has_a_valid_catalog_and_complete_queue(self):
        exams = sorted((ROOT / "exams").glob("*/exam.md"))
        self.assertTrue(exams)
        for config in exams:
            with self.subTest(exam=config.parent.name):
                catalog = coverage.read_json(config.parent / "blueprint.json")
                today = datetime.now(timezone.utc).date()
                coverage.validate_catalog(catalog, config.parent.name, today)
                result = coverage.report(catalog, coverage.empty_ledger(catalog), today)
                self.assertEqual(set(result["coverage_queue"]), set(result["states"]))
                self.assertEqual(len(result["coverage_queue"]), result["total_subskills"])
                self.assertEqual(result["objectives_fully_assessed"], 0)
                self.assertIn("blueprint.json", config.read_text(encoding="utf-8"))

    def test_workflow_entry_points_reference_coverage(self):
        paths = [
            ROOT / "AGENTS.md",
            ROOT / ".github" / "instructions" / "progress-tracking.instructions.md",
            *[
                ROOT / ".github" / "skills" / name / "SKILL.md"
                for name in (
                    "select-next-question", "build-sprint-plan", "grade-answer",
                    "update-progress", "follow-plan", "close-session", "run-mock-exam",
                )
            ],
            *[
                ROOT / ".github" / "agents" / f"{name}.agent.md"
                for name in ("quiz-agent", "tutor-agent", "study-planner-agent")
            ],
        ]
        for path in paths:
            with self.subTest(path=path.name):
                content = path.read_text(encoding="utf-8").lower()
                if path.name == "progress-tracking.instructions.md":
                    self.assertIn("coverage", content)
                else:
                    self.assertIn("progress-tracking.instructions.md", content)
                for obsolete in (
                    "~60% weak", "70–80% current weak", "70–80% weak-topic slots",
                    "~30% unseen/rotation",
                ):
                    self.assertNotIn(obsolete, content)

    def test_exam_onboarding_documents_required_catalog_and_validation(self):
        guide = (ROOT / "exams" / "README.md").read_text(encoding="utf-8")
        for required in (
            "exams/<exam-id>/blueprint.json", "official study guide", "stable IDs",
            "references/evidence.md#catalog", "assets/coverage.json",
            "coverage.py audit --exam <exam-id>", "coverage.py init --exam <exam-id>",
            "test_repository.py", "## Coverage summary",
        ):
            with self.subTest(required=required):
                self.assertIn(required, guide)
        self.assertLess(guide.index("blueprint.json"), guide.index("coverage.py init"))

    def test_plan_selection_preserves_date_matches_before_recency(self):
        resolver = (ROOT / ".github" / "instructions" / "active-exam.instructions.md").read_text(
            encoding="utf-8",
        )
        workflow = (ROOT / ".github" / "skills" / "follow-plan" / "SKILL.md").read_text(
            encoding="utf-8",
        )
        self.assertIn("Retain the matching plan paths", resolver)
        self.assertIn("pass its matching paths to follow-plan", resolver)
        locate = workflow.split("1. **Locate the plan**")[1].split("2. **Check today's date**")[0]
        for required in (
            "provided explicitly by the user", "reuse the matching plan paths",
            "Filter candidates to plans covering today's date",
            "before applying any tiebreaker", "most recently modified matching plan",
            "none cover today", "ask which",
        ):
            self.assertIn(required, locate)
        self.assertLess(locate.index("Filter candidates"), locate.index("most recently modified"))
        self.assertNotIn("active plan (most recently modified or explicitly marked active)", workflow)

    def test_evidence_is_private_and_helper_is_shareable(self):
        for path, expected in [
            ("exams/az-104/assets/coverage.json", 0),
            ("exams/az-104/assets/coverage.batch.json", 0),
            ("exams/az-104/assets/session.json", 0),
            ("exams/az-104/assets/session.backup.json", 0),
            ("exams/az-104/assets/session.json.lock", 0),
            (".github/skills/coverage-audit/scripts/coverage.py", 1),
            (".github/skills/coverage-audit/scripts/session.py", 1),
            ("exams/az-104/blueprint.json", 1),
        ]:
            with self.subTest(path=path):
                result = subprocess.run(
                    ["git", "check-ignore", "--quiet", path],
                    cwd=ROOT, check=False, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, expected, result.stderr)

    def test_mock_weighting_contract_defines_ranges_rounding_and_ties(self):
        workflow = (ROOT / ".github" / "skills" / "run-mock-exam" / "SKILL.md").read_text(
            encoding="utf-8",
        )
        weighting = workflow.split("## Domain weighting")[1].split("## Procedure")[0]
        for required in (
            "weight = (weight_min + weight_max) / 2",
            "quota = 10 * weight / sum(weights)",
            "count = max(1, floor(quota))",
            "quota - count", "count - quota", "count > 1",
            "recalculating after each addition", "recalculating after each removal",
            "earlier position in the catalog's `domains` array",
            "fractions rather than rounded percentages",
            "stop mock preparation", "no equal-weight fallback",
            "counts sum to 10", "more than 10 domains",
            "stop and ask to increase the mock length",
            "3, 2, 2, 3", "3, 2, 2, 2, 1", "2, 2, 2, 2, 1, 1",
        ):
            with self.subTest(required=required):
                self.assertIn(required, weighting)
        self.assertNotIn("rounding remainders to the highest-weighted domains", weighting)
        self.assertNotIn("use equal positive weights for all domains", weighting)

    def test_teacher_first_contract_is_wired_to_every_study_entry_point(self):
        policy = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("## Teacher-first conversation", policy)
        for required in (
            "Keep bookkeeping internal", "Show numbers when they serve the request",
            "Keep errors honest", "Warmth never means weaker validation",
        ):
            self.assertIn(required, policy)
        paths = [
            ROOT / ".github" / "instructions" / "progress-tracking.instructions.md",
            *[ROOT / ".github" / "agents" / f"{name}.agent.md"
              for name in ("quiz-agent", "tutor-agent", "study-planner-agent")],
            *[ROOT / ".github" / "skills" / name / "SKILL.md" for name in (
                "coverage-audit", "grade-answer", "update-progress", "select-next-question",
                "close-session", "run-mock-exam", "follow-plan", "build-sprint-plan",
            )],
        ]
        for path in paths:
            with self.subTest(path=path):
                content = path.read_text(encoding="utf-8")
                marker = "AGENTS.md#teacher-first-conversation"
                self.assertIn(marker, content)
                target = content.split(marker)[0].rsplit("](", 1)[1]
                self.assertEqual((path.parent / (target + "AGENTS.md")).resolve(), ROOT / "AGENTS.md")

    def test_script_development_contract_is_discoverable_and_distinguishes_evaluations(self):
        guide = ROOT / ".github" / "instructions" / "script-development.instructions.md"
        content = guide.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"))
        self.assertIn('applyTo: "**/*.py,.github/workflows/*.yml,.github/workflows/*.yaml"', content)
        for requirement in (
            "actual CLI", "fresh-process restart", "failed writes", "compound predicates",
            "before reading those findings", "Different from conversational evaluation",
        ):
            self.assertIn(requirement, content)
        self.assertIn(".github/instructions/script-development.instructions.md",
                      (ROOT / "AGENTS.md").read_text(encoding="utf-8"))

    def test_learner_output_templates_do_not_require_internal_bookkeeping(self):
        skills = ROOT / ".github" / "skills"
        grade = (skills / "grade-answer" / "SKILL.md").read_text(encoding="utf-8")
        template = grade.split("```")[1]
        self.assertNotIn("Evidence:", template)
        self.assertNotIn("Next action:", template)
        progress = (skills / "update-progress" / "SKILL.md").read_text(encoding="utf-8")
        output = progress.split("## Output")[1].split("## Guardrails")[0]
        self.assertIn("internal caller", output)
        self.assertIn("If a write fails", output)
        mock = (skills / "run-mock-exam" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Learning recap (separate from score)", mock)
        self.assertNotIn("Coverage (separate from score)", mock)
        self.assertNotIn("Report\n  correct-position counts", mock)
        close = (skills / "close-session" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Internal:", close)
        self.assertIn("Learner-facing:", close)
        self.assertIn("ask for confirmation before writing", close)
        evaluation = (skills / "coverage-audit" / "references" / "evaluation.md").read_text(
            encoding="utf-8",
        )
        self.assertIn("## Teacher-first conversation checks", evaluation)
        self.assertIn("do not claim tone is proven", evaluation)

    def test_close_session_plan_selection_contract_is_date_safe(self):
        close = (ROOT / ".github" / "skills" / "close-session" / "SKILL.md").read_text(encoding="utf-8")
        for rule in (
            "Reuse the retained plan path", "actual date ranges",
            "filter to plans covering today's date", "Exclude newer",
            "Use the sole date-matching plan", "multiple matches remain",
            "On pause/stop", "without asking a new question",
            "Any alternate plan needs the user's selection",
        ):
            self.assertIn(rule, close)
        self.assertNotIn("(most recent", close)

    def test_assets_are_private_by_default_except_shared_templates(self):
        cases = [
            ("assets/master-plan.json", True),
            ("assets/backups/progress.bak", True),
            ("assets/README.md", False),
        ]
        for exam in ("az-104", "az-305", "gh-300", "gh-600", "ai-500", "future-exam"):
            root = f"exams/{exam}/assets"
            cases.extend((f"{root}/{name}", True) for name in (
                "coverage.json.bak",
                "coverage.json.bak-20261004T194752",
                "mock50-state.md",
                "mock50-state.json",
                "backups/nested/session.data",
                "study-plans/sprint.json",
                "study-plans/nested/private-notes.md",
            ))
            cases.extend((f"{root}/{name}", False) for name in (
                "README.md", "study-plans/README.md",
            ))
        result = subprocess.run(
            ["git", "check-ignore", "--no-index", "--stdin", "-z"],
            input=("\0".join(path for path, _ in cases) + "\0").encode("utf-8"),
            cwd=ROOT, check=False, capture_output=True,
        )
        self.assertIn(result.returncode, (0, 1), result.stderr)
        ignored = set(result.stdout.decode("utf-8").split("\0"))
        for path, expected in cases:
            with self.subTest(path=path):
                self.assertEqual(path in ignored, expected)


if __name__ == "__main__":
    unittest.main()
