#!/usr/bin/env python3
"""
The Accountant — Cognitive Budgeting (Semantic Router)

Classifies user queries by complexity using a light local model (Ollama),
then routes to the appropriate backend:
  - LEVEL_1 (simple): Local/cheap model (ollama)
  - LEVEL_2 (complex): High-reasoning cloud model (anthropic or openai)

Usage:
    python router.py --query "Look up The Hobbit" --title "The Hobbit" --author "Tolkien"
    python router.py --query "Compare points of issue and binding across editions" --title "The Great Gatsby"

Environment:
    ACCOUNTANT_MODEL      Light model for classification (default: llama3.2)
    ACCOUNTANT_LEVEL_1_PROVIDER   Provider for LEVEL_1 (default: ollama)
    ACCOUNTANT_LEVEL_2_PROVIDER   Provider for LEVEL_2 (default: anthropic)
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from orchestrator import _get_prompts, get_model_client, run_forensic_audit

ACCOUNTANT_MODEL = os.environ.get("ACCOUNTANT_MODEL", "llama3.2")
ACCOUNTANT_LEVEL_1_PROVIDER = os.environ.get("ACCOUNTANT_LEVEL_1_PROVIDER", "ollama")
ACCOUNTANT_LEVEL_2_PROVIDER = os.environ.get("ACCOUNTANT_LEVEL_2_PROVIDER", "anthropic")


def _build_accountant_prompt() -> str:
    """Load accountant system and routing logic from prompts.yaml."""
    prompts = _get_prompts()
    accountant = prompts.get("accountant", {}) or {}
    system = (accountant.get("system_prefix") or "").strip()
    routing = (accountant.get("routing_logic") or "").strip()
    if not system or not routing:
        system = (
            "You are a strict classifier that analyzes user requests for complexity. "
            "You MUST respond with exactly one of: LEVEL_1 or LEVEL_2. No other output."
        )
        routing = (
            "LEVEL_1: Simple retrieval or formatting. "
            "LEVEL_2: Complex forensic reasoning, multi-step analysis, comparative evaluation."
        )
    return f"{system}\n\n{routing}"


async def classify_query(query: str) -> str:
    """
    Use a light model (Ollama) to classify the query into LEVEL_1 or LEVEL_2.
    Returns "LEVEL_1" or "LEVEL_2".
    """
    system = _build_accountant_prompt()
    user = f"Classify this request:\n\n{query}\n\nRespond with LEVEL_1 or LEVEL_2 only."
    old_model = os.environ.get("LLM_MODEL")
    os.environ["LLM_MODEL"] = ACCOUNTANT_MODEL
    try:
        async with get_model_client("ollama") as complete:
            raw = await complete(system, user)
    except Exception as e:
        print(f"Accountant classification failed ({e}), defaulting to LEVEL_2 for safety.")
        return "LEVEL_2"
    finally:
        if old_model is not None:
            os.environ["LLM_MODEL"] = old_model
        elif "LLM_MODEL" in os.environ:
            del os.environ["LLM_MODEL"]
    match = re.search(r"LEVEL_1|LEVEL_2", raw.strip().upper())
    return match.group(0) if match else "LEVEL_2"


def get_provider_for_level(level: str) -> str:
    """Map classification level to LLM provider."""
    if level.upper() == "LEVEL_1":
        return ACCOUNTANT_LEVEL_1_PROVIDER
    return ACCOUNTANT_LEVEL_2_PROVIDER


async def run_with_accountant(
    query: str,
    title: str,
    author: str | None = None,
    observed: dict | None = None,
    book_standard: dict | None = None,
) -> str:
    """
    Classify the query, print the cost decision, and run the forensic audit
    with the appropriate provider.
    """
    level = await classify_query(query)
    provider = get_provider_for_level(level)
    if level == "LEVEL_1":
        print("Accountant Decision: LEVEL_1 - Routing to Local SLM to save budget")
    else:
        print("Accountant Decision: LEVEL_2 - Routing to High-Reasoning Cloud Model")
    return await run_forensic_audit(
        title, author, observed,
        provider=provider,
        book_standard=book_standard,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="The Accountant — Semantic Router for Cognitive Budgeting"
    )
    parser.add_argument(
        "--query",
        required=True,
        help="User request to classify (used for routing decision)",
    )
    parser.add_argument(
        "--title",
        default="The Hobbit",
        help="Book title for the forensic audit",
    )
    parser.add_argument(
        "--author",
        default=None,
        help="Book author (optional)",
    )
    parser.add_argument(
        "--observed-indicators",
        default=None,
        help="JSON array of first edition indicators observed",
    )
    parser.add_argument(
        "--observed-points",
        default=None,
        help="JSON array of points of issue observed",
    )
    parser.add_argument(
        "--observed-year",
        type=int,
        default=None,
        help="Observed publication year",
    )
    args = parser.parse_args()

    observed = None
    if args.observed_indicators or args.observed_points or args.observed_year is not None:
        try:
            indicators = json.loads(args.observed_indicators or "[]")
            points = json.loads(args.observed_points or "[]")
            if not isinstance(indicators, list) or not isinstance(points, list):
                raise ValueError("must be JSON arrays")
        except json.JSONDecodeError as e:
            parser.error(f"Invalid JSON: {e}")
        except (ValueError, TypeError) as e:
            parser.error(f"--observed-indicators/--observed-points: {e}")
        observed = {
            "first_edition_indicators_observed": indicators,
            "points_of_issue_observed": points,
            "observed_year": args.observed_year,
        }

    report = asyncio.run(
        run_with_accountant(args.query, args.title, args.author, observed)
    )
    print(report)


if __name__ == "__main__":
    main()
