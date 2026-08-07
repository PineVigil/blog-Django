# toflower 博客

> 基于 Django 5.2 LTS 的个人博客,杂志风 Editorial 设计,支持亮/暗双主题。
> 部署目标:toflower.fun (150.109.76.168)

## 技术栈

| 组件 | 版本 |
|------|------|
| Python | 3.11.9 |
| Django | 5.2 LTS |
| 数据库 | MySQL 8.0(开发回退 SQLite) |
| Web 服务器 | Nginx 1.30.4 |
| 应用服务器 | Gunicorn |
| 前端 | HTML5 + CSS3 + 原生 JavaScript |

## 特性

- 杂志风 Editorial 设计:衬线大标题 + 无衬线正文、暖橙强调、纸张噪点纹理
- 亮 / 暗双主题切换(带圆形扩散动画)
- 首页 Hero:可配置背景(壁纸 / 视频 / 光斑)、视差滚动、站酷小微眉题
- 首页功能卡片:实时时钟、天气(反向地理编码显示中文城市)、快捷导航、博客统计、热门 Top3、每日金句
- 每日金句:每日自动抓取在线 API(金山词霸 → 一言 → 本地兜底),归档到专属文章,支持手动刷新(`/quote/fetch/`)
- 合集系统:文章归入合集连载、可调阅读顺序;自建后台支持搜索添加、一键移出、拖拽排序
- 壁纸亮度自适应:JS 提取壁纸平均色,光标 / 导航 / 文字颜色随壁纸与鼠标位置动态变化
- Markdown 写作 + 代码高亮(GitHub 官方风格,随主题自动亮 / 暗切换)
- 文章阅读风格:默认(紧凑排版、铺满页面仅留少量留白) / GitHub README 卡片,后台可设默认值,前台一键切换
- 背景透明度调节:顶栏按钮实时调节壁纸与遮罩透明度(记忆到本地)
- 文章 / 分类 / 标签 / 归档 / 搜索
- 评论系统(支持审核、嵌套回复、Cravatar 头像)
- 浏览量统计、阅读时长估算
- RSS(页脚点击自动复制订阅地址)/ Atom / sitemap.xml / robots.txt
- 自建后台管理 `/dijia/`:文章、合集、评论、Hero 背景、首页字号、关于页
- 首页各区块文字大小可在后台单独调节(字号,共 9 项)
- 关于页内容可在后台以 Markdown 编辑(留空显示默认模板)
- 响应式设计(手机 / 平板 / 桌面)
- 后台路径自定义:`/dijia/`(非默认 `/admin/`)
- GitHub Webhook 自动部署:push 后服务器自动拉取代码并重启
- 环境变量管理敏感配置(`.env`)
- 完整部署配置(Nginx + Gunicorn + systemd + MySQL)

## 快速开始(本地开发)

```bash
# 1. 创建虚拟环境(必须 Python 3.11)
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量(开发可不配,默认走 SQLite)
cp .env.example .env
# 编辑 .env,如不需要 MySQL,留空 DB_HOST 即可

# 4. 数据库迁移
python manage.py migrate

# 5. 创建超级用户
python manage.py createsuperuser

# 6. (可选)加载示例数据
python manage.py init_sample_data

# 7. 启动开发服务器
python manage.py runserver
```

打开浏览器:

- 博客首页:http://127.0.0.1:8000/
- 后台管理:http://127.0.0.1:8000/dijia/  ← 注意是 `dijia`
- RSS:http://127.0.0.1:8000/feed/rss/
- 站点地图:http://127.0.0.1:8000/sitemap.xml

## 项目结构

