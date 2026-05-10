# Hosting Glamr on a single Google Cloud VM

This guide deploys **FastAPI** (`backend/`), **React** (`frontend/` build), **nginx** (HTTPS + static files), and **systemd** (keeps the API running) on **one Compute Engine VM**. WhatsApp webhooks need a **public HTTPS URL** (for example `https://yourdomain.com/webhooks/whatsapp`).

## 1. Create the VM

1. In [Google Cloud Console](https://console.cloud.google.com/) → **Compute Engine** → **VM instances** → **Create instance**.
2. **Machine type:** `e2-small` or larger (more RAM helps builds).
3. **Boot disk:** Ubuntu 22.04 LTS, 20–30 GB balanced or SSD.
4. **Firewall:** Enable **Allow HTTP** and **Allow HTTPS** (or add rules below manually).
5. Create the instance and note its **External IP**.

**Firewall rules** (if not using the checkboxes):

- **Ingress** TCP `22` — SSH (restrict to your IP in production).
- **Ingress** TCP `80`, `443` — HTTP/HTTPS for the site and webhooks.

Reserve a **static IP** (VPC network → External IP addresses) if you want a stable DNS target.

## 2. Point DNS at the VM

Create an **A record** for your domain (e.g. `yourdomain.com` and `www`) to the VM’s **static** external IP. Wait for DNS to propagate before running Let’s Encrypt.

## 3. Initial server setup (SSH)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y nginx certbot python3-certbot-nginx git python3-venv rsync
```

If `python3 -m venv` still complains about `ensurepip`, install the matching package (e.g. `sudo apt install -y python3.11-venv`).

Install Node.js 20+ (for building the frontend once), for example via [NodeSource](https://github.com/nodesource/distributions) or `nvm`.

## 4. Deploy the code

```bash
sudo mkdir -p /opt/glamr
sudo chown "$USER:$USER" /opt/glamr
cd /opt/glamr
git clone https://github.com/rameshd-ai/Adore-Professional-Salon.git app
```

Use the directory that contains **`backend/`** and **`frontend/`**:

- If the Git repo root **is** this `sal` project folder: `cd /opt/glamr/app` (paths below use `/opt/glamr/app/backend`, not `.../sal/backend`).
- If the repo has a parent folder (e.g. `repo/sal/`): `cd /opt/glamr/app/sal`.

The examples below assume **`APP=/opt/glamr/app`** where `backend` lives at `$APP/backend`. Replace `$APP` accordingly.

## 5. Python API (venv + dependencies)

```bash
export APP=/opt/glamr/app   # see section 4
cd "$APP/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

**Production database:** SQLite is fine for light use; for anything serious set PostgreSQL and `DATABASE_URL`:

```bash
# Example after installing PostgreSQL on the same VM or using Cloud SQL:
export DATABASE_URL="postgresql+psycopg2://USER:PASS@127.0.0.1:5432/glamr"
```

## 6. Environment variables

Create `$APP/backend/.env` (or use `/etc/glamr.env` and reference it in systemd) with at least:

| Variable | Purpose |
|----------|---------|
| `ADMIN_USERNAME` | SQLAdmin login |
| `ADMIN_PASSWORD` | Strong password |
| `SESSION_SECRET` | Long random string for admin sessions |
| `DATABASE_URL` | Optional; omit for SQLite (`backend/glamr.db`) |
| `CORS_ORIGINS` | e.g. `https://yourdomain.com` (comma-separated if multiple) |

Optional: `UPLOAD_DIR` for gallery uploads (ensure the service user can write there).

## 7. Build the frontend

```bash
cd "$APP/frontend"
npm ci
echo 'VITE_API_URL=' | tee .env.production   # empty = same origin; or https://yourdomain.com
npm run build
sudo mkdir -p /var/www/glamr
sudo rsync -a --delete dist/ /var/www/glamr/
```

If the site and API share one domain, leave `VITE_API_URL` empty so the browser calls `/api` on the same host.

## 8. systemd unit for uvicorn

This keeps the API running after logout/reboot. It listens on **`127.0.0.1:8000`** only; nginx (§9) proxies `/api`, `/admin`, etc. to that port.

### Before you start

1. **`$APP/backend/.env`** (§6) — create it for production with at least `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SESSION_SECRET`, and `CORS_ORIGINS` for your real site URL. SQLite: leave `DATABASE_URL` unset. The unit file uses **`EnvironmentFile=-...`** so a **missing** `.env` no longer crashes systemd (you should still add `.env` before going live).
2. **Manual check** (proves venv + app work):

   ```bash
   cd /opt/glamr/app/backend
   source .venv/bin/activate
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

   Press Ctrl+C after you see it start; if this fails, fix errors before systemd.

### Install the unit file

From the repo root on the VM (adjust `/opt/glamr/app` if your clone path differs):

```bash
export APP=/opt/glamr/app
cd "$APP"
git pull   # ensures deploy/glamr-api.service exists if we added it after your first clone
sudo cp "$APP/deploy/glamr-api.service" /etc/systemd/system/glamr-api.service
```

If **`cp` fails** (`No such file or directory`), either pull failed or your branch never got `deploy/`. Create the unit file directly (paths assume `/opt/glamr/app/backend` — edit if needed):

```bash
sudo tee /etc/systemd/system/glamr-api.service << 'EOF'
[Unit]
Description=Adore salon FastAPI (uvicorn)
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/glamr/app/backend
EnvironmentFile=-/opt/glamr/app/backend/.env
ExecStart=/opt/glamr/app/backend/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

If your app lives somewhere other than `/opt/glamr/app/backend`, edit `WorkingDirectory`, `EnvironmentFile`, and `ExecStart` in that file (`sudo nano /etc/systemd/system/glamr-api.service`).

### Permissions: pick **one** approach

**A — Simplest (recommended if `www-data` permission errors):** edit the unit so the service runs as **your SSH login user** (the user that owns `backend/.venv`):

```bash
sudo nano /etc/systemd/system/glamr-api.service
# Set User= and Group= to your username (e.g. dramesh2610), save, then:
sudo systemctl daemon-reload
sudo systemctl restart glamr-api
```

**B — Traditional (`User=www-data`):** the API user must read `.venv`, read `.env`, and write SQLite + uploads:

```bash
export APP=/opt/glamr/app
sudo mkdir -p "$APP/backend/uploads"
sudo touch "$APP/backend/glamr.db" 2>/dev/null || true
sudo chown -R www-data:www-data "$APP/backend/uploads" "$APP/backend/glamr.db"
sudo chown www-data:www-data "$APP/backend/.env"
sudo chmod 640 "$APP/backend/.env"
# So SQLite can create/update the DB file:
sudo chown www-data:www-data "$APP/backend"
```

Ensure others can traverse directories to `.venv` (default `755` on `/opt/glamr/app` paths is usually enough). If it still fails, use approach **A**.

### Enable and verify

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now glamr-api
sudo systemctl status glamr-api
```

Quick API check from the VM:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/docs
```

You should see `200`.

### If it fails

```bash
sudo journalctl -u glamr-api -n 80 --no-pager
```

Common messages: missing `.env`, bad path to `.venv`, SQLite cannot write `glamr.db`, or `Permission denied` on the venv — fix with approach **A** or **B** above.

**`Failed to run 'start' task: No such file or directory`:** often the venv **`python`** or **`uvicorn`** path is wrong. The shipped unit uses **`python -m uvicorn`** (more reliable than calling the `uvicorn` script). Verify on the VM:

```bash
ls -la /opt/glamr/app/backend/.venv/bin/python /opt/glamr/app/backend/.venv/bin/python3
/opt/glamr/app/backend/.venv/bin/python -m uvicorn --help >/dev/null && echo OK
```

If only `python3` exists in `.venv/bin/`, edit `ExecStart=` to use `.../bin/python3 -m uvicorn ...`.

Use `--port 8000` internally; nginx terminates TLS and proxies to `127.0.0.1:8000`.

## 9. nginx

**Create the site file before enabling it** — `sites-available/glamr` must exist, or `nginx -t` will fail.

From the repo root (`export APP=/opt/glamr/app`), after `git pull`:

```bash
sudo cp "$APP/deploy/nginx-glamr.conf" /etc/nginx/sites-available/glamr
sudo nano /etc/nginx/sites-available/glamr
```

Set **`server_name`** to your domain (or use `_` as a catch‑all on HTTP only until you have DNS — Let’s Encrypt still needs a real hostname).

Enable and test:

```bash
sudo ln -sf /etc/nginx/sites-available/glamr /etc/nginx/sites-enabled/glamr
sudo nginx -t && sudo systemctl reload nginx
```

If Ubuntu’s default site steals port 80, disable it:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Inline reference (same as `deploy/nginx-glamr.conf`; includes `/health`):

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    root /var/www/glamr;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ``/admin`` alone is not routed to SQLAdmin (mount is ``/admin/...``); keep this or the SPA serves a blank tab.
    location = /admin {
        return 308 /admin/;
    }

    location /admin {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /webhooks/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /uploads/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /site-media/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /admin-theme/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /saul-admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
```

## 10. HTTPS (Let’s Encrypt)

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot will adjust the server block for TLS. Renewals are automatic via systemd timer.

## 11. WhatsApp webhook (Meta)

1. In **API → API settings** (admin), set **Webhook verify token** and (recommended) **App secret**.
2. In Meta Developer Console, webhook URL: `https://yourdomain.com/webhooks/whatsapp`
3. Subscribe to **messages** (and verify). Meta requires **HTTPS** with a valid certificate.

## 12. Updates and backups

**Deploy new code (recommended):** from the app directory (repo root — the folder that contains `backend/` and `frontend/`), after `git pull`:

```bash
chmod +x scripts/deploy-vm.sh   # once per clone
git pull
./scripts/deploy-vm.sh
```

The script installs backend deps, builds the SPA, rsyncs `dist/` to `/var/www/glamr`, and restarts `glamr-api`. Override paths if needed: `WEBROOT=/var/www/glamr SYSTEMD_SERVICE=glamr-api ./scripts/deploy-vm.sh`.

**Manual equivalent:**

```bash
export APP=/opt/glamr/app
cd "$APP" && git pull
cd "$APP/backend" && source .venv/bin/activate && pip install -r requirements.txt
cd "$APP/frontend" && npm ci && npm run build && sudo rsync -a --delete dist/ /var/www/glamr/
sudo systemctl restart glamr-api
```

**Backups:** Snapshot the VM disk, and copy `backend/glamr.db` (SQLite) or run PostgreSQL dumps regularly.

## Optional: Cloud SQL instead of SQLite

Create a PostgreSQL instance in the same region, set `DATABASE_URL` to the Cloud SQL connection string (often with Cloud SQL Auth Proxy on the VM), and run migrations/seeding on first deploy. This is still a single VM for the app; only the database is managed.
