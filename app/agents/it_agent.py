from langchain_core.messages import HumanMessage, SystemMessage
from app.models.state import AgentState
from app.prompts.it_prompt import IT_PROMPT
from app.services.llm_service import get_llm
from app.services.retrieval_service import get_related_questions, retrieve_docs

def it_agent(state: AgentState) -> AgentState:
    state.retrieved_chunks = retrieve_docs(state.user_message, domain="it")

    top_score = state.retrieved_chunks[0].score
    if not state.retrieved_chunks:
        suggestions = get_related_questions(state.user_message, "it")
        state.answer = (
            "I don't have an exact match for that, but here are some related topics:\n\n"
            + "\n".join(f"- {q}" for q in suggestions)
        )
        state.session["suggested_questions"] = suggestions
        # ✅ CRITICAL: do NOT escalate
        state.needs_escalation = False
        return state

    context = "\n\n".join([
        f"Source: {chunk.source}\nContent: {chunk.content}"
        for chunk in state.retrieved_chunks
    ])

    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=IT_PROMPT),
        HumanMessage(content=f"User question: {state.user_message}\n\nContext:\n{context}")
    ])

    state.answer = response.content

    if "I don’t have enough information" in state.answer:
        state.needs_escalation = True

    return state