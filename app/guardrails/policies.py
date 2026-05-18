"""
Centralized guardrail policies — tunable from one place.
"""

# ============================================================
# Input policies
# ============================================================
INPUT_MAX_LENGTH = 2000
INPUT_MIN_LENGTH = 2

# Prompt injection patterns (regex)
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) (instructions?|prompts?|rules?)",
    r"disregard (all )?(previous|prior|above) (instructions?|prompts?|rules?)",
    r"forget (everything|all|your instructions?|the system prompt)",
    r"you are now (a |an )?[a-zA-Z]+",
    r"act as (a |an )?[a-zA-Z]+",
    r"new instructions?:",
    r"system prompt:",
    r"reveal your (system prompt|instructions?|rules?)",
    r"<\|.*?\|>",                       # special tokens
    r"</?(system|user|assistant)>",     # role spoofing
]

# Toxic keywords (extend as needed)
TOXIC_KEYWORDS = ["kill", "suicide", "bomb", "weapon", "exploit", "hack into"]

# ============================================================
# PII policies
# ============================================================
PII_ENTITIES_TO_DETECT = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "CREDIT_CARD",
    "IP_ADDRESS",
]

# Email is needed in ticket flow — allow it in input
PII_ALLOWED_IN_TICKET_FLOW = ["EMAIL_ADDRESS"]

# ============================================================
# Output policies
# ============================================================
GROUNDEDNESS_THRESHOLD = 0.6
ANSWER_MAX_LENGTH = 1500

BLOCK_PHRASES_IN_OUTPUT = [
    "I am an AI language model",
    "As an AI",
    "openai",
    "gpt-4",
    "claude",
]