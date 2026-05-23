from langchain_core.messages import HumanMessage, SystemMessage
from app.models.state import AgentState
from app.prompts.hr_prompt import HR_PROMPT
from app.services.llm_service import get_llm
from app.services.retrieval_service import (
    get_related_questions,
    retrieve_docs,
)

def hr_agent(state: AgentState) -> AgentState:

    # Retrieve documents
    state.retrieved_chunks = retrieve_docs(
        state.user_message,
        domain="hr"
    )

    # Handle empty retrieval safely
    if not state.retrieved_chunks:
        state.answer = (
            "I could not find any relevant HR knowledge base articles "
            "for your request."
        )
        return state

    # Safe scoring
    top_score = state.retrieved_chunks[0].score

    # Retrieved context
    context = "\n".join(
        chunk.content
        for chunk in state.retrieved_chunks
    )

    # LLM
    llm = get_llm()

    messages = [
        SystemMessage(content=HR_PROMPT),
        HumanMessage(
            content=f"""
User Question:
{state.user_message}

Knowledge Base Context:
{context}
"""
        ),
    ]

    response = llm.invoke(messages)

    state.answer = response.content

    # Related questions
    try:
        state.related_questions = get_related_questions(
            state.user_message,
            state.retrieved_chunks
        )
    except Exception:
        state.related_questions = []

    return state