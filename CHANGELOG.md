# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.12.0] - 2026-03-10

### Added

- **LLM provider abstraction** – `orchestrator.py` now supports cloud and local LLMs via `--provider`:
  - Cloud: `anthropic`, `openai` (require API keys)
  - Local SLMs: `ollama`, `lm_studio` (Ollama or LM Studio running locally)
  - `none` for deterministic report only (no LLM synthesis)
- **get_model_client(provider)** – Abstract factory returning an async callable for LLM completion; unifies provider-specific APIs.
- **Instruction-Tuning block for local SLMs** – Ollama and LM Studio providers prepend an explicit Chain of Thought system prompt (`LOCAL_SLM_SYSTEM_PREFIX`) so SLMs handle MCP tool schema output correctly. Cloud models infer structure; smaller models need step-by-step guidance. All local inference logic tagged with `# [Post 3 - Edge AI]` comments.
- **LLM-powered report synthesis** – When a provider is set, the Supervisor uses the LLM to synthesize the Forensic Report from raw tool outputs; falls back to deterministic formatting on error.

### Changed

- **orchestrator.py** – New `--provider` CLI argument (default `none` for backward compatibility). Supervisor optionally invokes LLM based on provider. `requirements.txt` documents optional LLM deps (anthropic, openai, ollama).

### Fixed

- **Ollama response parsing** – Use `r.message.content` instead of dict-style `.get()`; the Ollama SDK returns a typed ChatResponse Pydantic object.
- **OpenAI/LM Studio empty response** – Guard `r.choices[0]` access to avoid IndexError on empty API responses.
- **Empty LLM_MODEL** – When `LLM_MODEL=` is set to empty string, fall back to provider default instead of passing empty model name to APIs.
- **Prompt injection mitigation** – Tool output is parsed as JSON and re-serialized before inclusion in the LLM prompt; fenced delimiters and explicit "treat as data only" instructions reduce risk from untrusted MCP server output.
- **Ollama None-return** – Guard `r.message.content` with `or ""` so the function always returns `str`, not `None`.
- **Sanitization fallback** – Parse-fail fallback now wraps raw excerpt in `---BEGIN RAW EXCERPT---` / `---END RAW EXCERPT---` fences.
- **CLI input sanitization** – `_sanitize_cli_for_prompt()` sanitizes title/author before LLM prompt inclusion (truncate, collapse newlines).
- **.gitignore** – Add `__pycache__/` and `*.pyc` to exclude compiled bytecode from tracking.
- **CLI JSON validation** – Wrap `json.loads` for `--observed-indicators`/`--observed-points` in try/except; malformed input produces friendly `parser.error` instead of uncaught traceback.
- **HTTP client lifecycle** – Construct Anthropic, OpenAI, Ollama, LM Studio clients once at factory time rather than inside the `complete()` closure on every invocation.
- **ImportError propagation** – Re-raise `ImportError` from LLM synthesis so missing provider SDKs surface clear install guidance; other exceptions still fall back to deterministic report.
- **README Ollama model** – Prerequisite example now pulls `llama3.2` to match orchestrator default; avoid "model not found" when following the guide verbatim.
- **LLM client lifecycle** – `get_model_client` returns an async context manager; clients are closed on exit (awaiting async `close`/`aclose` when present) to avoid connection leaks in non-CLI use.
- **Ollama host** – `OLLAMA_HOST` env var (default `http://localhost:11434`) for remote Ollama instances; mirrors `LM_STUDIO_BASE_URL` pattern.
- **Request timeout** – All LLM calls use `LLM_TIMEOUT` (default 120s, via `LLM_TIMEOUT` env); prevents indefinite hang on stalled local server.
- **Raw-excerpt delimiter** – Parse-fail fallback now JSON-escapes the excerpt so malicious output cannot embed `---END TOOL OUTPUT---` and break prompt fences.

## [0.11.0] - 2026-03-10

### Added

- **Python MCP client orchestrator** – `examples/orchestrator.py` implements a Supervisor Pattern:
  - Connects to the TypeScript MCP server via stdio transport using the MCP Python SDK
  - **Librarian agent** uses `find_book_in_master_bibliography` to pull book details
  - **Analyst agent** uses `audit_artifact_consistency` to check for discrepancies
  - **Supervisor** outputs a combined Forensic Report from both agents
  - Demo mode: sample `BookStandard` fallback for "The Hobbit" and "The Great Gatsby" when Notion is not configured
  - CLI options: `--title`, `--author`, `--observed-indicators`, `--observed-points`, `--observed-year`

