# Quick Start Guide 🚀

## ✅ What I Just Did For You

1. ✅ Installed `flask-limiter` for rate limiting
2. ✅ Generated secure SECRET_KEY
3. ✅ Generated secure ADMIN_API_KEY  
4. ✅ Created your `.env` file with all the keys

## 🎯 Your App is Now Secure!

Your `.env` file has been created with:
- **SECRET_KEY**: Secure 64-character key for Flask sessions
- **ADMIN_API_KEY**: Key to protect admin endpoints
- **DEBUG=False**: Production mode enabled

## 🏃 Running Your App

### For Development (with debug):
1. Edit `.env` and change `DEBUG=True`
2. Run: `python app.py`

### For Production:
- Just run: `python app.py`
- Or use gunicorn: `gunicorn -w 4 -b 0.0.0.0:5000 app:app`

## 🌐 Deploying to the Web

### Easy Options:

**Option 1: Railway (Easiest)**
1. Go to railway.app
2. Sign up for free account
3. Click "New Project" → "Deploy from GitHub repo"
4. Connect your repo
5. Add environment variables (copy from your .env file)
6. Railway handles everything else!

**Option 2: Render (Also Easy)**
1. Go to render.com
2. Sign up for free account  
3. Click "New Web Service"
4. Connect your GitHub repo
5. Set build command: `pip install -r requirements.txt`
6. Set start command: `gunicorn -w 4 -b 0.0.0.0:$PORT app:app`
7. Add environment variables from your .env file

### Using Your Custom Domain:

**On Railway/Render:**
1. After deployment, go to project settings
2. Click "Add Custom Domain"
3. Enter your domain name
4. Follow their DNS instructions (usually add a CNAME record)
5. SSL certificate is automatic!

**DNS Setup (if needed):**
- Add CNAME record: `www` → your railway/render URL
- Or A record: `@` → your server IP address

## 🔑 Using Admin Endpoints

If you need to call admin endpoints, include the API key:

```bash
# Using curl:
curl -X POST http://localhost:5000/api/run_lottery \
  -H "X-API-Key: 13883b925f2be1d1acf330dc0f3e0e470024fb20019eb26eb0e6e59c9ea9dfe6"
```

Or in JavaScript:
```javascript
fetch('/api/run_lottery', {
  method: 'POST',
  headers: {
    'X-API-Key': '13883b925f2be1d1acf330dc0f3e0e470024fb20019eb26eb0e6e59c9ea9dfe6'
  }
})
```

## 📝 Your Keys (Keep These Safe!)

- **SECRET_KEY**: `1bdfd2bf1dc5103bb3e08fff623481ddbf32a00b831f87584c56b56d3f31b894`
- **ADMIN_API_KEY**: `13883b925f2be1d1acf330dc0f3e0e470024fb20019eb26eb0e6e59c9ea9dfe6`

⚠️ **NEVER share these keys publicly or commit .env to git!**

## ✅ Security Status

- ✅ Debug mode fixed
- ✅ Admin endpoints protected
- ✅ Rate limiting enabled
- ✅ SECRET_KEY validation active
- ✅ Ready for production deployment!

You're all set! 🎉

