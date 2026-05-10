# Hosting notes — quick deploy

Full VM setup (nginx, TLS, systemd, first venv, `.env`) is in **`HOSTING_GCP.md`**. This file is the short **git → deploy** checklist.

## Deploy script

**`scripts/deploy-vm.sh`** (run on the Linux VM from the **repo root**, the directory that contains `backend/` and `frontend/`):

1. `pip install -r requirements.txt` inside `backend/.venv`
2. `npm ci` and `npm run build` in `frontend/`
3. `sudo rsync` of `frontend/dist/` → `/var/www/glamr/` (default)
4. `sudo systemctl restart glamr-api` (default service name)

**Google Maps (Contact page):** create **`frontend/.env`** on the VM (not in Git) with  
`VITE_GOOGLE_MAPS_EMBED_KEY=your_key`  
then run the deploy script so `npm run build` picks it up. Copy from **`frontend/.env.example`**.

**Overrides** (if your paths differ):

```bash
WEBROOT=/var/www/glamr SYSTEMD_SERVICE=glamr-api ./scripts/deploy-vm.sh
```

---

## On your machine (push changes)

```bash
git add -A
git commit -m "Your message"
git push
```

Adjust branch/remotes as you use them.

---

## On the VM — first time only (per clone)

```bash
chmod +x scripts/deploy-vm.sh
```

Ensure **`HOSTING_GCP.md`** steps are done once: packages, Node, clone location, `backend/.venv`, `backend/.env`, **`deploy/glamr-api.service`** copied to `/etc/systemd/system/` (see §8), nginx, Let’s Encrypt (if using a domain).

---

## On the VM — every release

```bash
cd /opt/glamr/app    # or wherever the repo is cloned
git pull
./scripts/deploy-vm.sh
```

If the service fails to start:

```bash
sudo journalctl -u glamr-api -n 50 --no-pager
```

---

## Admin URL

Use **`/admin/`** (trailing slash) or **`/admin/login`**. Plain **`/admin`** without a slash used to show a blank page (SPA catch-all); the app and nginx config redirect it to **`/admin/`**.

---

## Repo files related to hosting

| Item | Role |
|------|------|
| `HOSTING_GCP.md` | End-to-end GCP VM provisioning |
| `deploy/glamr-api.service` | systemd unit template — `sudo cp` to `/etc/systemd/system/glamr-api.service` |
| `deploy/nginx-glamr.conf` | nginx site — `sudo cp` to `/etc/nginx/sites-available/glamr` |
| `scripts/deploy-vm.sh` | Update deps, rebuild SPA, sync static files, restart API |
| `.gitattributes` | Keeps `scripts/*.sh` with LF line endings for Linux |
