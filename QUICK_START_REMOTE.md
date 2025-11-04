# 🚀 Quick Start: Remote Testing Setup

This guide will help you set up your SpaceIQ Bot for remote testing in **under 10 minutes**.

---

## 📋 Prerequisites

- Python 3.10+ installed
- Internet connection
- 15 minutes of time

---

## ⚡ Quick Setup (Choose Your OS)

### Windows:

```batch
# 1. Run production setup
setup_production.bat

# 2. Edit .env file with the generated SECRET_KEY
# (Open .env in notepad and paste the key from step 1)

# 3. Check if everything is ready
check_ready.bat

# 4. Start the Flask app (in one terminal)
start_app_production.bat

# 5. Start the Cloudflare tunnel (in another terminal)
quick-tunnel.bat
```

### Linux/Mac:

```bash
# 1. Run production setup
./setup_production.sh

# 2. Edit .env file with the generated SECRET_KEY
# nano .env (or use your preferred editor)

# 3. Check if everything is ready
./check_ready.sh

# 4. Start the Flask app (in one terminal)
./start_app_production.sh

# 5. Start the Cloudflare tunnel (in another terminal)
./quick-tunnel.sh
```

---

## 🔗 Share with Your Friend

After running the tunnel, you'll get a URL like:

```
https://random-name.trycloudflare.com
```

Send this to your friend along with:

```
🔗 Test URL: https://your-tunnel-url.trycloudflare.com

📝 Instructions:
1. Open the URL in your browser
2. Click "Register" to create an account
3. Click "Authenticate with SpaceIQ"
4. Login with your SpaceIQ credentials
5. Configure your bot settings
6. Click "Start Bot" and watch it work!

⚠️ Requirements:
- Access to your company's SpaceIQ instance
- Valid SpaceIQ credentials
```

---

## 🛑 When You're Done

Press `Ctrl+C` in both terminal windows to stop:
1. The Cloudflare tunnel
2. The Flask app

---

## 🔧 Troubleshooting

### "SECRET_KEY not set" error
Edit `.env` file and add a strong secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output to your `.env` file as `SECRET_KEY=...`

### "Port 5000 already in use"
Another process is using port 5000. Find and stop it:
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :5000
kill <PID>
```

### "cloudflared not found"
Install Cloudflare tunnel client:
- **Windows**: `winget install Cloudflare.cloudflared`
- **Mac**: `brew install cloudflared`
- **Linux**: See [installation guide](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/)

### "Flask-Limiter not installed"
Install updated dependencies:
```bash
pip install -r requirements_production.txt
```

### Friend can't register (Supabase whitelist)
You have two options:

**Option 1: Add them to whitelist (recommended)**
1. Go to your Supabase dashboard
2. Add their username to the whitelist table
3. Ask them to register again

**Option 2: Temporarily disable validation (testing only)**
Edit `app.py` around line 139-144 and comment out the validation:
```python
# Validate against Supabase whitelist (if configured)
# from src.utils.supabase_validator import validate_user_and_log
# is_valid, error_msg = validate_user_and_log(username)
# if not is_valid:
#     flash(f'Access denied: {error_msg}...', 'danger')
#     return render_template('register.html')
```

---

## 📚 Need More Details?

See the comprehensive guide: [REMOTE_TESTING_GUIDE.md](REMOTE_TESTING_GUIDE.md)

---

## ✅ Security Checklist

Before sharing your URL, verify:

- ✅ `FLASK_ENV=production` in `.env`
- ✅ `FLASK_DEBUG=0` in `.env`
- ✅ Strong `SECRET_KEY` set in `.env`
- ✅ Rate limiting enabled (automatic)
- ✅ HTTPS enabled (automatic via Cloudflare)

All security features are configured automatically! 🎉

---

## 🎯 What's Been Set Up

Your bot now has:

1. **Security Enhancements**
   - ProxyFix middleware for Cloudflare headers
   - Secure secret key handling
   - Security headers (XSS, clickjacking protection)
   - Rate limiting (5 registrations/hour, 10 logins/hour)

2. **Production Configuration**
   - Environment-based configuration
   - Automatic debug mode disabling in production
   - Proper error handling

3. **Deployment Tools**
   - Quick setup scripts
   - Production readiness checker
   - Tunnel configuration templates
   - One-command deployment

---

## 🆘 Support

Having issues? Check:
1. Run `check_ready.bat` (Windows) or `./check_ready.sh` (Unix) to diagnose problems
2. Review [REMOTE_TESTING_GUIDE.md](REMOTE_TESTING_GUIDE.md) for detailed troubleshooting
3. Check logs in `logs/app.log`

---

**Happy Testing! 🚀**
