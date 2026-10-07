import contextlib
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


GATE_PATH = Path(__file__).resolve().parents[3] / "check_coverage.py"
SPEC = importlib.util.spec_from_file_location("ci_coverage_gate", GATE_PATH)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def report():
    return {
        "meta": {"branch_coverage": True},
        "files": {
            path: {"summary": {
                "covered_lines": line_floor * 1000,
                "num_statements": 100000,
                "missing_lines": (100 - line_floor) * 1000,
                "covered_branches": branch_floor * 1000,
                "num_branches": 100000,
                "missing_branches": (100 - branch_floor) * 1000,
                "percent_covered": 100,
            }}
            for path, (line_floor, branch_floor) in gate.FLOORS.items()
        },
    }


class CICoverageGateTests(unittest.TestCase):
    def test_all_three_production_scripts_have_independent_floors(self):
        self.assertEqual(gate.FLOORS, {
            ".github/skills/coverage-audit/scripts/coverage.py": (99, 98),
            ".github/skills/coverage-audit/scripts/session.py": (99, 98),
            ".github/check_coverage.py": (99, 98),
        })

    def test_executable_entry_point_checks_all_three_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.json"
            path.write_text(json.dumps(report()), encoding="utf-8")
            out = io.StringIO()
            with patch.object(sys, "argv", [str(GATE_PATH), str(path)]):
                with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as raised:
                    runpy.run_path(str(GATE_PATH), run_name="__main__")
            self.assertEqual(raised.exception.code, 0)
            self.assertEqual(len(out.getvalue().splitlines()), 6)

    def test_exact_floors_pass(self):
        self.assertEqual(len(gate.check_report(report())), 6)

    def test_unlisted_measured_file_gets_the_default_floor(self):
        data = report()
        summary = deepcopy(next(iter(data["files"].values()))["summary"])
        data["files"][".github/new_script.py"] = {"summary": summary}
        self.assertEqual(len(gate.check_report(data)), 8)
        summary["covered_lines"] -= 1
        summary["missing_lines"] += 1
        with self.assertRaisesRegex(ValueError, "new_script.py: lines"):
            gate.check_report(data)

    def test_above_floors_pass(self):
        data = report()
        for entry in data["files"].values():
            for metric in ("lines", "branches"):
                entry["summary"][f"covered_{metric}"] += 1
                entry["summary"][f"missing_{metric}"] -= 1
        self.assertEqual(len(gate.check_report(data)), 6)

    def test_each_floor_is_independent_and_not_rounded(self):
        for path in gate.FLOORS:
            for metric in ("lines", "branches"):
                with self.subTest(path=path, metric=metric):
                    data = report()
                    summary = data["files"][path]["summary"]
                    summary[f"covered_{metric}"] -= 1
                    summary[f"missing_{metric}"] += 1
                    with self.assertRaisesRegex(ValueError, "below required floors"):
                        gate.check_report(data)

    def test_all_failing_floors_are_reported(self):
        data = report()
        for entry in data["files"].values():
            for metric in ("lines", "branches"):
                entry["summary"][f"covered_{metric}"] -= 1
                entry["summary"][f"missing_{metric}"] += 1
        with self.assertRaises(ValueError) as raised:
            gate.check_report(data)
        for path in gate.FLOORS:
            for metric in ("lines", "branches"):
                self.assertIn(f"{path}: {metric}", str(raised.exception))

    def test_windows_report_paths_pass(self):
        data = report()
        data["files"] = {name.replace("/", "\\"): entry for name, entry in data["files"].items()}
        self.assertEqual(len(gate.check_report(data)), 6)

    def test_duplicate_normalized_paths_fail(self):
        data = report()
        path = next(iter(gate.FLOORS))
        data["files"][path.replace("/", "\\")] = data["files"][path]
        with self.assertRaisesRegex(ValueError, "Duplicate coverage file"):
            gate.check_report(data)

    def test_missing_files_and_summaries_fail(self):
        for path in gate.FLOORS:
            for replacement in (None, {}, {"summary": None}, {"summary": []}):
                with self.subTest(path=path, replacement=replacement):
                    data = report()
                    data["files"][path] = replacement
                    with self.assertRaisesRegex(ValueError, "Missing coverage file or summary"):
                        gate.check_report(data)
            data = report()
            del data["files"][path]
            with self.assertRaisesRegex(ValueError, "Missing coverage file or summary"):
                gate.check_report(data)

    def test_same_basename_elsewhere_cannot_satisfy_required_file(self):
        data = report()
        path = next(iter(gate.FLOORS))
        data["files"][Path(path).name] = data["files"].pop(path)
        with self.assertRaisesRegex(ValueError, "Missing coverage file"):
            gate.check_report(data)

    def test_missing_or_disabled_branch_instrumentation_fails(self):
        for meta in (None, {}, [], {"branch_coverage": False}, {"branch_coverage": 1}):
            with self.subTest(meta=meta):
                data = report()
                data["meta"] = meta
                with self.assertRaisesRegex(ValueError, "branch instrumentation"):
                    gate.check_report(data)

    def test_invalid_report_shape_fails(self):
        for data in (None, [], "", {"meta": {"branch_coverage": True}},
                     {"meta": {"branch_coverage": True}, "files": []}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                gate.check_report(data)

    def test_nontext_file_name_fails_explicitly(self):
        data = report()
        data["files"][1] = {}
        with self.assertRaisesRegex(ValueError, "file names must be strings"):
            gate.check_report(data)

    def test_missing_or_invalid_counts_fail_closed(self):
        for path in gate.FLOORS:
            for key in ("covered_lines", "num_statements", "missing_lines",
                        "covered_branches", "num_branches", "missing_branches"):
                for value in (None, -1, True, "100", 100.0, float("nan"), float("inf")):
                    with self.subTest(path=path, key=key, value=value):
                        data = report()
                        data["files"][path]["summary"][key] = value
                        with self.assertRaisesRegex(ValueError, "invalid .* counts"):
                            gate.check_report(data)
                data = report()
                del data["files"][path]["summary"][key]
                with self.assertRaisesRegex(ValueError, "invalid .* counts"):
                    gate.check_report(data)

    def test_empty_and_inconsistent_counts_fail(self):
        for path in gate.FLOORS:
            for covered_key, total_key, missing_key in (
                ("covered_lines", "num_statements", "missing_lines"),
                ("covered_branches", "num_branches", "missing_branches"),
            ):
                for counts in ((0, 0, 0), (101, 100, 0), (94, 100, 1)):
                    with self.subTest(path=path, metric=covered_key, counts=counts):
                        data = report()
                        data["files"][path]["summary"].update(
                            zip((covered_key, total_key, missing_key), counts),
                        )
                        with self.assertRaisesRegex(ValueError, "inconsistent or empty"):
                            gate.check_report(data)

    def test_cli_missing_malformed_and_unreadable_report_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.json"
            for content in (None, "{invalid", "null", "[]"):
                with self.subTest(content=content):
                    if content is not None:
                        path.write_text(content, encoding="utf-8")
                    stderr = io.StringIO()
                    with contextlib.redirect_stderr(stderr):
                        self.assertEqual(gate.main([str(path)]), 1)
                    self.assertIn("Coverage gate failed:", stderr.getvalue())
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(gate.main([directory]), 1)

    def test_cli_exit_codes_and_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "coverage.json"
            good = report()
            bad = deepcopy(good)
            summary = next(iter(bad["files"].values()))["summary"]
            summary["covered_branches"] -= 1
            summary["missing_branches"] += 1
            for data, expected in ((good, 0), (bad, 1)):
                with self.subTest(expected=expected):
                    path.write_text(json.dumps(data), encoding="utf-8")
                    result = subprocess.run(
                        [sys.executable, "-B", str(GATE_PATH), str(path)],
                        check=False, capture_output=True, text=True,
                    )
                    self.assertEqual(result.returncode, expected, result.stderr)
                    if expected:
                        self.assertEqual(result.stdout, "")
                        self.assertIn("below required floors", result.stderr)
                    else:
                        self.assertEqual(result.stderr, "")
                        self.assertEqual(len(result.stdout.splitlines()), 6)


if __name__ == "__main__":
    unittest.main()
