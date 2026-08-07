# toflower 博客 · 服务器部署记录

> 本项目由用户本地开发，部署助手完成服务器端部署。技术栈：Django 5.2 LTS + Python 3.11.9 + MySQL 8.0 + gunicorn + Nginx。

## 环境信息

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.11.9 | 面板安装于 `/www/server/pyporject_evn/versions/3.11.9` |
| Django | 5.2 LTS | venv 内安装 |
| MySQL | 8.0.24 | 用户自行升级安装（原 5.7 升级） |
| gunicorn | 26.0.0 | venv 内安装 |
| Nginx | 1.30.4 | 面板管理 |

## 部署位置

- **项目目录**：`/www/wwwroot/blog-Django`
- **虚拟环境**：`/www/wwwroot/blog-Django/venv`（Python 3.11.9）
- **域名**：`toflower.fun`（绑定 80 端口，反向代理到 127.0.0.1:8000）
- **数据库**：MySQL `toflower_blog`（用户 `toflower`，仅限 127.0.0.1）

## 目录结构（服务器侧新增）

```
/www/wwwroot/blog-Django/
├── venv/                      # Python 3.11.9 虚拟环境
├── .env                       # 生产环境变量（MySQL 连接、DEBUG=False、SECRET_KEY 等）
├── staticfiles/               # collectstatic 输出（Nginx 直接服务）
├── media/                     # 用户上传文件（封面图等）
├── logs/                      # 项目日志目录（保留）
├── scripts/
│   ├── start.sh               # gunicorn 启动脚本（面板 AI 项目调用）
│   └── stop.sh                # gunicorn 停止脚本
└── .aiproject/                # 宝塔 AI 项目管理目录
    ├── ai_config.json         # 项目配置（面板动态识别）
    ├── blog_django.pid        # gunicorn PID
    ├── access.log             # gunicorn 访问日志
    └── error.log              # gunicorn 错误日志
```

## 运行方式

通过宝塔面板「AI 项目管理」控制：

- **启动**：`bash /www/wwwroot/blog-Django/scripts/start.sh`（gunicorn 绑定 127.0.0.1:8000）
- **停止**：`bash /www/wwwroot/blog-Django/scripts/stop.sh`

## Nginx 配置

- 配置文件：`/www/server/panel/vhost/nginx/ai_blog_django.conf`
- `location /` → 反向代理 `http://127.0.0.1:8000`
- `location /static/` → `alias /www/wwwroot/blog-Django/staticfiles/`（30 天缓存）
- `location /media/` → `alias /www/wwwroot/blog-Django/media/`（7 天缓存）

## 访问入口

| 路径 | 说明 |
|------|------|
| `/` | 博客首页 |
| `/dijia/` | 自建管理后台（登录跳转） |
| `/_djadmin/` | Django 原生 admin（隐藏逃生通道） |
| `/feed/rss/` | RSS 订阅 |
| `/sitemap.xml` | 站点地图 |
| `/robots.txt` | robots 文件 |

## 账户信息

- **后台管理员**：`admin` / 初始密码 `Guhu@2026wenhua`（**请登录后立即修改**）
- **MySQL**：库 `toflower_blog`，用户 `toflower`，密码见 `.env`
- **MySQL root**：由用户设置（`b32e842137cfbecc`，仅一次性用于建库授权）

## 部署过程要点

1. 克隆仓库 `git clone https://github.com/PineVigil/blog-Django.git`
2. 面板安装 Python 3.11.9（注意路径：`/www/server/pyporject_evn/versions/`）
3. venv 创建 + 依赖安装（Pillow 需 `--only-binary` 预编译 wheel，因 CentOS 7 gcc 默认 C89）
4. 创建 MySQL 库并配置 `.env`（DEBUG=False）
5. `migrate` + `collectstatic` + 创建超管 + `init_sample_data`（6 篇示例文章）
6. 面板 AI 项目接入（`blog_django`），Nginx 反代配置完成

## 注意事项

- 更新代码：`git pull` 后重启项目（面板 AI 项目管理 → 重启）
- 修改静态文件后需执行：`venv/bin/python manage.py collectstatic --noinput`
- MySQL 8.0 由用户手动安装，root 密码未入库面板，面板数据库操作可能受限
- 当前为 HTTP（80 端口），如需 HTTPS 需申请 SSL 证书（面板可一键申请）
