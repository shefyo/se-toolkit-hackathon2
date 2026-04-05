# 🚀 Deployment Guide — SmartReceipt v2

Complete step-by-step instructions for deploying SmartReceipt on Ubuntu 24.04.

---

## Prerequisites

- Ubuntu 24.04 server (or VM)
- Root or sudo access
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- (Optional) OpenAI API key for AI features

---

## Step 1: Install Docker and Docker Compose

```bash
# Update package index
sudo apt update

# Install Docker
sudo apt install -y docker.io

# Start and enable Docker
sudo systemctl enable --now docker

# Verify Docker
sudo docker --version

# Install Docker Compose (usually comes with docker.io package)
sudo apt install -y docker-compose

# Verify Docker Compose
docker-compose --version

# (Optional) Add your user to the docker group to run without sudo
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

---

## Step 2: Clone the Repository

```bash
git clone https://github.com/your-username/se-toolkit-lab-9.git
cd se-toolkit-lab-9
```

---

## Step 3: Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit with your values
nano .env
```

### Required Variables

```env
# Telegram Bot — Get token from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# LLM API — For AI features (optional, fallbacks available)
LLM_API_KEY=sk-your-openai-api-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# Backend URL (used by the bot to reach the backend)
BACKEND_URL=http://backend:8000
```

> **Important:** When running with Docker, `BACKEND_URL` must be `http://backend:8000` (the Docker service name), not `localhost`.

---

## Step 4: Get a Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow instructions — choose a name and username
4. Copy the token (looks like: `123456789:ABCdef...`)
5. Paste it into your `.env` file as `TELEGRAM_BOT_TOKEN`

---

## Step 5: Deploy with Docker Compose

```bash
# Build and start all services
docker-compose up --build -d

# Check that all containers are running
docker-compose ps

# Expected output:
# smartreceipt-backend    Up
# smartreceipt-bot        Up
# smartreceipt-frontend   Up
```

---

## Step 6: Verify Deployment

### Web Dashboard
Open in browser:
```
http://<YOUR_SERVER_IP>:3000
```

### API
Test the API:
```
http://<YOUR_SERVER_IP>:8000/health
http://<YOUR_SERVER_IP>:8000/docs  # Swagger UI
```

### Telegram Bot
Open your bot in Telegram and send `/start`. You should receive the welcome message.

---

## Step 7: View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f bot
docker-compose logs -f frontend

# Last 50 lines
docker-compose logs --tail=50 bot
```

---

## Step 8: Update and Redeploy

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose up --build -d

# Or restart without rebuild (if only config changed)
docker-compose restart
```

---

## Troubleshooting

### Bot doesn't respond
```bash
# Check bot logs
docker-compose logs bot

# Common issues:
# 1. TELEGRAM_BOT_TOKEN not set correctly
# 2. BACKEND_URL is wrong (should be http://backend:8000 in Docker)
# 3. Backend is not healthy — check: docker-compose ps
```

### Backend not accessible
```bash
# Check backend health
curl http://localhost:8000/health

# Check backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Frontend shows errors
```bash
# The frontend proxies API calls to the backend via nginx
# Ensure the backend container is running and accessible
docker-compose ps

# Check nginx config is mounted correctly
docker-compose logs frontend
```

### Database issues
```bash
# The SQLite database is stored in a Docker volume
# To view the volume:
docker volume ls | grep smartreceipt

# To backup the database:
docker cp smartreceipt-backend:/app/smartreceipt.db ./backup.db
```

### Out of disk space
```bash
# Clean up unused Docker resources
docker system prune -a

# Remove old images
docker image prune -a
```

---

## Alternative: Run Without Docker

If you prefer to run services directly on the server:

### Install Python dependencies
```bash
sudo apt install -y python3 python3-pip python3-venv
cd /path/to/se-toolkit-lab-9

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Set environment variables
```bash
export TELEGRAM_BOT_TOKEN="your-token"
export LLM_API_KEY="your-key"
export LLM_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-3.5-turbo"
export BACKEND_URL="http://localhost:8000"
```

### Start backend
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Start bot (in a separate terminal)
```bash
python -m bot.telegram_bot
```

### Serve frontend with nginx
```bash
sudo apt install -y nginx
sudo cp nginx.conf /etc/nginx/sites-available/default
sudo cp -r frontend/* /var/www/html/
sudo systemctl restart nginx
```

---

## Firewall Configuration

If you have `ufw` enabled, open the required ports:

```bash
sudo ufw allow 3000/tcp   # Frontend
sudo ufw allow 8000/tcp   # Backend API
sudo ufw reload
```

---

## Security Notes

- **Never commit `.env`** — It contains API keys. Use `.env.example` as a template.
- **Use HTTPS in production** — Set up a reverse proxy (nginx/caddy) with Let's Encrypt SSL.
- **Rotate tokens** — If your bot token is exposed, regenerate it via @BotFather (`/revoke`).
- **Restrict API access** — If possible, whitelist your server's IP in your LLM provider's settings.

---

## Production Checklist

- [ ] `.env` file configured with correct values
- [ ] Docker and docker-compose installed
- [ ] All containers running (`docker-compose ps`)
- [ ] Web dashboard accessible at port 3000
- [ ] API responding at port 8000
- [ ] Telegram bot responds to `/start`, `/stats`, `/advice`, `/chat`
- [ ] Logs checked for errors
- [ ] Firewall rules configured
- [ ] Database backup strategy in place
