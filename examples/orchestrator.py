#!/usr/bin/env python3
"""
MCP Forensic Orchestrator — Supervisor Pattern

Connects to the Rare Books Intelligence MCP server via stdio transport,
orchestrating a Librarian agent (book lookup) and an Analyst agent (audit)
to produce a combined Forensic Report.

Tool mapping (server exposes these; adapt if you add Youtube/audit_book):
  - Librarian: find_book_in_master_bibliography (pulls book details)
  - Analyst:   audit_artifact_consistency (checks for discrepancies)

Usage:
    python orchestrator.py [--title "Book Title"] [--author "Author Name"]
    
Prerequisites:
    - npm run build  (TypeScript server outputs to dist/index.js)
    - NOTION_API_KEY and database IDs for full Notion integration
"""

import argparse
import asyncio
import json
import os
import pathlib
from datetime import datetime

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# -----------------------------------------------------------------------------
# Paths: script lives in examples/, server in parent
# -----------------------------------------------------------------------------
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
# Server entry: dist/index.js (tsc default) or build/index.js
_server_dir = "dist" if (PROJECT_ROOT / "dist" / "index.js").exists() else "build"
SERVER_ENTRY = PROJECT_ROOT / _server_dir / "index.js"


def _sample_book_standard(title: str, author: str | None) -> dict | None:
    """Fallback BookStandard for demo when Notion is not configured."""
    samples = {
        "the hobbit": {
            "title": "The Hobbit",
            "author": "J.R.R. Tolkien",
            "publisher": "George Allen & Unwin",
            "expected_first_edition_year": 1937,
            "binding_type": "Cloth",
            "first_edition_indicators": [
                "1st printing has no mention of later impressions",
                "George Allen & Unwin at foot of title page",
            ],
            "points_of_issue": [
                'Typo "Dodgeson" instead of "Dodgson" on back flap',
            ],
        },
        "the great gatsby": {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "publisher": "Scribner",
            "expected_first_edition_year": 1925,
            "binding_type": "Cloth",
            "first_edition_indicators": [
                "Published April, 1925 on copyright page",
                "no later printings listed",
            ],
            "points_of_issue": [
                'lowercase "j" in "jay gatsby" on back of dust jacket',
            ],
        },
    }
    key = title.lower().strip() if title else ""
    return samples.get(key)


def get_server_params() -> StdioServerParameters:
    """Spawn the TypeScript MCP server via node."""
    return StdioServerParameters(
        command="node",
        args=[str(SERVER_ENTRY)],
        cwd=str(PROJECT_ROOT),
        env=os.environ.copy(),
    )


def extract_text_content(result) -> str:
    """Extract text from MCP CallToolResult content."""
    if not result.content:
        return ""
    parts = []
    for block in result.content:
        if isinstance(block, types.TextContent):
            parts.append(block.text)
    return "\n".join(parts)


# -----------------------------------------------------------------------------
# Agents
# -----------------------------------------------------------------------------


async def librarian_agent(session: ClientSession, title: str, author: str | None) -> dict:
    """
    Librarian: Uses find_book_in_master_bibliography to pull book details.
    Returns parsed JSON result for downstream use.
    """
    args: dict = {"title": title}
    if author:
        args["author"] = author

    result = await session.call_tool("find_book_in_master_bibliography", arguments=args)
    text = extract_text_content(result)

    if result.isError:
        return {"error": True, "message": text, "raw": text}

    try:
        return {"error": False, "data": json.loads(text), "raw": text}
    except json.JSONDecodeError:
        return {"error": False, "data": None, "raw": text}


async def analyst_agent(
    session: ClientSession,
    book_standard_page_id: str | None,
    book_standard: dict | None,
    observed: dict,
) -> dict:
    """
    Analyst: Uses audit_artifact_consistency to check for discrepancies.
    Requires either book_standard_page_id (Notion page ID) or book_standard (inline).
    """
    args: dict = {"observed": observed}
    if book_standard_page_id:
        args["book_standard_page_id"] = book_standard_page_id
    elif book_standard:
        args["book_standard"] = book_standard
    else:
        return {
            "error": True,
            "message": "Either book_standard_page_id or book_standard is required",
            "raw": "",
        }

    result = await session.call_tool("audit_artifact_consistency", arguments=args)
    text = extract_text_content(result)

    if result.isError:
        return {"error": True, "message": text, "raw": text}

    try:
        return {"error": False, "data": json.loads(text), "raw": text}
    except json.JSONDecodeError:
        return {"error": False, "data": None, "raw": text}


