#!/usr/bin/env python3
"""
MCP Forensic Orchestrator — Supervisor Pattern

Connects to the Rare Books Intelligence MCP server via stdio transport,
orchestrating a Librarian agent (book lookup) and an Analyst agent (audit)
to produce a combined Forensic Report.

Supports cloud providers (Anthropic, OpenAI) and local SLMs (Ollama, LM Studio).

Tool mapping (server exposes these; adapt if you add Youtube/audit_book):
  - Librarian: find_book_in_master_bibliography (pulls book details)
  - Analyst:   audit_artifact_consistency (checks for discrepancies)

Usage:
    python orchestrator.py [--title "Book Title"] [--author "Author Name"]
    python orchestrator.py --provider ollama --title "The Hobbit"
    
Prerequisites:
    - npm run build  (TypeScript server outputs to dist/index.js)
    - NOTION_API_KEY and database IDs for full Notion integration
    - For cloud: ANTHROPIC_API_KEY or OPENAI_API_KEY
    - For local: Ollama running (ollama serve) or LM Studio server
"""

import argparse
import asyncio
import functools
import json
import logging
import os
import pathlib
import sys
from datetime import datetime
from typing import Any, Awaitable, Callable

import yaml
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Ensure examples/ is on sys.path for router import (robust when imported as module)
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Load .env from project root (shared with MCP server) so NOTION_*, OLLAMA_*, etc. are set
load_dotenv(PROJECT_ROOT / ".env")

# Post 3.2: The Redactor — PII scrubbing for cloud egress (lazy; may fail if deps missing)
_REDACTOR_DISABLED = object()
_redactor: "SovereignRedactor | None" = None


def _get_redactor() -> "SovereignRedactor | None":
    """Lazy-init SovereignRedactor. Returns None if presidio/spacy not installed."""
    global _redactor
    if _redactor is _REDACTOR_DISABLED:
        return None
    if _redactor is None:
        try:
            import presidio_analyzer  # noqa: F401
            import presidio_anonymizer  # noqa: F401
        except ImportError:
            logger.warning(
                "PII Redactor disabled: presidio/spacy dependencies not found."
            )
            _redactor = _REDACTOR_DISABLED
            return None
        try:
            from redactor import SovereignRedactor
            _redactor = SovereignRedactor()
        except ImportError:
            logger.warning(
                "PII Redactor disabled: presidio/spacy dependencies not found."
            )
            _redactor = _REDACTOR_DISABLED
            return None
    return _redactor

logger = logging.getLogger(__name__)

# Request timeout for LLM calls (seconds); overridable via LLM_TIMEOUT env
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "120"))

# -----------------------------------------------------------------------------
# Paths: script lives in examples/, server in parent
# -----------------------------------------------------------------------------
CONFIG_DIR = PROJECT_ROOT / "config"
PROMPTS_PATH = CONFIG_DIR / "prompts.yaml"
PROMPTS_THE_JUDGE_PATH = CONFIG_DIR / "prompts_the_judge.yaml"
# Server entry: dist/index.js (tsc default) or build/index.js
_server_dir = "dist" if (PROJECT_ROOT / "dist" / "index.js").exists() else "build"
SERVER_ENTRY = PROJECT_ROOT / _server_dir / "index.js"

# Default model names per provider. Use provider-specific env vars to avoid
# cross-routing: ANTHROPIC_MODEL (cloud), OLLAMA_MODEL (local synthesis).
# OLLAMA_VISION_MODEL is separate (Sovereign Vault vision only, in MCP server).
DEFAULT_MODELS = {
    "anthropic": "claude-3-5-sonnet-latest",
    "openai": "gpt-4o-mini",
    "ollama": "llama3.2",
    "lm_studio": "local-model",  # LM Studio uses the loaded model name
}


