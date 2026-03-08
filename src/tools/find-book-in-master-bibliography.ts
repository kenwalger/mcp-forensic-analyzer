import { findBookStandardInMasterBibliography, fetchBookStandard } from "../lib/notion.js";
import type { BookStandard } from "../lib/schemas.js";

export interface FindBookInput {
  title: string;
  author?: string;
}

export interface FindBookResult {
  found: boolean;
  message: string;
  page_ids?: string[];
  book_standards?: BookStandard[];
}

/**
 * Find a book in the Master Bibliography. Returns gracefully when not found,
 * suggesting the user add it to Notion first to enable forensic auditing.
 */
export async function executeFindBookInMasterBibliography(
  args: FindBookInput
): Promise<FindBookResult> {
  const pageIds = await findBookStandardInMasterBibliography(
    args.title,
    args.author
  );

  if (pageIds.length === 0) {
    return {
      found: false,
      message:
        "This book was not found in the Master Bibliography. To enable forensic auditing, please add it to your Master Bibliography database in Notion first. Include Title, Author, Publisher, Expected First Edition Year, Binding Type, First Edition Indicators, and Points of Issue.",
    };
  }

  // Optionally fetch full BookStandards for convenience
  const bookStandards = await Promise.all(
    pageIds.map((id) => fetchBookStandard(id))
  );

  return {
    found: true,
    message: `Found ${pageIds.length} matching entr${pageIds.length === 1 ? "y" : "ies"} in the Master Bibliography.`,
    page_ids: pageIds,
    book_standards: bookStandards,
  };
}
