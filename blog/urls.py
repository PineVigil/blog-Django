"""
blog 应用路由。

URL 命名空间:blog
"""

from django.urls import path, register_converter

from . import feeds, views


# ============================================================================
# 自定义路径转换器:支持 Unicode(含中文)的 slug
# 默认的 <slug:slug> 仅匹配 [-a-zA-Z0-9_],会拒绝中文 slug
# ============================================================================

class UnicodeSlugConverter:
    """匹配 \w 与连字符,Python 3 的 \w 默认包含 Unicode 字母数字。"""
    regex = r'[\w-]+'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return str(value)


register_converter(UnicodeSlugConverter, 'uslug')


app_name = 'blog'

urlpatterns = [
    # 首页
    path('', views.index, name='index'),

    # 文章
    path('post/<uslug:slug>/', views.post_detail, name='post_detail'),
    path('post/<uslug:slug>/comment/', views.submit_comment, name='submit_comment'),

    # 归档
    path('archive/', views.archive, name='archive'),

    # 分类
    path('categories/', views.category_list, name='category_list'),
    path('category/<uslug:slug>/', views.category_detail, name='category'),

    # 标签
    path('tags/', views.tag_list, name='tag_list'),
    path('tag/<uslug:slug>/', views.tag_detail, name='tag'),

    # 合集
    path('collections/', views.collection_list, name='collection_list'),
    path('collection/<uslug:slug>/', views.collection_detail, name='collection_detail'),

    # 项目
    path('projects/', views.project_list, name='projects'),

    # 关于
    path('about/', views.about, name='about'),

    # 搜索
    path('search/', views.search, name='search'),

    # 每日金句:超级管理员手动触发写入
    path('quote/fetch/', views.daily_quote_fetch_force, name='daily_quote_fetch'),

    # 天气 API(首页天气卡片;后端代理和风天气,避免 Key 暴露)
    path('api/weather/', views.weather_api, name='weather_api'),

    # RSS / Atom
    path('feed/rss/', feeds.LatestPostsFeed(), name='rss_feed'),
    path('feed/atom/', feeds.LatestPostsAtomFeed(), name='atom_feed'),
]
