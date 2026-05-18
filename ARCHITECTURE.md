## ARCHITECTURE.md — Deep technical doc

Create `ARCHITECTURE.md` at project root:

# 🏗️ SmartDesk AI — Architecture Deep Dive

## System Overview

SmartDesk AI is a **multi-agent helpdesk assistant** built on the principle:
> *"One shared platform with thin specialized agents — not 5 separate systems."*

## Agent Topology

### Router Agent
- **Job:** Classify user intent (`kb_query`, `create_ticket`, `check_status`) + domain (`hr`, `it`)
- **Tech:** LLM-based JSON classifier with regex fallback
- **Confidence handling:** Routes to ticket creation if confidence is low

### HR / IT RAG Agents
- **Job:** Answer policy/procedure questions from KB
- **Tech:** ChromaDB similarity search + grounded LLM response
- **Escalation:** If `top_score < 0.5` OR `len(chunks) == 0` → escalate to ticket

### Ticket Create Agent
- **Job:** Collect email, summarize issue, get confirmation, call ticket API
- **Tech:** State machine — gathers fields across turns
- **Backend:** Pluggable (`mock`, `notion`, `jira`)

### Ticket Status Agent
- **Job:** Fetch tickets by email, format response
- **Tech:** Calls ticket service, handles 0/1/N tickets distinctly

## State Management

`AgentState` is a Pydantic model passed through every node:

```python
class AgentState:
    session_id: str
    user_message: str
    intent: IntentType
    domain: DomainType
    retrieved_chunks: List[RetrievedChunk]
    answer: str
    needs_escalation: bool
    ticket: TicketDraft
    history: List[ConversationTurn]
    session: Dict      # cross-turn signals
    errors: List[str]

```
## Memory Architecture

- Session ID generated per conversation
- SQLite persists email, ticket draft, last 20 turns
- In-flight ticket drafts survive across turns until confirmed

## Guardrail Layers

### Input Guard (pre-router)

- Length check (2-2000 chars)
- Prompt injection regex
- Toxicity (better-profanity + keywords)


### Output Guard (post-agent)

- Groundedness check (LLM-as-judge, threshold 0.6)
- PII redaction (Presidio with en_core_web_sm)
- Length cap + block phrases

## RAG Pipeline

- Chunking: Q&A pairs kept as atomic units (no further splitting)
- Embedding: text-embedding-3-small (1536 dim)
- Storage: ChromaDB persistent collection per domain
- Retrieval: Cosine similarity, k=4
- Filtering: Optional metadata filter on category

## Evaluation

- Golden set: 22 cases covering all agent paths + edge cases
- Metrics:

    - System-level: pass rate, intent match, content match, escalation correctness
    - RAGAS: faithfulness, answer relevancy, context precision


Output: JSON + HTML report

## Deployment
```
Local: docker compose up
Production target: AWS ECS Fargate + ALB + ECR
Secrets: AWS Secrets Manager
Storage: S3 for KB versioning, eval reports
Logs: CloudWatch
```
# 📂 PHASE 3: Missing Files

## `.env.example` (template for new devs)

Create `.env.example` at project root:

### OpenAI
```
OPENAI_API_KEY=sk-your-key-here
MODEL_NAME=gpt-4o-mini
```
### Vector DB
```
CHROMA_PERSIST_DIR=data/chroma
```
### Ticketing
```
TICKET_BACKEND=mock
# NOTION_API_KEY=
# NOTION_DATABASE_ID=
```
### Environment
```
APP_ENV=dev
```