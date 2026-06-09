# Docker Deployment Guide

## Prerequisites

Before starting, make sure the following are available:

**Docker** is installed and running
**A valid `.env` file** is created with all required secrets
* The project contains:
  * `Dockerfile`
  * `requirements.txt`
  * application source code

If running on **Windows**, make sure:

* Docker Desktop is installed
* WSL2 is enabled and updated
* Docker Desktop is running before executing Docker commands

## 1. Create the `.env` file

Create a `.env` file in the project root.

Example:

```env
OPENAI_API_KEY=your_openai_api_key
MODEL_NAME=gpt-4o-mini
TICKET_BACKEND=db
```

Add any additional environment variables your app requires.

***

## 2. Build the Docker image

From the project root, run:

```bash
docker build -t smarthelpdesk-copilot .
```

This command:

* Reads the `Dockerfile`
* Installs dependencies from `requirements.txt`
* Packages the app into a Docker image named `smarthelpdesk-copilot`

***

## 3. Run the Docker container

Start the application container with:

```bash
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

### What this does

* `-d` runs the container in detached mode
* `-p 8000:8000` maps container port `8000` to local machine port `8000`
* `--env-file .env` loads environment variables
* `--name smarthelpdesk` assigns a friendly container name

***

## 4. Verify the container is running

Run:

```bash
docker ps
```

You should see a running container similar to:

```bash
CONTAINER ID   IMAGE                PORTS                    NAMES
abcd1234       smarthelpdesk-copilot    0.0.0.0:8000->8000/tcp   smarthelpdesk
```

***

## 5. Access the application

Once the container is running, open:

### FastAPI Swagger UI

```text
http://localhost:8000/docs
```

### Health endpoint

```text
http://localhost:8000/health
```

### Streamlit UI (if running separately)

If the Streamlit UI is not inside the same Docker container, run it separately:

```bash
streamlit run ui/app.py --server.port 8501
```

Then open:

```text
http://localhost:8501
```

### Admin Dashboard (optional)

If using a separate admin dashboard:

```bash
streamlit run ui/admin_dashboard.py --server.port 8502
```

Then open:

```text
http://localhost:8502
```

***

## Useful Docker Commands

### View running containers

```bash
docker ps
```

### View logs

```bash
docker logs smarthelpdesk
```

### View live logs

```bash
docker logs -f smarthelpdesk
```

### Stop the container

```bash
docker stop smarthelpdesk
```

### Start the container again

```bash
docker start smarthelpdesk
```

### Remove the container

```bash
docker rm -f smarthelpdesk
```

### Rebuild and rerun after code changes

```bash
docker rm -f smarthelpdesk
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

## Docker Deployment Flow for AWS EC2

If deploying on AWS EC2, follow these additional steps.

***

### 1. Connect to the EC2 instance

```bash
ssh -i "your-key.pem" ec2-user@<your-ec2-public-dns>
```

For Amazon Linux 2023, the username is usually:

```bash
ec2-user
```

***

### 2. Install Docker on EC2

```bash
sudo dnf update -y
sudo dnf install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

Log out and log back in so the Docker group permissions apply.

Verify Docker:

```bash
docker version
```

***

### 3. Clone the repository

```bash
git clone <your-github-repo-url>
cd <your-project-folder>
```

***

### 4. Create the `.env` file on EC2

```bash
nano .env
```

Paste the required environment variables, save, and exit.

***

### 5. Build the Docker image on EC2

```bash
docker build -t smarthelpdesk-copilot .
```

***

### 6. Run the container on EC2

```bash
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

### 7. Open the EC2 Security Group

Allow inbound traffic on:

* **Port 22** → SSH
* **Port 8000** → FastAPI app

If the Streamlit UI is hosted directly on EC2, also allow:

* **Port 8501** → User UI
* **Port 8502** → Admin Dashboard (optional/internal only)

***

### 8. Access the deployed application

Use the EC2 public IP or DNS:

```text
http://<EC2-PUBLIC-IP>:8000/docs
```

Example:

```text
http://54.123.45.67:8000/docs
```

***

