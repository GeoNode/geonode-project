# gunicorn.conf.py
import multiprocessing
import os

bind = "0.0.0.0:8000"

wsgi_app = "geonode_project.wsgi:application"
chdir = "/usr/src/project/"

workers = multiprocessing.cpu_count() * 2 + 1  
threads = 4   

worker_class = "gthread"

max_requests = 1000
max_requests_jitter = 50
max_requests_lifetime = 360
limit_request_fields = 0 # Security flag limit reset
limit_request_field_size = 32768

timeout = 600
graceful_timeout = 60

accesslog = "/var/log/geonode.log"
errorlog = "/var/log/geonode.log"
loglevel = "info"

pidfile = "/tmp/geonode.pid"

# --- Development Auto-Reload ---
# CRITICAL: Set to False in production. Use `kill -HUP $(cat /tmp/geonode.pid)` to reload code safely.
reload = False 
reload_extra_files = [
    "/usr/src/project/geonode_project/reload.py",
]