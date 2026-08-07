"""
站点地图(sitemap.xml)。
"""

from django.contrib.sitemaps import Sitemap

from .models import Category, Post, Tag


class PostSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        return Post.published.all()

    def lastmod(self, obj):
        return obj.modified_time


class CategorySitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        return Category.objects.all()


class TagSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return Tag.objects.all()


class StaticSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.7

    def items(self):
        return ['blog:index', 'blog:archive', 'blog:category_list', 'blog:tag_list', 'blog:about']

    def location(self, item):
        from django.urls import reverse
        return reverse(item)
