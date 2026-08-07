"""
toflower_blog 主路由。

后台路由说明:
- /dijia/      → 自建后台(简约现代化 UI,支持 .md 文件上传)
- /_djadmin/   → 原 Django admin(隐藏路径,作为备用/逃生通道,可用 .env 的
                 DJANGO_NATIVE_ADMIN_PATH 自定义;不破坏既有 admin/admin12345 登录)

前台路由全部位于 blog 应用('', include('blog.urls'))。
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from blog.sitemaps import CategorySitemap, PostSitemap, StaticSitemap, TagSitemap
from blog.views import robots_txt
from toflower_blog.webhook import github_webhook

# 自建后台路径(可通过 .env 的 DJANGO_ADMIN_PATH 自定义,默认 /dijia/)
ADMIN_PATH = settings.SITE_CONFIG['ADMIN_PATH'].strip('/') or 'dijia'
# 原 Django admin 隐藏路径(可通过 .env 的 DJANGO_NATIVE_ADMIN_PATH 自定义)
NATIVE_ADMIN_PATH = settings.SITE_CONFIG['NATIVE_ADMIN_PATH'].strip('/') or '_djadmin'

# 站点地图
sitemaps = {
    'posts': PostSitemap,
    'categories': CategorySitemap,
    'tags': TagSitemap,
    'static': StaticSitemap,
}

urlpatterns = [
    # 自建后台(替代原 /dijia/)
    path(f'{ADMIN_PATH}/', include('blog.manage_urls')),

    # 原 Django admin(迁移至隐藏路径,保留可用,不影响前台)
    path(f'{NATIVE_ADMIN_PATH}/', admin.site.urls),

    # blog 应用(前台)
    path('', include('blog.urls')),

    # GitHub Webhook 自动部署
    path('webhook/deploy/', github_webhook, name='webhook_deploy'),

    # 站点地图 & robots.txt
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),

    # flatpages(用于 /pages/xxx/ 等静态页面)
    path('pages/', include('django.contrib.flatpages.urls')),
]

# 自定义错误页(DEBUG=False 时生效;handler404 接收 (request, exception))
handler404 = 'blog.views.handler404'
handler500 = 'blog.views.handler500'

# 开发期提供静态与媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # 可选:开发期启用 django-debug-toolbar(未安装时跳过)
    try:
        import debug_toolbar  # noqa: F401
        urlpatterns += [path('__debug__/', include('debug_toolbar.urls'))]
    except ImportError:
        pass
