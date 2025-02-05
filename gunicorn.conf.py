# gunicorn.conf.py
import os
bind = "0.0.0.0:" + os.environ.get("PORT", "5000")
workers = 2
threads = 4
timeout = 120
worker_class = "gevent"
accesslog = "-"
errorlog = "-"
preload_app = True
max_requests = 1000
max_requests_jitter = 50