def _load_prompts() -> dict[str, Any]:
    """Load prompts from config/prompts.yaml and config/prompts_the_judge.yaml."""
    if not PROMPTS_PATH.exists():
        raise FileNotFoundError(
            f"Prompts config not found: {PROMPTS_PATH}. "
            "Ensure config/prompts.yaml exists."
        )
    with open(PROMPTS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    result: dict[str, Any] = {
        "local_slm_system_prefix": (data.get("local_slm_system_prefix") or "").strip(),
        "supervisor_system": (data.get("supervisor_system") or "").strip(),
        "accountant": data.get("accountant") or {},
        "guardian": data.get("guardian") or {},
    }
    if PROMPTS_THE_JUDGE_PATH.exists():
        with open(PROMPTS_THE_JUDGE_PATH, encoding="utf-8") as f:
            judge_data = yaml.safe_load(f)
        if judge_data:
            result["the_judge"] = judge_data
    return result


@functools.lru_cache(maxsize=1)
def _get_prompts() -> dict[str, Any]:
    """Cached prompts loader. Use _get_prompts.cache_clear() in tests to invalidate."""
    return _load_prompts()


def _substitute_prompt_template(template: str, **kwargs: str) -> str:
    """
    Replace {{key}} placeholders with values. Use when consuming the_judge prompts.
    Uses str.replace (not re.sub) to avoid backslash interpretation in replacement
    strings (e.g. json.dumps output with \\n, \\t would be corrupted by regex).
    """
    result = template
    for key, value in kwargs.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result


class _LLMClientContext:
    """
    Async context manager wrapping an LLM client. Yields the complete()
    callable and closes the underlying HTTP client on exit to avoid connection leaks.
    """

    def __init__(self, client: Any, complete_fn: Callable[[str, str], Awaitable[str]]) -> None:
        self._client = client
        self._complete_fn = complete_fn

    async def __aenter__(self) -> Callable[[str, str], Awaitable[str]]:
        return self._complete_fn

    async def __aexit__(self, *args: Any) -> None:
        close_fn = getattr(self._client, "aclose", None) or getattr(
            self._client, "close", None
        )
        if close_fn is not None:
            result = close_fn()
            if asyncio.iscoroutine(result):
                await result


def get_model_client(
    provider: str,
    *,
    raw_system: bool = False,
    model_override: str | None = None,
) -> _LLMClientContext:
    """
    Abstract LLM client factory. Returns an async context manager that yields
    complete(system_prompt, user_prompt) -> str and closes the client on exit.

    Providers: anthropic, openai, ollama, lm_studio.

    When raw_system=True, Ollama/LM Studio clients skip the local_slm_system_prefix
    (used by The Accountant for classification; the forensic CoT prefix would
    conflict with the strict LEVEL_1/LEVEL_2 classifier persona).

    When model_override is set, use it instead of env / DEFAULT_MODELS.
    Provider-specific env vars prevent cross-routing (e.g. OLLAMA_MODEL
    must not affect --provider anthropic).
    """
    if model_override is not None and model_override.strip():
        model = model_override.strip()
    elif provider == "anthropic":
        model = (
            (os.environ.get("ANTHROPIC_MODEL") or "").strip()
            or DEFAULT_MODELS.get("anthropic", "")
        )
    elif provider == "openai":
        model = (
            (os.environ.get("OPENAI_MODEL") or "").strip()
            or DEFAULT_MODELS.get("openai", "")
        )
    elif provider == "ollama":
        model = (
            (os.environ.get("OLLAMA_MODEL") or os.environ.get("LLM_MODEL") or "").strip()
            or DEFAULT_MODELS.get("ollama", "")
        )
    elif provider == "lm_studio":
        model = (
            (os.environ.get("LM_STUDIO_MODEL") or os.environ.get("LLM_MODEL") or "").strip()
            or DEFAULT_MODELS.get("lm_studio", "")
        )
    else:
        model = DEFAULT_MODELS.get(provider, "")

    if provider == "anthropic":
        return _make_anthropic_client(model)
    elif provider == "openai":
        return _make_openai_client(model)
    # [Post 3 - Edge AI] Local inference paths: Ollama and LM Studio
    elif provider == "ollama":
        return _make_ollama_client(model, raw_system=raw_system)
    elif provider == "lm_studio":
        return _make_lm_studio_client(model, raw_system=raw_system)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _make_anthropic_client(model: str):
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic provider requires: pip install anthropic")

    client = anthropic.AsyncAnthropic(timeout=LLM_TIMEOUT)

    async def complete(system_prompt: str, user_prompt: str) -> str:
        msg = await client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return msg.content[0].text if msg.content else ""

    return _LLMClientContext(client, complete)


def _make_openai_client(model: str):
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise ImportError("openai provider requires: pip install openai")

    client = AsyncOpenAI(timeout=LLM_TIMEOUT)

    async def complete(system_prompt: str, user_prompt: str) -> str:
        r = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (r.choices[0].message.content or "") if r.choices else ""

    return _LLMClientContext(client, complete)


# [Post 3 - Edge AI] Ollama local inference. Uses the Instruction-Tuning block
# (local_slm_system_prefix from config/prompts.yaml) for Chain of Thought guidance
# when handling MCP tool schemas—unlike larger cloud models that can infer structure.
def _make_ollama_client(model: str, *, raw_system: bool = False):
    try:
        from ollama import AsyncClient
    except ImportError:
        raise ImportError("ollama provider requires: pip install ollama")

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    client = AsyncClient(host=host)
    # Ollama client uses host; timeout via request_options if supported
    _timeout = LLM_TIMEOUT

    async def complete(system_prompt: str, user_prompt: str) -> str:
        if raw_system:
            full_system = system_prompt  # e.g. Accountant classification; no CoT prefix
        else:
            prompts = _get_prompts()
            full_system = prompts["local_slm_system_prefix"] + "\n\n" + system_prompt
        r = await asyncio.wait_for(
            client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": full_system},
                    {"role": "user", "content": user_prompt},
                ],
            ),
            timeout=_timeout,
        )
        return (r.message.content or "") if r.message else ""

    return _LLMClientContext(client, complete)


