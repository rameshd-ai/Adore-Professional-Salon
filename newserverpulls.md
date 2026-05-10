# Server: pull + publish (frontend + backend)

Run on the VM after you **push** from your PC.

## Every deploy

```bash
cd /opt/glamr/app && git pull && ./scripts/deploy-vm.sh
```

## First time only

```bash
chmod +x /opt/glamr/app/scripts/deploy-vm.sh
```

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
