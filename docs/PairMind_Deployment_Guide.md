# PairMind — Complete Deployment Guide
**Stack:** FastAPI + LangGraph + React + OpenSearch + Claude Haiku  
**Deployment:** AWS EC2 (no Docker) — Nginx + Uvicorn on a single instance  
**Date:** May 2026

---

## EC2 Specifications

| Item | Value |
|------|-------|
| Instance type | t3.small |
| OS | Ubuntu 26.04 (Resolute) |
| Region | ap-south-1 (Mumbai) |
| Root volume | 20 GB gp3 (expanded from default 8 GB) |
| Swap | 1 GB (added manually) |
| RAM | 2 GB |
| Public IP | 43.205.210.113 |

### Security Group — Inbound Rules

| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Your IP | SSH access |
| 80 | TCP | 0.0.0.0/0 | HTTP (Nginx serves frontend + proxies API) |
| 9200 | TCP | Your IP | OpenSearch (already configured) |

> Port 8000 (FastAPI) is **not** opened to the internet — only Nginx talks to it internally.

---

## Architecture

```
Internet
    ↓
Nginx (port 80)
    ├── /          → serves React build (static files)
    └── /api/      → proxies to FastAPI on localhost:8000
                            ↓
                    FastAPI (uvicorn, port 8000)
                            ↓
                    OpenSearch (port 9200, already running)
```

---

## Step 1 — Expand EC2 Root Volume (AWS Console)

The default 8 GB root volume fills up when installing Python ML packages (torch alone is ~1.4 GB).

**In AWS Console:**
1. EC2 → Elastic Block Store → **Volumes**
2. Select the volume attached to your instance
3. Actions → **Modify Volume** → change size to **20 GB** → confirm

**Back in the EC2 terminal — grow the partition to use new space:**
```bash
# Check device name
lsblk
# Should show nvme0n1 with a partition nvme0n1p1

# Expand the partition
sudo growpart /dev/nvme0n1 1

# Resize the filesystem to fill the partition
sudo resize2fs /dev/nvme0n1p1

# Verify — should now show ~19 GB available
df -h /
```

---

## Step 2 — Add Swap Space

OpenSearch + FastAPI + sentence-transformers together exceed 2 GB RAM on a t3.small. Swap (virtual memory on disk) prevents OOM kills.

```bash
# Allocate a 1 GB swap file
sudo fallocate -l 1G /swapfile

# Secure it — only root can read it
sudo chmod 600 /swapfile

# Format it as swap
sudo mkswap /swapfile

# Activate it
sudo swapon /swapfile

# Make it survive reboots
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify — should show Swap: 1.0Gi
free -h
```

---

## Step 3 — Install System Dependencies

Ubuntu Resolute (26.04) ships with Python 3.14 — no need to install Python separately.

```bash
# Update package list
sudo apt update

# Install Nginx (web server) and Node.js tooling
sudo apt install -y nginx

# Install Node.js 20 (for building React frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
nginx -v        # nginx/1.28.x
node --version  # v20.x
npm --version   # 10.x
python3 --version  # Python 3.14.x
```

---

## Step 4 — Clone the Repository

```bash
cd ~
git clone https://github.com/Pawon25/PairMind.git

# Verify
ls  # should show: PairMind
```

---

## Step 5 — Set Up Python Backend

### Create virtual environment
```bash
cd ~/PairMind/backend

# Create isolated Python environment
python3 -m venv venv

# Activate it — prompt changes to (venv)
source venv/bin/activate
```

> **What's a venv?** An isolated Python environment so project packages don't conflict with system Python.

### Install dependencies (in two steps to manage disk space)

**Step 5a — Install everything except torch:**
```bash
pip install fastapi "uvicorn==0.24.0" pydantic python-multipart python-dotenv \
    langgraph langchain langchain-community langchain-openai langchain-text-splitters \
    anthropic tavily-python "opensearch-py==2.4.2" pypdf docx2txt markdown unstructured
```

**Step 5b — Install CPU-only torch (much smaller than GPU version) without caching:**
```bash
# --no-cache-dir saves ~400 MB of disk (we don't need to reinstall later)
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
```

**Step 5c — Install sentence-transformers:**
```bash
pip install --no-cache-dir sentence-transformers
```

> **Why separate steps?** The full torch GPU wheel is 532 MB and would fill the disk. CPU-only is 192 MB. Installing without cache prevents pip from keeping a copy after install.

### Create the .env file
```bash
nano ~/PairMind/backend/.env
```

Paste and fill in your actual keys:
```
ANTHROPIC_API_KEY=your_key_here
TAVILY_API_KEY=your_key_here
OPENSEARCH_URL=http://localhost:9200
```
Save: `Ctrl+X` → `Y` → `Enter`

### Test backend starts correctly
```bash
cd ~/PairMind/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
# Should see: Application startup complete.
# Ctrl+C to stop
```

---

## Step 6 — Register Backend as a systemd Service

> **Why systemd?** So the backend auto-starts on reboot and restarts if it crashes — same as OpenSearch.

```bash
sudo nano /etc/systemd/system/pairmind-backend.service
```

