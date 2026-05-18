"""
Groundedness checker — LLM-as-judge verifies answer is supported by context.
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage

GROUNDEDNESS_PROMPT = """You are a strict fact-checker.

Given:
1. CONTEXT (knowledge base excerpts)
2. ANSWER (the AI's response)

Decide if the ANSWER is fully supported by the CONTEXT.

Return JSON only:
{
  "grounded": true/false,
  "score": 0.0-1.0,
  "reason": "brief explanation"
}

Scoring:
- 1.0 = every claim in ANSWER is directly supported by CONTEXT
- 0.5 = partially supported (some unsupported claims)
- 0.0 = ANSWER fabricates info not in CONTEXT
- Generic "I don't know" → grounded=true, score=1.0
"""


def check_groundedness(answer: str, context_chunks: list) -> dict:
    """
    Returns: {grounded: bool, score: float, reason: str}
    """
    if not answer or not answer.strip():
        return {"grounded": True, "score": 1.0, "reason": "Empty answer"}

    # Skip check for safe fallbacks
    safe_phrases = [
        "i don't have enough information",
        "i don't know",
        "please provide",
        "please confirm",
        "ticket has been created",
    ]
    if any(p in answer.lower() for p in safe_phrases):
        return {"grounded": True, "score": 1.0, "reason": "Safe fallback response"}

    if not context_chunks:
        return {
            "grounded": False,
            "score": 0.0,
            "reason": "No context available to ground the answer",
        }

    context_text = "\n\n".join(
        f"[Source: {c.source}]\n{c.content}" for c in context_chunks
    )

    user_prompt = (
        f"CONTEXT:\n{context_text}\n\n"
        f"ANSWER:\n{answer}\n\n"
        "Is the ANSWER fully supported by CONTEXT? Respond in JSON."
    )

    try:
        llm = get_llm()
        response = llm.invoke([
            SystemMessage(content=GROUNDEDNESS_PROMPT),
            HumanMessage(content=user_prompt),
        ])

        # Strip code-block fences if present
        if isinstance(response.content, list):
            content = ' '.join(str(item) for item in response.content).strip()
        else:
            content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        parsed = json.loads(content)
        score = float(parsed.get("score", 0))
        return {
            "grounded": score >= GROUNDEDNESS_THRESHOLD,
            "score": score,
            "reason": parsed.get("reason", ""),
        }

    except Exception as e:
        # Fail open — don't block if the checker itself fails
        return {
            "grounded": True,
            "score": 0.5,
            "reason": f"Check failed: {e}",
        }
from app.services.llm_service import get_llm
from app.guardrails.policies import GROUNDEDNESS_THRESHOLD


