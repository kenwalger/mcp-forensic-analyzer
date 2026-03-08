/**
 * Generates a high-fidelity Markdown string formatted as a physical museum placard.
 * Inputs: book_data, audit_results, market_citation.
 * Sections: Archival Description, Forensic Verification Summary, Valuation Context.
 */

export interface GenerateExhibitLabelInput {
  book_data: Record<string, unknown>;
  audit_results: Record<string, unknown>;
  market_citation: string;
}

const DISCLAIMER = `⚠️ Disclaimer: Archival Intelligence is an MCP-based decision-support tool. Valuations are based on connected sample databases and historical auction results. Professional physical appraisal is always required for high-value asset transactions.`;

function getString(obj: Record<string, unknown>, ...keys: string[]): string {
  for (const k of keys) {
    const v = obj[k];
    if (typeof v === "string" && v.trim()) return v;
  }
  return "";
}

function getNumber(obj: Record<string, unknown>, ...keys: string[]): number | undefined {
  for (const k of keys) {
    const v = obj[k];
    if (typeof v === "number") return v;
  }
  return undefined;
}

function getArray(obj: Record<string, unknown>, key: string): unknown[] {
  const v = obj[key];
  if (Array.isArray(v)) return v;
  return [];
}

/** Build Archival Description section from book_data. */
function buildArchivalDescription(bookData: Record<string, unknown>): string {
  const title =
    getString(bookData, "title", "Title") ||
    (typeof bookData.title === "string" ? (bookData.title as string) : "Untitled");
  const author = getString(bookData, "author", "Author");
  const publisher = getString(bookData, "publisher", "Publisher");
  const year =
    getNumber(bookData, "expected_first_edition_year", "publicationYear", "year") ??
    getNumber(bookData, "Publication Year");
  const binding = getString(bookData, "binding_type", "binding");
  const edition = getString(bookData, "edition", "Edition");

  const lines: string[] = [];
  lines.push(`**${title}**`);
  if (author) lines.push(author);
  if (publisher || year) {
    const parts = [publisher, year ? String(year) : ""].filter(Boolean);
    lines.push(parts.join(" · "));
  }
  if (edition) lines.push(edition);
  if (binding) lines.push(`Binding: ${binding}`);

  return lines.join("\n\n");
}

/** Build Forensic Verification Summary from audit_results. */
function buildForensicSummary(auditResults: Record<string, unknown>): string {
  const result = getString(auditResults, "result", "overall_result");
  const confidence = getNumber(auditResults, "confidence_score", "confidence");
  const isConsistent = auditResults.is_consistent === true;
  const discrepancies = getArray(auditResults, "discrepancies");

  const lines: string[] = [];
  if (result || isConsistent !== undefined) {
    const status = result || (isConsistent ? "Pass" : "Flagged");
    lines.push(`**Verification status:** ${status}`);
  }
  if (confidence != null) {
    lines.push(`**Confidence score:** ${confidence}%`);
  }
  if (Array.isArray(discrepancies) && discrepancies.length > 0) {
    lines.push("");
    lines.push("**Findings:**");
    for (const d of discrepancies) {
      const dObj = typeof d === "object" && d !== null ? (d as Record<string, unknown>) : {};
      const sev = getString(dObj, "severity", "Severity");
      const field = getString(dObj, "field", "Field");
      const obs = getString(dObj, "observed", "Observed");
      const exp = getString(dObj, "expected", "Expected");
      const parts = [sev, field, exp && obs ? `Expected "${exp}"; observed "${obs}"` : obs || exp].filter(
        Boolean
      );
      lines.push(`- ${parts.join(" — ")}`);
    }
  }

  return lines.length > 0 ? lines.join("\n") : "No forensic data provided.";
}

/** Build Valuation Context section with market_citation. */
function buildValuationContext(marketCitation: string): string {
  if (!marketCitation.trim()) {
    return "Valuation context not available.";
  }
  return `Valuation informed by:\n\n${marketCitation.trim()}`;
}

export function executeGenerateExhibitLabel(
  args: GenerateExhibitLabelInput
): string {
  const bookData = args.book_data ?? {};
  const auditResults = args.audit_results ?? {};
  const marketCitation = args.market_citation ?? "";

  const lines: string[] = [];

  lines.push("# Exhibit Label");
  lines.push("");

  lines.push("## Archival Description");
  lines.push("");
  lines.push(buildArchivalDescription(bookData as Record<string, unknown>));
  lines.push("");
  lines.push("---");
  lines.push("");

  lines.push("## Forensic Verification Summary");
  lines.push("");
  lines.push(buildForensicSummary(auditResults as Record<string, unknown>));
  lines.push("");
  lines.push("---");
  lines.push("");

  lines.push("## Valuation Context");
  lines.push("");
  lines.push(buildValuationContext(marketCitation));
  lines.push("");
  lines.push("---");
  lines.push("");
  lines.push(DISCLAIMER);

  return lines.join("\n");
}