```
├── manage.py
├── requirements.txt
├── .env.example              # 环境变量模板
├── DEPLOYMENT.md             # 部署文档(含 webhook 自动部署)
├── toflower_blog/            # 项目主目录
│   ├── settings.py           # 配置(.env 加载、MySQL/SQLite 回退、markdown 渲染)
│   ├── urls.py               # 主路由(后台 /dijia/、webhook)
│   ├── webhook.py            # GitHub Webhook 自动部署视图
│   ├── wsgi.py
│   └── asgi.py
├── blog/                     # 博客 APP
│   ├── models.py             # Post/Category/Tag/Comment/Collection/SiteConfig
│   ├── views.py              # 首页/详情/归档/分类/标签/合集/关于/搜索/金句
│   ├── manage_views.py       # 自建后台视图
│   ├── manage_forms.py       # 自建后台表单
│   ├── manage_urls.py        # 自建后台路由
│   ├── admin.py              # Django admin 注册 + 批量操作
│   ├── forms.py              # 评论表单、搜索表单
│   ├── feeds.py              # RSS / Atom
│   ├── sitemaps.py           # 站点地图
│   ├── utils.py              # Markdown 渲染、摘要生成
│   ├── context_processors.py # 注入站点配置(含首页字号)
│   ├── templatetags/         # 自定义模板标签
│   └── management/commands/  # init_sample_data 命令
├── scripts/                  # 部署脚本
│   ├── deploy.sh             # 拉取代码 + 迁移 + 重启
│   ├── start.sh              # 启动 Gunicorn
│   └── stop.sh               # 停止服务
├── templates/                # 前台模板
│   └── manage/               # 自建后台模板
├── static/                   # 静态文件(CSS / JS / favicon)
├── media/                    # 用户上传文件(壁纸等)
└── deploy/                   # Nginx / Gunicorn / MySQL 部署配置
    ├── nginx_toflower.conf
    ├── gunicorn.service
    ├── gunicorn_config.py
    └── mysql_init.sql
```

## 关键配置说明

### 后台路径

后台路径默认为 `/dijia/`,可在 `.env` 中通过 `DJANGO_ADMIN_PATH` 自定义:

```env
DJANGO_ADMIN_PATH=myadmin/      # 则后台为 /myadmin/
```

### 数据库

- **本地开发**:不设置 `DB_HOST`,自动使用 SQLite (`db.sqlite3`)
- **生产**:在 `.env` 中设置 `DB_HOST` / `DB_USER` / `DB_PASSWORD`,使用 MySQL
- 使用 PyMySQL 作为 MySQL 驱动(纯 Python,Windows 无需编译)

### Markdown

- 文章正文与关于页以 Markdown 存储,服务端用 `markdown` 库渲染
- 启用 `codehilite`(代码高亮)、`toc`、`extra` 等扩展
- 代码高亮为 GitHub 官方风格,随站点亮 / 暗主题自动切换
- 渲染结果有 LRU 缓存,相同内容不重复渲染

### 评论

- 评论表单提交后,根据 `COMMENT_REQUIRE_APPROVAL` 决定是否需要审核
- 评论支持嵌套回复(一层)
- 头像使用 Cravatar(国内 gravatar 镜像)

### 每日金句

- 首页访问时惰性触发抓取:若金句文章当天无内容,自动调用在线 API 追加
- API 顺序:金山词霸 → 一言 → 本地经典语录兜底
- 手动触发:`/quote/fetch/`(需超级用户登录)

## 部署

详见 [DEPLOYMENT.md](DEPLOYMENT.md)(含 GitHub Webhook 自动部署说明)。

简要流程:

1. 安装系统依赖(Python 3.11 / MySQL 8.0 / Nginx)
2. 克隆代码,创建虚拟环境,安装依赖
3. 配置 `.env`,初始化 MySQL
4. `python manage.py migrate && collectstatic`
5. 创建超级用户与示例数据
6. 配置 Gunicorn systemd 服务与 Nginx 反向代理
7. 申请 HTTPS 证书(Let's Encrypt)
8. 配置 GitHub Webhook,之后 push 代码即自动部署

## 安全提示

- 生产环境务必在 `.env` 中设置强随机 `DJANGO_SECRET_KEY`
- 生产环境设 `DJANGO_DEBUG=False`
- `DJANGO_ADMIN_PATH` 改成不易猜到的字符串,降低被扫描风险
- `.env` 文件不要提交到 git(已加入 `.gitignore`)

## License

MIT
