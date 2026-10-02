# SmartHelpDesk AI — AWS Migration Steps (personal AWS account)

Companion to `DEPLOYMENT_GUIDE.md` (which documents the EC2 + Docker Hub
approach you validated before) and `DOCKER_DEPLOYMENT.md`. This version uses
**Amazon ECR** instead of Docker Hub, since you already have AWS credentials
ready and it keeps the image private with no extra sign-up. Same EC2 runtime
approach otherwise — the two guides can be cross-referenced.

## What was fixed in the repo before this guide

- `requirements.txt` was saved as UTF-16 (Windows editor artifact) — `pip
  install` would have failed to parse it. Re-saved as UTF-8.
- `Dockerfile` had `COPY .env.production /app/.env`, baking secrets straight
  into the image. Removed — secrets now go in only via `docker run -e` at
  runtime, never baked into the image, matching Section 5.2 of
  `DEPLOYMENT_GUIDE.md`. **You no longer need a `.env.production` file at
  all** — a local `.env` (from `.env.example`) is only for testing on your
  own machine.
- Added `.dockerignore` so `.env*`, `.git`, and local runtime data never
  land in the image.
- `Dockerfile` now runs `python -m spacy download en_core_web_sm` during
  build — without it, the Presidio PII redactor silently does nothing (it
  fails open and only logs the error).
- `ui/app.py` had a hardcoded `http://127.0.0.1:8000` backend URL (this is
  "Issue 9" in `DEPLOYMENT_GUIDE.md` — previously patched live with `sed`
  and never fixed in code). It now reads `API_URL` from an environment
  variable, matching the `-e API_URL=...` flag your own guide's `docker run`
  command already passes to the frontend container.
- `app/db/models.py`: `Ticket.created_at` default was the `datetime.datetime`
  class itself instead of `datetime.datetime.utcnow`. Fixed (was harmless
  today only because `ticket_service.py` always sets it explicitly).

Known but not fixed (call these out if you hit them):
- Only `test_smoke.py` has real tests; `test_hr_agent.py`, `test_it_agent.py`,
  `test_router.py`, `test_ticket_flow.py` are empty stubs.
- SQLite (`data/app.db`) and Chroma (`data/chroma`) live inside the
  container's filesystem. On a single EC2 instance that's fine as long as
  you don't remove the container without a volume. It will **not** survive
  if you later move to ECS Fargate (ARCHITECTURE.md's stated long-term
  target) — Fargate storage is ephemeral, so that move would need RDS/EFS
  first. Not today's problem, just flagging it for later.

---

## Phase 1 — Local prep (Windows)

1. Confirm Docker Desktop is running.
2. Install the AWS CLI v2 if you don't have it:
   https://awscli.amazonaws.com/AWSCLIV2.msi
3. Configure it with your new credentials:
   ```
   aws configure
   ```
   Enter Access Key ID, Secret Access Key, a region (e.g. `us-east-1`), and
   output format `json`.
4. Create a local `.env` (used only for local testing, never baked into the
   image):
   ```
   copy .env.example .env
   ```
   Fill in `OPENAI_API_KEY=` with your real key. Leave `TICKET_BACKEND=db`.

## Phase 2 — Build and test the image locally

```powershell
cd C:\Users\tvasu\Projects\smarthelpdesk-ai

docker build -t smarthelpdesk-copilot .

docker run -d --name smarthelpdesk -p 8000:8000 --env-file .env smarthelpdesk-copilot

docker run -d --name smarthelpdesk-ui -p 8501:8501 --link smarthelpdesk `
  -e API_URL=http://smarthelpdesk:8000 `
  smarthelpdesk-copilot `
  streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
```

Verify:
- Backend: http://localhost:8000/health → `{"status":"ok",...}`
- Frontend: http://localhost:8501 → ask a question, confirm you get an
  answer (not "Backend error").

If it works locally, clean up before pushing:
```powershell
docker rm -f smarthelpdesk smarthelpdesk-ui
```

