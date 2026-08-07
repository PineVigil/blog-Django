"""
博客视图:首页、文章详情、归档、分类、标签、关于、搜索、评论提交。

设计要点:
- 首页/分类/标签使用 ListView(分页)
- 文章详情处理浏览量+1、评论提交、上下篇导航
- 搜索使用 Q 对象在 title/content/excerpt 上做模糊匹配
- 关于页从 settings.SITE_CONFIG.ABOUT_MARKDOWN 或 flatpages 取
"""

from collections import OrderedDict
import gzip
import json
import urllib.request

from django.conf import settings
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import CommentForm, SearchForm
from .models import (
    Category,
    Collection,
    Comment,
    Post,
    Project,
    ProjectCategory,
    SiteConfig,
    Tag,
)
from .utils import (
    append_today_quote_if_needed,
    render_markdown,
    today_quote_display,
)


# ============================================================================
# 通用分页辅助
# ============================================================================

def _paginate(request, queryset, per_page=None):
    """对 queryset 进行分页,返回当前页对象。"""
    per_page = per_page or settings.SITE_CONFIG.get('POSTS_PER_PAGE', 10)
    paginator = Paginator(queryset, per_page)
    page = request.GET.get('page', 1)
    try:
        return paginator.page(page)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)


# ============================================================================
# 首页
# ============================================================================

def index(request):
    """首页:Hero → 功能卡片区 → 已发布文章列表,支持分页。"""
    from datetime import date
    from django.db.models import Count

    posts_qs = Post.published.all().select_related('category', 'author').prefetch_related('tags')
    page_obj = _paginate(request, posts_qs)

    # 仅真正首页触发"每日金句"惰性写入(一天只写一次),并取今日一句显示到卡片
    is_true_home = not request.resolver_match.kwargs
    if is_true_home:
        try:
            append_today_quote_if_needed()
        except Exception:
            pass
    daily_quote = today_quote_display()

    # 统计数据
    total_posts = posts_qs.count()
    total_comments = Comment.objects.filter(is_approved=True).count()
    total_collections = Collection.objects.filter(is_published=True).count()
    total_categories = Category.objects.annotate(
        c=Count('posts', filter=Q(posts__is_published=True))
    ).filter(c__gt=0).count()
    first_post = posts_qs.order_by('published_time').first()
    start_date = first_post.published_time.date() if first_post else date.today()
    running_days = max(1, (date.today() - start_date).days)

    stats = {
        'total_posts': total_posts,
        'total_comments': total_comments,
        'total_collections': total_collections,
        'total_categories': total_categories,
        'running_days': running_days,
    }

    # 热门文章 Top3
    hot_posts = list(posts_qs.order_by('-views')[:3])

    return render(request, 'index.html', {
        'page_obj': page_obj,
        'is_home': True,
        'stats': stats,
        'hot_posts': hot_posts,
        'daily_quote': daily_quote,
    })


# ============================================================================
# 每日金句: 超级管理员手动触发 URL (方便立刻看效果)
# ============================================================================

@require_http_methods(['GET'])
def daily_quote_fetch_force(request):
    """手动抓今日金句并写入专用文章。仅 superuser 可用。"""
    from django.contrib import messages
    from django.http import HttpResponseRedirect

    if not (request.user.is_authenticated and request.user.is_superuser):
        messages.error(request, '需要超级管理员权限。')
        return HttpResponseRedirect(reverse('blog:index'))

    try:
        result = append_today_quote_if_needed()
    except Exception as e:
        messages.error(request, f'抓取失败: {e}')
        return HttpResponseRedirect(reverse('blog:index'))

    if result is None:
        messages.info(request, f'今天({result["date"] if result else "今日"})的金句已经写入过啦,无需重复。')
    else:
        messages.success(request, f'抓取成功: {result["source"]} · {result.get("zh") or result.get("text")[:20]}')
    return HttpResponseRedirect(reverse('blog:post_detail', args=['daily-quotes']))


# ============================================================================
# 文章详情
# ============================================================================

