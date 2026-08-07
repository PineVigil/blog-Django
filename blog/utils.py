"""
博客通用工具:Markdown 渲染、摘要生成等。
"""

import re
from functools import lru_cache

import markdown as md
from django.conf import settings
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe


@lru_cache(maxsize=256)
def render_markdown(text: str) -> str:
    """
    将 Markdown 渲染为 HTML。

    - 启用 codehilite(代码高亮)、toc、extra 等扩展
    - 输出经过 mark_safe 标记,可直接在模板中使用
    - 使用 LRU 缓存,相同内容不重复渲染
    """
    html = md.markdown(
        text or '',
        extensions=settings.MARKDOWN_EXTENSIONS,
        extension_configs=settings.MARKDOWN_EXTENSION_CONFIGS,
        output_format='html5',
    )
    return mark_safe(html)


def make_excerpt(content: str, length: int = 200) -> str:
    """
    从 Markdown / HTML 内容中提取纯文本摘要。

    优先:去除 Markdown 语法标记 -> 去除 HTML 标签 -> 截断到指定长度。
    """
    if not content:
        return ''
    # 去除代码块(避免摘要中出现大段代码)
    text = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    # 去除行内代码
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 去除图片/链接,保留文字
    text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # 去除 Markdown 标题/列表/引用标记
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*>\s*', '', text, flags=re.MULTILINE)
    # 渲染为 HTML 后再 strip,确保彻底去标签
    text = strip_tags(render_markdown(text))
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:length] + ('…' if len(text) > length else '')


def reading_time(content: str, wpm: int = 400) -> int:
    """估算阅读时长(分钟),按中文 400 字/分钟估算。"""
    text = strip_tags(render_markdown(content or ''))
    chars = len(re.sub(r'\s+', '', text))
    return max(1, round(chars / wpm))


# ============================================================
# 每日金句: 在线 API 获取 → 追加到专用文章 (slug=daily-quotes)
# ============================================================

DAILY_QUOTE_SLUG = 'daily-quotes'
DAILY_QUOTE_TITLE = '每日金句 · Daily Quotes'

_API_ICIBA = 'https://open.iciba.com/dsapi/'
_API_HITOKOTO = 'https://v1.hitokoto.cn/?c=a&c=b&c=d&c=i&c=k'
_UA = 'Mozilla/5.0 (compatible; toflower-blog/1.0; +https://example.com)'


def _http_json(url: str, timeout: int = 8) -> dict | None:
    """简易 GET JSON。网络/解析失败返回 None。"""
    import json
    from urllib.request import Request, urlopen
    try:
        req = Request(url, headers={'User-Agent': _UA})
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
            return json.loads(data)
    except Exception:
        return None


def fetch_today_quote_from_api(today=None) -> dict:
    """
    从在线 API 获取今日金句;失败时用本地兜底。
    返回: {'date': 'YYYY-MM-DD', 'text': '中文一句', 'en': '英文(可选)', 'source': '来源'}
    """
    from datetime import date
    today = today or date.today()
    date_str = today.isoformat()

    # 1) 优先: 金山词霸每日一句 (英文+中文翻译, 每天一句稳定)
    j = _http_json(_API_ICIBA, timeout=6)
    if j and isinstance(j, dict) and (j.get('content') or j.get('note')):
        en = (j.get('content') or '').strip()
        zh = (j.get('note') or '').strip()
        text = zh or en
        if en and zh:
            text = f'{en}\n> — {zh}'
        return {
            'date': date_str,
            'text': text.strip(),
            'en': en,
            'zh': zh,
            'source': '金山词霸',
        }

    # 2) 回退: 一言 hitokoto.cn (类型 a=动画/b=漫画/d=文学/i=诗词/k=哲学)
    j = _http_json(_API_HITOKOTO, timeout=6)
    if j and isinstance(j, dict) and j.get('hitokoto'):
        text = j['hitokoto'].strip()
        frm = (j.get('from') or '').strip()
        who = (j.get('from_who') or '').strip()
        src = (who + '《' + frm + '》').strip('《》') or '一言'
        return {
            'date': date_str,
            'text': f'「{text}」\n> — {src}',
            'en': '',
            'zh': text,
            'source': src,
        }

    # 3) 本地兜底
    fallback = [
        '在人类历史的长河中,每一次思考都是一次小小的革命。',
        '未经审视的生活是不值得过的。',
        '世界上只有一种真正的英雄主义,就是在认清生活真相之后依然热爱生活。',
        '我们都在阴沟里,但仍有人仰望星空。',
        '人生像一盒巧克力,你永远不知道下一颗是什么味道。',
    ]
    text = fallback[today.day % len(fallback)]
    return {
        'date': date_str,
        'text': f'「{text}」',
        'en': '',
        'zh': text,
        'source': '本站默认',
    }


