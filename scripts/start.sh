#!/bin/bash
# toflower 博客 - gunicorn 启动脚本
# 由宝塔面板 AI 项目管理调用
# 启动后校验进程与端口,确保服务真正可用

cd /www/wwwroot/blog-Django

PID_FILE=/www/wwwroot/blog-Django/.aiproject/blog_django.pid
ACCESS_LOG=/www/wwwroot/blog-Django/.aiproject/access.log
ERROR_LOG=/www/wwwroot/blog-Django/.aiproject/error.log
PATTERN="gunicorn.*toflower_blog.wsgi"

# 若已有进程则先停止(按模式清理,不依赖 pid 文件)
if pgrep -f "$PATTERN" >/dev/null 2>&1 || [ -f "$PID_FILE" ]; then
    bash "$PWD/scripts/stop.sh" >/dev/null 2>&1
    sleep 1
fi

# 后台启动 gunicorn
nohup venv/bin/gunicorn toflower_blog.wsgi:application \
    -b 127.0.0.1:8000 \
    --workers 2 \
    --timeout 60 \
    --access-logfile "$ACCESS_LOG" \
    --error-logfile "$ERROR_LOG" \
    > "$ERROR_LOG" 2>&1 &

echo $! > "$PID_FILE"

# 校验:等待端口监听(最多约5秒)
for i in 1 2 3 4 5; do
    if ss -ltn 2>/dev/null | grep -q ':8000 '; then
        echo "gunicorn started, pid: $(cat $PID_FILE), port 8000 listening"
        exit 0
    fi
    sleep 1
done

echo "ERROR: gunicorn failed to listen on port 8000"
exit 1