- **examples/requirements.txt** – Python dependency `mcp>=1.25.0` for the MCP SDK

- **examples/usage.md** – Usage guide with prerequisites, CLI options, example commands, and Supervisor Pattern overview

### Changed

- **audit_artifact_consistency** – Added optional `book_standard` argument to input schema; allows inline BookStandard when Notion lookup is unavailable (enables demo mode without Notion configuration).

## [0.10.2] - 2025-03-04

### Fixed

- **containsMatch** – Remove `e.includes(o)` branch to prevent false-negatives: short or vague observed strings (e.g. "j") could previously match longer expected standards (e.g. "lowercase j on page 10"), silently suppressing High-severity discrepancies. Now uses one-directional matching only: observed must contain the full expected value.
- **README** – Fix malformed `[!TIP]` callout: add blockquote prefix (`> [!TIP]`) so it renders as a styled alert on GitHub.
- **Test file naming** – Rename `integration.test.ts` to `property-extraction.test.ts`; tests are unit tests for extraction helpers with no external dependencies.

### Added

- **Forensic test** – New test: vague observed value (e.g. "j") does NOT match expected "lowercase j on page 10"; ensures no false-negatives from short observed strings.

## [0.10.1] - 2025-03-04

### Fixed

- **extractMultiLineText** – Align parameter type with `extractRichText`: support `plain_text` and `text.content` fallback, optional fields. Resolves type mismatch in stricter compilation contexts.
- **audit_artifact_consistency** – Remove dead `medCount` logic; no code path assigns Medium severity, so `- medCount * 20` was permanently zero.
- **AuditSeverity** – Remove orphaned `Medium` from enum; audit tool only produces Low and High. Resolves schema/runtime inconsistency.
- **CHANGELOG** – Remove duplicate [0.10.0] entry.
- **ROADMAP** – Fix malformed bold syntax (`** Confidence-by-Field:**` → `**Confidence-by-Field:**`).

## [0.10.0] - 2025-03-04

### Added

- **Property extraction tests** – `src/__tests__/property-extraction.test.ts` mocks Notion property objects and verifies `extractTitle` and `extractRichText` work correctly for both `title` and `rich_text` property types. Covers plain_text, text.content, multiple segments, and edge cases.

### Changed

- **search_books** – When `query` is provided, it is now used as a Notion filter on the `Title` property using the `title` filter type (not `rich_text`). Ensures text search correctly targets the database's primary title column.

- **fetchBookStandard** – Fixed property extraction: Notion `Title` properties are type `title`, not `rich_text`. Added `extractTitle()` to pull `plain_text` from the `title` array. Updated `extractRichText()` to support both `plain_text` and `text.content`. Both helpers exported for testing.

- **audit_artifact_consistency** – Standardized severity: Points of Issue discrepancies are HIGH severity with significant confidence deduction (45 points per High). Updated schema documentation to reflect Points of Issue = High. Added comment explaining bidirectional substring matching is for demo flexibility; production would require normalized tokens.

## [0.9.0] - 2025-03-04

### Added

- **sample_data** – CSV files for project replication: `books_catalog.csv`, `master_bibliography.csv`, `market_results.csv`, `audit_history.csv`. Import into Notion to recreate the forensic test environment used for Alice, Hobbit, and Gatsby audits.

### Changed

- **generate_exhibit_label** – Rewritten with new inputs (`book_data`, `audit_results`, `market_citation`) and high-fidelity museum placard format. Sections: Archival Description, Forensic Verification Summary, Valuation Context. Disclaimer appended. Forensic Workflow: once an audit is successful, offer to generate a formal Exhibit Label; suggest saving output to the Notion page's Full Report field.

## [0.8.0] - 2025-03-04

### Added

- **get_market_signals** – Include `citation` field for each market result. Citation property (url or rich_text) is retrieved from the Market Results database and surfaced in the tool output. Forensic Workflow: when reporting market findings, always include the citation link or reference provided in the Market Results to ensure evidence-based auditing.

## [0.7.0] - 2025-03-04

### Added

- **create_audit_log** – `catalog_page_id` (required string). Notion page ID from the Catalog search result (search_books or find_book_in_master_bibliography); mapped to `'Linked Book'` relation property so audit logs link to catalog entries. Forensic Workflow: agent MUST pass the id from the Catalog search result into catalog_page_id to maintain the relational thread.