## Phase 3 — Push the image to Amazon ECR

```powershell
# Create the repository (one-time)
aws ecr create-repository --repository-name smarthelpdesk-copilot --region us-east-1

# Get your AWS account ID
aws sts get-caller-identity --query Account --output text

# Log Docker in to ECR (replace ACCOUNT_ID and region as needed)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag smarthelpdesk-copilot ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smarthelpdesk-copilot:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smarthelpdesk-copilot:latest
```

(If you'd rather use Docker Hub exactly as in `DEPLOYMENT_GUIDE.md` Section
2, that still works fine now that no secrets are baked into the image —
just skip this phase and follow that section instead.)

## Phase 4 — Launch the EC2 instance

Same as `DEPLOYMENT_GUIDE.md` Section 3, with one addition to the IAM role:

1. **EC2 → Launch Instance**
   - Name: `smarthelpdesk-ai`
   - AMI: Amazon Linux 2023
   - Instance type: `t2.medium` (4GB RAM — two containers need it; `t2.micro`
     caused SSM/memory issues before, per Issue 11)
   - Key pair: create new, download the `.pem`, save it securely
   - Security group inbound rules:
     - SSH (22) — Source: My IP
     - Custom TCP 8000 — Source: 0.0.0.0/0
     - Custom TCP 8501 — Source: 0.0.0.0/0
   - Storage: 30GB (default 8GB isn't enough — Issue 7)
2. **Elastic IP**: EC2 → Elastic IPs → Allocate → Associate to the instance
   (keeps the IP stable across restarts — Issue 5).
3. **IAM Role** — create one for the instance with:
   - `AmazonSSMManagedInstanceCore`
   - `AmazonEC2RoleforSSM`
   - `AmazonSSMManagedEC2InstanceDefaultPolicy`
   - `AmazonEC2ContainerRegistryReadOnly` (new — needed to pull from ECR;
     skip this one if you used Docker Hub instead)
   - Attach the role to the instance, then reboot it for the role to apply.

## Phase 5 — Connect and deploy

```bash
ssh -i "path\to\your-key.pem" ec2-user@YOUR_ELASTIC_IP
```
(If SSH times out or is denied, see Issues 1–4 in `DEPLOYMENT_GUIDE.md` —
SSM Session Manager is the fallback.)

On the instance:
```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
exit   # re-login for the group change to take effect
```

Log back in, then pull and run (Amazon Linux 2023 has the AWS CLI
preinstalled, so ECR login works out of the box given the IAM role above):

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker pull ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smarthelpdesk-copilot:latest

docker run -d --name smarthelpdesk --restart always -p 8000:8000 \
  -e OPENAI_API_KEY=your-real-key \
  -e MODEL_NAME=gpt-4o-mini \
  -e CHROMA_PERSIST_DIR=data/chroma \
  -e TICKET_BACKEND=db \
  -e APP_ENV=production \
  ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smarthelpdesk-copilot:latest

docker run -d --name smarthelpdesk-ui --restart always -p 8501:8501 \
  --link smarthelpdesk \
  -e API_URL=http://smarthelpdesk:8000 \
  ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/smarthelpdesk-copilot:latest \
  streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
```

Initialize the database (Issue 10):
```bash
docker exec smarthelpdesk python -c "
from app.db.models import Base
from sqlalchemy import create_engine
engine = create_engine('sqlite:///data/app.db')
Base.metadata.create_all(engine)
print('DB ready')
"
```

## Phase 6 — Verify

```bash
docker ps
curl http://localhost:8000/health
```
Then from your own machine:
```
Backend:  http://YOUR_ELASTIC_IP:8000
Frontend: http://YOUR_ELASTIC_IP:8501
```

If anything misbehaves, `DEPLOYMENT_GUIDE.md` Part 2 already has fixes for
the 13 issues you hit last time (container name conflicts, disk space,
volume mounts wiping the DB, etc.) — worth a skim before debugging from
scratch.
