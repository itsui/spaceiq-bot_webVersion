# SpaceIQ Desk Booking Bot - Web Version

A production-ready, multi-user web application for automated SpaceIQ desk booking with browser automation, real-time monitoring, and comprehensive security features.

## Overview

SpaceIQ Bot Web Version is a Flask-based multi-user platform that automates desk booking on SpaceIQ using Playwright browser automation. It features user authentication, encrypted session storage, concurrent bot execution, and real-time progress monitoring.

### Key Features

- **Multi-User Support**: Concurrent bot execution with complete user isolation
- **Web Interface**: Flask-based dashboard with real-time updates
- **Secure Authentication**:
  - User accounts with password hashing
  - Encrypted SpaceIQ session storage per user
  - SSO integration support
- **Smart Booking Engine**:
  - Multi-date booking workflows
  - Computer vision-based desk detection
  - Intelligent retry logic with configurable wait times
  - Polling mode for high-demand desks
- **Production Ready**:
  - Rate limiting and security headers
  - Cloudflare tunnel support for remote access
  - Comprehensive logging and monitoring
  - Database migrations and user management
- **User Isolation**: Thread-safe execution preventing cross-user interference

## Quick Start

### Prerequisites

- Python 3.10+
- Internet connection
- Access to your company's SpaceIQ instance

### Windows Setup

```batch
# 1. Clone the repository
git clone https://github.com/itsui/spaceiq-bot_webVersion.git
cd spaceiq-bot_webVersion

# 2. Run production setup
setup_production.bat

# 3. Edit .env file with the generated SECRET_KEY
notepad .env

# 4. Check if everything is ready
check_ready.bat

# 5. Start the application
start_app_production.bat
```

### Linux/Mac Setup

```bash
# 1. Clone the repository
git clone https://github.com/itsui/spaceiq-bot_webVersion.git
cd spaceiq-bot_webVersion

# 2. Run production setup
chmod +x setup_production.sh
./setup_production.sh

# 3. Edit .env file with the generated SECRET_KEY
nano .env

# 4. Check if everything is ready
chmod +x check_ready.sh
./check_ready.sh

# 5. Start the application
chmod +x start_app_production.sh
./start_app_production.sh
```

Access the application at `http://localhost:5000`

## Installation

### 1. Install Dependencies

```bash
# For web interface with multi-user support
pip install -r requirements_production.txt

# For single-user CLI mode
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
python -m playwright install chromium
```

### 3. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
# Generate a strong secret key
python -c "import secrets; print(secrets.token_hex(32))"
```

Edit `.env`:

```env
SECRET_KEY=your-generated-secret-key
FLASK_ENV=production
FLASK_DEBUG=0
SPACEIQ_URL=https://your-spaceiq-instance.com
HEADLESS=false
```

See [.env.example](.env.example) for all configuration options.

## Configuration

### Core Settings

- **SPACEIQ_URL**: Your company's SpaceIQ instance URL
- **HEADLESS**: Browser visibility (false for debugging, true for production)
- **BOOKING_TODAY_CUTOFF_HOUR/MINUTE**: Cutoff time for today's bookings

### Security Settings

- **SECRET_KEY**: Flask session encryption key (required for production)
- **SUPABASE_URL/ANON_KEY**: Optional user whitelisting and usage tracking
- **DEV_MODE**: Enable only for development (allows skipping validation)

### Logging Settings

- **ENABLE_CONSOLE_LOGGING**: Capture all UI output (can be large)
- **STRIP_ANSI_FROM_LOGS**: Remove color codes (saves 80% space)
- **MAX_CONSOLE_LOG_SIZE_MB**: Log rotation threshold
- **SCREENSHOT_RETENTION**: Number of screenshot sessions to keep

## Usage

### Web Interface (Multi-User)

1. **Register an Account**
   - Navigate to `http://localhost:5000`
   - Click "Register" and create your account

2. **Authenticate with SpaceIQ**
   - Log in to the web interface
   - Click "Authenticate with SpaceIQ"
   - Complete SSO login in the browser window
   - Session is captured and encrypted automatically

3. **Configure Bot Settings**
   - Set building, floor, and desk preferences
   - Select dates to book
   - Configure booking strategy (smart booking vs polling)

4. **Start Bot**
   - Click "Start Bot" to begin automated booking
   - Monitor real-time progress in the dashboard
   - View booking history and logs

### CLI Mode (Single-User)

