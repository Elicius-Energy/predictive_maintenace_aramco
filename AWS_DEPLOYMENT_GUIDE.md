# AWS EC2 Production Deployment Guide

This guide covers deploying the Elicius Predictive Maintenance Dashboards to an AWS EC2 instance from start to finish. The application runs inside isolated, resource-limited Docker containers for robust production deployment.

> [!CAUTION] 
> Because this application runs a Local LLM embedding model (Sentence Transformers) and Python memory structures for RAG processing, **do not use a minimum spec instance (like t2.micro)**. Your instance will run completely out of memory and the API will randomly crash. We recommend at least a **t3.medium** (2 cores, 4GB RAM) or ideally a **t3.large**.

---

## Phase 1: Provisioning the EC2 Instance

1. Log into your AWS Console and navigate to **EC2 > Launch Instances**.
2. **Name**: `Elicius-PdM-Prod`
3. **AMI**: Ubuntu Server 22.04 LTS (HVM), SSD Volume Type.
4. **Instance Type**: Select `t3.medium` or `t3.large`.
5. **Key Pair**: Select your existing key pair or create a new one (download the `.pem` file).
6. **Network Settings (Security Groups)**:
   Create a new Security Group and expose the following inbound traffic rules to `0.0.0.0/0` (Anywhere):
   - **Port 22 (SSH)**: For terminal access.
   - **Port 80 (HTTP)**: For your frontend React application.
   - **Port 443 (HTTPS)**: For secure frontend access (if using SSL).
   - **Port 1883 (Custom TCP)**: *[Optional]* Only if external physical PLC sensors need direct external access to your Mosquitto broker.
   *(Note: Port 8000 is intentionally NOT exposed to the internet. The Nginx reverse proxy handles all external traffic.)*
7. **Storage**: Allocate at least **30 GB** (gp3 is recommended). The Docker images and local FAISS models take up ~4-5GB total.

---

## Phase 2: Initial Server Setup

SSH into your new instance:
```bash
ssh -i "your-key.pem" ubuntu@<YOUR_EC2_PUBLIC_IP>
```

Clone the repository and run the automated EC2 setup script. This script installs Docker, configures the firewall, sets up swap space (to prevent memory crashes), configures log rotation, and sets up automated cron jobs for backups and health checks.

```bash
git clone <your-repo-url> predictive_maintenace_aramco
cd predictive_maintenace_aramco
sudo bash scripts/setup_ec2.sh
```

**IMPORTANT**: After the script finishes, **log out and log back in** so the Docker group permissions take effect.

---

## Phase 3: Configuration & Secrets

The environment file contains critical production secrets.

1. Copy the example configuration:
```bash
cp .env.example .env
```

2. Edit `.env` with `nano .env`:
   - Set `OPENAI_API_KEY` to your valid OpenAI API key.
   - Set `JWT_SECRET_KEY` to a secure random string. (You can generate one using `openssl rand -hex 32`).
   - Generate a bcrypt hash for your admin password and set it as `ADMIN_PASSWORD_HASH`.
     *To generate a hash, run:* `python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your_secure_password_here'))"`
   - Update `VITE_BACKEND_URL` and `VITE_WS_URL` to point to your EC2 public IP or domain name (e.g., `http://<IP_ADDRESS>` without the 8000 port, since Nginx proxies it).

---

## Phase 4: Launching Production

Use the automated deployment script to build and launch the container cluster. This script also performs pre-flight checks and backs up the database if one already exists.

```bash
bash scripts/deploy.sh
```

The script will build the containers, start them in detached mode, and poll until the health checks pass.

Confirm all containers are healthy manually if needed:
```bash
docker compose ps
```
You should see `backend`, `frontend`, and `mqtt-broker` all listed as "Up (healthy)".

---

## Phase 5: Monitoring & Maintenance

### Health Checks
The system runs a cron job every 5 minutes (`scripts/health_check.sh`) to monitor API responsiveness, frontend availability, disk space, memory usage, container status, and database size. 
Check the logs at: `backend/data/logs/health_check.log`

### Automated Backups
The database is backed up daily at 2:00 AM using `scripts/backup.sh`. Backups are compressed and retained for 7 days in the `backups/` directory.

### Checking Application Logs
Docker logs are configured with rotation (max 10MB per file, 5 files).
```bash
# View backend logs
docker compose logs -f backend

# View Nginx access/error logs
docker compose logs -f frontend
```

### Updating the Application
To deploy a new version of the code:
```bash
bash scripts/deploy.sh
```
This automatically pulls the latest code, backs up the database, rebuilds modified containers, and restarts the services.

---

## Troubleshooting Common Issues

**API is unreachable (Network Error)**
- Ensure your `.env` file has the correct `VITE_BACKEND_URL`. Because Nginx is handling the routing on port 80, the backend URL should just be the domain/IP without port 8000 (e.g., `http://123.45.67.89/api`).
- Check if the backend container is healthy: `docker compose ps`
- Check backend logs: `docker compose logs backend`

**Containers randomly crash (OOMKilled)**
- The FAISS model and Sentence Transformers require significant memory.
- Ensure you ran `scripts/setup_ec2.sh` which provisions a 2GB swap file.
- Verify your instance is at least a `t3.medium`.

**Login Always Fails**
- Ensure you have correctly hashed the password using `bcrypt` and placed it in `ADMIN_PASSWORD_HASH`.
- Do not put raw passwords in the `.env` file.

**Database Lock Errors**
- The database uses WAL (Write-Ahead Logging) mode, which handles concurrency well, but heavy synchronous operations can still cause timeouts.
- Ensure the `busy_timeout` is properly set in the application code.
