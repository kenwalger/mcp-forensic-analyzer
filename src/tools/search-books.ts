import { searchBooks } from "../lib/notion.js";
import { BookSearchParamsSchema } from "../lib/schemas.js";

export const searchBooksTool = {
  name: "search_books",
  description:
    "Search the rare books database in Notion. Filter by author, publication year range, condition, or text query.",
  inputSchema: {
    type: "object" as const,
    properties: {
      query: {
        type: "string",
        description: "Full-text search query",
      },
      author: {
        type: "string",
        description: "Filter by author name",
      },
      minYear: {
        type: "number",
        description: "Minimum publication year",
      },
      maxYear: {
        type: "number",
        description: "Maximum publication year",
      },
      condition: {
        type: "string",
        enum: ["mint", "fine", "very_good", "good", "fair", "poor"],
        description: "Book condition filter",
      },
      limit: {
        type: "number",
        description: "Maximum number of results (default 10, max 100)",
        default: 10,
      },
    },
  },
};

export async function executeSearchBooks(args: unknown) {
  const params = BookSearchParamsSchema.parse(args);
  const response = await searchBooks(params);
  return {
    results: response.results,
    has_more: response.has_more,
    next_cursor: response.next_cursor ?? undefined,
  };
}
