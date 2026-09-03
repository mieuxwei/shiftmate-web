"""Build or verify every offline evaluation report."""

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"


def _load(name: str) -> ModuleType:
    path = ROOT / name / "evaluate.py"
    spec = importlib.util.spec_from_file_location(f"{name}_evaluate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load evaluator: {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def build_reports() -> dict[str, dict[str, object]]:
    ocr = _load("ocr").evaluate(
        _json(ROOT / "ocr/cases.json"),
        _json(ROOT / "ocr/synthetic_predictions.json"),
    )
    rag = _load("rag").evaluate(
        _json(ROOT / "rag/cases.json"),
        _json(ROOT / "rag/synthetic_predictions.json"),
    )
    routing = _load("routing").evaluate(_json(ROOT / "routing/cases.json"))
    return {"ocr": ocr, "rag": rag, "routing": routing}


def render_summary(reports: dict[str, dict[str, object]]) -> str:
    failures = _json(ROOT / "failure_modes/cases.json")
    lines = [
        "# Offline evaluation report",
        "",
        "Generated from versioned synthetic fixtures by `python evals/run.py`.",
        "No network, credential, database, paid platform, or live model is used.",
        "",
    ]
    for name, report in reports.items():
        lines.extend(
            [
                f"## {name.upper()}",
                "",
                (
                    f"Samples: {report['sample_count']}; failed cases: "
                    f"{report['failure_count']}."
                ),
                "",
                "Metrics:",
                "",
            ]
        )
        excluded = {"failures", "limitations", "sample_count", "failure_count"}
        for key, value in report.items():
            if key not in excluded:
                lines.append(f"- `{key}`: {json.dumps(value, ensure_ascii=False)}")
        lines.extend(["", "Observed failures:", ""])
        report_failures = report["failures"]
        if report_failures:
            for failure in report_failures:  # type: ignore[union-attr]
                serialized = json.dumps(failure, ensure_ascii=False)
                lines.append(f"- `{failure['id']}`: {serialized}")
        else:
            lines.append("- None in this fixture run.")
        lines.extend(["", "Limitations:", ""])
        for limitation in report["limitations"]:  # type: ignore[union-attr]
            lines.append(f"- {limitation}")
        lines.append("")
    lines.extend(["## Failure-mode coverage", ""])
    for case in failures:
        lines.append(
            f"- `{case['id']}` — {case['expected_behavior']} Test: `{case['test']}`"
        )
    lines.extend(
        [
            "",
            "These are deterministic failure-injection tests. The report does not "
            "claim",
            "availability or latency characteristics for Gemini, Supabase, or Google.",
            "",
        ]
    )
    return "\n".join(lines)


def expected_files() -> dict[Path, str]:
    reports = build_reports()
    files = {
        REPORTS / f"{name}.json": json.dumps(
            report, ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n"
        for name, report in reports.items()
    }
    files[REPORTS / "summary.md"] = render_summary(reports)
    return files


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if versioned reports differ from current fixtures and code.",
    )
    args = parser.parse_args()
    files = expected_files()
    if args.check:
        stale = [
            path
            for path, content in files.items()
            if not path.exists() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            names = ", ".join(str(path.relative_to(ROOT)) for path in stale)
            raise SystemExit(f"Stale evaluation reports: {names}")
        print(f"Verified {len(files)} versioned offline evaluation reports.")
        return
    REPORTS.mkdir(parents=True, exist_ok=True)
    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
    print(f"Wrote {len(files)} offline evaluation reports to {REPORTS}.")


if __name__ == "__main__":
    main()
