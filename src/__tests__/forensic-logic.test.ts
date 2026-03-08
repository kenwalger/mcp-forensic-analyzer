import { describe, it, expect, vi, beforeEach } from "vitest";
import { executeAuditArtifactConsistency } from "../tools/audit-artifact-consistency.js";

vi.mock("../lib/notion.js", () => ({
  fetchBookStandard: vi.fn(),
}));

describe("audit_artifact_consistency", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const baseBookStandard = {
    title: "The Great Gatsby",
    author: "F. Scott Fitzgerald",
    publisher: "Scribner",
    expected_first_edition_year: 1925,
    binding_type: "Cloth" as const,
    first_edition_indicators: ["1925 on title page", "Scribner seal on verso"],
    points_of_issue: ['typo "wade" on page 21', "lowercase j on page 10"],
  };

  it("returns consistent when all points of issue match", async () => {
    const result = await executeAuditArtifactConsistency({
      book_standard: baseBookStandard,
      observed: {
        first_edition_indicators_observed: ["1925 on title page", "Scribner seal on verso"],
        points_of_issue_observed: ['typo "wade" on page 21', "lowercase j on page 10"],
      },
    });

    expect(result.is_consistent).toBe(true);
    expect(result.discrepancies).toHaveLength(0);
    expect(result.confidence_score).toBe(100);
  });

  it("returns High severity discrepancy when Point of Issue typo is wrong (e.g. wabe vs wade)", async () => {
    const result = await executeAuditArtifactConsistency({
      book_standard: baseBookStandard,
      observed: {
        first_edition_indicators_observed: ["1925 on title page", "Scribner seal on verso"],
        points_of_issue_observed: ['typo "wabe" on page 21', "lowercase j on page 10"],
      },
    });

    expect(result.is_consistent).toBe(false);
    const pointsDiscrepancy = result.discrepancies.find((d) => d.field === "points_of_issue");
    expect(pointsDiscrepancy).toBeDefined();
    expect(pointsDiscrepancy?.severity).toBe("High");
    expect(pointsDiscrepancy?.expected).toContain("wade");
    expect(pointsDiscrepancy?.observed).toContain("wabe");
  });

  it("returns High severity when Point of Issue is missing entirely", async () => {
    const result = await executeAuditArtifactConsistency({
      book_standard: baseBookStandard,
      observed: {
        first_edition_indicators_observed: ["1925 on title page"],
        points_of_issue_observed: [],
      },
    });

    expect(result.is_consistent).toBe(false);
    const pointsDiscrepancies = result.discrepancies.filter((d) => d.field === "points_of_issue");
    expect(pointsDiscrepancies).toHaveLength(2);
    expect(pointsDiscrepancies.every((d) => d.severity === "High")).toBe(true);
  });

  it("returns High severity when first_edition_indicators fail", async () => {
    const result = await executeAuditArtifactConsistency({
      book_standard: baseBookStandard,
      observed: {
        first_edition_indicators_observed: ["1926 on title page"],
        points_of_issue_observed: ['typo "wade" on page 21', "lowercase j on page 10"],
      },
    });

    expect(result.is_consistent).toBe(false);
    const indicatorDiscrepancy = result.discrepancies.find(
      (d) => d.field === "first_edition_indicators"
    );
    expect(indicatorDiscrepancy?.severity).toBe("High");
  });

  it("returns Low severity for year mismatch", async () => {
    const result = await executeAuditArtifactConsistency({
      book_standard: baseBookStandard,
      observed: {
        first_edition_indicators_observed: ["1925 on title page", "Scribner seal on verso"],
        points_of_issue_observed: ['typo "wade" on page 21', "lowercase j on page 10"],
        observed_year: 1926,
      },
    });

    expect(result.is_consistent).toBe(false);
    const yearDiscrepancy = result.discrepancies.find(
      (d) => d.field === "expected_first_edition_year"
    );
    expect(yearDiscrepancy?.severity).toBe("Low");
  });

  it("flags High severity when observed value is too vague (prevents false-negative)", async () => {
    const result = await executeAuditArtifactConsistency({
      book_standard: baseBookStandard,
      observed: {
        first_edition_indicators_observed: ["1925 on title page", "Scribner seal on verso"],
        points_of_issue_observed: ["j"],
      },
    });

    expect(result.is_consistent).toBe(false);
    const pointsDiscrepancies = result.discrepancies.filter((d) => d.field === "points_of_issue");
    expect(pointsDiscrepancies.length).toBeGreaterThanOrEqual(1);
    const vagueDiscrepancy = pointsDiscrepancies.find(
      (d) => d.expected === "lowercase j on page 10" && d.observed === "j"
    );
    expect(vagueDiscrepancy).toBeDefined();
    expect(vagueDiscrepancy?.severity).toBe("High");
  });

  it("reduces confidence_score based on discrepancy count and severity", async () => {
    const result = await executeAuditArtifactConsistency({
      book_standard: baseBookStandard,
      observed: {
        first_edition_indicators_observed: [],
        points_of_issue_observed: [],
      },
    });

    expect(result.confidence_score).toBeLessThan(100);
    expect(result.confidence_score).toBeGreaterThanOrEqual(0);
  });
});
