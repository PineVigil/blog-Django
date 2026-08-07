"""
RSS / Atom 订阅源。
"""

from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed

from .models import Post


class LatestPostsFeed(Feed):
    """RSS 2.0:最新文章订阅。"""

    title = 'toflower 博客 · 最新文章'
    link = '/'
    description = 'toflower.fun 博客的最新文章更新'
    description_template = None
    author_name = 'toflower'

    def items(self):
        return Post.published.all().order_by('-published_time')[:20]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or item.content[:200]

    def item_link(self, item):
        return item.get_absolute_url()

    def item_pubdate(self, item):
        return item.published_time

    def item_author_name(self, item):
        return item.author.get_username() if item.author else 'toflower'

    def item_categories(self, item):
        cats = [item.category.name] if item.category else []
        return cats + [t.name for t in item.tags.all()]


class LatestPostsAtomFeed(LatestPostsFeed):
    """Atom 1.0 版本。"""

    feed_type = Atom1Feed
    subtitle = LatestPostsFeed.description
