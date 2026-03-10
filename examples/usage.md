# MCP Forensic Orchestrator — Usage Guide

The `orchestrator.py` script acts as an MCP client that implements a **Supervisor Pattern**. It connects to the Rare Books Intelligence MCP server via stdio transport, runs two agents (Librarian and Analyst), and outputs a combined Forensic Report.

## Prerequisites

1. **TypeScript MCP server built**
   ```bash
   npm install
   npm run build
   ```
   Build output goes to `dist/index.js` (or `build/index.js` if that exists).

2. **Python 3.10+**
   ```bash
   pip install -r requirements.txt
   ```
   Or with a virtual environment:
   ```bash
   python -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

3. **Notion integration (optional)**
   For full functionality, set `NOTION_API_KEY` and the relevant database IDs:
   - `NOTION_MASTER_BIBLIOGRAPHY_DATABASE_ID` — for Librarian book lookups
   - Other DB IDs as in `.env.example`

   Without Notion, the script uses sample `BookStandard` data for "The Hobbit" and "The Great Gatsby" so you can run demos.

## Running the Orchestrator

From the `examples/` directory:

```bash
python orchestrator.py --title "The Hobbit" --author "J.R.R. Tolkien"
```

Or with the venv:

```bash
.venv/bin/python orchestrator.py --title "The Hobbit" --author "J.R.R. Tolkien"
```

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--title` | `"The Hobbit"` | Book title to look up and audit |
| `--author` | (none) | Book author (optional) |
| `--observed-indicators` | (none) | JSON array of first edition indicators observed (e.g. `'["Published April, 1925"]'`) |
| `--observed-points` | (none) | JSON array of points of issue observed (e.g. `'["typo on page 10"]'`) |
| `--observed-year` | (none) | Observed publication year for audit comparison |

## Example Commands

**Basic run (uses defaults):**
```bash
python orchestrator.py
```

**Specify book:**
```bash
python orchestrator.py --title "The Great Gatsby" --author "F. Scott Fitzgerald"
```

**Simulate discrepancies (audit fail):**
```bash
python orchestrator.py --title "The Hobbit" \
  --observed-points '["Wrong typo on back flap"]' \
  --observed-year 1940
```

## Output

The script prints a **Forensic Report** with:

- **Librarian Findings** — Result of `find_book_in_master_bibliography` (book details or Notion error)
- **Analyst Findings** — Result of `audit_artifact_consistency` (Pass/Fail, confidence score, discrepancies)

## Supervisor Pattern

1. **Librarian** — Uses `find_book_in_master_bibliography` to pull book details from the Master Bibliography.
2. **Analyst** — Uses `audit_artifact_consistency` to check observed data against ground truth and report discrepancies.
3. **Supervisor** — Combines both results into a single Forensic Report.

## Tool Mapping

The server exposes these tools (adapt if you add custom tools):

- **Librarian:** `find_book_in_master_bibliography` — pulls book details
- **Analyst:** `audit_artifact_consistency` — checks for discrepancies

## Judge Framework Evaluation

Run the evaluator against the golden dataset to grade report quality:

```bash
python evaluator.py --provider none
python evaluator.py --provider ollama -v
```

Scores each case on Precision, Recall, and Reasoning Quality (0-100).
