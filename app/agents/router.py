import json
from langchain_core.messages import HumanMessage, SystemMessage
from app.models.state import AgentState
from app.prompts.router_prompt import ROUTER_PROMPT
from app.services.llm_service import get_llm
from app.services.decision_logger import log_decision
from app.services.retrieval_service import get_vectorstore, get_embeddings

def router_agent(state: AgentState) -> AgentState:
    llm = get_llm()

    # Build conversation context for better routing
    context_lines = []
    if state.history:
        recent = state.history[-4:]  # last 4 turns
        for turn in recent:
            context_lines.append(f"{turn.role}: {turn.content}")
    
    context_block = "\n".join(context_lines) if context_lines else "(no prior context)"

    user_input = (
        f"Recent conversation:\n{context_block}\n\n"
        f"Current user message: {state.user_message}"
    )

    response = llm.invoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=user_input)
    ])
    
    log_decision(
    session_id=state.session_id,
    step="router",
    input_text=state.user_message,
    output_text=f"intent={state.intent}, domain={state.domain}",
    extra_data={"llm_response": response.content}
    )

    try:
        # Strip markdown code blocks if present
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        parsed = json.loads(content)
        state.intent = parsed.get("intent", "unknown")
        state.domain = parsed.get("domain", "unknown")
    except Exception as e:
        state.intent = "unknown"
        state.domain = "unknown"
        state.errors.append(f"Router parse failure: {e}")

    return state


def get_related_questions(query: str, domain: str, k: int = 3):
    collection = "hr_docs" if domain == "hr" else "it_docs"

    vs = get_vectorstore(collection)

    # Use vector similarity (cosine via embeddings)
    results = vs.similarity_search(query, k=k)

    questions = []
    for r in results:
        content = r.page_content
        if "Question:" in content:
            q = content.split("Question:")[1].split("\n")[0].strip()
            questions.append(q)

    return questions