# [Post 3 - Edge AI] LM Studio local inference. OpenAI-compatible API at localhost.
# Same Instruction-Tuning block as Ollama: SLMs require explicit Chain of Thought
# instructions to parse MCP tool output correctly; cloud models do not.
def _make_lm_studio_client(model: str, *, raw_system: bool = False):
    try:
        from openai import AsyncOpenAI
    except ImportError:
        raise ImportError("lm_studio provider requires: pip install openai")

    base_url = os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
    client = AsyncOpenAI(base_url=base_url, api_key="lm-studio", timeout=LLM_TIMEOUT)

    async def complete(system_prompt: str, user_prompt: str) -> str:
        if raw_system:
            full_system = system_prompt
        else:
            prompts = _get_prompts()
            full_system = prompts["local_slm_system_prefix"] + "\n\n" + system_prompt
        r = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": full_system},
                {"role": "user", "content": user_prompt},
            ],
        )
        return (r.choices[0].message.content or "") if r.choices else ""

    return _LLMClientContext(client, complete)


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


def _sanitize_tool_output_for_llm(raw: str, plain_text: bool = False) -> str:
    """
    Mitigate prompt injection: parse JSON and re-serialize so tool output is
    passed as structured data, not freeform text that could contain adversarial
    instructions. On parse failure, JSON-escape the excerpt so it cannot embed
    outer prompt delimiters (e.g. ---END TOOL OUTPUT---) that could undermine
    the injection mitigation.
    plain_text: when True, pass through as-is (e.g. Vision findings); no JSON parse.
    """
    if not raw or not raw.strip():
        return "(no output)"
    if plain_text:
        text = raw.strip()
        if "---END TOOL OUTPUT---" in text:
            text = text.replace("---END TOOL OUTPUT---", "[DELIMITER]")
        if "---BEGIN TOOL OUTPUT---" in text:
            text = text.replace("---BEGIN TOOL OUTPUT---", "[DELIMITER]")
        return text
    try:
        parsed = json.loads(raw.strip())
        return json.dumps(parsed, indent=2)
    except (json.JSONDecodeError, TypeError):
        excerpt = raw[:2000] + ("..." if len(raw) > 2000 else "")
        # JSON-escape so delimiter-like strings in malicious output cannot break fences
        return f"(parse failed; escaped raw): {json.dumps(excerpt)}"


def _sanitize_cli_for_prompt(s: str | None, max_len: int = 200) -> str:
    """Sanitize CLI-derived strings (title, author) before LLM prompt inclusion."""
    if s is None:
        return "(unspecified)"
    # Truncate and collapse newlines to prevent multiline injection
    cleaned = " ".join(s.split())[:max_len]
    return cleaned if cleaned else "(unspecified)"


# -----------------------------------------------------------------------------
# Agents
# -----------------------------------------------------------------------------


# SOVEREIGN-ONLY: The Vision tool (analyze_artifact_vision) must NEVER be routed to a
# cloud provider via The Accountant. It processes images locally only for data sovereignty.
# When using --use-accountant, vision is invoked only when artifact_image_path is
# provided, and it always calls the MCP tool (local Ollama). Do not add vision to
# LEVEL_2 cloud routing.


