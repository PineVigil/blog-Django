#!/bin/bash
# toflower 博客 - gunicorn 停止脚本
# 由宝塔面板 AI 项目管理调用
# 按进程命令行匹配清理,不依赖 pid 文件,避免 pid 失效导致旧进程残留

PID_FILE=/www/wwwroot/blog-Django/.aiproject/blog_django.pid
PATTERN="gunicorn.*toflower_blog.wsgi"

echo "stopping gunicorn (pattern: $PATTERN)..."

# 1. 先尝试按 pid 文件停止
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null
        sleep 1
    fi
fi

# 2. 按命令行模式清理所有匹配进程(不依赖 pid 文件)
pkill -f "$PATTERN" 2>/dev/null
sleep 1

# 3. 若仍有残留则强制清理
if pgrep -f "$PATTERN" >/dev/null 2>&1; then
    echo "force killing remaining..."
    pkill -9 -f "$PATTERN" 2>/dev/null
    sleep 1
fi

rm -f "$PID_FILE"

# 4. 校验端口是否释放
if ss -ltn 2>/dev/null | grep -q ':8000 '; then
    echo "WARNING: port 8000 still in use"
    exit 1
fi
echo "gunicorn stopped, port 8000 released"
exit 0
