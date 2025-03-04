# Panacea Tech - Agent DVR Surveillance System

A complete surveillance system with secure remote access using Agent DVR, MQTT, Telegram notifications, and Cloudflare Tunnel.

## Features

- **Agent DVR** - Feature-rich DVR software with AI-powered object detection
- **MQTT Integration** - Real-time messaging for alerts and notifications
- **Telegram Bot** - Receive instant alerts and camera snapshots on your phone
- **Cloudflare Tunnel** - Secure remote access without port forwarding
- **Nginx Reverse Proxy** - Handles web traffic efficiently
- **Persistent Storage** - Preserves recordings and configuration across restarts

## Requirements

- Raspberry Pi 4 (2GB+ RAM recommended)
- 16GB+ microSD card
- Power supply for Raspberry Pi
- Internet connection
- Cloudflare account (free)
- Telegram account

## Quick Installation

1. Flash Raspberry Pi OS (64-bit recommended) to your SD card
2. Boot your Raspberry Pi and complete initial setup
3. Download and run the installer:

```bash
wget -O install.sh https://raw.githubusercontent.com/Fruitloop24/agentdvr/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

4. Follow the on-screen instructions to complete the setup

## Manual Installation Steps

If you prefer to install manually or need more control, follow these steps:

### 1. Install Docker and Docker Compose

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
sudo systemctl enable docker
sudo systemctl start docker
```

### 2. Install Nginx

```bash
sudo apt install -y nginx
```

### 3. Install Cloudflared

```bash
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
sudo dpkg -i cloudflared-linux-arm64.deb
```

### 4. Create Directory Structure

```bash
# Create storage directories
mkdir -p ~/agent-dvr-setup/agentdvr/config
mkdir -p ~/agent-dvr-setup/agentdvr/media

# Create Panacea Tech directory for Docker
mkdir -p ~/panacea-tech/mqtt
mkdir -p ~/panacea-tech/telegram
```

### 5. Clone Repository

```bash
cd ~/panacea-tech
git clone https://github.com/Fruitloop24/agentdvr.git .
```

### 6. Update Docker Compose Config

Edit the docker-compose.yml file to point to your storage location:

```bash
nano ~/panacea-tech/docker-compose.yml
```

Update the volume paths:
```yaml
volumes:
  - /home/yourusername/agent-dvr-setup/agentdvr/config:/AgentDVR/Config
  - /home/yourusername/agent-dvr-setup/agentdvr/media:/AgentDVR/Media
```

### 7. Set up Cloudflare Tunnel

```bash
# Login to Cloudflare
cloudflared tunnel login

# Create a new tunnel
cloudflared tunnel create my-agent-dvr

# The above command will display your tunnel ID
# Set up DNS for the tunnel
cloudflared tunnel route dns YOUR_TUNNEL_ID yourdomain.panacea-tech.net
```

### 8. Configure Cloudflared

Create the config file:

```bash
sudo mkdir -p /etc/cloudflared
sudo nano /etc/cloudflared/config.yml
```

Add the following content (replace with your values):

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /home/yourusername/.cloudflared/YOUR_TUNNEL_ID.json
ingress:
  - hostname: yourdomain.panacea-tech.net
    service: http://localhost:80
  - service: http_status:404
```

### 9. Configure Nginx

Create the Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/agent-dvr
```

Add the following content:

```nginx
server {
    listen 80;
    server_name localhost;
    location / {
        proxy_pass http://localhost:8090;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/agent-dvr /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx
```

### 10. Create Cloudflared Service

```bash
sudo nano /etc/systemd/system/cloudflared.service
```

Add the following content (replace username with your username):

```ini
[Unit]
Description=cloudflared
After=network.target

[Service]
TimeoutStartSec=0
Type=simple
User=yourusername
ExecStart=/usr/bin/cloudflared --config /etc/cloudflared/config.yml tunnel run
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

### 11. Create .env File

```bash
nano ~/panacea-tech/.env
```

Add your Telegram bot details:

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_CHAT_ID=your_chat_id_here
```

### 12. Start Services

```bash
# Enable and start cloudflared
sudo systemctl enable cloudflared
sudo systemctl start cloudflared

# Start Docker containers
cd ~/panacea-tech
docker-compose up -d
```

## Telegram Bot Setup

1. Start a chat with [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the instructions to create a new bot
3. Copy the token provided by BotFather
4. To get your chat ID, search for "@get_id_bot" on Telegram and start a chat
5. Enter these values in your `.env` file

## Configuring Agent DVR

1. Access your Agent DVR interface at `https://yourdomain.panacea-tech.net`
2. Add your camera sources (RTSP, ONVIF, etc.)
3. Configure motion detection and object recognition
4. Set up alert triggers that will send notifications to your Telegram bot

## Directory Structure

The system uses two main directories:

- **~/agent-dvr-setup/** - Stores persistent data (recordings and configuration)
  - `agentdvr/config/` - Agent DVR configuration files
  - `agentdvr/media/` - Recordings and snapshots

- **~/panacea-tech/** - Contains the Panacea Tech software
  - `docker-compose.yml` - Main Docker configuration
  - `mqtt/` - MQTT broker configuration
  - `telegram/` - Telegram bot code

## Troubleshooting

### Cloudflare Tunnel Issues

If you see "Error 1033" or "Cloudflare Tunnel error":

```bash
# Check cloudflared status
sudo systemctl status cloudflared

# View logs
sudo journalctl -u cloudflared -f

# Verify configuration
cat /etc/cloudflared/config.yml
```

### Docker Issues

```bash
# Check container status
cd ~/panacea-tech
docker-compose ps

# View container logs
docker-compose logs

# View logs for a specific container
docker-compose logs telegram_bot
```

### Nginx Issues

```bash
# Check Nginx status
sudo systemctl status nginx

# Test configuration
sudo nginx -t

# View Nginx logs
sudo tail -f /var/log/nginx/error.log
```

## Upgrading

To upgrade the Panacea Tech system to the latest version:

```bash
cd ~/panacea-tech
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

## License

The Agent DVR software requires a license for commercial use. Please visit [ispyagentdvr.com](https://www.ispyagentdvr.com) for more information.

## Support

For issues with this installation script or the Docker setup, please contact Panacea Tech support or open an issue on GitHub.