def post_detail(request, slug):
    """文章详情页:渲染 Markdown、统计浏览量、显示评论与上下篇。"""
    post = get_object_or_404(Post, slug=slug, is_published=True)

    # 浏览量 +1(匿名用户也统计)
    post.increase_views()

    # 全站上下文的上下篇(按发布时间)
    site_prev = Post.published.filter(published_time__lt=post.published_time) \
        .order_by('-published_time').first()
    site_next = Post.published.filter(published_time__gt=post.published_time) \
        .order_by('published_time').first()

    # 合集上下文:如果当前文章属于某个合集,计算合集内上下篇 + 位置
    collection_ctx = None
    if post.collection_id and post.collection.is_published:
        col = post.collection
        position, col_prev, col_next = col.get_post_position(post)
        if position is not None:
            collection_ctx = {
                'collection': col,
                'position': position,
                'total': col.post_count,
                'prev_post': col_prev,
                'next_post': col_next,
            }

    # 评论:已审核的顶级评论 + 嵌套回复
    comments = post.comments.filter(is_approved=True, parent__isnull=True) \
        .prefetch_related('replies').order_by('created_time')

    # 评论提交
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = Comment(
                post=post,
                author=form.cleaned_data['author'],
                email=form.cleaned_data['email'],
                website=form.cleaned_data['website'],
                content=form.cleaned_data['content'],
                is_approved=not settings.SITE_CONFIG.get('COMMENT_REQUIRE_APPROVAL', False),
            )
            comment.save()
            return redirect(f'{post.get_absolute_url()}#comment-{comment.id}')
    else:
        form = CommentForm()

    return render(request, 'post_detail.html', {
        'post': post,
        'prev_post': site_prev,
        'next_post': site_next,
        'collection_ctx': collection_ctx,
        'comments': comments,
        'comment_form': form,
    })


# ============================================================================
# 归档(按年份分组)
# ============================================================================

def archive(request):
    """归档页:按年份分组列出所有已发布文章,顶部提供分类浏览入口。"""
    posts = Post.published.all().order_by('-published_time')
    archive_map = OrderedDict()
    for post in posts:
        year = post.published_time.year
        archive_map.setdefault(year, []).append(post)
    # Category 已有 @property post_count, 直接用它过滤并排序(避免 annotate 与 property 冲突)
    cats_with_posts = [c for c in Category.objects.all() if c.post_count > 0]
    cats_with_posts.sort(key=lambda c: (-c.post_count, c.name))
    return render(request, 'archive.html', {
        'archive_map': archive_map,
        'total_count': posts.count(),
        'categories': cats_with_posts,
        'is_archive': True,
    })


# ============================================================================
# 分类 & 标签
# ============================================================================

def category_list(request):
    """所有分类列表页。"""
    categories = Category.objects.all()
    return render(request, 'category.html', {
        'categories': categories,
        'is_category': True,
    })


def category_detail(request, slug):
    """某分类下的文章列表。"""
    category = get_object_or_404(Category, slug=slug)
    posts = Post.published.filter(category=category) \
        .select_related('category', 'author').prefetch_related('tags')
    page_obj = _paginate(request, posts)
    return render(request, 'index.html', {
        'page_obj': page_obj,
        'category': category,
        'is_category': True,
    })


def tag_list(request):
    """所有标签列表页。"""
    tags = Tag.objects.all()
    return render(request, 'tag.html', {
        'tags': tags,
        'is_tag': True,
    })


def tag_detail(request, slug):
    """某标签下的文章列表。"""
    tag = get_object_or_404(Tag, slug=slug)
    posts = Post.published.filter(tags=tag) \
        .select_related('category', 'author').prefetch_related('tags')
    page_obj = _paginate(request, posts)
    return render(request, 'index.html', {
        'page_obj': page_obj,
        'tag': tag,
        'is_tag': True,
    })


# ============================================================================
# 合集
# ============================================================================


def collection_list(request):
    """前台合集列表页:所有已发布的合集卡片。"""
    collections = (
        Collection.objects.filter(is_published=True)
        .order_by('-modified_time')
    )
    return render(request, 'collection_list.html', {
        'collections': collections,
        'is_collections': True,
    })


