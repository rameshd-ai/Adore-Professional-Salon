cd /opt/glamr/app && git pull
sudo systemctl restart glamr-api
sudo cp /opt/glamr/app/deploy/nginx-glamr.conf /etc/nginx/sites-available/glamr   # merge server_name if you customized it
sudo nginx -t && sudo systemctl reload nginx