## Common Issues and Fixes

### 1. Docker command not found

Docker is not installed or Docker Desktop is not running.

**Fix**

* Install Docker / Docker Desktop
* Start Docker Desktop
* Reopen terminal

***

### 2. `Error loading ASGI app`

The FastAPI module path in the `Dockerfile` is incorrect.

**Fix**
Make sure the `CMD` points to the correct app location.

Example:

```dockerfile
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

***

### 3. `No space left on device`

Common on small EC2 instances during Docker build.

**Fix**

* Increase the EC2 root volume size
* Clean Docker cache:

```bash
docker system prune -a -f
docker builder prune -a -f
```

***

### 4. Application starts but browser does not open

Do not use:

```text
http://0.0.0.0:8000
```

Use:

```text
http://localhost:8000
```

or, on EC2:

```text
http://<public-ip>:8000
```

***

### 5. Container is running but app is unreachable on EC2

Likely a security group issue.

**Fix**
Allow inbound traffic on port `8000`.

***

### 6. Changes are not reflected after editing code

Docker is still running an old image.

**Fix**
Rebuild and restart:

```bash
docker rm -f smarthelpdesk
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

## Recommended Production Improvements

For a more production-ready deployment, consider:

* Using **Nginx** as a reverse proxy
* Adding **HTTPS**
* Running containers with:

```bash
docker run -d -p 8000:8000 --env-file .env --restart unless-stopped --name smarthelpdesk smarthelpdesk-copilot
```

* Hosting the admin dashboard on a **different internal-only port**
* Using **Docker Compose** if running:
  * FastAPI backend
  * Streamlit user app
  * Streamlit admin dashboard

***

## Example Quick Start

### Local

```bash
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

Open:

```text
http://localhost:8000/docs
```

### EC2

```bash
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

Open:

```text
http://<EC2-PUBLIC-IP>:8000/docs
```

***

If you want, I can next turn this into a **more polished README section with headings, badges, and copy-paste commands exactly in GitHub markdown style**, or also add a **Docker Compose section** for:

* backend
* user UI
* admin dashboard
* **Docker** is installed and running
# * **A valid `.env` file** is created with all required secrets
# * The project contains:
#   * `Dockerfile`
#   * `requirements.txt`
#   * application source code

# If running on **Windows**, make sure:

# * Docker Desktop is installed
# * WSL2 is enabled and updated
# * Docker Desktop is running before executing Docker commands

# ***Absolutely — here’s a clean, README-ready section you can paste directly into your project.

***

# Docker Deployment Guide

This section explains how to run **SmartHelpDesk Copilot** using Docker, both **locally** and on an **AWS EC2 instance**.

## Prerequisites

Before starting, make sure the following are available:

* **Docker** is installed and running
* **A valid `.env` file** is created with all required secrets
* The project contains:
  * `Dockerfile`
  * `requirements.txt`
  * application source code

If running on **Windows**, make sure:

* Docker Desktop is installed
* WSL2 is enabled and updated
* Docker Desktop is running before executing Docker commands

***

## 1. Create the `.env` file

Create a `.env` file in the project root.

Example:

```env
OPENAI_API_KEY=your_openai_api_key
MODEL_NAME=gpt-4o-mini
TICKET_BACKEND=db
```

Add any additional environment variables your app requires.

***

## 2. Build the Docker image

From the project root, run:

```bash
docker build -t smarthelpdesk-copilot .
```

This command:

* Reads the `Dockerfile`
* Installs dependencies from `requirements.txt`
* Packages the app into a Docker image named `smarthelpdesk-copilot`

***

## 3. Run the Docker container

Start the application container with:

```bash
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

### What this does

* `-d` runs the container in detached mode
* `-p 8000:8000` maps container port `8000` to local machine port `8000`
* `--env-file .env` loads environment variables
* `--name smarthelpdesk` assigns a friendly container name

***

## 4. Verify the container is running

Run:

```bash
docker ps
```

You should see a running container similar to:

```bash
CONTAINER ID   IMAGE                PORTS                    NAMES
abcd1234       smarthelpdesk-copilot    0.0.0.0:8000->8000/tcp   smarthelpdesk
```

***

## 5. Access the application

Once the container is running, open:

### FastAPI Swagger UI

```text
http://localhost:8000/docs
```

### Health endpoint

```text
http://localhost:8000/health
```

### Streamlit UI (if running separately)

If the Streamlit UI is not inside the same Docker container, run it separately:

```bash
streamlit run ui/app.py --server.port 8501
```

Then open:

```text
http://localhost:8501
```

### Admin Dashboard (optional)

If using a separate admin dashboard:

```bash
streamlit run ui/admin_dashboard.py --server.port 8502
```

Then open:

```text
http://localhost:8502
```

***

## Useful Docker Commands

### View running containers

```bash
docker ps
```

### View logs

```bash
docker logs smarthelpdesk
```

### View live logs

```bash
docker logs -f smarthelpdesk
```

### Stop the container

```bash
docker stop smarthelpdesk
```

### Start the container again

```bash
docker start smarthelpdesk
```

### Remove the container

```bash
docker rm -f smarthelpdesk
```

### Rebuild and rerun after code changes

```bash
docker rm -f smarthelpdesk
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

## Docker Deployment Flow for AWS EC2

If deploying on AWS EC2, follow these additional steps.

***

### 1. Connect to the EC2 instance

```bash
ssh -i "your-key.pem" ec2-user@<your-ec2-public-dns>
```

For Amazon Linux 2023, the username is usually:

```bash
ec2-user
```

***

### 2. Install Docker on EC2

```bash
sudo dnf update -y
sudo dnf install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

Log out and log back in so the Docker group permissions apply.

Verify Docker:

```bash
docker version
```

***

### 3. Clone the repository

```bash
git clone <your-github-repo-url>
cd <your-project-folder>
```

***

### 4. Create the `.env` file on EC2

```bash
nano .env
```

Paste the required environment variables, save, and exit.

***

### 5. Build the Docker image on EC2

```bash
docker build -t smarthelpdesk-copilot .
```

***

### 6. Run the container on EC2

```bash
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

### 7. Open the EC2 Security Group

Allow inbound traffic on:

* **Port 22** → SSH
* **Port 8000** → FastAPI app

If the Streamlit UI is hosted directly on EC2, also allow:

* **Port 8501** → User UI
* **Port 8502** → Admin Dashboard (optional/internal only)

***

### 8. Access the deployed application

Use the EC2 public IP or DNS:

```text
http://<EC2-PUBLIC-IP>:8000/docs
```

Example:

```text
http://54.123.45.67:8000/docs
```

***

## Common Issues and Fixes

### 1. Docker command not found

Docker is not installed or Docker Desktop is not running.

**Fix**

* Install Docker / Docker Desktop
* Start Docker Desktop
* Reopen terminal

***

### 2. `Error loading ASGI app`

The FastAPI module path in the `Dockerfile` is incorrect.

**Fix**
Make sure the `CMD` points to the correct app location.

Example:

```dockerfile
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

***

### 3. `No space left on device`

Common on small EC2 instances during Docker build.

**Fix**

* Increase the EC2 root volume size
* Clean Docker cache:

```bash
docker system prune -a -f
docker builder prune -a -f
```

***

### 4. Application starts but browser does not open

Do not use:

```text
http://0.0.0.0:8000
```

Use:

```text
http://localhost:8000
```

or, on EC2:

```text
http://<public-ip>:8000
```

***

### 5. Container is running but app is unreachable on EC2

Likely a security group issue.

**Fix**
Allow inbound traffic on port `8000`.

***

### 6. Changes are not reflected after editing code

Docker is still running an old image.

**Fix**
Rebuild and restart:

```bash
docker rm -f smarthelpdesk
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

## Recommended Production Improvements

For a more production-ready deployment, consider:

* Using **Nginx** as a reverse proxy
* Adding **HTTPS**
* Running containers with:

```bash
docker run -d -p 8000:8000 --env-file .env --restart unless-stopped --name smarthelpdesk smarthelpdesk-copilot
```