def ensure_daily_quote_article() -> 'Post':
    """获取或创建 slug=DAILY_QUOTE_SLUG 的专用文章。"""
    from django.contrib.auth import get_user_model
    from .models import Category, Post

    qs = Post.objects.filter(slug=DAILY_QUOTE_SLUG)
    if qs.exists():
        return qs.first()

    # 首次创建: 选第一个存在的分类, 选第一个存在的作者
    cat = Category.objects.first()
    user_model = get_user_model()
    author = user_model.objects.filter(is_active=True).first()
    body = (
        f'# {DAILY_QUOTE_TITLE}\n\n'
        f'> 这里是「每日金句」合集。每天自动从在线接口更新一句,并带当天日期追加到本文。\n\n'
        f'---\n\n'
    )
    from django.utils.timezone import now
    post = Post(
        title=DAILY_QUOTE_TITLE,
        slug=DAILY_QUOTE_SLUG,
        excerpt='每日自动更新一句,日期追溯可见。',
        content=body,
        category=cat,
        author=author,
        is_published=True,
        published_time=now(),
    )
    post.save(force_insert=True)
    return post


def append_today_quote_if_needed(today=None) -> dict | None:
    """
    如果今天的金句还没写入到 daily-quotes 文章,则调用 API 取一条并追加。
    返回本次写入的 quote dict;若今天已存在或失败则返回 None。
    """
    from datetime import date
    today = today or date.today()
    date_str = today.isoformat()

    post = ensure_daily_quote_article()
    body = post.content or ''

    # 检查是否已存在今天标题行
    heading_mark = f'## {date_str}'
    if heading_mark in body:
        return None

    quote = fetch_today_quote_from_api(today)

    # 追加到正文末尾(保持时间正序,最新在最下);若正文为空则先补标题
    if not body.strip():
        body = f'# {DAILY_QUOTE_TITLE}\n\n'
    # 统一 blockquote: 先去掉每行已有的开头 "> ", 再每行重加一次 "> "
    lines = quote['text'].split(chr(10))
    q_lines = ['  ' + ln if ln.startswith('— ') else ln for ln in lines]
    q_lines = ['  ' + ln[2:] if ln.startswith('> ') else ln for ln in q_lines]
    blockquote = chr(10).join(['> ' + ln for ln in q_lines])
    block = (
        f'\n\n## {quote["date"]}\n'
        f'{blockquote}\n'
        f'\n_来源: {quote["source"]}_\n'
    )
    post.content = body.rstrip() + block
    # 重新生成摘要
    post.excerpt = make_excerpt(post.content, 120)
    post.save(update_fields=['content', 'excerpt', 'modified_time'])

    return quote


def today_quote_display(today=None) -> dict:
    """给首页卡片用的今日金句。优先读文章里今天的段落,否则实时抓 API。"""
    from datetime import date
    today = today or date.today()
    date_str = today.isoformat()
    try:
        post = ensure_daily_quote_article()
        body = post.content or ''
        heading = f'## {date_str}\n'
        if heading in body:
            chunk = body.split(heading, 1)[1].split('\n## ', 1)[0].strip()
            lines = [ln.strip('> ').strip() for ln in chunk.splitlines() if ln.strip()]
            lines = [ln for ln in lines if ln and not ln.startswith('_来源:')]
            text = ' / '.join(lines).strip() or '今日一句'
            return {
                'text': text,
                'source_title': post.title,
                'source_url': post.get_absolute_url(),
            }
    except Exception:
        pass
    # 兜底: 实时抓 API
    q = fetch_today_quote_from_api(today)
    from django.urls import reverse
    return {
        'text': q.get('zh') or q.get('text'),
        'source_title': DAILY_QUOTE_TITLE,
        'source_url': reverse('blog:post_detail', args=[DAILY_QUOTE_SLUG]),
    }
