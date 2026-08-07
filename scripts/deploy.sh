#!/bin/bash
# ============================================================
# toflower 博客 · 自动部署脚本
# 由 GitHub Webhook 触发,执行代码更新与项目重启
# 以 www 用户权限运行(gunicorn 以 www 启动,项目目录/venv 均属 www)
# ============================================================

PROJECT_DIR=/www/wwwroot/blog-Django
LOG_FILE=/www/wwwroot/blog-Django/.aiproject/deploy.log
BRANCH=main

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 部署开始 (user: $(whoami)) =====" >> "$LOG_FILE"

cd "$PROJECT_DIR" || { echo "项目目录不存在" >> "$LOG_FILE"; exit 1; }

# 1. 拉取最新代码
echo "[1/5] git pull..." >> "$LOG_FILE"
git checkout "$BRANCH" >> "$LOG_FILE" 2>&1
git pull origin "$BRANCH" >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
    echo "git pull 失败,终止部署" >> "$LOG_FILE"
    exit 1
fi

# 2. 安装依赖(如有变更)
echo "[2/5] pip install..." >> "$LOG_FILE"
venv/bin/pip install -r requirements.txt -q --only-binary :all: >> "$LOG_FILE" 2>&1

# 3. 数据库迁移
echo "[3/5] migrate..." >> "$LOG_FILE"
venv/bin/python manage.py migrate --noinput >> "$LOG_FILE" 2>&1

# 4. 收集静态文件
echo "[4/5] collectstatic..." >> "$LOG_FILE"
venv/bin/python manage.py collectstatic --noinput >> "$LOG_FILE" 2>&1

# 5. 重启 gunicorn(带新静态版本号,让浏览器拉取新 CSS/JS)
echo "[5/5] restart gunicorn..." >> "$LOG_FILE"
export STATIC_VERSION=$(date +%s)
bash "$PROJECT_DIR/scripts/stop.sh" >> "$LOG_FILE" 2>&1
sleep 1
if ! bash "$PROJECT_DIR/scripts/start.sh" >> "$LOG_FILE" 2>&1; then
    echo "gunicorn 启动失败(端口未监听),部署未完全生效" >> "$LOG_FILE"
    exit 1
fi

echo "===== $(date '+%Y-%m-%d %H:%M:%S') 部署完成 =====" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"
exit 0
