# AWS EC2 Production Deployment Guide

This guide covers deploying the Elicius Predictive Maintenance Dashboards to an AWS EC2 instance from start to finish. Since your application already includes a `docker-compose.yml`, deploying this application inside isolated Docker containers is the most robust, cleanest, and scalable approach.

> [!CAUTION] 
> Because this application runs a Local LLM embedding model and Python memory structures for RAG processing, **do not use a minimum spec instance (like t2.micro)**. Your instance will run completely out of memory and the API will randomly crash. I recommend at least a **t3.medium** (2 cores, 4GB RAM).

---

## Phase 1: Provisioning the EC2 Instance

1. Log into your AWS Console and navigate to **EC2 > Launch Instances**.
2. **Name**: `Elicius-PdM-Prod`
3. **AMI**: Ubuntu Server 22.04 LTS (HVM), SSD Volume Type.
4. **Instance Type**: Select `t3.medium`.
5. **Key Pair**: Select your existing key pair or create a new one (download the `.pem` file).
6. **Network Settings (Security Groups)**:
   Create a new Security Group and expose the following inbound traffic rules to `0.0.0.0/0` (Anywhere):
   - **Port 22 (SSH)**: For terminal access.
   - **Port 80 (HTTP)**: For your frontend React application.
   - **Port 8000 (Custom TCP)**: For FastAPI and WebSocket traffic.
   - **Port 1883 (Custom TCP)**: *[Optional]* Only if external physical PLC sensors need direct external access to your Mosquitto broker.
7. **Storage**: Allocate at least **15 GB gp3** storage. 
8. Launch the Instance and note down its **Public IPv4 address**.

---

## Phase 2: Server Architecture Setup

SSH into your newly provisioned Ubuntu instance:
```bash
ssh -i /path/to/your-key.pem ubuntu@<YOUR_EC2_PUBLIC_IP>
```

Install Docker, Docker Compose, and Git:
```bash
# Update package registries
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install docker.io docker-compose git -y

# Enable Docker to run on boot and give your user permissions
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu

# Apply permission group (You may need to logout and log back in, or run this)
newgrp docker
```

---

## Phase 3: Cloning and Configuration

Clone your application payload to the server:
```bash
git clone https://github.com/your-username/predictive_maintenace_aramco.git
cd predictive_maintenace_aramco
```

### 1. The Secrets Environment (Backend)
Create the root `.env` file for the docker-compose orchestrator to pass to your backend container. Here you configure the Anthropic variables and database.

```bash
nano .env
```
Add the following details:
```ini
# .env 
ANTHROPIC_API_KEY="sk-ant-xxxxxxxxxxxxxxxxxx"
DATABASE_PATH="/app/data/sensor_db.sqlite"
DATA_RETENTION_HOURS=720
```
> [!NOTE] 
> Because of your docker volume block (`./backend/data:/app/data`), the database will be securely persisted on the host EC2 hard drive even if you destroy and rebuild your containers later.

### 2. The Frontend Environment
This step is **critical**. Your React/Vite frontend compiles statically. If you build the image without updating the backend URLs to your EC2 public IP, the frontend will attempt to connect to `localhost:8000` on the end-user's local computer instead of the AWS server.

```bash
nano frontend/.env.production
```
Add exactly this (replace `<YOUR_EC2_PUBLIC_IP>` with real IP):
```ini
VITE_BACKEND_URL=http://<YOUR_EC2_PUBLIC_IP>:8000
VITE_WS_URL=ws://<YOUR_EC2_PUBLIC_IP>:8000/ws/stream
```

### 3. Exposing the Network
By default, your `docker-compose.yml` likely maps the frontend port to port `5173`. For a real deployment without a reverse proxy, we need it to serve directly on port 80.

```bash
nano docker-compose.yml
```
Locate the `frontend` service block, and change the port mapping from `"5173:80"` to `"80:80"`.
```yaml
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"       # Changed from 5173:80
    depends_on:
      - backend
    restart: always
```

---

## Phase 4: Launching Production

It's time to build the container clusters and deploy them in detached mode. This takes a few minutes as it downloads PyTorch, installs NPM dependencies, and bundles the assets.

```bash
docker-compose up --build -d
```

Confirm all three containers are healthy:
```bash
docker ps
```
You should see `backend`, `frontend`, and `mqtt-broker` all listed as "Up".

---

## Phase 5: End-to-End Validation

Open a browser anywhere in the world and type in `http://<YOUR_EC2_PUBLIC_IP>`.

1. **Login Validation**: Type `admin` / `admin`. Ensure it redirects to the interface properly. It should drop to the Asset Selector page. Reloading the page drops you back to `/login` (driven by the recent session architecture).
2. **Real-time WebSockets**: Go to the Mechanical Parameters page. The graphs should immediately begin drawing dynamically sourced data, confirming that Uvicorn WebSockets function through Port 8000 on EC2.
3. **Database Write/Read**: If graphs display historic data instead of blank states, your SQLite DB is successfully mapped to the active volume.
4. **CSV Downloads**: Verify the `Download CSV` button triggers the newly-fixed `StreamingResponse` database engine, and the chunked file generates correctly.
5. **Agentic RAG Validation**: Go to the AI Analysis page. Type a question. Ensure Claude responds accurately regarding asset anomalies, validating that HTTP outbound requests to Anthropic from the docker container succeed.

> [!TIP]
> If you make changes locally and push to Github later on, the deployment loop on the EC2 becomes extremely simple:
> `git pull` -> `docker-compose up --build -d`