* Hosting the admin dashboard on a **different internal-only port**
* Using **Docker Compose** if running:
  * FastAPI backend
  * Streamlit user app
  * Streamlit admin dashboard

***

## Example Quick Start

### Local

```bash
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

Open:

```text
http://localhost:8000/docs
```

### EC2

```bash
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

Open:

```text
http://<EC2-PUBLIC-IP>:8000/docs
```

***Absolutely — here’s a clean, README-ready section you can paste directly into your project.

***

# Docker Deployment Guide

This section explains how to run **SmartHelpDesk Copilot** using Docker, both **locally** and on an **AWS EC2 instance**.

## Prerequisites

Before starting, make sure the following are available:

* **Docker** is installed and running
* **A valid `.env` file** is created with all required secrets
* The project contains:
  * `Dockerfile`
  * `requirements.txt`
  * application source code

If running on **Windows**, make sure:

* Docker Desktop is installed
* WSL2 is enabled and updated
* Docker Desktop is running before executing Docker commands

***

## 1. Create the `.env` file

Create a `.env` file in the project root.

Example:

```env
OPENAI_API_KEY=your_openai_api_key
MODEL_NAME=gpt-4o-mini
TICKET_BACKEND=db
```

Add any additional environment variables your app requires.

***

## 2. Build the Docker image

From the project root, run:

```bash
docker build -t smarthelpdesk-copilot .
```

This command:

* Reads the `Dockerfile`
* Installs dependencies from `requirements.txt`
* Packages the app into a Docker image named `smarthelpdesk-copilot`

***

## 3. Run the Docker container

Start the application container with:

```bash
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

### What this does

* `-d` runs the container in detached mode
* `-p 8000:8000` maps container port `8000` to local machine port `8000`
* `--env-file .env` loads environment variables
* `--name smarthelpdesk` assigns a friendly container name

***

## 4. Verify the container is running

Run:

```bash
docker ps
```

You should see a running container similar to:

```bash
CONTAINER ID   IMAGE                PORTS                    NAMES
abcd1234       smarthelpdesk-copilot    0.0.0.0:8000->8000/tcp   smarthelpdesk
```

***

## 5. Access the application

Once the container is running, open:

### FastAPI Swagger UI

```text
http://localhost:8000/docs
```

### Health endpoint

```text
http://localhost:8000/health
```

### Streamlit UI (if running separately)

If the Streamlit UI is not inside the same Docker container, run it separately:

```bash
streamlit run ui/app.py --server.port 8501
```

Then open:

```text
http://localhost:8501
```

### Admin Dashboard (optional)

If using a separate admin dashboard:

```bash
streamlit run ui/admin_dashboard.py --server.port 8502
```

Then open:

```text
http://localhost:8502
```

***

## Useful Docker Commands

### View running containers

```bash
docker ps
```

### View logs

```bash
docker logs smarthelpdesk
```

### View live logs

```bash
docker logs -f smarthelpdesk
```

### Stop the container

```bash
docker stop smarthelpdesk
```

### Start the container again

```bash
docker start smarthelpdesk
```

### Remove the container

```bash
docker rm -f smarthelpdesk
```

### Rebuild and rerun after code changes

```bash
docker rm -f smarthelpdesk
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

## Docker Deployment Flow for AWS EC2

If deploying on AWS EC2, follow these additional steps.

***

### 1. Connect to the EC2 instance

```bash
ssh -i "your-key.pem" ec2-user@<your-ec2-public-dns>
```

For Amazon Linux 2023, the username is usually:

```bash
ec2-user
```

***

### 2. Install Docker on EC2

```bash
sudo dnf update -y
sudo dnf install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

Log out and log back in so the Docker group permissions apply.

Verify Docker:

```bash
docker version
```

***

### 3. Clone the repository

```bash
git clone <your-github-repo-url>
cd <your-project-folder>
```

***

### 4. Create the `.env` file on EC2

```bash
nano .env
```

Paste the required environment variables, save, and exit.

***

### 5. Build the Docker image on EC2

```bash
docker build -t smarthelpdesk-copilot .
```

***

### 6. Run the container on EC2

```bash
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