Paste exactly:
```ini
[Unit]
Description=PairMind Backend
After=network.target opensearch.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/PairMind/backend
EnvironmentFile=/home/ubuntu/PairMind/backend/.env
ExecStart=/home/ubuntu/PairMind/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Save, then enable and start:
```bash
# Reload systemd so it sees the new service file
sudo systemctl daemon-reload

# Enable = auto-start on reboot
sudo systemctl enable pairmind-backend

# Start it now
sudo systemctl start pairmind-backend

# Check it's running
sudo systemctl status pairmind-backend --no-pager
# Should show: Active: active (running)
```

---

## Step 7 — Build the React Frontend

### Fix hardcoded localhost URLs

The frontend had two files with hardcoded `http://localhost:8000`. These must use the environment variable instead.

**In `frontend/src/components/UploadPanel.jsx`:**
```js
// WRONG
await fetch('http://localhost:8000/reset', { method: 'POST' });
localId: crypto.randomUUID(),  // breaks without HTTPS

// CORRECT
await fetch(`${process.env.REACT_APP_API_URL}/reset`, { method: 'POST' });
localId: Math.random().toString(36).slice(2),  // works over HTTP
```

**In `frontend/src/components/CitationModal.jsx`:**
```js
// WRONG
fetch(`http://localhost:8000/citation?${params}`)

// CORRECT
fetch(`${process.env.REACT_APP_API_URL}/citation?${params}`)
```

> **Why backticks?** In JavaScript, `${variable}` only works inside backtick (`` ` ``) template literals — single or double quotes treat it as a plain string.

> **Why replace crypto.randomUUID()?** It requires a secure context (HTTPS). Since we're on plain HTTP, we use `Math.random()` instead.

### Set the API base URL
```bash
echo "REACT_APP_API_URL=http://43.205.210.113/api" > ~/PairMind/frontend/.env
```

### Fix the browser tab title
```bash
nano ~/PairMind/frontend/public/index.html
# Change: <title>React App</title>
# To:     <title>PairMind</title>
```

### Install and build
```bash
cd ~/PairMind/frontend
npm install
npm run build
# Creates frontend/build/ — static files ready to serve
```

---

## Step 8 — Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/pairmind
```

Paste:
```nginx
server {
    listen 80;
    server_name 43.205.210.113;

    # Serve React frontend static files
    root /home/ubuntu/PairMind/frontend/build;
    index index.html;

    # All frontend routes (React Router support)
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy /api/* to FastAPI backend (strips /api prefix)
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # Required for SSE streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

Enable and activate:
```bash
# Enable our config
sudo ln -s /etc/nginx/sites-available/pairmind /etc/nginx/sites-enabled/

# Disable the default placeholder page
sudo rm /etc/nginx/sites-enabled/default

# Test config syntax
sudo nginx -t
# Should say: syntax is ok / test is successful

# Apply
sudo systemctl restart nginx
```

### Fix file permissions for Nginx

Nginx runs as `www-data` user and can't read files in `/home/ubuntu/` by default.

```bash
# Give "others" (including www-data) permission to traverse each directory
sudo chmod o+x /home/ubuntu
sudo chmod o+x /home/ubuntu/PairMind
sudo chmod o+x /home/ubuntu/PairMind/frontend
sudo chmod o+x /home/ubuntu/PairMind/frontend/build

sudo systemctl restart nginx
```

---

## Step 9 — Verify Everything Works

```bash
# OpenSearch healthy
curl http://localhost:9200

# Backend healthy
curl http://localhost:8000/health
# Should return: {"status":"ok"}

# All services running
sudo systemctl status opensearch --no-pager | grep Active
sudo systemctl status pairmind-backend --no-pager | grep Active
sudo systemctl status nginx --no-pager | grep Active
```

Open in browser: **http://43.205.210.113**

---

## Useful Commands for Ongoing Management

```bash
# View backend logs (live)
sudo journalctl -u pairmind-backend -f

# Restart backend (after code changes)
sudo systemctl restart pairmind-backend

# Rebuild frontend and redeploy
cd ~/PairMind/frontend && npm run build && sudo systemctl restart nginx

# Pull latest code from GitHub and redeploy
cd ~/PairMind && git pull
cd backend && source venv/bin/activate && pip install -r requirements.txt
cd ../frontend && npm install && npm run build
sudo systemctl restart pairmind-backend
sudo systemctl restart nginx

# Check disk space
df -h /

# Check memory
free -h

# Check all service statuses
sudo systemctl status opensearch pairmind-backend nginx --no-pager
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Disk quota exceeded` during pip install | Disk full | `pip cache purge`, check `df -h /` |
| OpenSearch OOM killed | t3.small RAM exhausted | Ensure swap is active: `free -h` |
| `Permission denied` in Nginx logs | www-data can't read /home/ubuntu | Run `chmod o+x` on each directory in path |
| `${process.env...}` appears literally in URL | Single quotes used instead of backticks | Use backticks for JS template literals |
| `crypto.randomUUID is not a function` | Requires HTTPS | Replace with `Math.random().toString(36).slice(2)` |
| Backend not reachable at `/api/` | Nginx proxy not stripping prefix correctly | Ensure `proxy_pass http://localhost:8000/;` has trailing slash |
