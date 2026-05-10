# Hosting notes — quick deploy

Full VM setup (nginx, TLS, systemd, first venv, `.env`) is in **`HOSTING_GCP.md`**. This file is the short **git → deploy** checklist.

## Deploy script

**`scripts/deploy-vm.sh`** (run on the Linux VM from the **repo root**, the directory that contains `backend/` and `frontend/`):

1. `pip install -r requirements.txt` inside `backend/.venv`
2. `npm ci` and `npm run build` in `frontend/`
3. `sudo rsync` of `frontend/dist/` → `/var/www/glamr/` (default)
4. `sudo systemctl restart glamr-api` (default service name)

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

Ensure **`HOSTING_GCP.md`** steps are done once: packages, Node, clone location, `backend/.venv`, `backend/.env`, nginx, Let’s Encrypt (if using a domain), and the **`glamr-api`** systemd unit.

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

## Repo files related to hosting

| Item | Role |
|------|------|
| `HOSTING_GCP.md` | End-to-end GCP VM provisioning |
| `scripts/deploy-vm.sh` | Update deps, rebuild SPA, sync static files, restart API |
| `.gitattributes` | Keeps `scripts/*.sh` with LF line endings for Linux |
