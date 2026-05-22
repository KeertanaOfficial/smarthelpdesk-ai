"""
PII Detection & Redaction using Microsoft Presidio — hardened.
"""

import re
from typing import Tuple, List, Optional


def detect_pii(text: str) -> List[dict]:
    """Return list of detected PII entities, or empty list on error."""
    if not text:
        return []

    analyzer, _ = _get_engines()
    if analyzer is None:
        return []

    try:
        from app.guardrails.policies import PII_ENTITIES_TO_DETECT
        entities = _normalize_entities(PII_ENTITIES_TO_DETECT)
        results = analyzer.analyze(
            text=text,
            entities=entities,
            language="en",
        )
        return [
            {
                "entity_type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "score": r.score,
                "text": text[r.start:r.end],
            }
            for r in results
        ]
    except Exception as e:
        print(f"[pii_redactor] detect_pii error: {e}")
        return []


def redact_pii(text: str, allow_in_ticket_flow: bool = False) -> Tuple[str, list]:
    """
    Redact PII in text. ALWAYS returns a tuple (text, list).
    """
    # ✅ Defensive: always return tuple even on bad input
    if not text or not isinstance(text, str):
        return text or "", []

    analyzer, anonymizer = _get_engines()
    if analyzer is None or anonymizer is None:
        # Engines unavailable → return original text, no detections
        return text, []

    try:
        from app.guardrails.policies import (
            PII_ENTITIES_TO_DETECT,
            PII_ALLOWED_IN_TICKET_FLOW,
        )
        from presidio_anonymizer.entities import OperatorConfig

        entities_to_redact = _normalize_entities(PII_ENTITIES_TO_DETECT)
        allowed_in_ticket_flow = set(_normalize_entities(PII_ALLOWED_IN_TICKET_FLOW))
        if allow_in_ticket_flow:
            entities_to_redact = [
                e for e in entities_to_redact if e not in allowed_in_ticket_flow
            ]

        results = analyzer.analyze(
            text=text,
            entities=entities_to_redact,
            language="en",
        )

        if not results:
            return text, []

        operators = {
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
            "US_SSN": OperatorConfig("replace", {"new_value": "<SSN>"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "<CREDIT_CARD>"}),
            "IP_ADDRESS": OperatorConfig("replace", {"new_value": "<IP>"}),
        }

        anonymized = anonymizer.anonymize(
            text=text,
            analyzer_results=results,  # type: ignore[arg-type]
            operators=operators,
        )

        detected = [
            {
                "entity_type": r.entity_type,
                "text": text[r.start:r.end],
                "score": r.score,
            }
            for r in results
        ]
        return anonymized.text, detected

    except Exception as e:
        print(f"[pii_redactor] redact_pii error: {e}")
        # ✅ Fail open: return original text + empty list
        return text, []


def extract_email(text: Optional[str]) -> Optional[str]:
    """Extract first email from text (used for ticket flow)."""
    if not text:
        return None
    match = re.search(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        text,
    )
    return match.group(0) if match else None


def _normalize_entities(entities) -> List[str]:
    """Normalize entity configuration to a safe list of entity strings."""
    if not entities:
        return []
    if isinstance(entities, str):
        return [entities]
    try:
        return list(entities)
    except TypeError:
        return []


_analyzer = None
_anonymizer = None
_init_error = None


def _get_engines():
    """Lazy-load Presidio engines with explicit small spaCy model."""
    global _analyzer, _anonymizer, _init_error

    if _init_error is not None:
        return None, None

    if _analyzer is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            from presidio_anonymizer import AnonymizerEngine

            # ✅ Force small spaCy model (12MB instead of 400MB)
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()

            _analyzer = AnalyzerEngine(
                nlp_engine=nlp_engine,
                supported_languages=["en"],
            )
            _anonymizer = AnonymizerEngine()
            print("[pii_redactor] ✅ Presidio initialized with en_core_web_sm")

        except Exception as e:
            _init_error = str(e)
            print(f"[pii_redactor] ❌ Presidio init failed: {e}")
            print("   Fix: python -m spacy download en_core_web_sm")
            return None, None

    return _analyzer, _anonymizer