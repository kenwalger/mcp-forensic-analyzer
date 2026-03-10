import { z } from "zod";

// =============================================================================
// GENERAL SEARCH PATH – BookMetadataSchema for Notion DB entries & search_books
// =============================================================================

export const BookMetadataSchema = z.object({
  title: z.string().min(1, "Title is required"),
  author: z.string().optional(),
  publicationYear: z.number().int().min(1000).max(2100).optional(),
  publisher: z.string().optional(),
  isbn: z.string().optional(),
  condition: z
    .enum(["mint", "fine", "very_good", "good", "fair", "poor"])
    .optional(),
  edition: z.string().optional(),
  language: z.string().optional(),
  notes: z.string().optional(),
  estimatedValue: z.number().positive().optional(),
});

export type BookMetadata = z.infer<typeof BookMetadataSchema>;

export const BookSearchParamsSchema = z.object({
  query: z.string().optional(),
  author: z.string().optional(),
  minYear: z.number().int().optional(),
  maxYear: z.number().int().optional(),
  condition: z
    .enum(["mint", "fine", "very_good", "good", "fair", "poor"])
    .optional(),
  limit: z.number().int().min(1).max(100).default(10),
  startCursor: z.string().optional(),
});

export type BookSearchParams = z.infer<typeof BookSearchParamsSchema>;

// =============================================================================
// FORENSIC AUDIT PATH – BookStandardSchema as Ground Truth from Master Bibliography
// =============================================================================
//
// Severity hierarchy for audit_artifact_consistency:
// - High: first_edition_indicators or points_of_issue fail (typo/state mismatch indicates forgery or wrong edition)
// - Low: other discrepancies (binding, paper, year, etc.)
// Points of Issue discrepancies receive HIGH severity with significant confidence deduction.
//

export const BookStandardSchema = z.object({
  title: z.string(),
  author: z.string(),
  publisher: z.string(),
  expected_first_edition_year: z.number(),
  binding_type: z.enum(["Leather", "Cloth", "Paper Wrap", "Vellum"]),
  first_edition_indicators: z
    .array(z.string())
    .describe(
      "High-level bibliographic markers (e.g. '1925 on title page', 'Scribner seal on verso')"
    ),
  points_of_issue: z
    .array(z.string())
    .describe(
      "Microscopic forensic 'states' (e.g. 'lowercase j on page 10', 'typo \"wade\" on page 21')"
    ),
  paper_watermark: z.string().optional(),
});

export type BookStandard = z.infer<typeof BookStandardSchema>;

/** Observed state of a physical artifact for forensic comparison */
export const ObservedArtifactSchema = z.object({
  first_edition_indicators_observed: z.array(z.string()),
  points_of_issue_observed: z.array(z.string()),
  observed_year: z.number().optional(),
  binding_type_observed: z.string().optional(),
  paper_watermark_observed: z.string().optional(),
});

export type ObservedArtifact = z.infer<typeof ObservedArtifactSchema>;

/** Aligns with analyst prompt (LOW/MEDIUM/HIGH); audit tool currently emits Low | High only */
export const AuditSeverity = z.enum(["Low", "Medium", "High"]);
export type AuditSeverity = z.infer<typeof AuditSeverity>;

export const AuditReportSchema = z.object({
  is_consistent: z.boolean(),
  confidence_score: z.number().min(0).max(100),
  discrepancies: z.array(
    z.object({
      field: z.string(),
      expected: z.string(),
      observed: z.string(),
      severity: AuditSeverity,
    })
  ),
  market_context: z
    .string()
    .describe("Summary of recent Notion sales data for this item"),
});

export type AuditReport = z.infer<typeof AuditReportSchema>;
