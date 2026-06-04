# SmartDesk AI — Deployment Guide & Troubleshooting Reference

---

## PART 1: Complete Deployment Guide (From Scratch)

### Prerequisites
- Docker Desktop installed locally
- AWS account with EC2 access
- OpenAI API key
- Docker Hub account

---

### Section 1: Local Docker Setup

#### 1.1 Build the Docker Image
```bash
# From your project root (where Dockerfile lives)
docker build -t smartdesk-copilot .
```

#### 1.2 Run Locally to Verify
```bash
docker run -d \
  --name smartdesk \
  -p 8000:8000 \
  --env-file .env \
  smartdesk-copilot

# Run frontend
docker run -d \
  --name smartdesk-ui \
  -p 8501:8501 \
  --link smartdesk \
  -e API_URL=http://smartdesk:8000 \
  smartdesk-copilot \
  streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
```

#### 1.3 Verify locally
```
Backend:  http://localhost:8000
Frontend: http://localhost:8501
```

---

### Section 2: Push Docker Image to Docker Hub

#### 2.1 Create Docker Hub Repository
1. Go to [hub.docker.com](https://hub.docker.com)
2. Sign up / Log in
3. Click **Create Repository**
4. Name it `smartdesk-copilot`, set to **Public**
5. Click **Create**

#### 2.2 Login and Push Locally
```bash
# Login (use password or PAT token with Read & Write scope)
docker logout
docker login

# Tag image with your Docker Hub username
docker tag smartdesk-copilot YOUR_DOCKERHUB_USERNAME/smartdesk-copilot:latest

# Push
docker push YOUR_DOCKERHUB_USERNAME/smartdesk-copilot:latest
```

> **Note:** If push fails with "insufficient scope", create a Personal Access Token at Docker Hub → Account Settings → Personal Access Tokens with **Read & Write** permissions, and use that as your password when logging in.

---

### Section 3: AWS Setup

#### 3.1 Launch EC2 Instance
1. Go to **EC2 → Launch Instance**
2. Name: `smartdesk-ai`
3. AMI: **Amazon Linux 2023**
4. Instance type: **t2.medium** (recommended — 4GB RAM needed for two containers)
5. Key pair: Create new → Download `.pem` file → **save it securely**
6. Security group: Allow inbound rules:
   - SSH: Port 22, Source: My IP (or 0.0.0.0/0 for dev)
   - Custom TCP: Port 8000, Source: 0.0.0.0/0
   - Custom TCP: Port 8501, Source: 0.0.0.0/0
7. Storage: **30GB** (default 8GB is not enough)
8. Click **Launch Instance**

#### 3.2 Assign Elastic IP (Prevents IP changing on restart)
1. Go to **EC2 → Network & Security → Elastic IPs**
2. Click **Allocate Elastic IP address** → **Allocate**
3. Select the new IP → **Actions → Associate Elastic IP address**
4. Select your instance → **Associate**

#### 3.3 Create IAM Role for SSM Access
1. Go to **IAM → Roles → Create Role**
2. Select **AWS Service → EC2** → Next
3. Add these policies:
   - `AmazonSSMManagedInstanceCore`
   - `AmazonEC2RoleforSSM`
   - `AmazonSSMManagedEC2InstanceDefaultPolicy`
   - `AmazonS3FullAccess` (needed if using S3 for data transfer)
4. Name it `EC2-SSM-Role` → **Create Role**
5. Go to **EC2 → Instances → select your instance**
6. **Actions → Security → Modify IAM Role** → Select `EC2-SSM-Role` → **Update**
7. **Reboot** the instance for the role to take effect

---

### Section 4: Connect to EC2

#### 4.1 SSH (Primary method)
```bash
ssh -i "path/to/your-key.pem" ec2-user@YOUR_ELASTIC_IP
```

> **Note:** If SSH times out, check your Security Group — the inbound SSH rule source IP must match your current public IP (check at whatismyip.com).

#### 4.2 SSM Session Manager (Backup method — no IP restrictions)
1. Go to **AWS Console → Systems Manager → Session Manager**
2. Click **Start Session** → Select your instance → **Start Session**

---

### Section 5: Deploy on EC2

#### 5.1 Install and Start Docker (if not already installed)
```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
exit  # Re-login for group change
```

#### 5.2 Pull and Run Containers
```bash
# Pull image
docker pull YOUR_DOCKERHUB_USERNAME/smartdesk-copilot:latest

# Run backend
docker run -d \
  --name smartdesk \
  --restart always \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e MODEL_NAME=gpt-4o-mini \
  -e CHROMA_PERSIST_DIR=data/chroma \
  -e TICKET_BACKEND=mock \
  -e APP_ENV=dev \
  YOUR_DOCKERHUB_USERNAME/smartdesk-copilot:latest

# Run frontend
docker run -d \
  --name smartdesk-ui \
  --restart always \
  -p 8501:8501 \
  --link smartdesk \
  YOUR_DOCKERHUB_USERNAME/smartdesk-copilot:latest \
  streamlit run ui/app.py --server.port 8501 --server.address 0.0.0.0
```

#### 5.3 Initialize the Database
```bash
docker exec smartdesk python -c "
from app.db.models import Base
from sqlalchemy import create_engine
engine = create_engine('sqlite:///data/app.db')
Base.metadata.create_all(engine)
print('DB ready')
"
```

#### 5.4 Verify Everything is Running
```bash
docker ps
curl http://localhost:8000/health
```

#### 5.5 Access the App
```
Backend:  http://YOUR_ELASTIC_IP:8000
Frontend: http://YOUR_ELASTIC_IP:8501
```

---

### Section 6: SSM Run Command (Alternative to SSH for running commands)
1. Go to **Systems Manager → Run Command → Run command**
2. Search for **AWS-RunShellScript**
3. Under **Targets** → Select **Choose instances manually** → check your instance
4. Paste your command in the Commands box
5. Click **Run**

---

## PART 2: Issues Encountered & Solutions

---

### Issue 1: SSH Connection Timed Out
**Symptom:** `ssh: connect to host X.X.X.X port 22: Connection timed out`

**Cause:** The Security Group inbound rule for port 22 had a specific IP that didn't match your current public IP.

**Solution:**
1. Go to **EC2 → Security Groups → Edit inbound rules**
2. Find the SSH (port 22) rule
3. Change Source to **My IP** (or `0.0.0.0/0` for development)
4. Save rules and retry SSH

---

### Issue 2: SSH Permission Denied (publickey)
**Symptom:** `ec2-user@X.X.X.X: Permission denied (publickey,gssapi-keyex,gssapi-with-mic)`

**Cause:** The `.pem` key pair was deleted and recreated, but the EC2 instance still had the old public key in `~/.ssh/authorized_keys`.

**Solution:**
1. Connect via **EC2 Instance Connect** or **SSM Session Manager** (browser-based)
2. Get your new public key locally: `ssh-keygen -y -f your-key.pem`
3. Add it to the instance: `echo "NEW_PUBLIC_KEY" >> ~/.ssh/authorized_keys`
4. Fix permissions: `chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys`

---

### Issue 3: EC2 Instance Connect — Access Denied
**Symptom:** "Access denied by EC2 Instance Connect"

**Cause:** IAM user lacked permissions to use EC2 Instance Connect.

**Solution:** Use SSM Session Manager instead (see Issue 4).

---

### Issue 4: SSM Session Manager — No Instances Shown
**Symptom:** Session Manager shows no instances or "instance not configured for AWS Systems Manager"

**Cause:** EC2 instance lacked the required IAM role with SSM permissions.

**Solution:**
1. Create IAM role with `AmazonSSMManagedInstanceCore`, `AmazonEC2RoleforSSM`, `AmazonSSMManagedEC2InstanceDefaultPolicy`
2. Attach role to instance via **Actions → Security → Modify IAM Role**
3. Reboot the instance
4. Wait 2-3 minutes and retry

---

### Issue 5: IP Address Changes After Restart
**Symptom:** SSH works, then after instance restart the IP changes and SSH times out again.

**Cause:** EC2 public IPs are dynamic by default and change on every stop/start.

**Solution:** Assign an **Elastic IP**:
1. EC2 → Elastic IPs → Allocate
2. Associate to your instance
3. Always use the Elastic IP to connect — it never changes

---

### Issue 6: Docker Push — "Insufficient Scope: Authorization Failed"
**Symptom:** `push access denied, repository does not exist or may require authorization: insufficient_scope`

**Cause 1:** Repository didn't exist on Docker Hub yet.
**Solution:** Create the repository manually at hub.docker.com first.

**Cause 2:** Cached Docker credentials had limited scope.
**Solution:**
```bash
docker logout
docker login  # Use password or PAT with Read & Write scope
docker push YOUR_USERNAME/smartdesk-copilot:latest
```

---

### Issue 7: No Space Left on Device
**Symptom:** `failed to register layer: write ...: no space left on device`

**Cause:** Default EC2 instance storage is 8GB, which is insufficient for a Python/ML Docker image (~3GB+).

**Solution:** Increase EBS volume:
1. EC2 → Elastic Block Store → Volumes → Select volume → **Modify Volume**
2. Increase size to **30GB**
3. SSH into instance and extend filesystem:
```bash
sudo growpart /dev/xvda 1
sudo xfs_growfs /
df -h  # Verify new size
```

---

### Issue 8: Container Name Already in Use
**Symptom:** `The container name "/smartdesk" is already in use`

**Cause:** A previous container with the same name exists (even if stopped).

**Solution:**
```bash
docker rm -f smartdesk  # Force remove existing container
docker run ...          # Then re-run
```

---

### Issue 9: Frontend Shows "Backend Error: Connection Refused (127.0.0.1:8000)"
**Symptom:** UI loads but all queries return a backend connection error.

**Cause:** The frontend `ui/app.py` had hardcoded `http://127.0.0.1:8000` instead of pointing to the backend container.

**Solution:**
```bash
# Fix hardcoded URLs inside the running container
docker exec -it smartdesk-ui sed -i \
  's|http://127.0.0.1:8000/chat|http://smartdesk:8000/chat|g; s|http://127.0.0.1:8000/session|http://smartdesk:8000/session|g' \
  ui/app.py
docker restart smartdesk-ui
```

> **Long-term fix:** Update `ui/app.py` to read the URL from an environment variable, rebuild and push the image.

---

### Issue 10: App Responds With "I couldn't generate a response"
**Symptom:** UI loads, intent is detected, but answer is always empty or generic error.

**Cause:** Multiple possible causes investigated in order:
1. Missing database tables (`no such table: decision_logs`)
2. Volume mount overriding the image's built-in `data/` directory
3. OpenAI API key not passed to container

**Solution:**
- Remove the `-v` volume mount so the image uses its own built-in `data/chroma`
- Initialize the database:
```bash
docker exec smartdesk python -c "
from app.db.models import Base
from sqlalchemy import create_engine
engine = create_engine('sqlite:///data/app.db')
Base.metadata.create_all(engine)
print('Done')
"
```
- Ensure `OPENAI_API_KEY` is passed via `-e` flag when running the container

---

### Issue 11: SSM Agent Goes "Undeliverable" / Keeps Dropping
**Symptom:** Run Command fails with "Undeliverable" status; SSM session drops frequently.

**Cause:** t2.micro only has 1GB RAM. Running two Docker containers exhausted memory, causing the SSM agent to crash.

**Solution:** Upgrade instance type:
1. Stop the instance
2. **Actions → Instance Settings → Change Instance Type**
3. Select **t2.medium** (4GB RAM)
4. Start the instance

---

### Issue 12: SCP Transfer Hangs / Times Out
**Symptom:** `scp` command starts but hangs indefinitely even for small files.

**Cause:** Intermittent SSH connectivity issues on t2.micro with high memory usage.

**Solution:** Use S3 as an intermediary:
1. Upload files to S3 via AWS Console
2. Attach `AmazonS3FullAccess` to the EC2 IAM role
3. Download on EC2 via Run Command:
```bash
aws s3 cp s3://your-bucket/chroma /home/ec2-user/data/chroma --recursive
docker cp /home/ec2-user/data/chroma smartdesk:/app/data/chroma
```

---

### Issue 13: Ticket Created But Status Shows "No Tickets Found"
**Symptom:** Ticket creates successfully but checking status returns no results.

**Cause:** Volume mount (`-v`) was overriding `/app/data` with an empty host directory, wiping the SQLite database on container restart.

**Solution:** Remove the volume mount and let the container use its own built-in data directory. Only use volume mounts if you explicitly pre-populate the host directory with the required data files.

---

## Quick Reference: Useful Commands

```bash
# Check running containers
docker ps

# View container logs
docker logs smartdesk 2>&1 | tail -50

# Restart a container
docker restart smartdesk

# Free up disk space
docker system prune -af && docker volume prune -f

# Check disk usage
df -h

# Check memory usage
free -h

# Test backend directly
curl http://localhost:8000/health
```

---

## Architecture Summary

```
Internet
    │
    ▼
Elastic IP (23.21.203.201)
    │
    ├── Port 8501 → smartdesk-ui container (Streamlit)
    │                    │
    │                    └── http://smartdesk:8000 (Docker internal network)
    │
    └── Port 8000 → smartdesk container (FastAPI/Uvicorn)
                         │
                         ├── ChromaDB (data/chroma — baked into image)
                         ├── SQLite (data/app.db)
                         └── OpenAI API (via OPENAI_API_KEY env var)
```
