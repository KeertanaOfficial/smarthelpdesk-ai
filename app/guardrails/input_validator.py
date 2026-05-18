"""
Input validation: length, prompt injection, toxicity.
"""

import re
from typing import Optional

try:
    from better_profanity import profanity  # type: ignore[import]
    profanity.load_censor_words()
except ImportError:
    class _FallbackProfanity:
        @staticmethod
        def contains_profanity(text: str) -> bool:
            return False

    profanity = _FallbackProfanity()

from app.guardrails.policies import (
    INPUT_MAX_LENGTH,
    INPUT_MIN_LENGTH,
    INJECTION_PATTERNS,
    TOXIC_KEYWORDS,
)


class ValidationResult:
    def __init__(
        self,
        valid: bool,
        reason: str = "",
        risk_score: float = 0.0,
        flags: Optional[list] = None,
    ):
        self.valid = valid
        self.reason = reason
        self.risk_score = risk_score
        self.flags = flags or []

    def to_dict(self):
        return {
            "valid": self.valid,
            "reason": self.reason,
            "risk_score": self.risk_score,
            "flags": self.flags,
        }


# ============================================================
# Individual checks
# ============================================================
def check_length(text: str) -> ValidationResult:
    n = len(text or "")
    if n < INPUT_MIN_LENGTH:
        return ValidationResult(False, "Message too short.", 0.1, ["length"])
    if n > INPUT_MAX_LENGTH:
        return ValidationResult(
            False,
            f"Message exceeds {INPUT_MAX_LENGTH} characters.",
            0.3,
            ["length"],
        )
    return ValidationResult(True)


def check_prompt_injection(text: str) -> ValidationResult:
    lower = (text or "").lower()
    matched = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            matched.append(pattern)

    if matched:
        return ValidationResult(
            False,
            "Detected potential prompt injection attempt.",
            risk_score=0.9,
            flags=["prompt_injection"] + matched[:2],
        )
    return ValidationResult(True)


def check_toxicity(text: str) -> ValidationResult:
    if not text:
        return ValidationResult(True)

    if profanity.contains_profanity(text):
        return ValidationResult(
            False,
            "Message contains inappropriate language.",
            risk_score=0.7,
            flags=["profanity"],
        )

    lower = text.lower()
    for kw in TOXIC_KEYWORDS:
        if kw in lower:
            return ValidationResult(
                False,
                "Message contains restricted content.",
                risk_score=0.8,
                flags=["toxic_keyword", kw],
            )

    return ValidationResult(True)


# ============================================================
# Master check
# ============================================================
def validate_input(text: str) -> ValidationResult:
    """Run all input checks. Returns first failure or success."""
    for check in (check_length, check_prompt_injection, check_toxicity):
        result = check(text)
        if not result.valid:
            return result
    return ValidationResult(True, "All input checks passed.", 0.0)