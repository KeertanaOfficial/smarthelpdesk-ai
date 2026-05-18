# app/agents/hr_agent.py

from langchain_core.messages import HumanMessage, SystemMessage
from app.models.state import AgentState
from app.prompts.hr_prompt import HR_PROMPT
from app.services.llm_service import get_llm
from app.services.retrieval_service import retrieve_docs, get_related_questions


def hr_agent(state: AgentState) -> AgentState:
    # ✅ Retrieval
    state.retrieved_chunks = retrieve_docs(state.user_message, domain="hr")

    if not state.retrieved_chunks:
        suggestions = get_related_questions(state.user_message, "hr")

        state.answer = (
            "I don't have an exact answer for that.\n\n"
            "Here are some related topics you might find useful:\n\n"
            + "\n".join(f"- {q}" for q in suggestions)
        )

        state.session["suggested_questions"] = suggestions

        # ✅ DO NOT ESCALATE
        state.needs_escalation = False
        return state

    # ✅ Confidence check
    top_score = state.retrieved_chunks[0].score

    if top_score > 0.75:
        context = "\n\n".join(c.content for c in state.retrieved_chunks)

        llm = get_llm()
        response = llm.invoke(
            [
                SystemMessage(content=HR_PROMPT),
                HumanMessage(content=f"{state.user_message}\n\nContext:\n{context}"),
            ]
        )
        state.answer = response.content
    else:
        # ✅ LOW CONFIDENCE → suggestions NOT ticket
        suggestions = get_related_questions(state.user_message, "hr")

        state.answer = (
            "I'm not fully confident this matches exactly.\n\n"
            "Here are some related topics:\n\n"
            + "\n".join(f"- {q}" for q in suggestions)
        )

        state.session["suggested_questions"] = suggestions

    state.needs_escalation = False
    return state