#!/usr/bin/env python3
"""
Judge Framework Evaluator

Runs the forensic orchestrator against tests/golden_dataset.json and grades
each output on a rubric of Precision, Recall, and Reasoning Quality (0-100).
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

# Add parent so we can import orchestrator
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from orchestrator import run_forensic_audit

GOLDEN_DATASET_PATH = PROJECT_ROOT / "tests" / "golden_dataset.json"


def _parse_report(report: str) -> tuple[bool, list[dict[str, str]]]:
    """Extract consistency (PASS/FAIL) and discrepancies from report text."""
    consistent = True
    discrepancies: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    # Match "Consistency: PASS" or "Consistency: FAIL"
    consistency_match = re.search(r"Consistency:\s*(PASS|FAIL)", report, re.IGNORECASE)
    if consistency_match:
        consistent = consistency_match.group(1).upper() == "PASS"

    # Match discrepancy lines: "    - [High] field_name: ..." or "- [Low] expected_first_edition_year: ..."
    for m in re.finditer(r"-\s+\[(High|Low)\]\s+([\w_]+):", report):
        key = (m.group(2), m.group(1))
        if key not in seen:
            seen.add(key)
            discrepancies.append({"field": m.group(2), "severity": m.group(1)})

    return consistent, discrepancies


def _compute_precision_recall(
    expected: list[dict], actual: list[dict]
) -> tuple[float, float]:
    """Precision = TP/(TP+FP), Recall = TP/(TP+FN)."""
    expected_set = {(d["field"], d["severity"]) for d in expected}
    actual_set = {(d["field"], d["severity"]) for d in actual}
    tp = len(expected_set & actual_set)
    fp = len(actual_set - expected_set)
    fn = len(expected_set - actual_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    return precision, recall


def _reasoning_quality(report: str, case: dict) -> float:
    """
    Heuristic score 0-100 for report structure and completeness.
    Checks: required sections, consistency verdict, discrepancy handling.
    """
    score = 0.0
    # Has key sections (each ~20 pts)
    if "LIBRARIAN FINDINGS" in report:
        score += 20
    if "ANALYST FINDINGS" in report:
        score += 20
    if "Consistency:" in report and ("PASS" in report or "FAIL" in report):
        score += 20
    if "Confidence:" in report:
        score += 15
    # For clean cases: "Discrepancies: None" is good
    # For error cases: should list discrepancies
    expected_disc = case.get("expected_discrepancies", [])
    if expected_disc:
        if "Discrepancies:" in report and "None" not in report.split("Discrepancies:")[1].split("\n")[0]:
            score += 25
        else:
            score += 10  # partial
    else:
        if "Discrepancies: None" in report or ("Discrepancies:" in report and len(re.finditer(r"\[(High|Low)\]", report)) == 0):
            score += 25
        else:
            score += 10
    return min(100, score)


def _grade_report(report: str, case: dict) -> dict:
    """Judge Agent: grade output on Precision, Recall, Reasoning Quality."""
    expected_consistency = case.get("expected_consistency", True)
    expected_disc = case.get("expected_discrepancies", [])

    consistent, actual_disc = _parse_report(report)

    # Consistency correctness
    consistency_correct = consistent == expected_consistency

    # Precision & Recall on discrepancies
    precision, recall = _compute_precision_recall(expected_disc, actual_disc)

    # Reasoning quality
    rq = _reasoning_quality(report, case)

    # Weighted overall: Consistency (20), Precision (30), Recall (30), RQ (20)
    consistency_score = 100 if consistency_correct else 0
    overall = (
        consistency_score * 0.2
        + precision * 100 * 0.3
        + recall * 100 * 0.3
        + rq * 0.2
    )

    return {
        "precision": round(precision * 100, 1),
        "recall": round(recall * 100, 1),
        "reasoning_quality": round(rq, 1),
        "consistency_correct": consistency_correct,
        "overall": round(overall, 1),
    }


async def run_evaluation(provider: str = "none", verbose: bool = False) -> dict:
    """Run orchestrator against golden dataset and return graded results."""
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)
    cases = data.get("cases", [])

    results = []
    for case in cases:
        case_id = case.get("id", "unknown")
        title = case["title"]
        author = case.get("author")
        observed = case.get("observed")

        report = await run_forensic_audit(
            title, author, observed, provider=provider or None
        )
        grade = _grade_report(report, case)

        results.append({
            "case_id": case_id,
            "description": case.get("description", ""),
            "expected_outcome": case.get("expected_outcome", ""),
            "grade": grade,
            "report_preview": report[:500] + "..." if len(report) > 500 else report,
        })
        if verbose:
            print(f"\n--- {case_id} ---")
            print(f"  Overall: {grade['overall']}/100 (P={grade['precision']}, R={grade['recall']}, RQ={grade['reasoning_quality']})")

    avg_overall = sum(r["grade"]["overall"] for r in results) / len(results) if results else 0
    return {
        "summary": {
            "total_cases": len(results),
            "average_score": round(avg_overall, 1),
        },
        "results": results,
    }


def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(name)s: %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Judge Framework: evaluate orchestrator on golden dataset")
    parser.add_argument(
        "--provider",
        default="none",
        choices=["anthropic", "openai", "ollama", "lm_studio", "none"],
        help="LLM provider for report synthesis (default: deterministic)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Print per-case grades")

    args = parser.parse_args()
    out = asyncio.run(run_evaluation(provider=args.provider, verbose=args.verbose))

    print(f"\nJudge Framework Evaluation")
    print(f"  Cases: {out['summary']['total_cases']}")
    print(f"  Average Score: {out['summary']['average_score']}/100")
    if args.verbose:
        for r in out["results"]:
            print(f"    {r['case_id']}: {r['grade']['overall']}/100")

    sys.exit(0 if out["summary"]["average_score"] >= 70 else 1)


if __name__ == "__main__":
    main()
