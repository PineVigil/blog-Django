# toflower 博客部署检查清单

> 在 Ubuntu/Debian 服务器(150.109.76.168)上从零部署的步骤参考。

## 1. 系统准备

```bash
# 安装系统依赖
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
                    mysql-server nginx git curl

# 安装 MySQL 8.0(若未预装;Ubuntu 22.04+ 默认即 8.0)
# 此处假设 MySQL 已就绪
```

## 2. 创建站点目录与用户

```bash
sudo useradd -m -s /bin/bash toflower           # 系统用户
sudo mkdir -p /var/www/toflower_blog
sudo chown -R toflower:www-data /var/www/toflower_blog
```

## 3. 拉取代码 + 虚拟环境

```bash
sudo -u toflower -i
cd /var/www
git clone <your-repo-url> toflower_blog
cd toflower_blog

python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. 配置环境变量

```bash
cp .env.example .env
vim .env    # 填入 DJANGO_SECRET_KEY、DB_PASSWORD 等
```

## 5. 初始化数据库

```bash
# 在服务器上执行(修改 SQL 中的密码!)
sudo mysql -u root -p < deploy/mysql_init.sql
```

## 6. Django 初始化

```bash
# 创建必要目录
mkdir -p run logs media

# 迁移
python manage.py migrate

# 收集静态文件
python manage.py collectstatic --noinput

# 创建超级用户(用于后台 /dijia/)
python manage.py createsuperuser

# (可选)加载示例数据
python manage.py init_sample_data

# 测试 Gunicorn 能否启动
gunicorn --bind 127.0.0.1:8000 toflower_blog.wsgi:application
# Ctrl+C 退出
```

## 7. 配置 Gunicorn 服务(systemd)

```bash
exit    # 回到有 sudo 权限的账号

sudo cp deploy/gunicorn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn
sudo systemctl status gunicorn
```

## 8. 配置 Nginx

```bash
sudo cp deploy/nginx_toflower.conf /etc/nginx/sites-available/toflower.fun
sudo ln -s /etc/nginx/sites-available/toflower.fun /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 9. 申请 HTTPS 证书(Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d toflower.fun -d www.toflower.fun
# 自动续期已配置:cron 或 systemd timer
```

## 10. 防火墙

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 11. 验证

- 访问 `https://toflower.fun/` 应看到博客首页
- 访问 `https://toflower.fun/dijia/` 应看到后台登录页
- `https://toflower.fun/feed/rss/` 输出 RSS
- `https://toflower.fun/sitemap.xml` 输出站点地图

## 常用运维命令

```bash
# 重启 Gunicorn(更新代码后)
sudo systemctl restart gunicorn

# 重载 Nginx(改了配置后)
sudo nginx -t && sudo systemctl reload nginx

# 查看日志
sudo journalctl -u gunicorn -f
sudo tail -f /var/log/nginx/toflower_error.log
tail -f /var/www/toflower_blog/logs/gunicorn_error.log

# 数据库备份
mysqldump -u toflower -p toflower_blog | gzip > backup_$(date +%F).sql.gz
```
