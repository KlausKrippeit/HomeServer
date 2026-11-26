import os

bind = "0.0.0.0:" + os.getenv("PORT", "8080")
workers = int(os.getenv("WEB_CONCURRENCY", "4"))
threads = int(os.getenv("THREADS", "2"))
worker_class = "sync"
timeout = 120
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "debug")
