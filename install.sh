#!/bin/bash

# AgentDVR + MQTT + Telegram Bot Installation Script
# Author: Panacea Tech
# Description: Installs a complete Agent DVR system with Cloudflare Tunnel, Nginx, MQTT and Telegram notifications

# Exit on any error
set -e

# Text colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}    Panacea Tech - Agent DVR Installation       ${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Please run as root or with sudo${NC}"
  exit 1
fi

# Get username for services
echo -e "${BLUE}Enter the username for services (default: pi):${NC}"
read -r USERNAME
USERNAME=${USERNAME:-pi}

# Get domain for Cloudflare Tunnel
echo -e "${BLUE}Enter your Cloudflare domain (e.g., yourdomain.panacea-tech.net):${NC}"
read -r DOMAIN

# Create storage directory
STORAGE_DIR="/home/$USERNAME/agent-dvr-setup"
echo -e "${YELLOW}Creating storage directory at $STORAGE_DIR...${NC}"
mkdir -p "$STORAGE_DIR"
mkdir -p "$STORAGE_DIR/agentdvr/config"
mkdir -p "$STORAGE_DIR/agentdvr/media"

# Create Panacea Tech directory for Docker setup
PANACEA_DIR="/home/$USERNAME/panacea-tech"
echo -e "${YELLOW}Creating Panacea Tech directory at $PANACEA_DIR...${NC}"
mkdir -p "$PANACEA_DIR"
mkdir -p "$PANACEA_DIR/mqtt"
mkdir -p "$PANACEA_DIR/telegram"

# Update package lists
echo -e "${YELLOW}Updating package lists...${NC}"
apt update

# Install dependencies
echo -e "${YELLOW}Installing required packages...${NC}"
apt install -y docker.io docker-compose nginx curl gnupg2 lsb-release

# Add user to docker group
echo -e "${YELLOW}Adding user to docker group...${NC}"
usermod -aG docker "$USERNAME"

# Enable docker service
echo -e "${YELLOW}Enabling Docker service...${NC}"
systemctl enable docker
systemctl start docker

# Install Cloudflared
echo -e "${YELLOW}Installing Cloudflared...${NC}"
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
dpkg -i cloudflared.deb
rm cloudflared.deb

# Create Cloudflared directories
echo -e "${YELLOW}Setting up Cloudflared directories...${NC}"
mkdir -p /etc/cloudflared
mkdir -p "/home/$USERNAME/.cloudflared"

# Set up Nginx
echo -e "${YELLOW}Configuring Nginx...${NC}"
cat > /etc/nginx/sites-available/agent-dvr << EOF
server {
    listen 80;
    server_name localhost;
    location / {
        proxy_pass http://localhost:8090;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/agent-dvr /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx

# Create Cloudflared service file
echo -e "${YELLOW}Creating Cloudflared service...${NC}"
cat > /etc/systemd/system/cloudflared.service << EOF
[Unit]
Description=cloudflared
After=network.target

[Service]
TimeoutStartSec=0
Type=simple
User=$USERNAME
ExecStart=/usr/bin/cloudflared --config /etc/cloudflared/config.yml tunnel run
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

# Clone the repository
echo -e "${YELLOW}Downloading Panacea Tech files...${NC}"
cd "$PANACEA_DIR"
git clone https://github.com/Fruitloop24/agentdvr.git .

# Update docker-compose.yml to use the storage directory
echo -e "${YELLOW}Updating docker-compose.yml to use storage directory...${NC}"
sed -i "s|./agentdvr/config|$STORAGE_DIR/agentdvr/config|g" docker-compose.yml
sed -i "s|./agentdvr/media|$STORAGE_DIR/agentdvr/media|g" docker-compose.yml

# Check for .env file and create if it doesn't exist
if [ ! -f "$PANACEA_DIR/.env" ]; then
  echo -e "${YELLOW}Creating .env file...${NC}"
  echo -e "${BLUE}Enter your Telegram Bot Token:${NC}"
  read -r TELEGRAM_BOT_TOKEN
  
  echo -e "${BLUE}Enter your Telegram Chat ID:${NC}"
  read -r TELEGRAM_CHAT_ID
  
  cat > "$PANACEA_DIR/.env" << EOF
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
ADMIN_CHAT_ID=$TELEGRAM_CHAT_ID
EOF
fi

# Setup Cloudflare Tunnel
echo -e "${YELLOW}Setting up Cloudflare Tunnel...${NC}"
echo -e "${GREEN}Please follow these steps to set up your Cloudflare Tunnel:${NC}"
echo -e "${BLUE}1. Login to Cloudflare (a browser will open):${NC}"
echo -e "${YELLOW}   cloudflared tunnel login${NC}"
echo -e "${BLUE}2. Create a tunnel and note the ID it generates:${NC}"
echo -e "${YELLOW}   cloudflared tunnel create my-agent-dvr${NC}"
echo -e "${BLUE}3. Set up DNS for your tunnel (replace TUNNEL_ID with the ID from step 2):${NC}"
echo -e "${YELLOW}   cloudflared tunnel route dns TUNNEL_ID $DOMAIN${NC}"
echo -e "${BLUE}4. Create a Cloudflare config file with the following content:${NC}"
echo -e "${YELLOW}   sudo nano /etc/cloudflared/config.yml${NC}"
echo ""
echo -e "tunnel: YOUR_TUNNEL_ID"
echo -e "credentials-file: /home/$USERNAME/.cloudflared/YOUR_TUNNEL_ID.json"
echo -e "ingress:"
echo -e "  - hostname: $DOMAIN"
echo -e "    service: http://localhost:80"
echo -e "  - service: http_status:404"
echo ""

# Fix ownership of the files
echo -e "${YELLOW}Setting correct ownership...${NC}"
chown -R "$USERNAME:$USERNAME" "$STORAGE_DIR"
chown -R "$USERNAME:$USERNAME" "$PANACEA_DIR"
chown -R "$USERNAME:$USERNAME" "/home/$USERNAME/.cloudflared"

# Instructions for starting services
echo -e "${GREEN}==================== Installation Complete ====================${NC}"
echo -e "${GREEN}Your Panacea Tech Agent DVR system is ready for final setup!${NC}"
echo -e "${BLUE}1. Complete the Cloudflare Tunnel setup as instructed above${NC}"
echo -e "${BLUE}2. Enable and start the cloudflared service:${NC}"
echo -e "${YELLOW}   sudo systemctl enable cloudflared${NC}"
echo -e "${YELLOW}   sudo systemctl start cloudflared${NC}"
echo -e "${BLUE}3. Start the Docker containers:${NC}"
echo -e "${YELLOW}   cd $PANACEA_DIR${NC}"
echo -e "${YELLOW}   docker-compose up -d${NC}"
echo -e "${BLUE}4. Visit your Agent DVR instance at:${NC}"
echo -e "${YELLOW}   https://$DOMAIN${NC}"
echo -e "${GREEN}===============================================================${NC}"
echo -e "${BLUE}Thank you for choosing Panacea Tech!${NC}"