def collection_detail(request, slug):
    """合集详情页:显示合集信息 + 旗下文章(按序号/发布时间排序)。"""
    from django.db.models import F
    collection = get_object_or_404(Collection, slug=slug, is_published=True)
    posts = list(
        collection.posts.filter(is_published=True)
        .select_related('category', 'author')
        .prefetch_related('tags')
        .order_by(F('order_in_collection').asc(nulls_last=True), 'published_time')
    )
    # 计算每篇文章的 position(1 起)
    pos_map = {p.pk: i + 1 for i, p in enumerate(posts)}
    # 给每篇临时挂个 display_position(只读属性,不保存)
    for p in posts:
        p.display_position = p.order_in_collection or pos_map[p.pk]
    return render(request, 'collection_detail.html', {
        'collection': collection,
        'posts': posts,
        'is_collection': True,
    })


# ============================================================================
# 项目页(按分类分组,仿 passer-by.com/project.html)
# ============================================================================

def project_list(request):
    """项目页:已发布项目按分类分组展示,未分类的项目单独一组放最后。"""
    projects = list(
        Project.published.select_related('category').order_by('sort_order', '-created_time')
    )
    cats = list(
        ProjectCategory.objects.filter(projects__is_published=True)
        .distinct()
        .order_by('sort_order', 'name')
    )
    groups = []
    for cat in cats:
        items = [p for p in projects if p.category_id == cat.pk]
        if items:
            groups.append((cat, items))
    uncategorized = [p for p in projects if p.category_id is None]
    if uncategorized:
        groups.append((None, uncategorized))
    return render(request, 'projects.html', {
        'groups': groups,
        'total_count': len(projects),
        'is_projects': True,
    })


# ============================================================================
# 关于页
# ============================================================================

def about(request):
    """关于页:优先用后台 SiteConfig.about_markdown,其次 settings 配置,再退到模板内置默认。"""
    about_md = SiteConfig.get_solo().about_markdown.strip()
    if not about_md:
        about_md = settings.SITE_CONFIG.get('ABOUT_MARKDOWN', '')

    about_html = render_markdown(about_md) if about_md else ''
    return render(request, 'about.html', {
        'about_html': about_html,
        'is_about': True,
    })


# ============================================================================
# 搜索
# ============================================================================

def search(request):
    """全站搜索:title / content / excerpt 模糊匹配。"""
    form = SearchForm(request.GET)
    results = []
    query = ''
    if form.is_valid():
        query = form.cleaned_data['q'].strip()
        if query:
            results = Post.published.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(excerpt__icontains=query)
            ).select_related('category', 'author').prefetch_related('tags')
            results = _paginate(request, results)
    return render(request, 'search.html', {
        'form': form,
        'query': query,
        'page_obj': results,
        'is_search': True,
    })


# ============================================================================
# 评论提交 API(供 AJAX 使用,可选)
# ============================================================================

@require_http_methods(['POST'])
def submit_comment(request, slug):
    """AJAX 评论提交端点。"""
    post = get_object_or_404(Post, slug=slug, is_published=True)
    form = CommentForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    comment = Comment(
        post=post,
        author=form.cleaned_data['author'],
        email=form.cleaned_data['email'],
        website=form.cleaned_data['website'],
        content=form.cleaned_data['content'],
        is_approved=not settings.SITE_CONFIG.get('COMMENT_REQUIRE_APPROVAL', False),
    )
    comment.save()
    return JsonResponse({
        'ok': True,
        'comment': {
            'id': comment.id,
            'author': comment.author,
            'content': comment.content,
            'created_time': comment.created_time.strftime('%Y-%m-%d %H:%M'),
            'approved': comment.is_approved,
        }
    })


# ============================================================================
# 天气 API(首页天气卡片数据源)
# 优先和风天气(国内精度高),未配置 QWEATHER_KEY 时回退 Open-Meteo。
# Key 只存在后端 .env,不暴露给前端;结果按经纬度缓存 10 分钟省配额。
# ============================================================================