### 7. Open the EC2 Security Group

Allow inbound traffic on:

* **Port 22** → SSH
* **Port 8000** → FastAPI app

If the Streamlit UI is hosted directly on EC2, also allow:

* **Port 8501** → User UI
* **Port 8502** → Admin Dashboard (optional/internal only)

***

### 8. Access the deployed application

Use the EC2 public IP or DNS:

```text
http://<EC2-PUBLIC-IP>:8000/docs
```

Example:

```text
http://54.123.45.67:8000/docs
```

***

## Common Issues and Fixes

### 1. Docker command not found

Docker is not installed or Docker Desktop is not running.

**Fix**

* Install Docker / Docker Desktop
* Start Docker Desktop
* Reopen terminal

***

### 2. `Error loading ASGI app`

The FastAPI module path in the `Dockerfile` is incorrect.

**Fix**
Make sure the `CMD` points to the correct app location.

Example:

```dockerfile
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

***

### 3. `No space left on device`

Common on small EC2 instances during Docker build.

**Fix**

* Increase the EC2 root volume size
* Clean Docker cache:

```bash
docker system prune -a -f
docker builder prune -a -f
```

***

### 4. Application starts but browser does not open

Do not use:

```text
http://0.0.0.0:8000
```

Use:

```text
http://localhost:8000
```

or, on EC2:

```text
http://<public-ip>:8000
```

***

### 5. Container is running but app is unreachable on EC2

Likely a security group issue.

**Fix**
Allow inbound traffic on port `8000`.

***

### 6. Changes are not reflected after editing code

Docker is still running an old image.

**Fix**
Rebuild and restart:

```bash
docker rm -f smarthelpdesk
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

## Recommended Production Improvements

For a more production-ready deployment, consider:

* Using **Nginx** as a reverse proxy
* Adding **HTTPS**
* Running containers with:

```bash
docker run -d -p 8000:8000 --env-file .env --restart unless-stopped --name smarthelpdesk smarthelpdesk-copilot
```

* Hosting the admin dashboard on a **different internal-only port**
* Using **Docker Compose** if running:
  * FastAPI backend
  * Streamlit user app
  * Streamlit admin dashboard

***

## Example Quick Start

### Local

```bash
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

Open:

```text
http://localhost:8000/docs
```

### EC2

```bash
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

Open:

```text
http://<EC2-PUBLIC-IP>:8000/docs
```

***


## 1. Create the `.env` file

Create a `.env` file in the project root.

Example:

```env
OPENAI_API_KEY=your_openai_api_key
MODEL_NAME=gpt-4o-mini
TICKET_BACKEND=db
```

Add any additional environment variables your app requires.

***

## 2. Build the Docker image

From the project root, run:

```bash
docker build -t smarthelpdesk-copilot .
```

This command:

* Reads the `Dockerfile`
* Installs dependencies from `requirements.txt`
* Packages the app into a Docker image named `smarthelpdesk-copilot`

***

## 3. Run the Docker container

Start the application container with:

```bash
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

### What this does

* `-d` runs the container in detached mode
* `-p 8000:8000` maps container port `8000` to local machine port `8000`
* `--env-file .env` loads environment variables
* `--name smarthelpdesk` assigns a friendly container name

***

## 4. Verify the container is running

Run:

```bash
docker ps
```

You should see a running container similar to:

```bash
CONTAINER ID   IMAGE                PORTS                    NAMES
abcd1234       smarthelpdesk-copilot    0.0.0.0:8000->8000/tcp   smarthelpdesk
```

***

## 5. Access the application

Once the container is running, open:

### FastAPI Swagger UI

```text
http://localhost:8000/docs
```

### Health endpoint

```text
http://localhost:8000/health
```

### Streamlit UI (if running separately)

If the Streamlit UI is not inside the same Docker container, run it separately:

```bash
streamlit run ui/app.py --server.port 8501
```

Then open:

```text
http://localhost:8501
```

### Admin Dashboard (optional)

If using a separate admin dashboard:

```bash
streamlit run ui/admin_dashboard.py --server.port 8502
```

Then open:

```text
http://localhost:8502
```

***

## Useful Docker Commands

### View running containers

```bash
docker ps
```

### View logs

```bash
docker logs smarthelpdesk
```

### View live logs

```bash
docker logs -f smarthelpdesk
```

### Stop the container

```bash
docker stop smarthelpdesk
```

### Start the container again

```bash
docker start smarthelpdesk
```

### Remove the container

```bash
docker rm -f smarthelpdesk
```

### Rebuild and rerun after code changes

```bash
docker rm -f smarthelpdesk
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

