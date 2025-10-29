# Railway Custom Domain Setup 🌐

## Step-by-Step Guide

### Step 1: Deploy Your App to Railway (If Not Done Yet)

1. Go to **railway.app** and sign up/login
2. Click **"New Project"**
3. Choose **"Deploy from GitHub repo"**
4. Select your repository or give Railway access to connect it
5. Railway will automatically detect it's a Python/Flask app
6. It will build and deploy automatically! ✨

### Step 2: Add Your Environment Variables

1. In your Railway project, click **"Variables"** tab
2. Click **"New Variable"** and add each one from your `.env` file:
   - `SECRET_KEY=1bdfd2bf1dc5103bb3e08fff623481ddbf32a00b831f87584c56b56d3f31b894`
   - `DEBUG=False`
   - `ADMIN_API_KEY=13883b925f2be1d1acf330dc0f3e0e470024fb20019eb26eb0e6e59c9ea9dfe6`
3. Add any other variables you need (Twitter API keys, etc.)

### Step 3: Add Your Custom Domain

1. In Railway, go to your **project settings**
2. Click on **"Settings"** → **"Networking"** tab
3. Scroll down to **"Custom Domains"** section
4. Click **"Add Domain"** or **"Custom Domain"**
5. Enter your domain:
   - Example: `pointslotto.com` or `www.pointslotto.com`
   - Or both (you can add multiple domains)

### Step 4: Configure Your DNS

Railway will show you DNS instructions. You have two options:

#### Option A: CNAME Method (Easiest - Use This!)

1. Railway gives you a target like: `xxxx.up.railway.app` or `xxxx.railway.app`

2. Go to your domain registrar (where you bought the domain):
   - **GoDaddy**: DNS Management
   - **Namecheap**: Advanced DNS
   - **Cloudflare**: DNS Records
   - **Google Domains**: DNS Settings

3. Add a CNAME record:
   - **Type**: CNAME
   - **Name/Host**: `www` (for www.yourdomain.com)
   - **Value/Target**: `xxxx.railway.app` (Railway's provided URL)
   - **TTL**: 3600 (or Auto)

4. For root domain (yourdomain.com without www):
   - Some providers support CNAME on root, but most need:
   - **Type**: A record pointing to Railway's IP (they'll provide it)

#### Option B: A Record Method

If Railway provides an IP address:
- **Type**: A
- **Name/Host**: `@` (for root domain) or leave blank
- **Value**: Railway's IP address
- **TTL**: 3600

### Step 5: Wait for DNS Propagation

- DNS changes take **5 minutes to 48 hours** (usually 15-60 minutes)
- Railway will show a status: "Pending" → "Active" → "Live"
- SSL certificate is **automatic** once DNS is verified! 🔒

### Step 6: Verify It's Working

1. Check Railway dashboard - domain should show "Active" or "Live"
2. Visit your domain in browser
3. You should see your app, and the lock icon (🔒) means SSL is working!

## Common DNS Providers Setup

### GoDaddy:
1. Go to **My Products** → Click on your domain → **DNS**
2. Add Record:
   - Type: `CNAME`
   - Name: `www`
   - Value: Railway's target URL
   - TTL: 600 seconds

### Namecheap:
1. **Domain List** → Manage → **Advanced DNS**
2. Add New Record:
   - Type: `CNAME Record`
   - Host: `www`
   - Value: Railway's target URL
   - TTL: Automatic

### Cloudflare:
1. Go to your domain → **DNS** → **Records**
2. Add Record:
   - Type: `CNAME`
   - Name: `www`
   - Target: Railway's target URL
   - Proxy status: DNS only (orange cloud OFF) initially
   - Then turn on proxy (orange cloud ON) for Cloudflare protection

### Google Domains:
1. **DNS** → **Custom resource records**
2. Add:
   - Name: `www`
   - Type: `CNAME`
   - Data: Railway's target URL
   - TTL: 3600

## Troubleshooting

**Domain shows "Pending" for a long time?**
- Check DNS records are correct
- Use `nslookup yourdomain.com` to verify DNS propagation
- Make sure TTL is set correctly (don't use 0)

**SSL certificate not working?**
- Railway handles this automatically
- Wait 10-15 minutes after DNS is active
- Try accessing via https:// (Railway forces HTTPS)

**App not loading?**
- Check Railway logs in the dashboard
- Verify environment variables are set
- Make sure app is running (green status in Railway)

## Your Railway URL vs Custom Domain

- **Railway URL**: `your-project.railway.app` (free, works immediately)
- **Custom Domain**: `yourdomain.com` (needs DNS setup, but it's yours!)

Both can work at the same time - users can access via either URL!

## Summary

1. ✅ Deploy app to Railway
2. ✅ Add environment variables
3. ✅ Add custom domain in Railway settings
4. ✅ Update DNS records at your domain registrar
5. ✅ Wait for DNS propagation (15-60 min usually)
6. ✅ SSL certificate auto-generates
7. ✅ Done! Your app is live on your domain! 🎉

Need help with a specific step? Let me know!

