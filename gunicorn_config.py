"""
Gunicorn configuration for production deployment
"""

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 4  # Number of CPU cores or (2 * CPU cores) + 1
worker_class = "sync"  # Use sync workers for compatibility
worker_connections = 1000
timeout = 300  # 5 minutes (long enough for booking operations)
keepalive = 5

# Server mechanics
max_requests = 1000  # Restart workers after 1000 requests
max_requests_jitter = 100  # Random variation in restart timing
preload_app = True  # Load app before forking workers

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "spaceiq-bot"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Graceful shutdown
graceful_timeout = 300
worker_exit_timeout = 300

# SSL (if you have certificates)
# keyfile = "/path/to/private.key"
# certfile = "/path/to/certificate.crt"