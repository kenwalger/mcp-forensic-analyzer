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
from collections import Counter
from pathlib import Path

# Add parent so we can import orchestrator
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from orchestrator import _get_prompts, run_forensic_audit

GOLDEN_DATASET_PATH = PROJECT_ROOT / "tests" / "golden_dataset.json"

_logger = logging.getLogger(__name__)

# Default weights if the_judge not loaded (must sum to 100)
_DEFAULT_RUBRIC_WEIGHTS = {
    "consistency": 20,
    "precision": 30,
    "recall": 30,
    "reasoning_quality": 20,
}


def _get_rubric_weights() -> dict[str, int]:
    """Load rubric weights from the_judge config; fallback to defaults."""
    try:
        prompts = _get_prompts()
        judge = prompts.get("the_judge", {}).get("judge", {})
        w = judge.get("rubric_weights")
        if w and isinstance(w, dict) and sum(w.values()) == 100:
            return {k: int(v) for k, v in w.items()}
    except Exception:
        pass
    return _DEFAULT_RUBRIC_WEIGHTS.copy()


def _parse_report(report: str) -> tuple[bool | None, list[dict[str, str]], bool]:
    """
    Extract consistency (PASS/FAIL) and discrepancies from report text.
    Returns (consistent, discrepancies, consistency_found).
    When consistency_found is False, consistent is None (format not recognized).
    """
    consistent: bool | None = None
    discrepancies: list[dict[str, str]] = []
    consistency_found = False

    # Match "Consistency: PASS" or "Consistency: FAIL"
    consistency_match = re.search(r"Consistency:\s*(PASS|FAIL)", report, re.IGNORECASE)
    if consistency_match:
        consistent = consistency_match.group(1).upper() == "PASS"
        consistency_found = True

    # Match discrepancy lines: " - [High/Medium/Low] field_name: ..." (no dedup; Counter handles multi-indicator)
    for m in re.finditer(
        r"-\s+\[(High|Medium|Low)\]\s+([\w_]+):", report, re.IGNORECASE
    ):
        discrepancies.append({"field": m.group(2), "severity": m.group(1)})

    return consistent, discrepancies, consistency_found


def _compute_precision_recall(
    expected: list[dict], actual: list[dict]
) -> tuple[float, float]:
    """
    Precision = TP/(TP+FP), Recall = TP/(TP+FN). Severity matched case-insensitively.
    Uses Counter to handle duplicate (field, severity) pairs correctly.
    """
    expected_count = Counter(
        (d["field"], d["severity"].lower()) for d in expected
    )
    actual_count = Counter(
        (d["field"], d["severity"].lower()) for d in actual
    )
    tp = sum((expected_count & actual_count).values())
    fp = sum((actual_count - expected_count).values())
    fn = sum((expected_count - actual_count).values())
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
    if re.search(r"Consistency:\s*(PASS|FAIL)", report, re.IGNORECASE):
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
        if "Discrepancies: None" in report or (
            "Discrepancies:" in report
            and re.search(r"\[(High|Medium|Low)\]", report, re.IGNORECASE) is None
        ):
            score += 25
        else:
            score += 10
    return min(100, score)


def _grade_report(report: str, case: dict) -> dict:
    """
    Judge Agent: grade output on Precision, Recall, Reasoning Quality.
    Uses rubric_weights from config/prompts_the_judge.yaml when available.
    When report format is unrecognized (no Consistency: line), applies
    conservative consistency score (0) and logs a warning.
    """
    expected_consistency = case.get("expected_consistency", True)
    expected_disc = case.get("expected_discrepancies", [])
    weights = _get_rubric_weights()

    consistent, actual_disc, consistency_found = _parse_report(report)

    # Consistency correctness
    if not consistency_found:
        _logger.warning(
            "Report format not recognized: no 'Consistency: PASS|FAIL' line found; "
            "applying conservative consistency score (0)"
        )
        consistency_score = 0
        consistency_correct = None  # unknown
    else:
        consistency_correct = consistent == expected_consistency
        consistency_score = 100 if consistency_correct else 0

    # Precision & Recall on discrepancies
    precision, recall = _compute_precision_recall(expected_disc, actual_disc)

    # Reasoning quality
    rq = _reasoning_quality(report, case)

    # Weighted overall from rubric_weights
    w_cons = weights.get("consistency", 20) / 100.0
    w_prec = weights.get("precision", 30) / 100.0
    w_rec = weights.get("recall", 30) / 100.0
    w_rq = weights.get("reasoning_quality", 20) / 100.0
    overall = (
        consistency_score * w_cons
        + precision * 100 * w_prec
        + recall * 100 * w_rec
        + rq * w_rq
    )

    out: dict = {
        "precision": round(precision * 100, 1),
        "recall": round(recall * 100, 1),
        "reasoning_quality": round(rq, 1),
        "consistency_correct": consistency_correct,
        "format_recognized": consistency_found,
        "overall": round(overall, 1),
    }
    return out


async def run_evaluation(provider: str = "none", verbose: bool = False) -> dict:
    """Run orchestrator against golden dataset and return graded results."""
    with open(GOLDEN_DATASET_PATH, encoding="utf-8") as f:
        data = json.load(f)
    cases = data.get("cases", [])

    async def _run_case(case: dict) -> dict:
        case_id = case.get("id", "unknown")
        report = await run_forensic_audit(
            case["title"],
            case.get("author"),
            case.get("observed"),
            provider=provider or None,
            book_standard=case.get("book_standard"),
        )
        grade = _grade_report(report, case)
        if verbose:
            print(f"\n--- {case_id} ---")
            print(f"  Overall: {grade['overall']}/100 (P={grade['precision']}, R={grade['recall']}, RQ={grade['reasoning_quality']})")
        return {
            "case_id": case_id,
            "description": case.get("description", ""),
            "expected_outcome": case.get("expected_outcome", ""),
            "grade": grade,
            "report_preview": report[:500] + "..." if len(report) > 500 else report,
        }

    raw = await asyncio.gather(
        *(_run_case(c) for c in cases), return_exceptions=True
    )
    results = []
    for i, r in enumerate(raw):
        if isinstance(r, BaseException):
            case_id = cases[i].get("id", "unknown") if i < len(cases) else "unknown"
            _logger.error("Case %s failed: %s", case_id, r, exc_info=r)
            results.append({
                "case_id": case_id,
                "description": cases[i].get("description", "") if i < len(cases) else "",
                "expected_outcome": cases[i].get("expected_outcome", "") if i < len(cases) else "",
                "grade": {
                    "overall": 0,
                    "precision": 0,
                    "recall": 0,
                    "reasoning_quality": 0,
                    "consistency_correct": None,
                    "format_recognized": False,
                    "error": str(r),
                },
                "report_preview": f"[Evaluation failed: {r}]",
            })
        else:
            results.append(r)

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
    parser.add_argument(
        "--threshold",
        type=int,
        default=70,
        help="Minimum average score to pass (default: 70)",
    )

    args = parser.parse_args()
    out = asyncio.run(run_evaluation(provider=args.provider, verbose=args.verbose))

    print(f"\nJudge Framework Evaluation")
    print(f"  Cases: {out['summary']['total_cases']}")
    print(f"  Average Score: {out['summary']['average_score']}/100")
    if args.verbose:
        for r in out["results"]:
            print(f"    {r['case_id']}: {r['grade']['overall']}/100")

    sys.exit(0 if out["summary"]["average_score"] >= args.threshold else 1)


if __name__ == "__main__":
    main()
