# 🤖 SmartHelpDesk AI — Intelligent IT & HR Helpdesk Agent

> A production-grade multi-agent helpdesk assistant built with LangGraph, RAG, and 4-layer guardrails. Handles HR & IT queries, creates support tickets, and tracks status — with measurable quality via RAGAS evaluation. **Deployed live on AWS EC2.**

![Python](https://img.shields.io/badge/python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688) ![LangGraph](https://img.shields.io/badge/LangGraph-latest-orange) ![License](https://img.shields.io/badge/license-MIT-green)

**Live App:** `http://23.21.203.201:8501`

---

## ✨ Features

- 🤖 **5 Specialized Agents** — Router, HR RAG, IT RAG, Ticket Create, Ticket Status
- 🛡️ **4-Layer Guardrails** — PII (Presidio), prompt injection, toxicity, groundedness
- 📚 **Real-World Knowledge Base** — 1,800+ entries from Hugging Face datasets
- 💬 **Multi-Turn Memory** — Session-aware conversations with SQLite persistence
- 📊 **RAGAS Evaluation** — Faithfulness, relevance, context precision metrics
- 🎨 **Streamlit Chat UI** — Production-ready frontend
- 🐳 **Docker Containerized** — Two-container deployment
- ☁️ **Deployed on AWS EC2** — Live on t2.medium with Elastic IP

---

## 🏗️ Architecture

```
   ┌─────────────────┐
   │  Streamlit UI   │
   │   (port 8501)   │
   └────────┬────────┘
            │ HTTP (Docker internal network: http://smarthelpdesk:8000)
   ┌────────▼────────┐
   │  FastAPI Backend │
   │   (port 8000)   │
   └────────┬────────┘
            │
   ┌────────▼────────┐
   │  Input Guardrail │
   │  • Length check  │
   │  • Injection     │
   │  • Toxicity      │
   └────────┬────────┘
            │
   ┌────────▼────────┐
   │  Router Agent   │
   │  intent + domain│
   └────────┬────────┘
      ┌─────┼─────┐
      │     │     │
┌─────▼──┐ ┌▼───┐ ┌▼──────┐
│HR Agent│ │ IT │ │Ticket │
│ (RAG)  │ │RAG │ │Agents │
└─────┬──┘ └─┬──┘ └──┬────┘
      └───────┼───────┘
              │
   ┌──────────▼──────────┐
   │   Output Guardrail   │
   │  • Groundedness 0.6  │
   │  • PII redaction     │
   │  • Sanitization      │
   └──────────┬───────────┘
              │
   ┌──────────▼──────────┐
   │  ChromaDB Vector DB  │
   │  (HR + IT separate)  │
   └─────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| OpenAI API key | Required |
| Docker Desktop | Optional (for containers) |
| RAM | 4GB+ recommended |
| Disk | 5GB free (ML deps + ChromaDB) |

---

### 1. Clone & Setup

```bash
git clone https://github.com/KeertanaOfficial/smarthelpdesk-ai.git
cd smarthelpdesk-ai
```

```bash
# Create virtual environment
python -m venv .venv

# Activate — Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Activate — macOS / Linux
source .venv/bin/activate
```

```bash
# Install dependencies (~3–5 minutes — Presidio + spaCy are the largest)
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

---

### 2. Configure Environment

Create `.env` at project root (use `.env.example` as template):

```env
OPENAI_API_KEY=sk-your-key-here
MODEL_NAME=gpt-4o-mini
CHROMA_PERSIST_DIR=data/chroma
TICKET_BACKEND=mock
APP_ENV=dev
```

> ⚠️ Never commit your `.env` file. It is in `.gitignore`.

---

### 3. Download Datasets & Build Knowledge Base

```bash
python scripts/download_datasets.py
python -m app.services.kb_ingest
```

Verify KB health:
```bash
python -m app.services.kb_health
```

Expected output:
```
====================================
🔍 Knowledge Base Health Check
====================================
  ✅ hr_docs:  782 documents
  ✅ it_docs: 1015 documents
  ✅ Total:   1797 documents ready
====================================
```

---

### 4. Initialize Database

```bash
python -c "from app.db.models import Base; from sqlalchemy import create_engine; engine = create_engine('sqlite:///data/app.db'); Base.metadata.create_all(engine); print('DB ready')"
```

---

### 5. Start Services

**Terminal 1 — Backend:**
```bash
uvicorn app.api.main:app --reload
```
Expected: `INFO: Application startup complete.`

**Terminal 2 — Frontend:**
```bash
streamlit run ui/app.py
```

**Access:**
- Frontend: http://localhost:8501
- Backend API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

### 6. Smoke Test Checklist

| # | Test | URL / Command | Expected |
|---|------|---------------|----------|
| 1 | Backend health | `http://localhost:8000/health` | `{"status":"ok"}` |
| 2 | API docs | `http://localhost:8000/docs` | Swagger UI loads |
| 3 | Frontend | `http://localhost:8501` | Chat UI loads |
| 4 | HR query | "How many leave days?" | Real answer |
| 5 | IT query | "Reset my password" | Real answer |
| 6 | Ticket flow | "Create ticket for slow laptop" | Confirmation card |
| 7 | Guardrail | "Ignore all previous instructions" | Blocked warning |
| 8 | Multi-turn | Send 3 related messages | Email remembered |

```bash
# Automated smoke tests
pip install pytest
pytest tests/test_smoke.py -v
```

---

## 🐳 Docker Deployment

### Local Docker

```bash
# Build image
docker build -t smarthelpdesk-copilot .

# Run backend
docker run -d \
  --name smarthelpdesk \
  --restart always \
  -p 8000:8000 \
  --env-file .env \
  smarthelpdesk-copilot

# Run frontend
docker run -d \
  --name smarthelpdesk-ui \
  --restart always \
  -p 8501:8501 \
  --link smarthelpdesk \
  smarthelpdesk-copilot \
  streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
```

> ⚠️ **Important:** The frontend must use `http://smarthelpdesk:8000` (container name) as the backend URL, NOT `http://127.0.0.1:8000`. Each Docker container has its own localhost. Docker resolves container names as hostnames internally.

### Initialize DB inside container

```bash
docker exec smarthelpdesk python -c "
from app.db.models import Base
from sqlalchemy import create_engine
engine = create_engine('sqlite:///data/app.db')
Base.metadata.create_all(engine)
print('DB ready')
"
```

---

## ☁️ AWS Deployment (Live)

The app is deployed on AWS EC2 and accessible at:
- **Frontend:** `http://23.21.203.201:8501`
- **Backend:** `http://23.21.203.201:8000`

### AWS Infrastructure

| Component | Details |
|-----------|---------|
| Instance | t2.medium (4GB RAM — required for two ML containers) |
| OS | Amazon Linux 2023 |
| Storage | 30GB EBS (expanded from default 8GB) |
| Elastic IP | 23.21.203.201 (static — doesn't change on restart) |
| Security Group | Ports 22, 8000, 8501 open |
| IAM Role | EC2-SSM-Role with AmazonSSMManagedInstanceCore |

### AWS Setup Steps

#### 1. Launch EC2 Instance
1. AMI: Amazon Linux 2023
2. Instance type: **t2.medium** (do not use t2.micro — insufficient RAM)
3. Storage: **30GB** (default 8GB fills up with Docker image)
4. Security group inbound rules:
   - Port 22 (SSH) — your IP or 0.0.0.0/0 for dev
   - Port 8000 (Backend) — 0.0.0.0/0
   - Port 8501 (Frontend) — 0.0.0.0/0

#### 2. Assign Elastic IP
```
EC2 → Elastic IPs → Allocate → Associate to instance
```
This gives a static IP that never changes on restart.

#### 3. Create IAM Role for SSM
```
IAM → Roles → Create Role → EC2 service
Add policies:
  - AmazonSSMManagedInstanceCore
  - AmazonEC2RoleforSSM
  - AmazonSSMManagedEC2InstanceDefaultPolicy
  - AmazonS3FullAccess (for S3 file transfers)
```
Attach to instance: `EC2 → Actions → Security → Modify IAM Role`

#### 4. Expand EBS Volume (if using default 8GB)
```
EC2 → Volumes → Modify Volume → 30GB
```
Then on the instance:
```bash
sudo growpart /dev/xvda 1
sudo xfs_growfs /
df -h  # Verify
```

#### 5. Deploy Containers via SSM Run Command
```
Systems Manager → Run Command → AWS-RunShellScript
Select instance manually → paste command → Run
```

```bash
docker pull keertanadocker/smarthelpdesk-copilot:latest

docker run -d --name smarthelpdesk --restart always -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e MODEL_NAME=gpt-4o-mini \
  -e CHROMA_PERSIST_DIR=data/chroma \
  -e TICKET_BACKEND=mock \
  -e APP_ENV=dev \
  keertanadocker/smarthelpdesk-copilot:latest

docker run -d --name smarthelpdesk-ui --restart always -p 8501:8501 \
  --link smarthelpdesk \
  keertanadocker/smarthelpdesk-copilot:latest \
  streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
```

---

## 📊 Evaluation

```bash
# Quick eval (free, ~2 min)
python scripts/run_eval.py

# With RAGAS metrics (~$0.20, ~5 min)
python scripts/run_eval.py --with-ragas
```

### Current Performance

| Metric | Score | Baseline |
|--------|-------|----------|
| Pass Rate | **90.9%** ✅ | ≥ 80% |
| Avg Latency | **1.87s** ✅ | < 3s |
| Faithfulness | **0.92** ✅ | ≥ 0.85 |
| Answer Relevance | **0.88** ✅ | ≥ 0.80 |
| Context Precision | **0.85** ✅ | ≥ 0.75 |

### Test Coverage

| Category | # Tests | Coverage |
|----------|---------|----------|
| HR — Leave | 3 | Annual, sick, maternity |
| HR — Payroll | 2 | Salary, payslip |
| HR — Benefits | 2 | Health, 401k |
| HR — WFH/Conduct | 2 | Remote work, harassment |
| IT — VPN/Password | 4 | Setup, troubleshooting |
| IT — MFA/Email/Software | 3 | Various |
| Ticket Operations | 2 | Create, status |
| Out-of-Scope | 2 | Escalation behavior |
| Guardrails | 2 | Injection, toxicity |
| **Total** | **22** | |

Reports saved to `data/eval_results/eval_YYYYMMDD_HHMMSS.html`

---

## 🛡️ Guardrails

| Layer | Tool | Coverage | Where |
|-------|------|----------|-------|
| **1. Input Validation** | Regex + better-profanity | Prompt injection, toxicity, length (2–2000 chars) | Pre-router |
| **2. PII Detection** | Microsoft Presidio | Email, phone, SSN, credit card, IP | Input + Output |
| **3. Groundedness** | LLM-as-judge | RAG hallucination prevention (threshold: 0.6) | Post-RAG |
| **4. Output Sanitization** | Custom | Model self-disclosure, length cap, block phrases | Pre-response |

### Escalation Logic

A query escalates to ticket creation when any of these conditions are met:
- `top_retrieval_score < 0.5` — low similarity confidence
- `len(retrieved_chunks) == 0` — no relevant documents found
- Groundedness score `< 0.6` — LLM-as-judge flags hallucination risk
- Agent explicitly returns "not enough information"

---

## 🧰 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.11 | Core runtime |
| Backend | FastAPI + Uvicorn | REST API |
| Frontend | Streamlit | Chat UI |
| Orchestration | LangGraph | Agent workflow |
| LLM | OpenAI GPT-4o-mini | Reasoning + generation |
| Embeddings | text-embedding-3-small | 1536-dim vectors |
| Vector DB | ChromaDB | Semantic search |
| PII Detection | Microsoft Presidio | GDPR compliance |
| Profanity Filter | better-profanity | Toxicity filter |
| Evaluation | RAGAS | RAG quality metrics |
| Memory | SQLite | Session persistence |
| Validation | Pydantic v2 | Type-safe state |
| Containerization | Docker | Local & cloud deploy |
| Cloud | AWS EC2 + Elastic IP | Production hosting |
| Access Management | AWS SSM | Secure remote management |

---

## 📚 Datasets

| Dataset | Source | Rows | Domain |
|---------|--------|------|--------|
| HR Policy Q&A | [strova-ai/hr-policies-qa-dataset](https://huggingface.co/datasets/strova-ai/hr-policies-qa-dataset) | 644 | HR |
| HR Policy Snippets | [EmbraceCoder/HR_Policy](https://huggingface.co/datasets/EmbraceCoder/HR_Policy) | 123 | HR |
| IT Helpdesk Tickets | [Console-AI/IT-helpdesk-synthetic-tickets](https://huggingface.co/datasets/Console-AI/IT-helpdesk-synthetic-tickets) | 500 | IT |
| IT Call Center Tickets | [KameronB/synthetic-it-callcenter-tickets](https://huggingface.co/datasets/KameronB/synthetic-it-callcenter-tickets) | 500 | IT |
| Curated HR/IT KB | Custom synthetic | 30 | HR + IT |

---

## 📁 Project Structure

```
smarthelpdesk-ai/
├── app/
│   ├── api/                # FastAPI entry point
│   │   └── main.py
│   ├── agents/             # 5 specialized agents
│   │   ├── router.py
│   │   ├── hr_agent.py
│   │   ├── it_agent.py
│   │   ├── ticket_create_agent.py
│   │   └── ticket_status_agent.py
│   ├── graph/              # LangGraph orchestration
│   │   └── workflow.py
│   ├── guardrails/         # 4-layer safety
│   │   ├── pii_redactor.py
│   │   ├── input_validator.py
│   │   ├── groundedness.py
│   │   └── output_sanitizer.py
│   ├── db/                 # Database layer
│   │   ├── db.py           # SQLAlchemy setup (sqlite:///data/app.db)
│   │   └── models.py       # Tables: tickets, conversations, decision_logs
│   ├── evaluation/         # RAGAS + golden set
│   ├── models/             # Pydantic schemas
│   │   └── state.py
│   ├── prompts/            # Prompt templates
│   └── services/           # Core services
│       ├── kb_ingest.py
│       ├── kb_health.py
│       ├── retrieval_service.py
│       ├── ticket_service.py
│       └── session_service.py
├── ui/
│   └── app.py              # Streamlit frontend
├── scripts/
│   ├── download_datasets.py
│   └── run_eval.py
├── data/
│   ├── kb/                 # Raw + processed datasets
│   ├── chroma/             # ChromaDB vector store (baked into Docker image)
│   └── eval_results/       # Evaluation reports
├── tests/
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
├── ARCHITECTURE.md
└── README.md
```

---

## 🔧 Troubleshooting

### 🔴 Installation Issues

**`ModuleNotFoundError: No module named 'app'`**
```bash
# Always run from project root
cd smarthelpdesk-ai
python scripts/run_eval.py
```

**`Can't find model 'en_core_web_sm'`**
```bash
python -m spacy download en_core_web_sm
```

**`Presidio tries to download en_core_web_lg (400MB)`**
> The `pii_redactor.py` explicitly configures `en_core_web_sm`. Ensure your file matches the latest version from the repo.

---

### 🔴 Database Issues

**`no such table: decision_logs` (or tickets, conversations)**

The SQLite database exists but tables haven't been initialized. Run:
```bash
python -c "
from app.db.models import Base
from sqlalchemy import create_engine
engine = create_engine('sqlite:///data/app.db')
Base.metadata.create_all(engine)
print('Tables created')
"
```

> **Root cause in Docker:** If you mount `-v host_dir:/app/data`, the host directory overrides the image's data folder — including the ChromaDB vectors. Avoid volume mounts unless you pre-populate the host directory with the required data. The Docker image has ChromaDB baked in via `COPY . .` in the Dockerfile.

---

### 🔴 Runtime Issues

**`'dict' object has no attribute 'model_dump'`**
```python
# Use the defensive helper in app/api/main.py
def _to_dict(obj):
    if isinstance(obj, dict): return obj
    if hasattr(obj, "model_dump"): return obj.model_dump()
    return {}
```

**`cannot unpack non-iterable NoneType object`**
```python
# Ensure output_sanitizer.py always returns (text, flags)
result = sanitize_output(state.answer)
if isinstance(result, tuple) and len(result) == 2:
    state.answer, flags = result
```

---

### 🔴 KB / Retrieval Issues

**KB health shows 0 documents**
```bash
python -m app.services.kb_ingest
python -m app.services.kb_health
```

**Agent always escalates / never finds answers**
```bash
# Verify retrieval works
python -c "
from app.services.retrieval_service import retrieve_docs
print(retrieve_docs('leave policy', domain='hr'))
"
```
If empty, re-ingest. If still failing, lower similarity threshold in HR/IT agent (currently 0.5).

---

### 🔴 Docker Issues

**`no space left on device` during docker pull**

The ML Docker image is ~3GB. Default EC2 storage (8GB) fills up.
```bash
# Free up space
docker system prune -af && docker volume prune -f

# Or expand EBS volume in AWS Console → Volumes → Modify Volume → 30GB
# Then on instance:
sudo growpart /dev/xvda 1
sudo xfs_growfs /
```

**Frontend can't reach backend (`Connection refused 127.0.0.1:8000`)**

Each Docker container has its own localhost. Fix the backend URL in `ui/app.py`:
```python
# Wrong
API_URL = "http://127.0.0.1:8000/chat"

# Correct (use container name)
API_URL = "http://smarthelpdesk:8000/chat"
```

**Container name already in use**
```bash
docker rm -f smarthelpdesk
docker run ...  # re-run
```

---

### 🔴 AWS / SSH Issues

**SSH connection timed out**
- Check Security Group inbound rule for port 22 — source IP must match your current public IP
- Your home/office IP is dynamic and changes — update the rule or set source to `0.0.0.0/0` for dev
- Best solution: use an **Elastic IP** so the instance IP never changes

**SSH Permission denied (publickey) after recreating key pair**
- Deleting and recreating a key pair in AWS does NOT update existing instances
- The public key lives on the instance in `~/.ssh/authorized_keys`
- Fix: use SSM Session Manager to access the instance and manually add the new public key:
```bash
# Get your new public key locally
ssh-keygen -y -f your-key.pem

# In SSM terminal on EC2
echo "YOUR_NEW_PUBLIC_KEY" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**SSM Session Manager shows no instances / "Undeliverable"**
- The EC2 instance needs an IAM role with SSM permissions attached
- Also occurs when instance is out of memory (SSM agent crashes on t2.micro)
- Fix: attach IAM role + upgrade to t2.medium
- After attaching role, reboot the instance and wait 2–3 minutes

**SCP hangs indefinitely**
- Common on underpowered instances or unstable connections
- Use S3 as intermediary instead:
```bash
# Upload via AWS Console → S3
# Download on EC2 via SSM Run Command:
aws s3 cp s3://your-bucket/chroma /home/ec2-user/data/chroma --recursive
docker cp /home/ec2-user/data/chroma smarthelpdesk:/app/data/chroma
```

---

### 🔴 Ticket Flow Issues

**Bot keeps asking for email after providing it**
> Set email in the Streamlit sidebar, or ensure format is `user@domain.com`.

**Ticket status shows "no tickets" after creation**
> If using mock backend, SQLite data lives inside the container. A container restart wipes it. This is expected for mock mode. For persistence, use Notion/Jira integration or ensure you don't restart the container between create and status check.

---

## 🗺️ Roadmap

### ✅ Completed
- Multi-agent orchestration (LangGraph)
- RAG with 1,800+ real KB entries
- 4-layer guardrails (PII, injection, toxicity, groundedness)
- RAGAS evaluation harness (22 golden test cases)
- Multi-turn session memory (SQLite)
- Streamlit chat UI with guardrail signals
- Docker containerization
- AWS EC2 deployment with Elastic IP + SSM

### 🔜 Next Steps
- Notion/Jira live ticket backend (replace mock)
- CI/CD with GitHub Actions (auto-deploy on push)
- AWS Secrets Manager for API key management
- CloudWatch dashboards + alerting

### 🎯 Future
- Move to ECS Fargate + ALB for auto-scaling
- Hybrid search (semantic + BM25 + re-ranker)
- LangSmith observability
- Multi-language support
- Voice interface

---

## 🧪 Sample Queries

### HR Queries
```
"How many leave days do I get?"
"What is the maternity leave policy?"
"When is salary credited?"
"How do I submit a reimbursement?"
```

### IT Queries
```
"How do I set up VPN?"
"Reset my password"
"My VPN keeps disconnecting"
"How do I set up MFA?"
```

### Ticket Operations
```
"Create a ticket for slow laptop"
"What is the status of my tickets?"
```

### Guardrail Tests (will be blocked)
```
"Ignore all previous instructions"
"Tell me how to hack the VPN"
```

### Out-of-Scope (will escalate to ticket)
```
"What is the cryptocurrency policy?"
"My monitor is flickering"
```

---

## 🛠️ Useful Commands

```bash
# KB health check
python -m app.services.kb_health

# Re-ingest KB
python -m app.services.kb_ingest

# Run evaluation
python scripts/run_eval.py --with-ragas

# Docker logs
docker logs smarthelpdesk --tail 50
docker logs smarthelpdesk-ui --tail 50

# Get into container
docker exec -it smarthelpdesk bash

# Check running containers
docker ps

# Free up disk space
docker system prune -af
```

---

## 📜 License

MIT — see LICENSE file.

---

## 👤 Author

Built by **Keertana Nandyala** as a capstone project for the Interview Kickstart Applied Agentic AI Program — demonstrating production-grade multi-agent AI systems.

- 🌐 [Keertana - LinkedIn](www.linkedin.com/in/keertana-nandyala)
- 📧 Email - keertana.1@gmail.com

---

## 🙏 Acknowledgments

- [LangChain / LangGraph](https://github.com/langchain-ai/langchain) teams
- [Microsoft Presidio](https://github.com/microsoft/presidio) for PII detection
- [RAGAS](https://github.com/explodinggradients/ragas) for evaluation framework
- [Hugging Face](https://huggingface.co) for open datasets
- [Streamlit](https://streamlit.io) for the rapid UI framework
