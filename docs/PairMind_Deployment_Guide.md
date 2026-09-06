# PairMind — Deployment Guide

Complete, copy-pasteable steps for standing up PairMind on a single EC2 instance: OpenSearch, the FastAPI backend, the `landing/` gate page, the `frontend/` negotiation UI, Nginx, HTTPS, and the access-token system. For architecture, design rationale, and local development, see the main [README](../README.md) — this file is pure ops.

**Reference instance:** Ubuntu 26.04, t3.small, 20 GB gp3, ap-south-1 (Mumbai), domain `pairmind.pavanb.in`. Substitute your own instance/domain throughout.

---

## Infrastructure layout

| Service | Port | Exposed |
|---|---|---|
| Nginx (TLS via Let's Encrypt) | 80 → 443 | ✅ Public |
| `landing/` (TanStack Start, SSR) | 3001 | 🔒 Internal only |
| Backend (FastAPI) | 8000 | 🔒 Internal only |
| OpenSearch | 9200 | 🔒 Internal only |

Nginx routes by path on one domain: `/` → `landing/` (proxied), `/app/*` → `frontend/` (static files), `/api/*` → FastAPI. Plain HTTP redirects to HTTPS once Certbot is set up (§6).

---

## 1. EC2 base setup

**Security group inbound rules:** `22` (SSH, ideally restricted to your IP), `80` and `443` (HTTP/HTTPS, public). Don't open `9200` — OpenSearch stays internal.

```bash
ssh -i "your-key.pem" ubuntu@<EC2_PUBLIC_IP>

# Expand disk (after resizing the volume in AWS Console, if you started smaller than 20 GB)
sudo growpart /dev/nvme0n1 1
sudo resize2fs /dev/nvme0n1p1

# Add 1 GB swap — prevents OOM kills on t3.small's 2 GB RAM
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# System dependencies
sudo apt update
sudo apt install -y git nginx python3-venv python3-pip
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

---

## 2. OpenSearch

Runs on the same box, bound to `localhost` only — never exposed in the security group. `backend/ingestion/opensearch_store.py` connects with **no auth**, so the security plugin must be disabled (the apt package ships with it enabled by default).

```bash
sudo apt install -y openjdk-21-jdk

curl -o- https://artifacts.opensearch.org/publickeys/opensearch.pgp | sudo gpg --dearmor --batch --yes -o /usr/share/keyrings/opensearch-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/opensearch-keyring.gpg] https://artifacts.opensearch.org/releases/bundle/opensearch/2.x/apt stable main" | sudo tee /etc/apt/sources.list.d/opensearch-2.x.list
sudo apt update

# The admin password below only matters during install (security plugin is
# on by default at this point) — it stops mattering once security is disabled.
sudo OPENSEARCH_INITIAL_ADMIN_PASSWORD="$(openssl rand -base64 16)" apt install -y opensearch

echo "plugins.security.disabled: true" | sudo tee -a /etc/opensearch/opensearch.yml
echo "network.host: 127.0.0.1"        | sudo tee -a /etc/opensearch/opensearch.yml
echo "discovery.type: single-node"     | sudo tee -a /etc/opensearch/opensearch.yml

# t3.small — keep JVM heap modest
sudo sed -i 's/-Xms1g/-Xms512m/' /etc/opensearch/jvm.options
sudo sed -i 's/-Xmx1g/-Xmx512m/' /etc/opensearch/jvm.options

sudo systemctl daemon-reload
sudo systemctl enable opensearch
sudo systemctl start opensearch

curl http://localhost:9200/_cluster/health   # no credentials needed — security plugin is off
```

---

## 3. Backend

```bash
git clone https://github.com/Pawon25/PairMind.git
cd ~/PairMind/backend

python3 -m venv venv
source venv/bin/activate

# CPU-only torch first — sentence-transformers would otherwise pull the
# default GPU build, which is much larger
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

nano .env
```

Add to `.env`:
```
ANTHROPIC_API_KEY=<your_key>
TAVILY_API_KEY=<your_key>
OPENSEARCH_URL=http://localhost:9200
```

Register as a systemd service:

```bash
sudo nano /etc/systemd/system/pairmind-backend.service
```
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
```bash
sudo systemctl daemon-reload
sudo systemctl enable pairmind-backend
sudo systemctl start pairmind-backend

curl http://localhost:8000/health   # → {"status":"ok"}
```

---

## 4. Landing (gate page)

`landing/` is a TanStack Start (SSR) app — unlike `frontend/`, it needs a running Node process, not just a static file drop.

```bash
cd ~/PairMind/landing
npm install
npm run build   # outputs to landing/.output/

sudo nano /etc/systemd/system/pairmind-landing.service
```
```ini
[Unit]
Description=PairMind Landing
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/PairMind/landing
Environment=PORT=3001
ExecStart=/usr/bin/node /home/ubuntu/PairMind/landing/.output/server/index.mjs
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable pairmind-landing
sudo systemctl start pairmind-landing

curl http://localhost:3001/
```

---

## 5. Frontend

```bash
cd ~/PairMind/frontend
echo "REACT_APP_API_URL=https://<your-domain>/api" > .env
npm install
npm run build   # outputs to frontend/build/, base path is /app (see "homepage" in package.json)
```

---

## 6. Nginx

```bash
sudo nano /etc/nginx/sites-available/pairmind
```
```nginx
server {
    listen 80;
    server_name <your-domain>;

    location / {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Bare "/app" (no trailing slash) doesn't match the block below on its
    # own — nginx prefix matching needs the slash — so without this it
    # silently falls through to "/" instead of the frontend.
    location = /app {
        return 301 /app/;
    }

    location /app/ {
        alias /home/ubuntu/PairMind/frontend/build/;
        try_files $uri $uri/ /app/index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```
```bash
sudo ln -s /etc/nginx/sites-available/pairmind /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Allow Nginx to traverse into /home/ubuntu to reach the frontend build
sudo chmod o+x /home/ubuntu /home/ubuntu/PairMind /home/ubuntu/PairMind/frontend /home/ubuntu/PairMind/frontend/build

sudo nginx -t
sudo systemctl restart nginx
```

---

## 7. HTTPS (Let's Encrypt / Certbot)

Point a DNS **A record** at the EC2's public IP, and open port **443** in the security group (Type: HTTPS, Source: Anywhere). Then:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d <your-domain>
```

Follow the prompts and say **yes** to the HTTP→HTTPS redirect offer — Certbot rewrites `/etc/nginx/sites-enabled/pairmind` in place to add the TLS block, and installs a `certbot.timer` systemd timer for auto-renewal (90-day cert validity). Verify with `systemctl list-timers | grep certbot`.

---

## 8. Access Tokens

The demo is invite-only (see README for why). Day-to-day operator commands, run on the EC2 box:

```bash
cd ~/PairMind/backend
source venv/bin/activate

python manage_demo_requests.py list          # see pending demo requests
python issue_token.py issue --note "jane@company.com"   # defaults: 7-day expiry, 3 uses
python issue_token.py issue --note "jane@company.com" --expires-days 14 --uses 5  # override
python manage_demo_requests.py review 1      # mark a request handled
python issue_token.py list                   # see all issued tokens + their status
```

---

## 9. Redeploying after code changes

```bash
cd ~/PairMind
git pull

cd frontend && npm run build && cd ..
cd landing && npm run build && cd ..
sudo systemctl restart pairmind-landing
sudo systemctl restart nginx

# If backend code changed:
sudo systemctl restart pairmind-backend
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Backend `Application startup failed`, OpenSearch `ConnectTimeoutError` | `OPENSEARCH_URL` wrong, or OpenSearch not running | `curl http://localhost:9200/_cluster/health`; check `.env` points at `localhost:9200` |
| `curl http://localhost:8000/health` connection refused right after restart | Backend still loading the embedding model | Wait ~10–15s and retry — first load is slow, subsequent requests aren't |
| `/app` (no trailing slash) 404s or shows the landing page | Nginx prefix matching needs the trailing slash | Confirm the `location = /app { return 301 /app/; }` block is present |
| `pip install` fails with disk errors | t3.small's 8 GB default root volume is too small | Resize to 20 GB in AWS Console, then §1's `growpart`/`resize2fs` |
| OpenSearch or backend OOM-killed | t3.small RAM (2 GB) exhausted | Confirm swap is active: `free -h` |
| `Failed to establish a new connection` immediately after `git pull` on `landing/` | Wrong Node version — TanStack Start needs Node ≥22.12 | `curl -fsSL https://deb.nodesource.com/setup_22.x \| sudo -E bash -` then `sudo apt install -y nodejs`, then `rm -rf node_modules package-lock.json && npm install` |
