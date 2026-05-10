# Server: pull + publish (frontend + backend)

Run on the VM after you **push** from your PC.

**Use the full deploy script** — do **not** only `git pull` + `systemctl restart` or new Python deps / migrations can break the API (**502** / “Could not reach the API”).

## Every deploy

```bash
cd /opt/glamr/app && git pull && ./scripts/deploy-vm.sh
```

Wait until it prints **`Deploy finished.`** If anything errors above that, fix it before ignoring.

## Right after deploy (catch API down early)

```bash
sudo systemctl is-active glamr-api
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/settings
```

First line should be **`active`**. Second should be **`200`**. If not:

```bash
sudo journalctl -u glamr-api -n 60 --no-pager
sudo systemctl restart glamr-api
```

## One-time per server (skip if already done)

Only if `./scripts/deploy-vm.sh` says **Permission denied**:

```bash
chmod +x /opt/glamr/app/scripts/deploy-vm.sh
```

## Optional: Google Maps key (only if you use it)

Before `./scripts/deploy-vm.sh`, ensure **`/opt/glamr/app/frontend/.env`** exists with:

```bash
VITE_GOOGLE_MAPS_EMBED_KEY=your_key
```

(`npm run build` reads this; it is **not** in Git.)

## If `deploy/nginx-glamr.conf` changed

```bash
sudo cp /opt/glamr/app/deploy/nginx-glamr.conf /etc/nginx/sites-available/glamr
sudo nginx -t && sudo systemctl reload nginx
```

## If `deploy/glamr-api.service` changed

```bash
sudo cp /opt/glamr/app/deploy/glamr-api.service /etc/systemd/system/glamr-api.service
sudo systemctl daemon-reload
sudo systemctl restart glamr-api
```
