# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.13.10] - 2026-03-10

### Added

- **ACCOUNTANT_CLASSIFICATION_PROVIDER** – Env var for classification backend (default: ollama); use `lm_studio` when only LM Studio is available. Previously hardcoded to ollama.
- **run_with_accountant emit_decision** – Optional `emit_decision=False` to suppress routing log when used as a library; defaults True for CLI.

### Changed

- **classify_query** – Uses `ACCOUNTANT_CLASSIFICATION_PROVIDER`; removed `os.environ` mutation; passes `model_override` to `get_model_client` for concurrency-safe model selection.
- **get_model_client** – New `model_override` parameter bypasses env/DEFAULT_MODELS; avoids global side effects.
- **run_with_accountant** – Routing decisions logged via `logging` instead of `print()`; respects `emit_decision` for programmatic use.
- **orchestrator** – Ensures `examples/` is on `sys.path` before router import for robust module usage.

## [0.13.9] - 2026-03-10

### Fixed

- **Accountant prompt contamination** – `classify_query` now uses `get_model_client("ollama", raw_system=True)` so the accountant's strict LEVEL_1/LEVEL_2 classifier instructions are not contaminated by the forensic `local_slm_system_prefix` (CoT) injected for supervisor synthesis. New `raw_system` parameter on `get_model_client` bypasses the prefix for classification calls.

### Changed

- **orchestrator --provider warning** – When both `--use-accountant` and `--provider` are supplied, log a warning that `--provider` is ignored; the router chooses the provider based on query complexity.

## [0.13.8] - 2026-03-10

### Fixed

- **router.py JSON parsing** – Catch `ValueError` and `TypeError` in addition to `json.JSONDecodeError` when parsing `--observed-indicators`/`--observed-points`; matches orchestrator behavior and prevents tracebacks on non-array JSON input.
- **_build_accountant_prompt** – Simplify return type from `tuple[str, str]` to `str`; second value was unused.

### Changed

- **Version alignment** – `package.json` and `src/index.ts` set to 0.13.8 to match CHANGELOG.

## [0.13.7] - 2026-03-10

### Added

- **The Accountant (Cognitive Budgeting)** – Semantic router that classifies user queries by complexity and routes to the appropriate backend:
  - `config/prompts.yaml`: New `accountant` section with `system_prefix` and `routing_logic` (LEVEL_1: simple retrieval/formatting vs LEVEL_2: complex forensic reasoning).
  - `examples/router.py`: Standalone script using a light model (Ollama, default llama3.2) to classify queries; LEVEL_1 routes to local SLM (ollama), LEVEL_2 to high-reasoning cloud (anthropic). Prints cost decision before running the audit.
  - `orchestrator.py`: `--use-accountant` and `--query` flags to route via The Accountant from the orchestrator CLI. Provider override chosen by the router.
  - Env: `ACCOUNTANT_MODEL`, `ACCOUNTANT_LEVEL_1_PROVIDER`, `ACCOUNTANT_LEVEL_2_PROVIDER`.
  - README: Running with The Accountant section.

## [0.13.6] - 2026-03-10

### Changed

- **Version strings** – `src/index.ts` JSDoc and McpServer constructor updated from 0.1.0 to 0.13.6 to match CHANGELOG.
- **FORENSIC_WORKFLOW_INSTRUCTIONS** – Removed "Medium" from update_book_status step; audit tool emits Low or High only, so "High severity discrepancy" avoids misleading LLM clients.

### Fixed

- **_parse_report deduplication** – Removed set-based dedup; discrepancies are now passed through to _compute_precision_recall so Counter-based handling correctly processes multi-indicator cases.
- **_reasoning_quality consistency check** – Anchored to `Consistency:\s*(PASS|FAIL)` regex instead of loose "PASS" or "FAIL" anywhere in report.

## [0.13.5] - 2026-03-10

### Added

- **Evaluator --threshold** – CLI option for pass/fail exit threshold (default 70); configurable via `--threshold N`.

### Changed

- **Audit framing inside fence** – Moved audit_instruction framing into the `---BEGIN TOOL OUTPUT---` / `---END TOOL OUTPUT---` block so the supervisor_system guard covers it; previously it was outside the fence.
- **Analyst prompt severity** – Aligned with audit tool: "LOW (cosmetic), HIGH (critical mismatch). The audit tool currently emits Low or High only; MEDIUM is reserved for future use." Prevents LLM-generated MEDIUM false positives in evaluation.
- **_compute_precision_recall** – Switched from set-based to Counter-based deduplication; correctly handles duplicate (field, severity) pairs for multi-indicator cases.

## [0.13.4] - 2026-03-10

### Added

- **run_forensic_audit book_standard param** – Optional `book_standard` argument allows callers (e.g. evaluator) to pass pinned reference data; when provided, librarian lookup is skipped and the given standard is used for deterministic evaluation.

### Changed

- **Evaluator uses golden dataset book_standard** – `run_evaluation` now passes `case.get("book_standard")` to `run_forensic_audit`, so evaluation runs against the dataset's reference standard rather than librarian/sample fallback. Fixes unreliable error-publisher-binding and other cases that depend on exact standard data.

### Fixed