async def vision_agent(
    session: ClientSession,
    image_path: str,
    analysis_focus: str = "typography",
) -> dict:
    """
    Vision: Uses analyze_artifact_vision to analyze artifact images locally.
    Sovereign Vault: processes only on local Ollama; never routed to cloud.
    Returns {visual_findings: str} or {error: True, message: str}.
    """
    args: dict = {
        "image_path": image_path,
        "analysis_focus": _sanitize_cli_for_prompt(analysis_focus, max_len=200),
    }
    result = await session.call_tool("analyze_artifact_vision", arguments=args)
    text = extract_text_content(result)

    if result.isError:
        return {"error": True, "message": text, "raw": text, "visual_findings": ""}

    try:
        data = json.loads(text)
        # Use visual_findings only when tool succeeded; never inject error messages
        vf = "" if data.get("error") else (data.get("visual_findings", "") or "")
        return {
            "error": False,
            "data": data,
            "raw": text,
            "visual_findings": vf,
        }
    except json.JSONDecodeError:
        logger.error(f"Vision Agent parse failure: {text[:100]}{'...' if len(text) > 100 else ''}")
        return {
            "error": True,
            "message": "Vision Agent failed to parse tool response (invalid JSON)",
            "raw": text,
            "visual_findings": "",
        }


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
    vision_context: str | None = None,
) -> dict:
    """
    Analyst: Uses audit_artifact_consistency to check for discrepancies.
    Requires either book_standard_page_id (Notion page ID) or book_standard (inline).
    vision_context: optional visual description from VisionAgent (Sovereign Vault).
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
    if vision_context:
        args["vision_context"] = vision_context

    result = await session.call_tool("audit_artifact_consistency", arguments=args)
    text = extract_text_content(result)

    if result.isError:
        return {"error": True, "message": text, "raw": text}

    try:
        return {"error": False, "data": json.loads(text), "raw": text}
    except json.JSONDecodeError:
        return {"error": False, "data": None, "raw": text}


async def _apply_guardian_handshake(
    analyst_result: dict,
) -> tuple[dict, list[dict]]:
    """
    Human-in-the-Loop: if Analyst has HIGH discrepancies, prompt for authorization.
    Uses asyncio.to_thread for input() to avoid blocking the event loop.
    Returns (modified_analyst_result, disputed_discrepancies).
    disputed_discrepancies are moved to "Requires Further Investigation".
    """
    disputed: list[dict] = []
    data = analyst_result.get("data") or {}
    disc = data.get("discrepancies") or []  # guard against {"discrepancies": null}
    high_disc = [d for d in disc if (d.get("severity") or "").upper() == "HIGH"]
    if not high_disc:
        return analyst_result, disputed

    disputed_keys: set[tuple[str, str, str, str]] = set()
    stdin_closed = False
    for d in high_disc:
        summary = (
            f"[{d.get('severity', '?')}] {d.get('field', '')}: "
            f"expected '{d.get('expected', '')}' vs observed '{d.get('observed', '')}'"
        )
        print(f"\n  Guardian: HIGH severity finding — {summary}")
        if stdin_closed:
            answer = "no"
        else:
            try:
                # 5min timeout per prompt to avoid indefinite MCP session hold (server timeout risk).
                # Note: On timeout, the underlying input() thread may orphan; orchestrator's
                # stdin_closed state ensures we skip further input() calls and proceed gracefully.
                answer = await asyncio.wait_for(
                    asyncio.to_thread(
                        input, "  Do you authorize this forensic finding? (yes/no): "
                    ),
                    timeout=300,
                )
                answer = answer.strip().lower()
            except asyncio.TimeoutError:
                logger.warning(
                    "Guardian: input timeout (300s); treating as 'no' and disputing. "
                    "Use --no-guardian for CI."
                )
                stdin_closed = True
                answer = "no"
            except EOFError:
                logger.warning(
                    "Guardian: stdin closed (non-interactive); treating as 'no' and "
                    "disputing all HIGH findings. Use --no-guardian for CI."
                )
                stdin_closed = True
                answer = "no"
        if answer in ("yes", "y"):
            pass  # authorized
        elif answer in ("no", "n"):
            disputed.append({**d, "status": "DISPUTED_BY_HUMAN"})
            disputed_keys.add((
                d.get("field", ""),
                d.get("expected", ""),
                d.get("observed", ""),
                (d.get("severity") or "").upper(),
            ))
        else:
            print("  Guardian: Unrecognized response; treating as 'no' (disputed).")
            disputed.append({**d, "status": "DISPUTED_BY_HUMAN"})
            disputed_keys.add((
                d.get("field", ""),
                d.get("expected", ""),
                d.get("observed", ""),
                (d.get("severity") or "").upper(),
            ))

    if disputed:
        new_disc = [
            d for d in disc
            if (d.get("field", ""), d.get("expected", ""), d.get("observed", ""), (d.get("severity") or "").upper()) not in disputed_keys
        ]
        # Match audit-artifact-consistency.ts for High=45, Low=5. Extend with Medium=20, other=10
        # (TS does not emit these today; Python tiers avoid inflated scores if extended later).
        penalty = 0
        for item in new_disc:
            s = (item.get("severity") or "").upper()
            if s == "HIGH":
                penalty += 45
            elif s == "MEDIUM":
                penalty += 20
            elif s == "LOW":
                penalty += 5
            else:
                penalty += 10  # unknown severity: moderate penalty
        confidence = max(0, 100 - penalty)
        data = {
            **data,
            "discrepancies": new_disc,
            "is_consistent": len(new_disc) == 0,
            "confidence_score": confidence,
        }
        # Replace raw with post-dispute serialization so LLM synthesis receives current confirmed
        # findings; disputed items are passed separately in tool_parts.
        analyst_result = {
            **analyst_result,
            "data": data,
            "raw": json.dumps(data),
        }
    return analyst_result, disputed


def build_forensic_report(
    title: str,
    author: str | None,
    librarian_result: dict,
    analyst_result: dict,
    disputed_discrepancies: list[dict] | None = None,
    vision_context: str | None = None,
    vision_error_message: str | None = None,
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
        disputed = disputed_discrepancies or []
        if disc:
            lines.append("  Discrepancies:")
            for d in disc:
                lines.append(f"    - [{d.get('severity', '?')}] {d.get('field', '')}: "
                            f"expected '{d.get('expected', '')}' vs observed '{d.get('observed', '')}'")
        else:
            lines.append("  Discrepancies: None")

        if disputed:
            lines.extend([
                "",
                "───────────────────────────────────────────────────────────────",
                "  REQUIRES FURTHER INVESTIGATION (Disputed by Human)",
                "───────────────────────────────────────────────────────────────",
            ])
            for d in disputed:
                lines.append(f"    - [DISPUTED_BY_HUMAN] {d.get('field', '')}: "
                            f"expected '{d.get('expected', '')}' vs observed '{d.get('observed', '')}'")

    vf = ((analyst_result.get("data") or {}).get("visual_findings") or vision_context or "").strip()
    if vf:
        lines.extend([
            "",
            "───────────────────────────────────────────────────────────────",
            "  VISION FINDINGS (Sovereign Vault — Local Analysis)",
            "───────────────────────────────────────────────────────────────",
            "",
            f"  {vf}",
        ])
    elif vision_error_message:
        lines.extend([
            "",
            "───────────────────────────────────────────────────────────────",
            "  VISION ANALYSIS (Sovereign Vault)",
            "───────────────────────────────────────────────────────────────",
            "",
            f"  Status: Failed — {vision_error_message}",
        ])

    lines.extend([
        "",
        "═══════════════════════════════════════════════════════════════",
        "                    END OF REPORT",
        "═══════════════════════════════════════════════════════════════",
    ])

    return "\n".join(lines)


async def run_forensic_audit(
    title: str,
    author: str | None,
    observed: dict | None,
    provider: str | None = None,
    book_standard: dict | None = None,
    guardian_enabled: bool = True,
    artifact_image_path: str | None = None,
    analysis_focus: str = "typography",
) -> str:
    """
    Main orchestration: connect to MCP server, run Librarian → [Vision] → Analyst → Report.
    When provider is set (anthropic, openai, ollama, lm_studio), uses LLM to
    synthesize the report; otherwise uses deterministic build_forensic_report().
    When book_standard is provided (e.g. from golden dataset), uses it directly
    instead of librarian/sample, ensuring deterministic evaluation.
    When guardian_enabled=True (default), HIGH severity discrepancies trigger
    a human-in-the-loop authorization prompt before finalizing.
    When artifact_image_path is provided, VisionAgent runs first (Sovereign Vault:
    local Ollama only, never routed to cloud) and injects visual findings into Analyst.
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

            # 1. Librarian: pull book details (skip when book_standard provided)
            if book_standard is not None:
                librarian_result = {
                    "error": False,
                    "data": {"book_standards": [book_standard], "page_ids": []},
                    "raw": json.dumps({"book_standards": [book_standard]}),
                }
            else:
                librarian_result = await librarian_agent(session, title, author)

            # 2. Analyst: audit for discrepancies
            book_page_id = None
            if book_standard is None:
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

            # Sovereign Vault: if artifact image provided, run Vision first; inject into Analyst
            vision_context: str | None = None
            vision_result: dict | None = None
            if artifact_image_path:
                vision_result = await vision_agent(
                    session, artifact_image_path, analysis_focus
                )
                if not vision_result.get("error") and vision_result.get("visual_findings"):
                    vision_context = vision_result["visual_findings"]
                elif vision_result.get("error"):
                    logger.warning(
                        "Vision analysis failed: %s; proceeding without visual context.",
                        vision_result.get("message", "unknown"),
                    )
                elif vision_context is None:
                    logger.warning(
                        "Proceeding without visual context; text-based audit will complete."
                    )

            analyst_result = await analyst_agent(
                session, book_page_id, book_standard, observed,
                vision_context=vision_context,
            )

            # 2b. Guardian: human-in-the-loop for HIGH severity findings
            disputed: list[dict] = []
            if guardian_enabled:
                analyst_result, disputed = await _apply_guardian_handshake(analyst_result)

            # 3. Supervisor: combine and output Forensic Report
            if provider and provider != "none":
                try:
                    async with get_model_client(provider) as complete:
                        prompts = _get_prompts()
                        system = prompts["supervisor_system"]
                        if guardian_enabled:
                            guardian_prefix = (prompts.get("guardian") or {}).get("system_prefix") or ""
                            if guardian_prefix.strip():
                                system = guardian_prefix.strip() + "\n\n" + system
                        librarian_safe = _sanitize_tool_output_for_llm(
                            librarian_result.get("raw", "")
                        )
                        analyst_safe = _sanitize_tool_output_for_llm(
                            analyst_result.get("raw", "")
                        )
                        # Build tool output block; audit framing must be inside fence for guard coverage
                        the_judge = prompts.get("the_judge", {})
                        audit_instr = (the_judge.get("analyst", {}) or {}).get("audit_instruction")
                        tool_parts = []
                        if audit_instr and book_standard is not None and observed is not None:
                            obs_str = json.dumps(observed) if isinstance(observed, dict) else str(observed)
                            std_str = json.dumps(book_standard) if isinstance(book_standard, dict) else str(book_standard)
                            obs_safe = _sanitize_tool_output_for_llm(obs_str)
                            std_safe = _sanitize_tool_output_for_llm(std_str)
                            framed = _substitute_prompt_template(
                                audit_instr,
                                observed_data=obs_safe,
                                standard_data=std_safe,
                            )
                            tool_parts.append(f"Audit framing:\n{framed}")
                        tool_parts.extend([f"Librarian:\n{librarian_safe}", f"Analyst:\n{analyst_safe}"])
                        if vision_context and vision_context.strip():
                            vision_for_egress = vision_context
                            if provider in ("anthropic", "openai"):
                                red = _get_redactor()
                                if red is not None:
                                    try:
                                        vision_for_egress, n = red.scrub(vision_context)
                                        if n > 0:
                                            logger.info(
                                                "🛡️ Sovereign Vault: %d entities redacted from egress.",
                                                n,
                                            )
                                    except Exception:
                                        logger.warning(
                                            "PII Redactor failed during scrub; using unredacted vision findings."
                                        )
                            vision_safe = _sanitize_tool_output_for_llm(vision_for_egress, plain_text=True)
                            tool_parts.append(
                                f"Vision Findings (Sovereign Vault — Local Analysis):\n{vision_safe}"
                            )
                        elif vision_result and vision_result.get("error"):
                            msg = vision_result.get("message", "unknown error")
                            tool_parts.append(
                                f"Vision analysis failed: {_sanitize_cli_for_prompt(msg, max_len=200)}"
                            )
                        if disputed:
                            disputed_raw = json.dumps(disputed)
                            disputed_safe = _sanitize_tool_output_for_llm(disputed_raw)
                            tool_parts.append(
                                f"Requires Further Investigation (Disputed by Human):\n{disputed_safe}"
                            )
                        tool_block = "\n\n".join(tool_parts)
                        user = (
                            f"Title: {_sanitize_cli_for_prompt(title)}\n"
                            f"Author: {_sanitize_cli_for_prompt(author)}\n\n"
                            "---BEGIN TOOL OUTPUT---\n"
                            f"{tool_block}\n"
                            "---END TOOL OUTPUT---"
                        )
                        return await complete(system, user)
                except ImportError:
                    raise  # Missing provider SDK; propagate with clear install guidance
                except Exception as e:
                    logger.exception(
                        "LLM synthesis failed for provider=%s: %s",
                        provider,
                        e,
                    )
                    vision_err = (
                        vision_result.get("message")
                        if vision_result and vision_result.get("error")
                        else None
                    )
                    return (
                        f"[LLM synthesis failed: {e}]\n\n"
                        + build_forensic_report(
                            title, author, librarian_result, analyst_result,
                            disputed_discrepancies=disputed,
                            vision_context=vision_context,
                            vision_error_message=vision_err,
                        )
                    )
            vision_err = (
                vision_result.get("message")
                if vision_result and vision_result.get("error")
                else None
            )
            return build_forensic_report(
                title, author, librarian_result, analyst_result,
                disputed_discrepancies=disputed,
                vision_context=vision_context,
                vision_error_message=vision_err,
            )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(
        description="MCP Forensic Orchestrator — Supervisor Pattern"
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai", "ollama", "lm_studio", "none"],
        default="none",
        help="LLM provider: cloud (anthropic, openai) or local SLM (ollama, lm_studio). "
             "Use 'none' for deterministic report only.",
    )
    parser.add_argument(
        "--use-accountant",
        action="store_true",
        help="Route via The Accountant (semantic router) to choose provider from query complexity.",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="User query for Accountant classification (required with --use-accountant).",
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
    parser.add_argument(
        "--no-guardian",
        action="store_true",
        help="Skip human-in-the-loop authorization for HIGH findings (for CI/non-interactive use).",
    )
    parser.add_argument(
        "--artifact-image",
        default=None,
        help="Path to artifact image for Vision analysis (Sovereign Vault: local Ollama only).",
    )
    parser.add_argument(
        "--analysis-focus",
        default="typography",
        help="Focus for Vision analysis (e.g. typography, binding_texture). Default: typography.",
    )

    args = parser.parse_args()

    observed = None
    if args.observed_indicators or args.observed_points or args.observed_year is not None:
        try:
            indicators = (
                json.loads(args.observed_indicators)
                if args.observed_indicators
                else []
            )
            points = (
                json.loads(args.observed_points)
                if args.observed_points
                else []
            )
            if not isinstance(indicators, list) or not isinstance(points, list):
                raise ValueError("must be JSON arrays")
        except json.JSONDecodeError as e:
            parser.error(f"--observed-indicators/--observed-points: invalid JSON ({e})")
        except (ValueError, TypeError) as e:
            parser.error(f"--observed-indicators/--observed-points: {e}")
        observed = {
            "first_edition_indicators_observed": indicators,
            "points_of_issue_observed": points,
            "observed_year": args.observed_year,
        }

    if args.use_accountant:
        if not args.query:
            parser.error("--query is required when using --use-accountant")
        if args.provider and args.provider != "none":
            logger.warning(
                "--provider=%s ignored when using --use-accountant; "
                "provider is chosen by the router based on query complexity.",
                args.provider,
            )
        from router import run_with_accountant
        report = asyncio.run(
            run_with_accountant(
                args.query, args.title, args.author, observed,
                guardian_enabled=not args.no_guardian,
                artifact_image_path=args.artifact_image,
                analysis_focus=args.analysis_focus,
            )
        )
    else:
        report = asyncio.run(
            run_forensic_audit(
                args.title, args.author, observed,
                provider=args.provider if args.provider != "none" else None,
                guardian_enabled=not args.no_guardian,
                artifact_image_path=args.artifact_image,
                analysis_focus=args.analysis_focus,
            )
        )
    print(report)


if __name__ == "__main__":
    main()
