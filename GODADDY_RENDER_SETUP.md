# Connect GoDaddy Domain to Render

## Step-by-Step Instructions

### Step 1: Get Your Render URL
1. In Render dashboard, go to your service
2. Look at the top - you'll see your URL like: `points-lotto.onrender.com`
3. **Copy this URL** - you'll need it!

### Step 2: Add Domain in Render
1. In Render → Your Service → Click **"Settings"** tab
2. Scroll down to **"Custom Domains"** section
3. Click **"Add Custom Domain"**
4. Enter your domain: `yourdomain.com` (or `www.yourdomain.com`)
5. Render will show you DNS instructions - take note of what they tell you

### Step 3: Configure GoDaddy DNS

#### Go to GoDaddy DNS Management:
1. Go to **godaddy.com** and sign in
2. Click **"My Products"** (or "Domains" in new interface)
3. Find your domain → Click **"DNS"** button (or "Manage DNS")

#### Add CNAME Record for WWW:
1. In DNS Management, scroll to **"Records"** section
2. Click **"Add"** or **"Add Record"**
3. Set up:
   - **Type**: `CNAME`
   - **Name**: `www`
   - **Value**: `points-lotto.onrender.com` (your Render URL from Step 1)
   - **TTL**: `1 hour` (or 600 seconds)
4. Click **"Save"**

#### For Root Domain (yourdomain.com without www):

**Option A: Domain Forwarding (Easiest)**
1. In GoDaddy, go to your domain settings
2. Find **"Forwarding"** section
3. Click **"Add Forwarding"**
4. Set:
   - **Domain**: `yourdomain.com` (leave blank or @)
   - **Forward to**: `https://www.yourdomain.com`
   - **Type**: `301 - Permanent`
   - **Settings**: `Forward Only` (not masking)
5. Save

**Option B: A Record (If Render Provides IP)**
1. In DNS Records, click **"Add"**
2. Set up:
   - **Type**: `A`
   - **Name**: `@` (or leave blank)
   - **Value**: [IP address Render gives you]
   - **TTL**: `1 hour`
3. Save

### Step 4: Wait for DNS Propagation
- DNS changes take **15-60 minutes** to propagate
- You can check status in Render dashboard (Custom Domains section)
- Status will show: "Pending" → "Active" → "Live"

### Step 5: SSL Certificate
- Render **automatically** issues SSL certificates (free!)
- This happens automatically once DNS is verified
- Takes about 10-15 minutes after DNS is active
- You'll see a lock icon (🔒) when it's ready

### Step 6: Test Your Domain
1. Wait 30-60 minutes for DNS to propagate
2. Visit `https://www.yourdomain.com`
3. You should see your pointslottery site!
4. Try `https://yourdomain.com` (should forward to www version)

## Troubleshooting

**Domain shows "Pending" for a long time?**
- Check DNS records are correct (no typos in CNAME value)
- Make sure TTL isn't set to 0
- Try accessing via `nslookup yourdomain.com` in terminal

**SSL not working?**
- Wait 15 minutes after DNS is active
- Make sure you're using `https://` not `http://`
- Check Render dashboard shows "SSL Active"

**Site not loading?**
- Check Render service is running (green status)
- Verify DNS records are saved correctly
- Try clearing browser cache

## Quick Checklist

- [ ] Got Render URL (e.g., `points-lotto.onrender.com`)
- [ ] Added domain in Render settings
- [ ] Added CNAME record for `www` → Render URL
- [ ] Set up forwarding or A record for root domain
- [ ] Waited 30-60 minutes for DNS propagation
- [ ] Tested domain in browser
- [ ] SSL certificate is active (lock icon)

## Your Setup Should Look Like:

**GoDaddy DNS Records:**
```
Type    Name    Value                        TTL
CNAME   www     points-lotto.onrender.com    1 hour
A       @       [Render IP if provided]     1 hour
```

**Or with Forwarding:**
```
Type    Name    Value                        TTL
CNAME   www     points-lotto.onrender.com    1 hour
(Forward @ → https://www.yourdomain.com)
```

That's it! Your domain will work with Render! 🎉

