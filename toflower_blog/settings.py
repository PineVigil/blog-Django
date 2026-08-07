"""
Django settings for toflower_blog project.

部署目标:toflower.fun (150.109.76.168)
技术栈:Python 3.11.9 + Django 5.2 LTS + MySQL 5.7.44 + Nginx 1.30.4

敏感配置通过 .env 文件 / 环境变量读取,开发环境无 .env 时回退到 SQLite。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件(若存在)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def _env_bool(name, default=False):
    """读取布尔型环境变量:on/1/true/yes 视为真。"""
    return str(os.environ.get(name, default)).strip().lower() in ('1', 'true', 'yes', 'on')


# ============================================================================
# 安全配置
# ============================================================================

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-dev-key-change-me-in-production-please-0123456789abcdef',
)

DEBUG = _env_bool('DJANGO_DEBUG', True)

# 生产环境部署时通过环境变量补充,如:toflower.fun,150.109.76.168,localhost,127.0.0.1
ALLOWED_HOSTS = [h.strip() for h in os.environ.get(
    'DJANGO_ALLOWED_HOSTS', 'toflower.fun,www.toflower.fun,150.109.76.168,localhost,127.0.0.1'
).split(',') if h.strip()]


# ============================================================================
# 第三方 API
# ============================================================================

# 和风天气(https://console.qweather.com 免费注册获取 Key)
# 用于首页天气卡片,经后端 /api/weather/ 代理,避免 Key 暴露在前端
QWEATHER_KEY = os.environ.get('QWEATHER_KEY', '')
# 和风天气 API Host(新账号在控制台「设置」中查看,形如 xxx.qweatherapi.com;
# 老账号可留空,自动回退到默认的 geoapi/devapi 域名)
QWEATHER_API_HOST = os.environ.get('QWEATHER_API_HOST', '')


# ============================================================================
# 应用注册
# ============================================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'django.contrib.flatpages',
    'blog.apps.BlogConfig',
]

# django.contrib.sites 需要的站点 ID(默认 1)
SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
]

ROOT_URLCONF = 'toflower_blog.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'blog.context_processors.site_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'toflower_blog.wsgi.application'
ASGI_APPLICATION = 'toflower_blog.asgi.application'


# ============================================================================
# 数据库(默认 MySQL;未配置 DB_HOST 时回退 SQLite 便于本地开发)
# ============================================================================

if os.environ.get('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('DB_NAME', 'toflower_blog'),
            'USER': os.environ.get('DB_USER', 'root'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT': os.environ.get('DB_PORT', '3306'),
            # 连接池配置( Django 5.0+ 内置)
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
    # 使用 PyMySQL 作为 MySQL 驱动(纯 Python,Windows 友好)
    import pymysql
    pymysql.install_as_MySQLdb()
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ============================================================================
# 密码校验
# ============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ============================================================================
# 国际化 / 时区
# ============================================================================

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True


# ============================================================================
# 静态文件 & 媒体文件
# ============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'          # collectstatic 输出目录
STATICFILES_DIRS = [BASE_DIR / 'static']        # 开发期静态源目录

# 静态文件版本号:用于 URL 加 ?v= 缓存失效(Nginx 对 /static/ 设了 30 天 immutable 缓存)
# 生产部署时 deploy.sh 会传入时间戳,每次部署自动更新;本地开发默认 "1"
STATIC_VERSION = os.environ.get("STATIC_VERSION", "1")

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ============================================================================
# 默认主键 / 会话
# ============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 14 天

# ============================================================================
# 自建后台(/dijia/)登录跳转
# 使用命名 URL,登录/登出后跳转由 manage_urls 处理
# ============================================================================

LOGIN_URL = 'manage:login'
LOGIN_REDIRECT_URL = 'manage:dashboard'
LOGOUT_REDIRECT_URL = 'manage:login'


# ============================================================================
# 站点信息(自定义,供模板上下文使用)
# ============================================================================

SITE_CONFIG = {
    'SITE_NAME': 'toflower',
    'SITE_TITLE': 'toflower · 个人博客',
    'SITE_DESC': '一个简约的个人博客,记录代码、思考与生活。',
    'SITE_DOMAIN': 'toflower.fun',
    'SITE_AUTHOR': 'toflower',
    'SITE_EMAIL': os.environ.get('SITE_EMAIL', 'admin@toflower.fun'),
    'SITE_ICP': '',                       # 备案号(可选)
    'POSTS_PER_PAGE': 10,                 # 首页每页文章数
    'ADMIN_PATH': os.environ.get('DJANGO_ADMIN_PATH', 'dijia/'),  # 自建后台路径
    # 原 Django admin 迁移到隐藏路径(仍可访问,作为备用/逃生通道)
    'NATIVE_ADMIN_PATH': os.environ.get('DJANGO_NATIVE_ADMIN_PATH', '_djadmin/'),
    'ABOUT_MARKDOWN': '',                 # 关于页 Markdown(可由 flatpages 覆盖)
}

# 后台标题(模板未直接使用,但 admin 会显示)
admin_site_header = 'toflower 博客管理后台'
admin_site_title = 'toflower 博客管理'
admin_index_title = '站点管理'


# ============================================================================
# Markdown 渲染配置(供 blog/utils.py 使用)
# ============================================================================

MARKDOWN_EXTENSIONS = [
    'extra',            # 表格、脚注、定义列表等
    'codehilite',       # 代码高亮(需 Pygments)
    'toc',              # 目录
    'nl2br',            # 换行转 <br>
    'sane_lists',       # 列表解析改进
]

MARKDOWN_EXTENSION_CONFIGS = {
    'codehilite': {
        'guess_lang': False,     # 不猜测语言,避免误高亮
        'css_class': 'highlight',
        'noclasses': False,
    },
    'toc': {
        # 不生成可见的永久链接 #(GitHub 风格:标题锚点仅在悬停时由 CSS 显示)
        'permalink': False,
    },
}


# ============================================================================
# 安全(生产环境生效)
# ============================================================================

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# ============================================================================
# 日志
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'blog': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
