"""Gunicorn 配置文件。用法:gunicorn -c deploy/gunicorn_config.py toflower_blog.wsgi:application"""

import multiprocessing
import os

# 项目根目录的绝对路径(生产环境)
BASE_DIR = '/var/www/toflower_blog'

# Unix socket(配合 Nginx)
bind = f'unix:{BASE_DIR}/run/gunicorn.sock'
# 同时监听 TCP(可选,便于调试)
# bind = '127.0.0.1:8000'

# Worker 数量:CPU 核数 × 2 + 1
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'      # 同步 worker,Django 默认足够
timeout = 60               # 请求超时(秒)
keepalive = 5              # 长连接保持

# 并发与性能
max_requests = 1000        # 每个 worker 处理 1000 请求后重启(防内存泄漏)
max_requests_jitter = 50
preload_app = True         # 预加载应用,节省内存

# 进程权限
umask = 0o007              # socket 文件权限 770

# 日志
accesslog = f'{BASE_DIR}/logs/gunicorn_access.log'
errorlog = f'{BASE_DIR}/logs/gunicorn_error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# 安全
capture_output = True
enable_stdio_inheritance = False

# 优雅关闭
graceful_timeout = 30
