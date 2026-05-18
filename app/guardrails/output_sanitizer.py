"""
Final output sanitization — hardened, always returns tuple.
"""

import re
from typing import Tuple, List

from app.guardrails.pii_redactor import redact_pii
from app.guardrails.policies import BLOCK_PHRASES_IN_OUTPUT, ANSWER_MAX_LENGTH


def sanitize_output(text) -> Tuple[str, List[str]]:
    """
    Sanitize final output.
    GUARANTEES return type: (str, list) — never None, never single value.
    """
    flags: List[str] = []

    # Defensive: handle None / non-string
    if text is None:
        return "", flags
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return text, flags

    try:
        # 1. Truncate
        if len(text) > ANSWER_MAX_LENGTH:
            text = text[:ANSWER_MAX_LENGTH] + "...[truncated]"
            flags.append("truncated")

        # 2. Block model self-disclosure
        for phrase in BLOCK_PHRASES_IN_OUTPUT:
            if phrase.lower() in text.lower():
                flags.append(f"blocked_phrase:{phrase}")
                text = re.sub(re.escape(phrase), "[redacted]", text, flags=re.IGNORECASE)

        # 3. Redact PII (defensive unpack)
        result = redact_pii(text, allow_in_ticket_flow=True)
        if isinstance(result, tuple) and len(result) == 2:
            redacted_text, pii_found = result
            if pii_found:
                flags.append(f"pii_redacted:{len(pii_found)}")
                text = redacted_text
        else:
            print(f"[output_sanitizer] redact_pii returned unexpected: {type(result)}")

    except Exception as e:
        flags.append(f"sanitize_error:{type(e).__name__}")

    # ✅ GUARANTEED tuple return
    return text, flags
