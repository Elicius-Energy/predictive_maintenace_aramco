#!/usr/bin/env bash
# Elicius PdM — EC2 Initial Setup Script
# Usage: sudo bash scripts/setup_ec2.sh
# Run this ONCE on a fresh Ubuntu 22.04 EC2 instance
set -euo pipefail

echo "=== Elicius PdM EC2 Setup ==="
echo "[1/7] Updating system packages..."
apt update && apt upgrade -y

echo "[2/7] Installing Docker and Git..."
apt install -y docker.io git sqlite3 curl
systemctl enable --now docker

# Install Docker Compose v2 plugin
echo "[3/7] Installing Docker Compose..."
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Add ubuntu user to docker group
usermod -aG docker ubuntu

echo "[4/7] Configuring firewall..."
apt install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (Frontend)
ufw allow 8000/tcp  # FastAPI (direct, for debugging — remove in production)
ufw allow 1883/tcp  # MQTT (only if external devices need access)
ufw --force enable

echo "[5/7] Configuring swap space (2GB)..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    # Optimize swap usage
    sysctl vm.swappiness=10
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
fi

echo "[6/7] Setting up log rotation..."
cat > /etc/logrotate.d/elicius-pdm << 'INNER_EOF'
/home/ubuntu/predictive_maintenace_aramco/backend/data/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    copytruncate
}
INNER_EOF

echo "[7/7] Setting up cron jobs..."
# Backup at 2 AM daily
(crontab -u ubuntu -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/predictive_maintenace_aramco/scripts/backup.sh >> /home/ubuntu/predictive_maintenace_aramco/backend/data/logs/backup.log 2>&1") | crontab -u ubuntu -
# Health check every 5 minutes  
(crontab -u ubuntu -l 2>/dev/null; echo "*/5 * * * * /home/ubuntu/predictive_maintenace_aramco/scripts/health_check.sh") | crontab -u ubuntu -

echo ""
echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. Log out and log back in (for docker group)"
echo "  2. Clone your repo: git clone <repo-url> ~/predictive_maintenace_aramco"
echo "  3. Configure: cp .env.example .env && nano .env"
echo "  4. Deploy: bash scripts/deploy.sh"
echo ""
echo "IMPORTANT: Generate a password hash for production:"
echo "  python3 -c \"from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your_password'))\""