- **Lost traceback in evaluator error handling** – Replaced `_logger.exception()` (no-op outside except block) with `_logger.error(..., exc_info=r)` so exception tracebacks are logged when `asyncio.gather(return_exceptions=True)` returns an exception.
- **Prompt injection via unsanitized audit framing** – `observed` and `book_standard` data passed through `_sanitize_tool_output_for_llm()` before substitution into the analyst audit_instruction; prevents malicious content in caller-supplied fields from being injected outside the `---BEGIN TOOL OUTPUT---` guard.

## [0.13.3] - 2026-03-10

### Added

- **AuditSeverity Medium** – `src/lib/schemas.ts` adds `"Medium"` to `AuditSeverity` enum so the schema aligns with the analyst prompt in `prompts_the_judge.yaml` (LOW/MEDIUM/HIGH). Audit tool still emits Low | High only; Medium reserved for future use.

### Changed

- **run_evaluation error handling** – `asyncio.gather` now uses `return_exceptions=True`; a single failing case no longer aborts the entire evaluation. Failed cases are logged, recorded with grade 0 and error details, and included in the results.
- **prompts_the_judge.yaml** – Trailing newline added for POSIX EOF convention.

## [0.13.2] - 2026-03-10

### Fixed

- **_substitute_prompt_template** – Replaced `re.sub` with `str.replace` to avoid backslash interpretation in replacement strings; `json.dumps` output (e.g. `\n`, `\t`) was being corrupted when passed to the LLM. Also removes unescaped `{`/`}` from regex pattern (Python 3.12+ deprecation).
- **_parse_report case-sensitivity** – Discrepancy regex now uses `re.IGNORECASE`; analyst prompt instructs uppercase `[HIGH]`/`[LOW]`/`[MEDIUM]`, so LLM-generated reports were previously missed and precision/recall were wrong.
- **_compute_precision_recall** – Severity comparison now case-insensitive; ensures golden dataset (`High`) matches LLM output (`HIGH`).
- **_reasoning_quality** – Discrepancy-presence check now case-insensitive.

## [0.13.1] - 2026-03-10

### Added

- **rubric_weights** – `config/prompts_the_judge.yaml` now defines `rubric_weights`; evaluator consumes them for heuristic grading. Fallback to defaults if the_judge not loaded.
- **format_recognized** – Evaluator grade output includes `format_recognized`; `False` when no `Consistency: PASS|FAIL` line is found.

### Changed

- **prompts_the_judge rubric** – Rubric prompt text now aligns with `rubric_weights`: Consistency (20 pts), Precision (30), Recall (30), Reasoning (20). Ensures LLM-graded and heuristic scores are comparable.
- **_get_prompts** – Switched from manual `_cache` attribute to `@functools.lru_cache(maxsize=1)`; tests can invalidate via `_get_prompts.cache_clear()`.
- **run_evaluation** – Golden dataset cases now run in parallel via `asyncio.gather()` for faster evaluation, especially with LLM providers.

### Fixed

- **Medium severity in scoring** – `_parse_report` and `_reasoning_quality` now recognize `[Medium]` discrepancy tags; analyst prompt assigns MEDIUM, so reports were previously misgraded when Medium discrepancies appeared.
- **_parse_report silent default** – When no `Consistency: PASS|FAIL` line is found, evaluator applies conservative consistency score (0) and logs a warning instead of silently defaulting to pass.
- **_substitute_prompt_template usage** – Orchestrator now injects substituted `analyst.audit_instruction` (`{{observed_data}}`, `{{standard_data}}`) into the supervisor prompt when using an LLM provider.

## [0.13.0] - 2026-03-10

### Added

- **Prompt externalization** – `config/prompts.yaml` holds `local_slm_system_prefix` and `supervisor_system`; `config/prompts_the_judge.yaml` holds librarian, analyst, and judge agent prompts (Series 2 – The Judge). Both ingested via `_load_prompts()` / `_get_prompts()`. Adds `pyyaml>=6.0` to requirements.
- **Judge Framework** – `tests/golden_dataset.json` with 5 forensic cases (2 clean, 3 with year/points-of-issue/binding discrepancies). `examples/evaluator.py` runs orchestrator against the dataset and grades output on Precision, Recall, Reasoning Quality (0–100 rubric). Exits 0 if average ≥ 70.
- **Structured logging** – LLM synthesis failures call `logger.exception()` with provider and error details; deterministic fallback still returned. Basic logging config in orchestrator `main()`.

### Changed

- **orchestrator.py** – Prompts moved to config; logging for synthesis errors; evaluator usage in `usage.md`.
- **audit_artifact_consistency** – Input schema for `observed` extended with `binding_type_observed` and `paper_watermark_observed` for golden dataset binding case.
- **audit-artifact-consistency.ts** – Phase 5 Tokenization (ROADMAP) comment added; ready for stricter tokenization per roadmap.

### Fixed

- **evaluator _reasoning_quality** – Replace `len(re.finditer(...))` with `re.search(...) is None`; `re.finditer` returns a non-Sized iterator, causing TypeError for clean-case grading.
- **orchestrator logger.exception** – Remove redundant `exc_info=True`; `logger.exception()` already captures current exception info.
- **orchestrator PEP 8 E302** – Add second blank line before `_load_prompts()` top-level function.

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