def build_forensic_report(
    title: str,
    author: str | None,
    librarian_result: dict,
    analyst_result: dict,
) -> str:
    """Supervisor: Combine Librarian and Analyst findings into a Forensic Report."""
    lines = [
        "═══════════════════════════════════════════════════════════════",
        "                    FORENSIC REPORT",
        "═══════════════════════════════════════════════════════════════",
        "",
        f"  Title:  {title}",
        f"  Author: {author or '(unspecified)'}",
        f"  Date:   {datetime.now().isoformat()}",
        "",
        "───────────────────────────────────────────────────────────────",
        "  LIBRARIAN FINDINGS (Book Lookup)",
        "───────────────────────────────────────────────────────────────",
    ]

    if librarian_result.get("error"):
        lines.append(f"  Status: ERROR")
        lines.append(f"  {librarian_result.get('message', 'Unknown error')}")
    else:
        data = librarian_result.get("data") or {}
        if data.get("found"):
            lines.append(f"  Status: Found {data.get('message', '')}")
            if data.get("book_standards"):
                std = data["book_standards"][0]
                lines.append(f"  Publisher: {std.get('publisher', 'N/A')}")
                lines.append(f"  Expected Year: {std.get('expected_first_edition_year', 'N/A')}")
                lines.append(f"  Binding: {std.get('binding_type', 'N/A')}")
        else:
            lines.append(f"  Status: Not Found")
            lines.append(f"  {data.get('message', 'N/A')}")

    lines.extend([
        "",
        "───────────────────────────────────────────────────────────────",
        "  ANALYST FINDINGS (Audit)",
        "───────────────────────────────────────────────────────────────",
    ])

    if analyst_result.get("error"):
        lines.append(f"  Status: ERROR")
        lines.append(f"  {analyst_result.get('message', 'Unknown error')}")
    else:
        data = analyst_result.get("data") or {}
        consistent = data.get("is_consistent", False)
        confidence = data.get("confidence_score", 0)
        lines.append(f"  Consistency: {'PASS' if consistent else 'FAIL'}")
        lines.append(f"  Confidence: {confidence}%")

        disc = data.get("discrepancies", [])
        if disc:
            lines.append("  Discrepancies:")
            for d in disc:
                lines.append(f"    - [{d.get('severity', '?')}] {d.get('field', '')}: "
                            f"expected '{d.get('expected', '')}' vs observed '{d.get('observed', '')}'")
        else:
            lines.append("  Discrepancies: None")

    lines.extend([
        "",
        "═══════════════════════════════════════════════════════════════",
        "                    END OF REPORT",
        "═══════════════════════════════════════════════════════════════",
    ])

    return "\n".join(lines)


async def run_forensic_audit(title: str, author: str | None, observed: dict | None) -> str:
    """
    Main orchestration: connect to MCP server, run Librarian → Analyst → Report.
    """
    server_params = get_server_params()

    if not SERVER_ENTRY.exists():
        return (
            f"Error: Server not found at {SERVER_ENTRY}\n"
            "Run `npm run build` in the project root first."
        )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Librarian: pull book details
            librarian_result = await librarian_agent(session, title, author)

            # 2. Analyst: audit for discrepancies
            book_page_id = None
            book_standard = None
            if not librarian_result.get("error") and librarian_result.get("data"):
                data = librarian_result["data"]
                if data.get("page_ids"):
                    book_page_id = data["page_ids"][0]
                if data.get("book_standards"):
                    book_standard = data["book_standards"][0]

            # Demo fallback: use sample BookStandard when Notion unavailable
            if book_standard is None and title:
                book_standard = _sample_book_standard(title, author)

            # Default observed data if not provided (for demo)
            if observed is None and book_standard:
                observed = {
                    "first_edition_indicators_observed": book_standard.get(
                        "first_edition_indicators", []
                    ),
                    "points_of_issue_observed": book_standard.get("points_of_issue", []),
                    "observed_year": book_standard.get("expected_first_edition_year"),
                }
            if observed is None:
                observed = {
                    "first_edition_indicators_observed": [],
                    "points_of_issue_observed": [],
                }

            analyst_result = await analyst_agent(
                session, book_page_id, book_standard, observed
            )

            # 3. Supervisor: combine and output Forensic Report
            return build_forensic_report(title, author, librarian_result, analyst_result)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCP Forensic Orchestrator — Supervisor Pattern"
    )
    parser.add_argument(
        "--title",
        default="The Hobbit",
        help="Book title to look up and audit",
    )
    parser.add_argument(
        "--author",
        default=None,
        help="Book author (optional)",
    )
    parser.add_argument(
        "--observed-indicators",
        default=None,
        help="JSON array of first edition indicators observed (for audit)",
    )
    parser.add_argument(
        "--observed-points",
        default=None,
        help="JSON array of points of issue observed (for audit)",
    )
    parser.add_argument(
        "--observed-year",
        type=int,
        default=None,
        help="Observed publication year (for audit)",
    )

    args = parser.parse_args()

    observed = None
    if args.observed_indicators or args.observed_points or args.observed_year is not None:
        observed = {
            "first_edition_indicators_observed": (
                json.loads(args.observed_indicators) if args.observed_indicators else []
            ),
            "points_of_issue_observed": (
                json.loads(args.observed_points) if args.observed_points else []
            ),
            "observed_year": args.observed_year,
        }

    report = asyncio.run(run_forensic_audit(args.title, args.author, observed))
    print(report)


if __name__ == "__main__":
    main()
