import { describe, it, expect } from "vitest";
import {
  extractTitle,
  extractRichText,
} from "../lib/notion.js";

/**
 * Unit tests for Notion property extraction logic.
 * Verifies that title-type and rich_text-type properties are correctly parsed
 * per @notionhq/client response structures. No external dependencies.
 */
describe("Notion property extraction", () => {
  describe("extractTitle", () => {
    it("extracts plain_text from title-type property", () => {
      const prop = {
        title: [{ plain_text: "The Great Gatsby", text: { content: "The Great Gatsby" } }],
      };
      expect(extractTitle(prop)).toBe("The Great Gatsby");
    });

    it("extracts text.content when plain_text is absent (title type)", () => {
      const prop = {
        title: [{ text: { content: "Alice's Adventures in Wonderland" } }],
      };
      expect(extractTitle(prop)).toBe("Alice's Adventures in Wonderland");
    });

    it("concatenates multiple title segments", () => {
      const prop = {
        title: [
          { plain_text: "The ", text: { content: "The " } },
          { plain_text: "Hobbit", text: { content: "Hobbit" } },
        ],
      };
      expect(extractTitle(prop)).toBe("The Hobbit");
    });

    it("returns empty string for empty or missing title", () => {
      expect(extractTitle({})).toBe("");
      expect(extractTitle({ title: [] })).toBe("");
    });
  });

  describe("extractRichText", () => {
    it("extracts plain_text from rich_text-type property", () => {
      const prop = {
        rich_text: [{ plain_text: "F. Scott Fitzgerald", text: { content: "F. Scott Fitzgerald" } }],
      };
      expect(extractRichText(prop)).toBe("F. Scott Fitzgerald");
    });

    it("extracts text.content when plain_text is absent (rich_text type)", () => {
      const prop = {
        rich_text: [{ text: { content: "Charles Scribner's Sons" } }],
      };
      expect(extractRichText(prop)).toBe("Charles Scribner's Sons");
    });

    it("concatenates multiple rich_text segments", () => {
      const prop = {
        rich_text: [
          { plain_text: "First ", text: { content: "First " } },
          { plain_text: "Edition", text: { content: "Edition" } },
        ],
      };
      expect(extractRichText(prop)).toBe("First Edition");
    });

    it("returns empty string for empty or missing rich_text", () => {
      expect(extractRichText({})).toBe("");
      expect(extractRichText({ rich_text: [] })).toBe("");
    });
  });

  describe("Notion API property object shapes", () => {
    it("handles full Notion title property response shape", () => {
      const notionTitleProp = {
        id: "abc123",
        type: "title",
        title: [
          {
            type: "text",
            text: { content: "The Great Gatsby", link: null },
            plain_text: "The Great Gatsby",
            href: null,
          },
        ],
      };
      expect(extractTitle(notionTitleProp)).toBe("The Great Gatsby");
    });

    it("handles full Notion rich_text property response shape", () => {
      const notionRichTextProp = {
        id: "def456",
        type: "rich_text",
        rich_text: [
          {
            type: "text",
            text: { content: "Scribner", link: null },
            plain_text: "Scribner",
            href: null,
          },
        ],
      };
      expect(extractRichText(notionRichTextProp)).toBe("Scribner");
    });
  });
});
