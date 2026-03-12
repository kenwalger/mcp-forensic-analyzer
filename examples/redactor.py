"""
Post 3.2: The Redactor — Contextual PII Obfuscation for Sovereign Vault.

Scrubs PERSON, LOCATION, and ORGANIZATION entities from forensic text
before it leaves the local environment (cloud egress). Uses presidio-analyzer
and presidio-anonymizer with the spacy provider and en_core_web_lg model.

The Redactor is applied only to data sent to cloud providers (Anthropic, OpenAI).
Local output (terminal, build_forensic_report) remains unredacted.

To control Redactor log verbosity, configure the 'mcp_forensic_analyzer.redactor'
(or 'redactor') logger level in your logging setup.
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)

# Entity types to redact before cloud egress (presidio supported entities)
_REDACT_ENTITIES = ["PERSON", "LOCATION", "ORGANIZATION"]


class SovereignRedactor:
    """
    Airlock for forensic text: scrubs PII (PERSON, LOCATION, ORGANIZATION)
    before cloud egress. Lazy-loads presidio to avoid startup cost when unused.
    """

    def __init__(self) -> None:
        self._analyzer = None
        self._anonymizer = None
        self._load_failed = False

    def _ensure_loaded(self) -> bool:
        """Load presidio engines if needed. Returns True if ready, False if load failed."""
        if self._load_failed:
            return False
        if self._analyzer is not None:
            return True
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            from presidio_anonymizer import AnonymizerEngine

            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
            }
            logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
            anonymizer = AnonymizerEngine()
            self._analyzer = analyzer
            self._anonymizer = anonymizer
            return True
        except Exception as e:
            self._load_failed = True
            self._analyzer = None
            self._anonymizer = None
            logger.error(
                "Sovereign Redactor load failed (presidio/spaCy): %s. "
                "To enable PII redaction: pip install presidio-analyzer presidio-anonymizer spacy "
                "&& python -m spacy download en_core_web_lg",
                e,
            )
            return False

    def scrub(
        self,
        text: str,
        *,
        allow_list: list[str] | None = None,
        on_failure: Callable[[], None] | None = None,
    ) -> tuple[str, int]:
        """
        Replace PERSON, LOCATION, and ORGANIZATION entities with <REDACTED>.

        allow_list: Strings to exclude from redaction (e.g. book metadata: author, title,
            publisher). Distinguishes Metadata from PII for precision-guided redaction.
        on_failure: If provided and a runtime error occurs, invoked before returning
            (text, 0), allowing the caller to disable the redactor.

        Returns:
            (scrubbed_text, num_entities_redacted)
        """
        if not text or not text.strip():
            return text, 0

        if not self._ensure_loaded():
            logger.warning(
                "🛡️ Sovereign Vault: Redactor load failed. Egressing unredacted."
            )
            if on_failure is not None:
                on_failure()
            return text, 0

        try:
            exclude = list(allow_list) if allow_list else []
            results = self._analyzer.analyze(
                text=text,
                language="en",
                entities=_REDACT_ENTITIES,
                allow_list=exclude,
            )
            if not results:
                return text, 0

            from presidio_anonymizer.entities import OperatorConfig

            redacted = OperatorConfig("replace", {"new_value": "<REDACTED>"})
            operators = {entity: redacted for entity in ["DEFAULT"] + _REDACT_ENTITIES}

            anonymized = self._anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators=operators,
            )
            count = len(getattr(anonymized, "items", []))
            return anonymized.text, count
        except Exception as e:
            logger.error("PII scrubbing failed during execution: %s", e)
            logger.warning(
                "🛡️ Sovereign Vault: Scrubbing failed mid-call. "
                "Egressing unredacted text for forensic continuity."
            )
            if on_failure is not None:
                on_failure()
            return text, 0
