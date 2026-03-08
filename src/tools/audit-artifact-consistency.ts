import type { AuditReport, BookStandard, ObservedArtifact } from "../lib/schemas.js";
import {
  BookStandardSchema,
  ObservedArtifactSchema,
} from "../lib/schemas.js";
import { fetchBookStandard } from "../lib/notion.js";

/**
 * Forensic audit tool: compares observed physical artifact against Ground Truth
 * from the Master Bibliography.
 *
 * Severity hierarchy:
 * - High: first_edition_indicators or points_of_issue fail (typo/state mismatch indicates forgery or wrong edition)
 * - Low: other discrepancies (binding, paper, year, etc.)
 */

export interface AuditToolInput {
  /** Notion page ID in Master Bibliography; fetches BookStandard from Notion */
  book_standard_page_id?: string;
  /** Or provide BookStandard directly (overrides page_id if both present) */
  book_standard?: unknown;
  /** Observed state of the physical artifact */
  observed: unknown;
  /** Optional: summary of recent market/sales context for the report */
  market_context?: string;
}

function normalizeStrings(arr: string[]): string[] {
  return arr
    .map((s) => s.toLowerCase().trim())
    .filter(Boolean);
}

/**
 * One-directional substring matching: a match occurs only when the observed value
 * contains the full expected standard (o.includes(e)). We intentionally do NOT
 * use e.includes(o), because a short or vague observed string (e.g. "j") would
 * falsely match a longer expected standard (e.g. "lowercase j on page 10"),
 * silently suppressing High-severity discrepancies. A production system would
 * require normalized tokens (tokenization, stemming) for stricter forensic accuracy.
 */
function containsMatch(expected: string, observedList: string[]): boolean {
  const e = expected.toLowerCase().trim();
  const normalized = normalizeStrings(observedList);
  return normalized.some((o) => o.includes(e));
}

export async function executeAuditArtifactConsistency(
  args: AuditToolInput
): Promise<AuditReport> {
  const observed = ObservedArtifactSchema.parse(args.observed);

  let standard: BookStandard;
  if (args.book_standard) {
    standard = BookStandardSchema.parse(args.book_standard);
  } else if (args.book_standard_page_id) {
    standard = await fetchBookStandard(args.book_standard_page_id);
  } else {
    throw new Error(
      "Either book_standard or book_standard_page_id is required"
    );
  }

  const discrepancies: AuditReport["discrepancies"] = [];
  let isConsistent = true;

  // 1. Check first_edition_indicators first – failures = High severity
  for (const expected of standard.first_edition_indicators) {
    if (!containsMatch(expected, observed.first_edition_indicators_observed)) {
      discrepancies.push({
        field: "first_edition_indicators",
        expected,
        observed: observed.first_edition_indicators_observed.join("; ") || "(none observed)",
        severity: "High",
      });
      isConsistent = false;
    }
  }

  // 2. Check points_of_issue – failures = High severity (typo mismatch indicates forgery/wrong state)
  for (const expected of standard.points_of_issue) {
    if (!containsMatch(expected, observed.points_of_issue_observed)) {
      discrepancies.push({
        field: "points_of_issue",
        expected,
        observed: observed.points_of_issue_observed.join("; ") || "(none observed)",
        severity: "High",
      });
      isConsistent = false;
    }
  }

  // 3. Other checks – Low severity
  if (
    standard.expected_first_edition_year &&
    observed.observed_year !== undefined &&
    observed.observed_year !== standard.expected_first_edition_year
  ) {
    discrepancies.push({
      field: "expected_first_edition_year",
      expected: String(standard.expected_first_edition_year),
      observed: String(observed.observed_year),
      severity: "Low",
    });
    isConsistent = false;
  }

  if (
    standard.binding_type &&
    observed.binding_type_observed &&
    !observed.binding_type_observed
      .toLowerCase()
      .includes(standard.binding_type.toLowerCase())
  ) {
    discrepancies.push({
      field: "binding_type",
      expected: standard.binding_type,
      observed: observed.binding_type_observed,
      severity: "Low",
    });
    isConsistent = false;
  }

  if (standard.paper_watermark && observed.paper_watermark_observed) {
    if (
      !observed.paper_watermark_observed
        .toLowerCase()
        .includes(standard.paper_watermark.toLowerCase())
    ) {
      discrepancies.push({
        field: "paper_watermark",
        expected: standard.paper_watermark,
        observed: observed.paper_watermark_observed,
        severity: "Low",
      });
      isConsistent = false;
    }
  }

  // Confidence: penalize by severity. High (first_edition_indicators, points_of_issue)
  // receives significant deduction; Low (year, binding, paper) receives minor deduction.
  const highCount = discrepancies.filter((d) => d.severity === "High").length;
  const lowCount = discrepancies.filter((d) => d.severity === "Low").length;
  const confidenceScore = Math.max(
    0,
    100 - highCount * 45 - lowCount * 5
  );

  return {
    is_consistent: isConsistent,
    confidence_score: confidenceScore,
    discrepancies,
    market_context:
      args.market_context ??
      "(No market context provided)",
  };
}