```bash
# Multi-date booking
python multi_date_book.py

# Session warming (initial authentication)
python auto_warm_session.py

# SpaceIQ authentication capture
python spaceiq_auth_capture.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-User Web Platform                  │
├─────────────────────────────────────────────────────────────┤
│  Flask App (app.py)                                         │
│  ├── User Authentication (Flask-Login)                      │
│  ├── API Endpoints (@login_required)                       │
│  ├── Real-time Updates (WebSocket)                          │
│  └── Bot Management Interface                               │
├─────────────────────────────────────────────────────────────┤
│  Bot Manager (bot_manager.py)                               │
│  ├── Thread-Safe Orchestration                             │
│  ├── Per-User Bot Workers                                  │
│  ├── Session File Management                               │
│  └── Progress Reporting                                     │
├─────────────────────────────────────────────────────────────┤
│  Database Layer (models.py)                                 │
│  ├── User (Accounts & Authentication)                       │
│  ├── SpaceIQSession (Encrypted Auth Data)                  │
│  ├── BotConfig (Per-User Settings)                         │
│  ├── BotInstance (Runtime Status)                           │
│  └── BookingHistory (Historical Records)                    │
├─────────────────────────────────────────────────────────────┤
│  Bot Engine (Per User Thread)                               │
│  ├── SessionManager - Multi-user session isolation          │
│  ├── BookingEngine - Advanced booking workflows             │
│  ├── SpaceIQPage - Page automation logic                   │
│  ├── MultiDateBooking - Multi-date workflows               │
│  └── AuthEncryption - Session encryption                    │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

- **src/auth/**: Authentication and session management
- **src/pages/**: Playwright page automation
- **src/workflows/**: Booking workflow implementations
- **src/core/**: Core booking engine
- **src/adapters/**: Unified booking adapter
- **src/reporters/**: Progress reporting (console and web)
- **src/utils/**: Utilities (logging, encryption, date calculation)

## Security Features

- **User Authentication**: Flask-Login with bcrypt password hashing
- **Session Encryption**: Per-user encrypted SpaceIQ session storage (Fernet)
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **XSS Protection**: Flask template auto-escaping
- **CSRF Protection**: Built-in Flask CSRF tokens
- **Path Traversal Prevention**: Username sanitization in file paths
- **Rate Limiting**: Configurable limits per endpoint
- **Security Headers**: XSS, clickjacking, and MIME-sniffing protection
- **ProxyFix Middleware**: Proper header handling behind reverse proxies

See [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md) for detailed security analysis.

## Remote Deployment

### Cloudflare Tunnel (Recommended)

```bash
# Windows
quick-tunnel.bat

# Linux/Mac
./quick-tunnel.sh
```

This provides:
- HTTPS encryption (automatic)
- No port forwarding required
- Easy sharing with temporary URLs

### Production Deployment

See [DEPLOYMENT_CHANGES.md](DEPLOYMENT_CHANGES.md) and [MULTI_USER_DEPLOYMENT_REPORT.md](MULTI_USER_DEPLOYMENT_REPORT.md) for:
- Systemd service setup (Linux)
- Windows service configuration
- Nginx reverse proxy setup
- Cloudflare tunnel permanent configuration
- Database management
- User migration

## Troubleshooting

### Common Issues

**"SECRET_KEY not set" error**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Copy output to .env as SECRET_KEY=...
```

**"Port 5000 already in use"**
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :5000
kill <PID>
```

**"cloudflared not found"**
- Windows: `winget install Cloudflare.cloudflared`
- Mac: `brew install cloudflared`
- Linux: See [Cloudflare docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/)

**Flask-Limiter not installed**
```bash
pip install -r requirements_production.txt
```

### Diagnostic Tools

```bash
# Check production readiness
python check_production_ready.py

# Run setup checker
python check_setup.py

# Check database migrations
python migrate_database.py --check
```

## Documentation

- [QUICK_START_REMOTE.md](QUICK_START_REMOTE.md) - Remote testing setup guide
- [REMOTE_TESTING_GUIDE.md](REMOTE_TESTING_GUIDE.md) - Comprehensive remote deployment
- [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md) - Security analysis and fixes
- [SECURITY_FIXES_SUMMARY.md](SECURITY_FIXES_SUMMARY.md) - Security improvements summary
- [DEPLOYMENT_CHANGES.md](DEPLOYMENT_CHANGES.md) - Production deployment changes
- [MULTI_USER_DEPLOYMENT_REPORT.md](MULTI_USER_DEPLOYMENT_REPORT.md) - Multi-user deployment guide

## Project Structure

```
spaceiq-bot_webVersion/
├── app.py                      # Main Flask application
├── bot_manager.py              # Multi-user bot orchestration
├── models.py                   # Database models
├── config.py                   # Configuration management
├── requirements_production.txt # Production dependencies
├── src/
│   ├── auth/                  # Authentication modules
│   ├── pages/                 # Page automation
│   ├── workflows/             # Booking workflows
│   ├── core/                  # Core booking engine
│   ├── adapters/              # Unified booking adapter
│   ├── reporters/             # Progress reporters
│   └── utils/                 # Utilities
├── templates/                 # HTML templates
├── static/                    # CSS and JavaScript
├── config/                    # Configuration files
├── logs/                      # Application logs
└── playwright/.auth/          # Encrypted session storage
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is private and proprietary. All rights reserved.

## Support

For issues and questions:
1. Run diagnostics: `python check_production_ready.py`
2. Check logs: `logs/app.log` and `logs/booking_*.log`
3. Review documentation in the project root

## Acknowledgments

- Built with [Playwright](https://playwright.dev/) for browser automation
- [Flask](https://flask.palletsprojects.com/) for web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) for database ORM
- [Cryptography](https://cryptography.io/) for session encryption
