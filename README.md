# IP Source Tracker

Infor MT AWS NAT IP'lerinden gelen istekleri izlemek ve doğrulamak için basit bir servis.

## Expected NAT IPs (EU-Central-1 Frankfurt)
- 52.58.37.0
- 52.29.28.67
- 18.197.50.73

## Endpoints

- `GET /` - Servis bilgisi
- `POST /webhook` - İstekleri kaydet (tüm HTTP methodları desteklenir)
- `GET /logs` - Tüm logları göster
- `GET /stats` - İstatistikler ve karşılaştırma

## Heroku Deployment

```bash
# Git init
git init
git add .
git commit -m "Initial commit"

# Heroku create
heroku create your-app-name

# Deploy
git push heroku main

# URL'i aç
heroku open
```

## Test

```bash
curl https://your-app.herokuapp.com/webhook
curl https://your-app.herokuapp.com/logs
curl https://your-app.herokuapp.com/stats
```

## Local Test

```bash
pip install -r requirements.txt
python app.py
```