## Docker Deployment Flow for AWS EC2

If deploying on AWS EC2, follow these additional steps.

***

### 1. Connect to the EC2 instance

```bash
ssh -i "your-key.pem" ec2-user@<your-ec2-public-dns>
```

For Amazon Linux 2023, the username is usually:

```bash
ec2-user
```

***

### 2. Install Docker on EC2

```bash
sudo dnf update -y
sudo dnf install docker -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

Log out and log back in so the Docker group permissions apply.

Verify Docker:

```bash
docker version
```

***

### 3. Clone the repository

```bash
git clone <your-github-repo-url>
cd <your-project-folder>
```

***

### 4. Create the `.env` file on EC2

```bash
nano .env
```

Paste the required environment variables, save, and exit.

***

### 5. Build the Docker image on EC2

```bash
docker build -t smarthelpdesk-copilot .
```

***

### 6. Run the container on EC2

```bash
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

### 7. Open the EC2 Security Group

Allow inbound traffic on:

* **Port 22** → SSH
* **Port 8000** → FastAPI app

If the Streamlit UI is hosted directly on EC2, also allow:

* **Port 8501** → User UI
* **Port 8502** → Admin Dashboard (optional/internal only)

***

### 8. Access the deployed application

Use the EC2 public IP or DNS:

```text
http://<EC2-PUBLIC-IP>:8000/docs
```

Example:

```text
http://54.123.45.67:8000/docs
```

***

## Common Issues and Fixes

### 1. Docker command not found

Docker is not installed or Docker Desktop is not running.

**Fix**

* Install Docker / Docker Desktop
* Start Docker Desktop
* Reopen terminal

***

### 2. `Error loading ASGI app`

The FastAPI module path in the `Dockerfile` is incorrect.

**Fix**
Make sure the `CMD` points to the correct app location.

Example:

```dockerfile
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

***

### 3. `No space left on device`

Common on small EC2 instances during Docker build.

**Fix**

* Increase the EC2 root volume size
* Clean Docker cache:

```bash
docker system prune -a -f
docker builder prune -a -f
```

***

### 4. Application starts but browser does not open

Do not use:

```text
http://0.0.0.0:8000
```

Use:

```text
http://localhost:8000
```

or, on EC2:

```text
http://<public-ip>:8000
```

***

### 5. Container is running but app is unreachable on EC2

Likely a security group issue.

**Fix**
Allow inbound traffic on port `8000`.

***

### 6. Changes are not reflected after editing code

Docker is still running an old image.

**Fix**
Rebuild and restart:

```bash
docker rm -f smarthelpdesk
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

***

## Recommended Production Improvements

For a more production-ready deployment, consider:

* Using **Nginx** as a reverse proxy
* Adding **HTTPS**
* Running containers with:

```bash
docker run -d -p 8000:8000 --env-file .env --restart unless-stopped --name smarthelpdesk smarthelpdesk-copilot
```

* Hosting the admin dashboard on a **different internal-only port**
* Using **Docker Compose** if running:
  * FastAPI backend
  * Streamlit user app
  * Streamlit admin dashboard

***

## Example Quick Start

### Local

```bash
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

Open:

```text
http://localhost:8000/docs
```

### EC2

```bash
docker build -t smarthelpdesk-copilot .
docker run -d -p 8000:8000 --env-file .env --name smarthelpdesk smarthelpdesk-copilot
```

Open:

```text
http://<EC2-PUBLIC-IP>:8000/docs
```

