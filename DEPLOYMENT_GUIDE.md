# Deployment Guide for pointslotto

## 🚀 Quick Deployment Options

### Option 1: Deploy to Railway/Render/Fly.io (Recommended)

These platforms handle SSL, domain setup, and environment variables automatically.

**Railway:**
```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login and link project
railway login
railway init

# 3. Add environment variables in Railway dashboard
# - SECRET_KEY (generate: python -c "import secrets; print(secrets.token_hex(32))")
# - DEBUG=False
# - Any Twitter API keys if needed

# 4. Deploy
railway up
```

**Render:**
1. Connect your GitHub repo to Render
2. Create new "Web Service"
3. Set:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn -w 4 -b 0.0.0.0:$PORT app:app`
4. Add environment variables in Render dashboard
5. Add your custom domain in Render settings

### Option 2: VPS (DigitalOcean, Linode, AWS EC2)

1. **Setup Server:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip nginx

# Install Gunicorn
pip3 install gunicorn
```

2. **Deploy Application:**
```bash
# Clone your repo
cd /var/www
sudo git clone <your-repo-url> pointslotto
cd pointslotto

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# Create .env file
nano .env
# Add your SECRET_KEY, DEBUG=False, etc.
```

3. **Setup Nginx Reverse Proxy:**
```nginx
# /etc/nginx/sites-available/pointslotto
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. **Setup SSL with Let's Encrypt:**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

5. **Create Systemd Service:**
```ini
# /etc/systemd/system/pointslotto.service
[Unit]
Description=PointsLotto Flask App
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/pointslotto
Environment="PATH=/var/www/pointslotto/venv/bin"
ExecStart=/var/www/pointslotto/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable pointslotto
sudo systemctl start pointslotto
```

## 🔒 Pre-Deployment Security Checklist

**CRITICAL - Do These Before Going Live:**

1. ✅ Set `DEBUG=False` in your `.env` file
2. ✅ Generate a strong `SECRET_KEY`:
   ```python
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
3. ⚠️ **Protect Admin Endpoints** (see below)
4. ⚠️ **Add Rate Limiting** (see below)
5. ✅ Verify `.env` is in `.gitignore`
6. ✅ Use HTTPS (automatic with Let's Encrypt/Railway/Render)

## 🛡️ Securing Admin Endpoints

Before deploying, add authentication to these endpoints:
- `/api/run_lottery`
- `/api/start_monitoring`
- `/api/stop_monitoring`
- `/api/sync_pointsmarket`

**Quick Fix - Add to `app.py`:**

```python
import os
from functools import wraps
from flask import request, abort

ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', None)

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not ADMIN_API_KEY:
            return jsonify({'success': False, 'message': 'Admin API not configured'}), 503
        
        api_key = request.headers.get('X-API-Key') or request.json.get('api_key') if request.is_json else None
        
        if api_key != ADMIN_API_KEY:
            abort(401)
        return f(*args, **kwargs)
    return decorated_function

# Then protect endpoints:
@app.route('/api/run_lottery', methods=['POST'])
@require_api_key
def api_run_lottery():
    # ... existing code
```

Add `ADMIN_API_KEY=your-secret-key` to your `.env` file.

## ⚡ Adding Rate Limiting

```bash
pip install flask-limiter
```

Add to `app.py`:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

@app.route('/api/qualified')
@limiter.limit("30 per minute")
def api_qualified():
    # ... existing code
```

## 🌐 Custom Domain Setup

### If using Railway/Render:
1. Go to your project settings
2. Click "Add Custom Domain"
3. Enter your domain
4. Follow DNS instructions (usually CNAME to their URL)

### If using VPS:
1. Point your domain's A record to your server IP
2. Configure Nginx as shown above
3. Run Certbot for SSL

### DNS Records Needed:
- **A Record**: `@` → Your server IP
- **CNAME**: `www` → Your domain or server

## 📝 Environment Variables Checklist

Create `.env` file with:
```env
# Required for Production
SECRET_KEY=your-generated-secret-key-here
DEBUG=False

# Optional - Admin API Protection
ADMIN_API_KEY=another-secret-key-for-admin-endpoints

# Optional - Twitter API (if using Twitter features)
TWITTER_API_KEY=your-key
TWITTER_API_SECRET=your-secret
# ... etc
```

## 🚨 Current Status

**⚠️ NOT READY FOR PUBLIC DEPLOYMENT YET**

You need to:
1. ✅ Fix debug mode (DONE - now uses Config().DEBUG)
2. ⚠️ Protect admin endpoints (needs API key auth)
3. ⚠️ Add rate limiting (recommended)
4. ⚠️ Set strong SECRET_KEY
5. ✅ Use HTTPS (automatic on most platforms)

**Once you complete steps 1-4, you'll be ready to deploy!**

## 🧪 Testing Before Launch

1. Test on localhost with `DEBUG=False`
2. Verify admin endpoints return 401 without API key
3. Check that public pages load correctly
4. Test rate limiting works
5. Verify HTTPS redirect works
6. Test domain DNS resolution

## 📊 Monitoring

After deployment:
- Set up uptime monitoring (UptimeRobot, Pingdom)
- Monitor server logs
- Check database size/backups
- Set up error alerting
