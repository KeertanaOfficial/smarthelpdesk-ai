from langchain_core.messages import HumanMessage, SystemMessage

from app.models.state import AgentState
from app.services.llm_service import get_llm
from app.services.retrieval_service import retrieve_docs


IT_PROMPT = """
You are an internal IT support assistant.

Use the provided knowledge base context to answer the user question clearly and concisely.

If the knowledge base does not contain the answer,
say:
"I could not find a matching IT knowledge base article."
"""


def it_agent(state: AgentState) -> AgentState:
    try:
        docs = retrieve_docs(state.user_message, domain="it")

        state.retrieved_chunks = docs

        if not docs:
            state.answer = "I could not find a matching IT knowledge base article."
            return state

        context = "\n\n".join([d.content for d in docs])

        llm = get_llm()

        response = llm.invoke([
            SystemMessage(content=IT_PROMPT),
            HumanMessage(
                content=f"""
User Question:
{state.user_message}

Knowledge Base Context:
{context}
"""
            )
        ])

        state.answer = response.content.strip()

    except Exception as e:
        state.answer = f"IT agent error: {str(e)}"
        state.errors.append(str(e))

    return state