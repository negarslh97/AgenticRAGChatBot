# Gunicorn configuration file for SallyBot Backend

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# Timeout settings
timeout = 300  # 5 minutes - increased for long-running operations and streaming
keepalive = 2

# Restart workers after serving a certain number of requests
max_requests = 1000
max_requests_jitter = 50

# Graceful timeout
graceful_timeout = 30

# Worker lifecycle
preload_app = False
worker_tmp_dir = None

# Logging
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'
log_level = "info"

# Process naming
proc_name = "sallybot-backend"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
ssl_version = None
cert_reqs = None
ca_certs = None
certfile = None
keyfile = None
ciphers = None

# Advanced settings for streaming support
worker_timeout = 300
worker_shutdowm = 30
worker_int_1 = 10
worker_int_2 = 10

# HTTP settings for better streaming support
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190