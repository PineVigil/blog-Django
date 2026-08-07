"""blog 应用自定义模板标签与过滤器。"""

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

from blog.utils import render_markdown

register = template.Library()


@register.filter(name='markdown', is_safe=True)
@stringfilter
def markdown_filter(value):
    """将 Markdown 文本渲染为 HTML。用法:{{ content|markdown }}"""
    return mark_safe(render_markdown(value))


@register.simple_tag
def site_url(name, *args, **kwargs):
    """反向解析 URL。用法:{% site_url 'blog:post_detail' slug=post.slug %}"""
    from django.urls import reverse
    return reverse(name, args=args, kwargs=kwargs)


@register.simple_tag
def recent_posts(limit=5):
    """获取最新已发布文章列表。用法:{% recent_posts 5 as posts %}"""
    from blog.models import Post
    return Post.published.all().order_by('-published_time')[:limit]


@register.simple_tag
def popular_tags(limit=20):
    """获取热门标签列表(按文章数排序)。用法:{% popular_tags 20 as tags %}"""
    from blog.models import Tag
    from django.db.models import Count
    return Tag.objects.annotate(
        post_count=Count('posts', filter={'posts__is_published': True})
    ).filter(post_count__gt=0).order_by('-post_count')[:limit]


@register.simple_tag
def hero_title_with_accent(title, accent_word=''):
    """把标题中出现的 accent_word 包裹成 <span class="accent">…</span>。

    用法:{% hero_title_with_accent hero_config.hero_title hero_config.hero_accent_word %}
    若 accent_word 为空或不在标题中,则原样返回(转义后的安全文本)。
    """
    from django.utils.html import escape

    safe_title = escape(title)
    word = (accent_word or '').strip()
    if not word:
        return mark_safe(safe_title)

    # 转义 accent_word 后做替换(大小写敏感,中文友好)
    safe_word = escape(word)
    if safe_word and safe_word in safe_title:
        wrapped = f'<span class="accent">{safe_word}</span>'
        return mark_safe(safe_title.replace(safe_word, wrapped))
    return mark_safe(safe_title)
