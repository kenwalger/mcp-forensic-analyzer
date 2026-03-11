"""
Post 3.2: The Redactor — Contextual PII Obfuscation for Sovereign Vault.

Scrubs PERSON, LOCATION, and ORGANIZATION entities from forensic text
before it leaves the local environment (cloud egress). Uses presidio-analyzer
and presidio-anonymizer with the spacy provider and en_core_web_lg model.

The Redactor is applied only to data sent to cloud providers (Anthropic, OpenAI).
Local output (terminal, build_forensic_report) remains unredacted.
"""

import logging

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

    def _ensure_loaded(self) -> None:
        if self._analyzer is not None:
            return
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            from presidio_anonymizer import AnonymizerEngine

            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            self._analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
            self._anonymizer = AnonymizerEngine()
        except ImportError as e:
            raise ImportError(
                "Sovereign Redactor requires: pip install presidio-analyzer presidio-anonymizer spacy && "
                "python -m spacy download en_core_web_lg"
            ) from e

    def scrub(self, text: str) -> tuple[str, int]:
        """
        Replace PERSON, LOCATION, and ORGANIZATION entities with <REDACTED>.

        Returns:
            (scrubbed_text, num_entities_redacted)
        """
        if not text or not text.strip():
            return text, 0

        self._ensure_loaded()

        results = self._analyzer.analyze(
            text=text,
            language="en",
            entities=_REDACT_ENTITIES,
        )

        if not results:
            return text, 0

        anonymized = self._anonymizer.anonymize(
            text=text,
            analyzer_results=results,
        )

        return anonymized.text, len(results)