## [0.6.0] - 2025-03-04

### Added

- **create_audit_log** – `audit_date` argument (optional string, ISO 8601), defaulting to current time via `new Date().toISOString()`. Maps to Notion property `'Audit Date'` (date type).

### Changed

- **find_book_in_master_bibliography** – Title filter uses `equals` (not `contains`) to avoid fuzzy search misses. `fetchBookStandard` parses Points of Issue and First Edition Indicators from `multi_select` arrays in the full page response, with fallback to rich_text.

## [0.5.0] - 2025-03-04

### Changed

- **create_audit_log** – Map book_title to the primary title property `"title"` (lowercase), the default primary column for Notion databases. Add optional `NOTION_AUDIT_LOG_TITLE_PROPERTY` env var if the column was renamed. Remove reference to "Book Title" property.

- **find_book_in_master_bibliography**, **get_market_signals** – Document that both use `databases.query` with Title filter (not `notion.search`), scoping lookups to the specific database rather than the whole workspace.

## [0.4.0] - 2025-03-04

### Added

- **Production test suite** – Vitest
  - `vitest` dev dependency, `npm run test` script
  - `src/__tests__/forensic-logic.test.ts` with mocked Notion client
  - Tests for `audit_artifact_consistency`: Point of Issue typo (wabe vs wade) → High severity, first_edition_indicators fail, missing points, year mismatch, confidence score

### Changed

- **audit_artifact_consistency** – points_of_issue failures now return High severity (was Medium). Point-of-issue typo mismatches indicate forgery/wrong state.

## [0.3.0] - 2025-03-04

### Added

- **create_audit_log** tool
  - Create permanent audit records in the Audit Logs Notion database
  - Arguments: book_title, result (enum: Pass, Flagged, Fail), summary, full_report
  - Forensic Workflow step 6: after audit is complete, automatically call to maintain permanent record
  - `createAuditLog()`, `getAuditLogDatabaseId()` in notion client
  - `NOTION_AUDIT_LOG_DATABASE_ID` environment variable

## [0.2.0] - 2025-03-04

### Added

- **update_book_status** tool
  - Update the Status property of any Notion page by page_id and status string
  - Forensic Workflow step 5: when audit reveals High or Medium severity discrepancy, update status to "Flagged for Review"
  - `updateBookStatus()` in notion client

## [0.1.0] - 2025-03-04

### Added

- **Project setup** – TypeScript MCP server for rare books intelligence
  - `@modelcontextprotocol/sdk`, `@notionhq/client`, `zod`, `express`
  - ES modules, strict TypeScript config, Node ≥18

- **General search path** – `search_books` tool
  - Query Notion books database by author, year, condition
  - `BookMetadataSchema`, `BookSearchParamsSchema` for validation
  - `searchBooks()`, `bookToNotionProperties()` in notion client

- **Forensic audit path** – `audit_artifact_consistency` tool
  - Compare observed artifact vs Master Bibliography ground truth
  - Severity: High (first_edition_indicators), Medium (points_of_issue), Low (other)
  - `BookStandardSchema`, `ObservedArtifactSchema`, `AuditReportSchema`
  - `fetchBookStandard()`, `findBookStandardInMasterBibliography()`

- **Find book in Master Bibliography** – `find_book_in_master_bibliography` tool
  - Returns page IDs and BookStandards when found
  - If not found, suggests adding the book to Notion first

- **Market signals** – `get_market_signals` tool
  - Query Market Results for last 3 sales, return average Hammer Price
  - Third Notion database for auction/sales data

- **Reporting** – `generate_exhibit_label` tool
  - Produce Markdown Exhibit Placard from audit report + book standard
  - Curator's Note and Caveat Emptor / Forensic Note (when Medium or High severity)

- **Orchestration** – Forensic Workflow instructions
  - LLM guidance: find → audit → market signals → offer exhibit label
  - Graceful handling when book is missing from Master Bibliography

- **Streamable HTTP transport** – ngrok / Notion Custom Agent support
  - Express server on port 3000, `/mcp` endpoint
  - Stateless mode for remote clients
  - Binds to `0.0.0.0` for tunnel access

- **Configuration**
  - `.env.example` for `NOTION_API_KEY`, books DB, Master Bibliography DB, Market Results DB
  - `PORT` env var (default 3000)