_WEATHER_CACHE_TTL = 600  # 秒


def _fetch_json(url, timeout=10):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0', 'Accept-Encoding': 'gzip'},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        # 和风天气等接口返回 gzip,urllib 不会自动解压
        if resp.headers.get('Content-Encoding', '').lower() == 'gzip':
            raw = gzip.decompress(raw)
        return json.loads(raw.decode('utf-8'))


def _qweather_now(lat, lon):
    """和风天气: 经纬度 → 逆地理拿 LocationID → 实况天气。"""
    key = settings.QWEATHER_KEY
    if not key:
        return None
    host = settings.QWEATHER_API_HOST
    if host:
        # 新账号:独立 API Host(控制台「设置」里查看)
        geo_api = 'https://{}/geo/v2/city/lookup'.format(host)
        now_api = 'https://{}/v7/weather/now'.format(host)
    else:
        # 老账号:默认域名
        geo_api = 'https://geoapi.qweather.com/v2/city/lookup'
        now_api = 'https://devapi.qweather.com/v7/weather/now'
    geo = _fetch_json(
        '{}?location={:.2f},{:.2f}&number=1&key={}'
        .format(geo_api, lon, lat, key)
    )
    if geo.get('code') != '200' or not geo.get('location'):
        raise RuntimeError('QWeather 逆地理失败: ' + str(geo.get('code')))
    loc = geo['location'][0]
    now = _fetch_json(
        '{}?location={}&key={}'.format(now_api, loc['id'], key)
    )
    if now.get('code') != '200':
        raise RuntimeError('QWeather 实况失败: ' + str(now.get('code')))
    n = now['now']
    return {
        'source': 'qweather',
        'city': loc['name'],
        'temp': round(float(n['temp'])),
        'text': n['text'],
        'icon': int(n['icon']),
    }


def _openmeteo_now(lat, lon):
    """Open-Meteo 兜底(无 Key 时用,精度一般)。"""
    data = _fetch_json(
        'https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}'
        '&current=temperature_2m,weather_code&timezone=auto'.format(lat, lon)
    )
    cur = data.get('current') or {}
    city = '{},{}'.format(lat, lon)
    try:
        geo = _fetch_json(
            'https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={}'
            '&longitude={}&localityLanguage=zh'.format(lat, lon)
        )
        city = geo.get('city') or geo.get('locality') or geo.get('principalSubdivision') or city
    except Exception:
        pass
    return {
        'source': 'open-meteo',
        'city': city,
        'temp': round(float(cur.get('temperature_2m') or 0)),
        'text': '',
        'icon': int(cur.get('weather_code') or 0),
    }


@require_http_methods(['GET'])
def weather_api(request):
    """GET /api/weather/?lat=..&lon=.. → 天气 JSON,带 10 分钟缓存。"""
    from django.core.cache import cache

    try:
        lat = round(float(request.GET.get('lat')), 2)
        lon = round(float(request.GET.get('lon')), 2)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': '缺少有效的 lat/lon 参数'}, status=400)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return JsonResponse({'ok': False, 'error': '经纬度超出范围'}, status=400)

    cache_key = 'weather:{},{}'.format(lat, lon)
    data = cache.get(cache_key)
    if data is None:
        try:
            data = _qweather_now(lat, lon) or _openmeteo_now(lat, lon)
            data['ok'] = True
        except Exception as e:
            data = {'ok': False, 'error': str(e)}
        cache.set(cache_key, data, _WEATHER_CACHE_TTL)
    return JsonResponse(data)


# ============================================================================
# 自定义错误页
# ============================================================================

def handler404(request, exception=None):
    return render(request, 'errors/404.html', status=404)


def handler500(request):
    return render(request, 'errors/500.html', status=500)


# ============================================================================
# robots.txt / favicon
# ============================================================================

def robots_txt(request):
    """生成 robots.txt,允许全站抓取并指向 sitemap。"""
    lines = [
        'User-agent: *',
        'Allow: /',
        f'Sitemap: https://{settings.SITE_CONFIG["SITE_DOMAIN"]}/sitemap.xml',
        '',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')
