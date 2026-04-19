#!/usr/bin/env bash
# deploy.sh — Deploy Capital Lens to a Hetzner VPS (Ubuntu 22.04)
# Usage: VPS_IP=1.2.3.4 bash deploy.sh
set -euo pipefail

VPS_IP="${VPS_IP:-YOUR_VPS_IP}"
DEPLOY_DIR="/opt/capital-lens"

echo "=== Capital Lens Deploy → $VPS_IP ==="

# 1. Build frontend
echo "[1/5] Building frontend..."
cd frontend
npm install --legacy-peer-deps
npm run build
cd ..

# 2. Rsync project to VPS
echo "[2/5] Uploading to VPS..."
ssh root@"$VPS_IP" "mkdir -p $DEPLOY_DIR"
rsync -az --exclude node_modules --exclude __pycache__ --exclude "*.pyc" \
  --exclude frontend/node_modules \
  ./ root@"$VPS_IP":"$DEPLOY_DIR"/

# 3. Remote: install deps + configure
echo "[3/5] Installing server deps..."
ssh root@"$VPS_IP" << 'REMOTE'
set -e
cd /opt/capital-lens

# System packages
apt-get install -y python3.11 python3-pip nginx

# Python deps
pip3 install -r requirements.txt

# Copy env if not present
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  Edit /opt/capital-lens/.env with your API keys!"
fi
REMOTE

# 4. Deploy frontend static files
echo "[4/5] Deploying frontend..."
ssh root@"$VPS_IP" << 'REMOTE'
mkdir -p /var/www/capital-lens
cp -r /opt/capital-lens/frontend/dist/* /var/www/capital-lens/
cp /opt/capital-lens/nginx.conf /etc/nginx/sites-available/capital-lens
ln -sf /etc/nginx/sites-available/capital-lens /etc/nginx/sites-enabled/capital-lens
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
REMOTE

# 5. Start/restart FastAPI with systemd
echo "[5/5] Starting backend service..."
ssh root@"$VPS_IP" << 'REMOTE'
cat > /etc/systemd/system/capital-lens.service << 'SERVICE'
[Unit]
Description=Capital Lens FastAPI
After=network.target

[Service]
WorkingDirectory=/opt/capital-lens
EnvironmentFile=/opt/capital-lens/.env
ExecStart=/usr/local/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable capital-lens
systemctl restart capital-lens
sleep 2
systemctl status capital-lens --no-pager
REMOTE

echo ""
echo "✅ Capital Lens deployed!"
echo "   Open: http://$VPS_IP"
echo "   API:  http://$VPS_IP/health"
echo "   Docs: http://$VPS_IP/docs"
