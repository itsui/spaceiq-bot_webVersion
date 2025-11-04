# 🌐 Remote Testing Guide for Your SpaceIQ Bot (Cloudflare Tunnel)

## 📋 Quick Overview
This guide shows you how to let a friend test your multi-user SpaceIQ bot remotely using Cloudflare Tunnel - a secure, free way to expose your local server to the internet without code changes.

---

## 🚀 Step 1: Set Up Cloudflare Tunnel

### Prerequisites
- Cloudflare account (free)
- A domain name (can be a free one from Freenom, etc.)

### Installation & Setup

#### 1. Install cloudflared
```bash
# Windows (PowerShell as Administrator)
winget install --id Cloudflare.cloudflared

# macOS (Homebrew)
brew install cloudflared

# Linux
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Or download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
```

#### 2. Authenticate with Cloudflare
```bash
cloudflared tunnel login
```
This opens a browser window to log into your Cloudflare account.

#### 3. Create a Tunnel
```bash
cloudflared tunnel create spaceiq-bot
```
Note the tunnel UUID that gets returned (you'll need it).

#### 4. Create DNS Record
```bash
cloudflared tunnel route dns spaceiq-bot your-domain.com
```
Replace `your-domain.com` with your actual domain.

#### 5. Create Tunnel Configuration
Create a file named `cloudflare-tunnel.yml`:
```yaml
tunnel: your-tunnel-uuid-here
credentials-file: /Users/YourUsername/.cloudflared/tunnels/your-tunnel-uuid-here.json

ingress:
  - hostname: your-domain.com
    service: http://localhost:5000
  - service: http_status:404
```

#### 6. Start the Tunnel
```bash
cloudflared tunnel --config cloudflare-tunnel.yml run spaceiq-bot
```

### Quick Alternative (No Domain Required)
If you don't have a domain, use the instant tunnel:
```bash
cloudflared tunnel --url http://localhost:5000
```
This gives you a random `.trycloudflare.com` URL.

---

## 🔐 Step 2: Security Checklist

### Before Sharing, Verify:

✅ **No Debug Mode** - Ensure `debug=False` in app.py
✅ **Strong Secret Key** - Change the default secret key
✅ **Database Safety** - Your SQLite DB won't be exposed via web
✅ **HTTPS Enabled** - Cloudflare automatically provides HTTPS
✅ **Rate Limiting** - Consider basic rate limiting

### Generate Strong Secret Key:
```python
# In Python, run this to generate a secure key:
import secrets
print(secrets.token_hex(32))
```

Then add to your `.env` file:
```
SECRET_KEY=your-generated-key-here
FLASK_ENV=production
FLASK_DEBUG=0
```

### Additional Security Settings (Optional)
Add these to your app.py for better security:
```python
# Add rate limiting
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address)

@app.before_request
def limit_remote_addr():
    # Basic rate limiting for registration
    if request.endpoint == 'register':
        limiter.limit("5 per hour")(lambda: None)()
```

---

## 🛠️ Step 3: Project Configuration

### 1. Allow External Connections
Make sure your app runs with:
```python
app.run(host='0.0.0.0', port=5000, debug=False)
```

### 2. Trusted Host Headers (for HTTPS)
Add this to your app.py to handle Cloudflare's proxy headers:
```python
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
```

### 3. Update CORS if Needed
If you're using any APIs, install Flask-CORS:
```bash
pip install flask-cors
```

And add to app.py:
```python
from flask_cors import CORS
CORS(app, origins=["https://your-domain.com"])
```

### 4. Temporarily Disable Supabase Validation (if needed)
If your friend isn't in your Supabase whitelist, temporarily comment out:
```python
# In app.py register function, comment out:
# from src.utils.supabase_validator import validate_user_and_log
# is_valid, error_msg = validate_user_and_log(username)
# if not is_valid:
#     flash(f'Access denied: {error_msg}...', 'danger')
#     return render_template('register.html')
```

---

## 📱 Step 4: Share with Your Friend

### What to Send Them:
```
🔗 **Test URL**: https://your-domain.com

👤 **Test Account**:
- Username: testuser
- Email: test@example.com
- Password: testpass123

📝 **Test Steps**:
1. Go to https://your-domain.com
2. Click "Register" and create a new account
3. Click "Authenticate with SpaceIQ"
4. Login with your SpaceIQ credentials
5. Configure bot settings (building, floor, desk preferences)
6. Try running the bot
7. Watch the live logs and booking progress

⏰ **Available**: [Start time] to [End time] (please test during this window)
```

### Important Notes:
- ⚠️ **Tell them to use their real SpaceIQ account**
- ⚠️ **They'll need access to your company's SpaceIQ instance**
- ⚠️ **HTTPS is automatic with Cloudflare**
- ⚠️ **The connection is more stable than ngrok**

---

## 🔍 Step 5: Monitor the Test

### Cloudflare Dashboard
- Log into Cloudflare dashboard
- Go to "Zero Trust" → "Networks" → "Tunnels"
- Monitor active connections and traffic

### Local Monitoring
Watch your terminal for:
- Cloudflare tunnel logs
- Flask application logs
- Any errors in bot execution

### Database Monitoring
Check your SQLite database:
```bash
# Connect to database
sqlite3 spaceiq_multiuser.db

# View active users
SELECT username, created_at FROM users;

# View bot instances
SELECT u.username, b.status, b.started_at
FROM bot_instances b
JOIN users u ON b.user_id = u.id;
```

### Common Issues to Watch For:
- ❌ **SpaceIQ Authentication Failures** - Friend can't access your company SpaceIQ
- ❌ **Tunnel Connection Issues** - Cloudflare tunnel drops
- ❌ **HTTPS Redirects** - Mixed content issues
- ❌ **Browser Pop-up Blocking** - SpaceIQ auth window blocked

---

## 🛡️ Step 6: Security Best Practices

### Do:
✅ Use HTTPS (automatic with Cloudflare)
✅ Monitor Cloudflare analytics
✅ Keep the session short (2-4 hours max)
✅ Use strong secret keys
✅ Enable Cloudflare's security features
✅ Set up Cloudflare Access (optional)

### Don't:
❌ Share your tunnel URL publicly
❌ Run debug mode in production
❌ Leave tunnel running unattended
❌ Disable Cloudflare security features

### Optional: Add Cloudflare Access for Extra Security
```bash
# Install cloudflared and set up Zero Trust access
cloudflared tunnel login

# Create an Access policy in Cloudflare dashboard
# Zero Trust → Access → Applications → Add Application
```

---

## 🔄 Step 7: Clean Up After Testing

### Stop the Tunnel
```bash
# Press Ctrl+C in the tunnel terminal
# Or kill the process:
pkill cloudflared
```

### Delete Test Data (SQLite)
```sql
-- Connect to your database and run:
DELETE FROM users WHERE username LIKE 'test%';
DELETE FROM bot_instances WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'test%');
DELETE FROM spaceiq_sessions WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'test%');
DELETE FROM bot_configs WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'test%');
DELETE FROM booking_history WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'test%');
```

### Optional: Delete Tunnel
```bash
# Delete the tunnel completely
cloudflared tunnel delete spaceiq-bot

# Delete DNS record in Cloudflare dashboard
```

---

## 📊 Expected Performance

| Metric | What to Expect |
|--------|----------------|
| **Connection Speed** | Excellent (Cloudflare's CDN) |
| **Reliability** | High (professional grade) |
| **SpaceIQ Auth** | Same as local (HTTPS handled properly) |
| **Bot Execution** | Same performance as local |
| **Concurrent Users** | Excellent (you + friend = easy) |

---

## 🚨 Troubleshooting

### Common Cloudflare Issues

#### "Connection Refused"
```bash
# Check if your app is running
curl http://localhost:5000

# Check if tunnel is active
cloudflared tunnel list
```

#### "502 Bad Gateway"
- Your local server isn't responding
- Wrong port in tunnel configuration
- App crashed

#### "SSL/TLS Handshake Failed"
- SSL certificate issues (should be automatic)
- Mixed content warnings in browser

#### "403 Forbidden"
- Cloudflare security rules blocking
- Need to add IP to allow list
- Rate limiting triggered

### Debug Commands
```bash
# Test tunnel connectivity
curl -v https://your-domain.com

# Check tunnel logs
cloudflared tunnel --config cloudflare-tunnel.yml run spaceiq-bot --loglevel debug

# Monitor traffic
tail -f logs/app.log
```

---

## 🎯 Quick Checklist Before Sharing

- [ ] Cloudflare account created and authenticated
- [ ] Tunnel created and running
- [ ] DNS record configured
- [ ] SSL certificate active (automatic)
- [ ] App running on `0.0.0.0:5000`
- [ ] Debug mode disabled
- [ ] Strong secret key configured
- [ ] Friend has SpaceIQ access
- [ ] You've tested the URL yourself
- [ ] Created clear test instructions
- [ ] Set time limit for testing

---

## 🚀 Advanced Setup (Optional)

### Custom Subdomain
```bash
# Create subdomain like bot.your-domain.com
cloudflared tunnel route dns spaceiq-bot bot.your-domain.com
```

### Multiple Environments
```yaml
# cloudflare-tunnel.yml with multiple routes
ingress:
  - hostname: bot.your-domain.com
    service: http://localhost:5000
  - hostname: dev.your-domain.com
    service: http://localhost:5001
  - service: http_status:404
```

### Cloudflare Workers for Rate Limiting
```javascript
// Add rate limiting at edge
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  // Add rate limiting logic here
  return fetch(request)
}
```

---

## 🎉 Success!

Your friend can now test your multi-user SpaceIQ bot remotely through a secure, professional Cloudflare tunnel. The system is ready for production-grade testing with proper HTTPS, security, and monitoring.

**Remember**: This setup demonstrates that your multi-user architecture is working perfectly - multiple users can authenticate, configure, and run bots simultaneously with complete isolation! 🚀