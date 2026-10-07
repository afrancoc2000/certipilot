"""Enforce separate, per-file line and branch floors on coverage.py JSON."""

import argparse
import json
from pathlib import Path
import sys


FLOORS = {
    ".github/skills/coverage-audit/scripts/coverage.py": (99, 98),
    ".github/skills/coverage-audit/scripts/session.py": (99, 98),
    ".github/check_coverage.py": (99, 98),
}
# Any other measured file (for example a newly added script) gets the same floor.
DEFAULT_FLOOR = (99, 98)


def check_report(report):
    if not isinstance(report, dict):
        raise ValueError("Coverage report must be an object")
    meta = report.get("meta")
    if not isinstance(meta, dict) or meta.get("branch_coverage") is not True:
        raise ValueError("Coverage report must include branch instrumentation")
    files = report.get("files")
    if not isinstance(files, dict):
        raise ValueError("Coverage report must include a files object")
    normalized = {}
    for name, entry in files.items():
        if not isinstance(name, str):
            raise ValueError("Coverage file names must be strings")
        path = name.replace("\\", "/")
        if path in normalized:
            raise ValueError(f"Duplicate coverage file: {path}")
        normalized[path] = entry
    failures = []
    results = []
    extras = {path: DEFAULT_FLOOR for path in sorted(normalized) if path not in FLOORS}
    for path, floors in {**FLOORS, **extras}.items():
        entry = normalized.get(path)
        if not isinstance(entry, dict) or not isinstance(entry.get("summary"), dict):
            raise ValueError(f"Missing coverage file or summary: {path}")
        summary = entry["summary"]
        for metric, covered_key, total_key, missing_key, floor in (
            ("lines", "covered_lines", "num_statements", "missing_lines", floors[0]),
            ("branches", "covered_branches", "num_branches", "missing_branches", floors[1]),
        ):
            counts = [summary.get(key) for key in (covered_key, total_key, missing_key)]
            if any(type(value) is not int or value < 0 for value in counts):
                raise ValueError(f"{path}: missing or invalid {metric} counts")
            covered, total, missing = counts
            if total == 0 or covered > total or covered + missing != total:
                raise ValueError(f"{path}: inconsistent or empty {metric} counts")
            result = f"{path}: {metric} {100 * covered / total:.2f}% (floor {floor}%)"
            results.append(result)
            # Compare counts, not rounded report percentages.
            if 100 * covered < floor * total:
                failures.append(result)
    if failures:
        raise ValueError("Coverage below required floors:\n" + "\n".join(failures))
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="coverage json report")
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        results = check_report(report)
    except (OSError, ValueError) as exc:
        print(f"Coverage gate failed: {exc}", file=sys.stderr)
        return 1
    print("\n".join(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
