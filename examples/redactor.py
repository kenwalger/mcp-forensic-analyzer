"""
Post 3.2: The Redactor — Contextual PII Obfuscation for Sovereign Vault.

Scrubs PERSON, LOCATION, and ORGANIZATION entities from forensic text
before it leaves the local environment (cloud egress). Uses presidio-analyzer
and presidio-anonymizer with the spacy provider and en_core_web_lg model.

The Redactor is applied only to data sent to cloud providers (Anthropic, OpenAI).
Local output (terminal, build_forensic_report) remains unredacted.
"""

import logging

logger = logging.getLogger(__name__).setLevel(logging.ERROR)

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

    def _ensure_loaded(self) -> None:
        if self._load_failed:
            raise RuntimeError("Redactor load previously failed; skipping retry.")
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
            analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
            anonymizer = AnonymizerEngine()
            self._analyzer = analyzer
            self._anonymizer = anonymizer
        except ImportError as e:
            self._load_failed = True
            self._analyzer = None
            self._anonymizer = None
            raise ImportError(
                "Sovereign Redactor requires: pip install presidio-analyzer presidio-anonymizer spacy && "
                "python -m spacy download en_core_web_lg"
            ) from e
        except OSError:
            self._load_failed = True
            self._analyzer = None
            self._anonymizer = None
            logger.error(
                "Sovereign Redactor: spaCy model not found. Please run: python -m spacy download en_core_web_lg"
            )
            raise

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

        from presidio_anonymizer.entities import OperatorConfig

        operators = {
            "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
            "PERSON": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
            "LOCATION": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
            "ORGANIZATION": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
        }

        anonymized = self._anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators,
        )
        count = len(getattr(anonymized, "items", []))
        return anonymized.text, count
