"""
自建后台(/dijia/)视图:简约现代化管理后台。

设计要点:
- 全部视图 @login_required,登录走 Django auth
- 文章 CRUD + .md 文件上传(智能解析首行 H1 作标题)
- 文章 zip 打包上传(自动托管本地资源 + 改写相对路径,外链保留)
- 分类 / 标签 CRUD
- 评论列表 / 审核切换 / 删除
- 不修改前台任何视图,不影响前台路由
"""

import os
import re
import shutil
import uuid
import zipfile

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Max, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .manage_forms import (
    AboutForm,
    BackgroundImageForm,
    CategoryForm,
    CollectionForm,
    PostForm,
    PostUploadMDForm,
    PostUploadZipForm,
    ProjectCategoryForm,
    ProjectForm,
    SiteConfigForm,
    TagForm,
    parse_md_for_post,
)
from .models import (
    BackgroundImage,
    Category,
    Collection,
    Comment,
    Post,
    Project,
    ProjectCategory,
    SiteConfig,
    Tag,
)


# ============================================================================
# 通用辅助
# ============================================================================

def _manage_context(active_menu: str = '', **extra):
    """构造后台模板通用上下文(高亮当前菜单)。"""
    ctx = {
        'active_menu': active_menu,
        'now': timezone.now(),
    }
    ctx.update(extra)
    return ctx


def _paginated(request, queryset, per_page=20):
    """简单分页:返回 page_obj。"""
    from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
    paginator = Paginator(queryset, per_page)
    page = request.GET.get('page', 1)
    try:
        return paginator.page(page)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)


def _qs(request):
    """返回去除 page 参数后的查询串,供分页链接保留过滤条件。"""
    q = request.GET.copy()
    q.pop('page', None)
    return q.urlencode()


# ============================================================================
# zip 打包上传:解压安全 + 相对路径改写
# ============================================================================

# 解压保护:总未压缩大小 / 文件数上限,防 zip 炸弹
_MAX_ZIP_UNCOMPRESSED = 50 * 1024 * 1024   # 50MB
_MAX_ZIP_ENTRIES = 500


def _is_external_url(url):
    """判断 URL 是否为外链/锚点等不应改写的形式。"""
    if not url:
        return True
    u = url.strip().lower()
    return (u.startswith('http://') or u.startswith('https://')
            or u.startswith('mailto:') or u.startswith('tel:')
            or u.startswith('data:') or u.startswith('#')
            or u.startswith('//'))


def _rewrite_md_relative_paths(content, base_url):
    """把 md 中"相对路径"的图片/链接改写为 base_url + 原路径。

    外链(http/https/mailto/tel/data/#//)保持不动。
    同时处理图片 ![](url) 与普通链接 [text](url)(后者用后行断言排除图片)。
    """
    if not content:
        return content

    def rewrite_url(url):
        if _is_external_url(url):
            return url
        path = url.strip()
        # 去掉前导 ./
        if path.startswith('./'):
            path = path[2:]
        # 去掉前导 / (相对根)
        path = path.lstrip('/')
        return f'{base_url.rstrip("/")}/{path}'

    # 图片:![alt](url)
    content = re.sub(
        r'!\[([^\]]*)\]\(([^)]+)\)',
        lambda m: f'![{m.group(1)}]({rewrite_url(m.group(2))})',
        content,
    )
    # 普通链接:[text](url),后行断言确保前面不是 !(避免重复改写图片)
    content = re.sub(
        r'(?<!!)\[([^\]]+)\]\(([^)]+)\)',
        lambda m: f'[{m.group(1)}]({rewrite_url(m.group(2))})',
        content,
    )
    return content


def _decode_bytes_text(raw):
    """把 bytes 解码为文本,UTF-8 优先,回退 GB18030/UTF-16。"""
    if isinstance(raw, str):
        return raw
    for enc in ('utf-8-sig', 'utf-8', 'gb18030', 'utf-16'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace')


def _extract_zip_resources(zip_file, target_dir):
    """安全解压 zip 到 target_dir,返回 (md_name, md_text, file_count)。

    安全措施:
    - 拒绝绝对路径与含 .. 的成员(防路径穿越)
    - 限制总未压缩大小与文件数(防 zip 炸弹)
    - 跳过 macOS __MACOSX 目录与 .DS_Store
    - 解压后再用 abspath 校验最终路径必须在 target_dir 内
    """
    os.makedirs(target_dir, exist_ok=True)
    abs_base = os.path.abspath(target_dir)

    md_name = None
    md_text = ''
    total_size = 0
    file_count = 0

    with zipfile.ZipFile(zip_file, 'r') as zf:
        for info in zf.infolist():
            name = info.filename
            if info.is_dir():
                continue
            # 跳过 macOS 元数据
            if '__MACOSX/' in name or os.path.basename(name) == '.DS_Store':
                continue
            # 统一用 / 分隔,规范化后校验
            rel = name.replace('\\', '/')
            norm = os.path.normpath(rel)
            if os.path.isabs(norm) or norm.startswith('..'):
                continue
            if '..' in norm.split(os.sep):
                continue
            # 大小 / 数量上限
            total_size += info.file_size
            if total_size > _MAX_ZIP_UNCOMPRESSED:
                raise ValueError(
                    f'解压总大小超过 {_MAX_ZIP_UNCOMPRESSED // 1024 // 1024}MB 上限。'
                )
            file_count += 1
            if file_count > _MAX_ZIP_ENTRIES:
                raise ValueError(
                    f'zip 内文件数超过 {_MAX_ZIP_ENTRIES} 上限。'
                )
            # 计算目标绝对路径,二次校验在 target_dir 内
            dest = os.path.join(abs_base, norm)
            if not os.path.abspath(dest).startswith(abs_base + os.sep):
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with zf.open(info) as src, open(dest, 'wb') as out:
                shutil.copyfileobj(src, out)

            # 识别 .md 文件(优先根目录的)
            lower = name.lower()
            if lower.endswith('.md') or lower.endswith('.markdown'):
                if md_name is None or '/' not in rel:
                    try:
                        with open(dest, 'rb') as fh:
                            md_text = _decode_bytes_text(fh.read())
                        md_name = os.path.basename(name)
                    except Exception:
                        pass

    if md_name is None:
        raise ValueError('zip 内未找到 .md / .markdown 文件。')
    return (md_name, md_text, file_count)


# ============================================================================
# 认证
# ============================================================================

def login_view(request):
    """后台登录:用 Django auth 校验用户名/密码。"""
    # 已登录直接跳仪表盘
    if request.user.is_authenticated:
        return redirect(reverse('manage:dashboard'))

    error = ''
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        next_url = request.POST.get('next', '') or ''
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            messages.success(request, f'欢迎回来,{user.get_username()}。')
            target = next_url or reverse('manage:dashboard')
            return redirect(target)
        error = '用户名或密码错误。'
    return render(request, 'manage/login.html', {
        'error': error,
        'next': next_url,
        'hide_layout': True,  # 登录页不套用后台布局
    })


@login_required
def logout_view(request):
    """登出。"""
    logout(request)
    return redirect(reverse('manage:login'))


# ============================================================================
# 仪表盘
# ============================================================================

@login_required
def dashboard(request):
    """后台首页:统计概览 + 最近文章 + 待审评论。"""
    post_total = Post.objects.count()
    post_published = Post.published.count()
    post_draft = post_total - post_published
    comment_total = Comment.objects.count()
    comment_pending = Comment.objects.filter(is_approved=False).count()
    category_total = Category.objects.count()
    tag_total = Tag.objects.count()
    collection_total = Collection.objects.count()

    recent_posts = Post.objects.select_related('category', 'author').order_by('-created_time')[:6]
    pending_comments = Comment.objects.filter(is_approved=False).select_related('post').order_by('-created_time')[:6]

    stats = [
        {'label': '文章总数', 'value': post_total, 'sub': f'已发布 {post_published} / 草稿 {post_draft}',
         'url': reverse('manage:post_list'), 'icon': 'doc'},
        {'label': '合集', 'value': collection_total, 'sub': '',
         'url': reverse('manage:collection_list'), 'icon': 'book'},
        {'label': '评论总数', 'value': comment_total, 'sub': f'待审核 {comment_pending}',
         'url': reverse('manage:comment_list'), 'icon': 'comment'},
        {'label': '分类', 'value': category_total, 'sub': '',
         'url': reverse('manage:category_list'), 'icon': 'folder'},
        {'label': '标签', 'value': tag_total, 'sub': '',
         'url': reverse('manage:tag_list'), 'icon': 'tag'},
    ]

    return render(request, 'manage/dashboard.html', _manage_context(
        active_menu='dashboard',
        stats=stats,
        recent_posts=recent_posts,
        pending_comments=pending_comments,
    ))


# ============================================================================
# 文章 CRUD + MD 上传
# ============================================================================

@login_required
def post_list(request):
    """文章列表:支持按标题/正文搜索 + 按状态/分类过滤。"""
    qs = Post.objects.select_related('category', 'author').all()

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    cat = request.GET.get('cat', '').strip()

    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(content__icontains=q))
    if status == 'published':
        qs = qs.filter(is_published=True)
    elif status == 'draft':
        qs = qs.filter(is_published=False)
    elif status == 'pinned':
        qs = qs.filter(is_pinned=True)
    if cat:
        qs = qs.filter(category_id=cat)

    qs = qs.order_by('-is_pinned', '-published_time', '-created_time')
    page_obj = _paginated(request, qs, per_page=15)

    return render(request, 'manage/post_list.html', _manage_context(
        active_menu='posts',
        page_obj=page_obj,
        q=q,
        status=status,
        cat=cat,
        categories=Category.objects.all().order_by('name'),
        qs=_qs(request),
    ))


@login_required
def post_create(request):
    """新建文章(表单输入)。"""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()  # 保存 tags
            messages.success(request, f'文章「{post.title}」已创建。')
            return redirect(reverse('manage:post_list'))
    else:
        # 默认发布时间为当前
        initial = {'published_time': timezone.now().strftime('%Y-%m-%dT%H:%M')}
        form = PostForm(initial=initial)
    return render(request, 'manage/post_form.html', _manage_context(
        active_menu='posts',
        form=form,
        is_create=True,
        form_title='新建文章',
    ))


@login_required
def post_update(request, pk):
    """编辑文章。"""
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.author = updated.author or request.user
            updated.save()
            form.save_m2m()
            messages.success(request, f'文章「{updated.title}」已更新。')
            return redirect(reverse('manage:post_list'))
        # form 错误时,把 Django 表单级错误并入 messages 保证用户可见
        if form.non_field_errors():
            for err in form.non_field_errors():
                messages.error(request, err)
    else:
        form = PostForm(instance=post)
    return render(request, 'manage/post_form.html', _manage_context(
        active_menu='posts',
        form=form,
        is_create=False,
        form_title='编辑文章',
        post=post,
    ))


@login_required
@require_http_methods(['POST'])
def post_delete(request, pk):
    """删除文章(物理删除)+ 同步清理 zip 上传时托管的资源目录。"""
    post = get_object_or_404(Post, pk=pk)
    title = post.title
    asset_dir = os.path.join(settings.MEDIA_ROOT, 'post_assets', str(pk))
    post.delete()
    # 清理该文章的资源目录(zip 上传时解压的图片/Word/PDF 等)
    if os.path.isdir(asset_dir):
        shutil.rmtree(asset_dir, ignore_errors=True)
    messages.success(request, f'文章「{title}」已删除。')
    return redirect(reverse('manage:post_list'))


@login_required
@require_http_methods(['POST'])
def post_toggle(request, pk, field):
    """切换文章的 is_published / is_pinned 状态。"""
    if field not in ('is_published', 'is_pinned'):
        raise Http404('未知字段')
    post = get_object_or_404(Post, pk=pk)
    setattr(post, field, not getattr(post, field))
    post.save(update_fields=[field, 'modified_time'])
    label = '已发布' if field == 'is_published' else '置顶'
    state = '开启' if getattr(post, field) else '关闭'
    messages.success(request, f'「{post.title}」{label}已{state}。')
    return redirect(reverse('manage:post_list') + f'?{request.GET.urlencode()}')


@login_required
def post_upload_md(request):
    """通过 .md 文件上传创建文章(智能解析)。"""
    if request.method == 'POST':
        form = PostUploadMDForm(request.POST, request.FILES)
        if form.is_valid():
            title = form.parsed_title
            content = form.parsed_content
            post = Post(
                title=title,
                content=content,
                author=request.user,
                category=form.cleaned_data['category'] or None,
                collection=form.cleaned_data.get('collection') or None,
                order_in_collection=form.cleaned_data.get('order_in_collection') or None,
                cover=form.cleaned_data.get('cover') or None,
                is_published=form.cleaned_data.get('is_published', True),
                is_pinned=form.cleaned_data.get('is_pinned', False),
                published_time=form.cleaned_data.get('published_time') or timezone.now(),
            )
            # excerpt 留空,由 Post.save() 自动生成
            post.save()
            if form.cleaned_data.get('tags'):
                post.tags.set(form.cleaned_data['tags'])
            messages.success(
                request,
                f'已从 .md 文件创建文章「{post.title}」。可继续编辑补充信息。'
            )
            return redirect(reverse('manage:post_update', args=[post.pk]))
    else:
        initial = {
            'is_published': True,
            'is_pinned': False,
            'published_time': timezone.now().strftime('%Y-%m-%dT%H:%M'),
        }
        form = PostUploadMDForm(initial=initial)
    return render(request, 'manage/post_upload.html', _manage_context(
        active_menu='posts',
        form=form,
    ))


@login_required
def post_upload_zip(request):
    """通过 zip 压缩包上传创建文章(自动托管本地资源 + 改写相对路径)。

    流程:
    1. 解压到临时目录 media/post_assets/<uuid>/(安全校验:防穿越/炸弹)
    2. 取 zip 内 .md 文件 → parse_md_for_post 提取标题/正文
    3. 改写正文相对路径为 /media/post_assets/<uuid>/...(外链保留)
    4. 创建 Post 得到 pk → 把目录改名为 <pk>
    5. 把正文里的 <uuid> 前缀替换为 <pk>,再次保存 content
    6. 失败时回滚:删 Post + 清理临时/已改名目录
    """
    if request.method == 'POST':
        form = PostUploadZipForm(request.POST, request.FILES)
        if form.is_valid():
            tmp_uuid = uuid.uuid4().hex
            tmp_dir = os.path.join(settings.MEDIA_ROOT, 'post_assets', tmp_uuid)
            created_post = None
            try:
                md_name, md_text, file_count = _extract_zip_resources(
                    form.cleaned_data['zip_file'], tmp_dir
                )
                title, content = parse_md_for_post(md_text, md_name)
                tmp_base_url = f'{settings.MEDIA_URL}post_assets/{tmp_uuid}'
                content = _rewrite_md_relative_paths(content, tmp_base_url)

                post = Post(
                    title=title,
                    content=content,
                    author=request.user,
                    category=form.cleaned_data.get('category') or None,
                    collection=form.cleaned_data.get('collection') or None,
                    order_in_collection=form.cleaned_data.get('order_in_collection') or None,
                    cover=form.cleaned_data.get('cover') or None,
                    is_published=form.cleaned_data.get('is_published', True),
                    is_pinned=form.cleaned_data.get('is_pinned', False),
                    published_time=form.cleaned_data.get('published_time') or timezone.now(),
                )
                post.save()
                created_post = post
                if form.cleaned_data.get('tags'):
                    post.tags.set(form.cleaned_data['tags'])

                # 把临时目录改名为 <pk>,并改写正文中的路径前缀
                pk_dir = os.path.join(settings.MEDIA_ROOT, 'post_assets', str(post.pk))
                shutil.rmtree(pk_dir, ignore_errors=True)
                shutil.move(tmp_dir, pk_dir)
                tmp_dir = pk_dir  # 更新引用,便于异常时清理
                pk_base_url = f'{settings.MEDIA_URL}post_assets/{post.pk}'
                if tmp_base_url != pk_base_url:
                    post.content = post.content.replace(tmp_base_url, pk_base_url)
                    post.save(update_fields=['content', 'modified_time'])

                messages.success(
                    request,
                    f'已从 zip 创建文章「{post.title}」,资源已托管({file_count} 个文件)。'
                )
                return redirect(reverse('manage:post_update', args=[post.pk]))
            except ValueError as e:
                messages.error(request, f'zip 解析失败:{e}')
            except Exception as e:
                messages.error(request, f'上传失败:{e}')
            # 失败回滚:删 Post + 清理目录
            if created_post is not None:
                pk_to_clean = created_post.pk
                created_post.delete()
                for d in (
                    tmp_dir,
                    os.path.join(settings.MEDIA_ROOT, 'post_assets', str(pk_to_clean)),
                ):
                    if os.path.isdir(d):
                        shutil.rmtree(d, ignore_errors=True)
            elif os.path.isdir(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
    else:
        initial = {
            'is_published': True,
            'is_pinned': False,
            'published_time': timezone.now().strftime('%Y-%m-%dT%H:%M'),
        }
        form = PostUploadZipForm(initial=initial)
    return render(request, 'manage/post_upload_zip.html', _manage_context(
        active_menu='posts',
        form=form,
    ))


# ============================================================================
# 分类 CRUD
# ============================================================================

@login_required
def category_list(request):
    qs = Category.objects.annotate(post_count_total=Count('posts')).order_by('name')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    page_obj = _paginated(request, qs, per_page=20)
    return render(request, 'manage/category_list.html', _manage_context(
        active_menu='categories',
        page_obj=page_obj,
        q=q,
        qs=_qs(request),
    ))


@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'分类「{obj.name}」已创建。')
            return redirect(reverse('manage:category_list'))
    else:
        form = CategoryForm()
    return render(request, 'manage/category_form.html', _manage_context(
        active_menu='categories',
        form=form,
        is_create=True,
        form_title='新建分类',
    ))


@login_required
def category_update(request, pk):
    obj = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'分类「{obj.name}」已更新。')
            return redirect(reverse('manage:category_list'))
    else:
        form = CategoryForm(instance=obj)
    return render(request, 'manage/category_form.html', _manage_context(
        active_menu='categories',
        form=form,
        is_create=False,
        form_title='编辑分类',
    ))


@login_required
@require_http_methods(['POST'])
def category_delete(request, pk):
    obj = get_object_or_404(Category, pk=pk)
    name = obj.name
    # 关联文章的 category 会被 SET_NULL,不会报错
    obj.delete()
    messages.success(request, f'分类「{name}」已删除,其下文章的分类已置空。')
    return redirect(reverse('manage:category_list'))


# ============================================================================
# 标签 CRUD
# ============================================================================

@login_required
def tag_list(request):
    qs = Tag.objects.annotate(post_count_total=Count('posts')).order_by('name')
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(name__icontains=q)
    page_obj = _paginated(request, qs, per_page=30)
    return render(request, 'manage/tag_list.html', _manage_context(
        active_menu='tags',
        page_obj=page_obj,
        q=q,
        qs=_qs(request),
    ))


@login_required
def tag_create(request):
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'标签「{obj.name}」已创建。')
            return redirect(reverse('manage:tag_list'))
    else:
        form = TagForm()
    return render(request, 'manage/tag_form.html', _manage_context(
        active_menu='tags',
        form=form,
        is_create=True,
        form_title='新建标签',
    ))


@login_required
def tag_update(request, pk):
    obj = get_object_or_404(Tag, pk=pk)
    if request.method == 'POST':
        form = TagForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'标签「{obj.name}」已更新。')
            return redirect(reverse('manage:tag_list'))
    else:
        form = TagForm(instance=obj)
    return render(request, 'manage/tag_form.html', _manage_context(
        active_menu='tags',
        form=form,
        is_create=False,
        form_title='编辑标签',
    ))


@login_required
@require_http_methods(['POST'])
def tag_delete(request, pk):
    obj = get_object_or_404(Tag, pk=pk)
    name = obj.name
    obj.delete()
    messages.success(request, f'标签「{name}」已删除。')
    return redirect(reverse('manage:tag_list'))


# ============================================================================
# 评论:列表 / 审核切换 / 删除
# ============================================================================

@login_required
def comment_list(request):
    qs = Comment.objects.select_related('post').all()
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    if q:
        qs = qs.filter(Q(author__icontains=q) | Q(content__icontains=q) | Q(post__title__icontains=q))
    if status == 'approved':
        qs = qs.filter(is_approved=True)
    elif status == 'pending':
        qs = qs.filter(is_approved=False)
    qs = qs.order_by('-created_time')
    page_obj = _paginated(request, qs, per_page=20)
    return render(request, 'manage/comment_list.html', _manage_context(
        active_menu='comments',
        page_obj=page_obj,
        q=q,
        status=status,
        qs=_qs(request),
    ))


@login_required
@require_http_methods(['POST'])
def comment_toggle_approve(request, pk):
    obj = get_object_or_404(Comment, pk=pk)
    obj.is_approved = not obj.is_approved
    obj.save(update_fields=['is_approved', 'modified_time'])
    state = '通过' if obj.is_approved else '取消'
    messages.success(request, f'评论#{obj.pk} 已{state}审核。')
    return redirect(reverse('manage:comment_list') + f'?{request.GET.urlencode()}')


@login_required
@require_http_methods(['POST'])
def comment_delete(request, pk):
    obj = get_object_or_404(Comment, pk=pk)
    obj.delete()
    messages.success(request, '评论已删除。')
    return redirect(reverse('manage:comment_list') + f'?{request.GET.urlencode()}')


# ============================================================================
# 首页 Hero 配置(单例,只允许编辑)
# ============================================================================


@login_required
def hero_edit(request):
    """Hero 站点配置编辑:单例(禁止新增/删除)。"""
    config = SiteConfig.get_solo()
    if request.method == 'POST':
        form = SiteConfigForm(request.POST, request.FILES, instance=config)
        if form.is_valid():
            saved = form.save()
            # 若用户在表单里没选 hero_bg_image,但勾了 BackgroundImage.is_active,
            # 自动把当前 is_active 那张设为 config.hero_bg_image,保持一致
            if (
                saved.hero_bg_image is None
                and BackgroundImage.objects.filter(is_active=True).exists()
            ):
                saved.hero_bg_image = BackgroundImage.objects.filter(
                    is_active=True
                ).first()
                saved.save(update_fields=['hero_bg_image'])
            messages.success(request, 'Hero 配置已更新。')
            return redirect(reverse('manage:hero_edit'))
        if form.non_field_errors():
            for err in form.non_field_errors():
                messages.error(request, err)
    else:
        form = SiteConfigForm(instance=config)
    return render(request, 'manage/hero_edit.html', _manage_context(
        active_menu='hero',
        form=form,
        config=config,
        font_size_fields=[
            form[f] for f in (
                'hero_eyebrow_fs', 'hero_title_fs', 'hero_subtitle_fs', 'hero_meta_fs',
                'card_big_fs', 'card_text_fs',
                'post_title_fs', 'post_excerpt_fs', 'post_meta_fs',
            )
        ],
    ))


@login_required
def about_edit(request):
    """关于页内容编辑:存到 SiteConfig.about_markdown(单例)。"""
    config = SiteConfig.get_solo()
    if request.method == 'POST':
        form = AboutForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, '关于页内容已更新。')
            return redirect(reverse('manage:about_edit'))
        if form.non_field_errors():
            for err in form.non_field_errors():
                messages.error(request, err)
    else:
        form = AboutForm(instance=config)
    return render(request, 'manage/about_edit.html', _manage_context(
        active_menu='about',
        form=form,
    ))


# ============================================================================
# Hero 背景图库 CRUD
# ============================================================================


@login_required
def background_list(request):
    """Hero 背景图列表。"""
    qs = BackgroundImage.objects.all().order_by('-is_active', '-uploaded_at')
    return render(request, 'manage/background_list.html', _manage_context(
        active_menu='backgrounds',
        page_obj=_paginated(request, qs, per_page=20),
    ))


@login_required
def background_new(request):
    """上传背景图。"""
    if request.method == 'POST':
        form = BackgroundImageForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'背景图「{obj}」已上传。')
            return redirect(reverse('manage:background_list'))
        if form.non_field_errors():
            for err in form.non_field_errors():
                messages.error(request, err)
    else:
        form = BackgroundImageForm()
    return render(request, 'manage/background_form.html', _manage_context(
        active_menu='backgrounds',
        form=form,
        form_title='上传背景图',
    ))


@login_required
def background_edit(request, pk):
    """编辑背景图(改标题/切换是否启用)。"""
    obj = get_object_or_404(BackgroundImage, pk=pk)
    if request.method == 'POST':
        form = BackgroundImageForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            saved = form.save()
            # 若启用了这张,同步更新 SiteConfig.hero_bg_image
            if saved.is_active:
                cfg = SiteConfig.get_solo()
                cfg.hero_bg_image = saved
                cfg.save()
            messages.success(request, f'背景图「{saved}」已更新。')
            return redirect(reverse('manage:background_list'))
        if form.non_field_errors():
            for err in form.non_field_errors():
                messages.error(request, err)
    else:
        form = BackgroundImageForm(instance=obj)
    return render(request, 'manage/background_form.html', _manage_context(
        active_menu='backgrounds',
        form=form,
        form_title='编辑背景图',
        obj=obj,
    ))


@login_required
@require_http_methods(['POST'])
def background_delete(request, pk):
    obj = get_object_or_404(BackgroundImage, pk=pk)
    # 如果 SiteConfig 正在引用这张,先把引用置空,避免 FK 约束
    SiteConfig.objects.filter(hero_bg_image=obj).update(hero_bg_image=None)
    # 删图片文件 + DB 行
    if obj.image:
        try:
            obj.image.delete(save=False)
        except Exception:
            pass
    obj.delete()
    messages.success(request, '背景图已删除。')
    return redirect(reverse('manage:background_list'))


@login_required
@require_http_methods(['POST'])
def background_set_active(request, pk):
    """快捷:把指定背景图设为当前启用(自动取消其他)并同步到 SiteConfig。"""
    obj = get_object_or_404(BackgroundImage, pk=pk)
    obj.is_active = True
    obj.save(update_fields=['is_active', 'modified_time'])
    cfg = SiteConfig.get_solo()
    cfg.hero_bg_image = obj
    cfg.save()
    messages.success(request, f'「{obj}」已设为当前 Hero 背景。')
    return redirect(reverse('manage:background_list'))


# ============================================================================
# 合集 CRUD
# ============================================================================


@login_required
def collection_list(request):
    """合集列表:按最近修改倒序,支持搜索(合集名/描述)。"""
    q = request.GET.get('q', '').strip()
    qs = Collection.objects.all().order_by('-is_published', '-modified_time')
    if q:
        qs = qs.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )
    ctx = _manage_context(
        active_menu='collections',
        page_obj=_paginated(request, qs, per_page=20),
        q=q,
        total=qs.count(),
    )
    return render(request, 'manage/collection_list.html', ctx)


@login_required
def collection_new(request):
    """新建合集。"""
    if request.method == 'POST':
        form = CollectionForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.author = request.user
            obj.save()
            form.save_m2m()
            messages.success(request, f'合集「{obj}」已创建。')
            return redirect(reverse('manage:collection_list'))
        if form.non_field_errors():
            for err in form.non_field_errors():
                messages.error(request, err)
    else:
        form = CollectionForm()
    return render(request, 'manage/collection_form.html', _manage_context(
        active_menu='collections',
        form=form,
        form_title='新建合集',
    ))


@login_required
def collection_update(request, pk):
    """编辑合集。"""
    obj = get_object_or_404(Collection, pk=pk)
    if request.method == 'POST':
        form = CollectionForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            saved = form.save()
            messages.success(request, f'合集「{saved}」已更新。')
            return redirect(reverse('manage:collection_list'))
        if form.non_field_errors():
            for err in form.non_field_errors():
                messages.error(request, err)
    else:
        form = CollectionForm(instance=obj)
    # 顺便把当前合集下的文章列出来(只读参考)
    related_posts = list(obj.posts.all().order_by(
        F('order_in_collection').asc(nulls_last=True), 'published_time'
    )) if obj.pk else []
    # 可添加文章: 仅在输入搜索词时查询, 避免把全部文章渲染到页面(文章会越来越多)
    q_add = request.GET.get('q_add', '').strip()
    available_posts = []
    if q_add:
        available = Post.objects.exclude(pk__in=obj.posts.values_list('pk', flat=True))
        available = available.filter(Q(title__icontains=q_add) | Q(slug__icontains=q_add))
        available_posts = list(available.order_by('-published_time')[:20])
    return render(request, 'manage/collection_form.html', _manage_context(
        active_menu='collections',
        form=form,
        form_title='编辑合集',
        obj=obj,
        related_posts=related_posts,
        available_posts=available_posts,
        q_add=q_add,
    ))


@login_required
@require_http_methods(['POST'])
def collection_delete(request, pk):
    obj = get_object_or_404(Collection, pk=pk)
    name = str(obj)
    # 清空所有引用此合集的文章的 FK(不删文章本身)
    Post.objects.filter(collection=obj).update(collection=None, order_in_collection=None)
    # 删封面文件 + DB 行
    if obj.cover:
        try:
            obj.cover.delete(save=False)
        except Exception:
            pass
    obj.delete()
    messages.success(request, f'合集「{name}」已删除(旗下文章未被删除,合集关联已解除)。')
    return redirect(reverse('manage:collection_list'))


@login_required
@require_http_methods(['POST'])
def collection_toggle_publish(request, pk):
    obj = get_object_or_404(Collection, pk=pk)
    obj.is_published = not obj.is_published
    obj.save(update_fields=['is_published', 'modified_time'])
    state = '已发布' if obj.is_published else '已下架'
    messages.success(request, f'合集「{obj}」{state}。')
    return redirect(reverse('manage:collection_list') + f'?{request.GET.urlencode()}')


@login_required
@require_http_methods(['POST'])
def collection_remove_post(request, collection_pk, post_pk):
    """把文章移出合集(不删除文章,仅解除关联与顺序)。"""
    obj = get_object_or_404(Collection, pk=collection_pk)
    post = get_object_or_404(Post, pk=post_pk, collection=obj)
    post.collection = None
    post.order_in_collection = None
    post.save(update_fields=['collection', 'order_in_collection', 'modified_time'])
    # 重新编号剩余文章的合集内顺序(1,2,3...), 保持连续
    remaining = list(obj.posts.all().order_by(
        F('order_in_collection').asc(nulls_last=True), 'published_time'
    ))
    for idx, p in enumerate(remaining, start=1):
        if p.order_in_collection != idx:
            p.order_in_collection = idx
            p.save(update_fields=['order_in_collection'])
    messages.success(request, f'文章「{post.title}」已移出合集「{obj.name}」(文章本身未删除)。')
    return redirect(reverse('manage:collection_update', args=[obj.pk]))


@login_required
@require_http_methods(['POST'])
def collection_add_post(request, collection_pk, post_pk):
    """把文章添加到合集末尾(不改动文章其他属性)。"""
    obj = get_object_or_404(Collection, pk=collection_pk)
    post = get_object_or_404(Post, pk=post_pk)
    if post.collection_id == obj.pk:
        messages.error(request, f'文章「{post.title}」已在合集「{obj.name}」中。')
    else:
        max_order = obj.posts.aggregate(m=Max('order_in_collection'))['m'] or 0
        post.collection = obj
        post.order_in_collection = max_order + 1
        post.save(update_fields=['collection', 'order_in_collection', 'modified_time'])
        messages.success(request, f'文章「{post.title}」已添加到合集「{obj.name}」(排在末尾第 {max_order + 1} 篇)。')
    return redirect(reverse('manage:collection_update', args=[obj.pk]))


@login_required
@require_http_methods(['POST'])
def collection_reorder(request, pk):
    """拖拽排序: 按提交的文章 id 顺序重写 order_in_collection。"""
    from django.http import JsonResponse
    obj = get_object_or_404(Collection, pk=pk)
    ids = [int(x) for x in request.POST.getlist('post_ids') if x.strip().isdigit()]
    valid = set(obj.posts.values_list('pk', flat=True))
    idx = 1
    updated = 0
    for pid in ids:
        if pid in valid:
            Post.objects.filter(pk=pid).update(order_in_collection=idx)
            idx += 1
            updated += 1
    # 未提交到的本合集文章(兜底)排到末尾, 保证顺序完整
    rest = Post.objects.filter(collection=obj).exclude(pk__in=ids).order_by('order_in_collection')
    for p in rest:
        Post.objects.filter(pk=p.pk).update(order_in_collection=idx)
        idx += 1
    return JsonResponse({'ok': True, 'updated': updated})


# ============================================================================
# 项目分类 CRUD
# ============================================================================

@login_required
def project_category_list(request):
    qs = ProjectCategory.objects.annotate(project_count_total=Count('projects')).order_by(
        'sort_order', 'name'
    )
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q))
    page_obj = _paginated(request, qs, per_page=20)
    return render(request, 'manage/project_category_list.html', _manage_context(
        active_menu='project_categories',
        page_obj=page_obj,
        q=q,
    ))


@login_required
def project_category_create(request):
    if request.method == 'POST':
        form = ProjectCategoryForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'项目分类「{obj.name}」已创建。')
            return redirect(reverse('manage:project_category_list'))
    else:
        form = ProjectCategoryForm()
    return render(request, 'manage/project_category_form.html', _manage_context(
        active_menu='project_categories',
        form=form,
        is_create=True,
        form_title='新建项目分类',
    ))


@login_required
def project_category_update(request, pk):
    obj = get_object_or_404(ProjectCategory, pk=pk)
    if request.method == 'POST':
        form = ProjectCategoryForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'项目分类「{obj.name}」已更新。')
            return redirect(reverse('manage:project_category_list'))
    else:
        form = ProjectCategoryForm(instance=obj)
    return render(request, 'manage/project_category_form.html', _manage_context(
        active_menu='project_categories',
        form=form,
        is_create=False,
        form_title='编辑项目分类',
    ))


@login_required
@require_http_methods(['POST'])
def project_category_delete(request, pk):
    obj = get_object_or_404(ProjectCategory, pk=pk)
    name = obj.name
    # 关联项目的 category 会被 SET_NULL,不会报错
    obj.delete()
    messages.success(request, f'项目分类「{name}」已删除,其下项目已归入未分类。')
    return redirect(reverse('manage:project_category_list'))


# ============================================================================
# 项目 CRUD
# ============================================================================

@login_required
def project_list(request):
    qs = Project.objects.select_related('category').order_by(
        'sort_order', '-created_time'
    )
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '').strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if cat.isdigit():
        qs = qs.filter(category_id=int(cat))
    page_obj = _paginated(request, qs, per_page=20)
    return render(request, 'manage/project_list.html', _manage_context(
        active_menu='projects',
        page_obj=page_obj,
        q=q,
        cat=cat,
        categories=ProjectCategory.objects.order_by('sort_order', 'name'),
    ))


@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f'项目「{obj.name}」已创建。')
            return redirect(reverse('manage:project_list'))
    else:
        form = ProjectForm()
    return render(request, 'manage/project_form.html', _manage_context(
        active_menu='projects',
        form=form,
        is_create=True,
        form_title='新建项目',
    ))


@login_required
def project_update(request, pk):
    obj = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'项目「{obj.name}」已更新。')
            return redirect(reverse('manage:project_list'))
    else:
        form = ProjectForm(instance=obj)
    return render(request, 'manage/project_form.html', _manage_context(
        active_menu='projects',
        form=form,
        is_create=False,
        form_title='编辑项目',
        obj=obj,
    ))


@login_required
@require_http_methods(['POST'])
def project_delete(request, pk):
    obj = get_object_or_404(Project, pk=pk)
    name = obj.name
    if obj.cover:
        try:
            obj.cover.delete(save=False)
        except Exception:
            pass
    obj.delete()
    messages.success(request, f'项目「{name}」已删除。')
    return redirect(reverse('manage:project_list'))


@login_required
@require_http_methods(['POST'])
def project_toggle_publish(request, pk):
    obj = get_object_or_404(Project, pk=pk)
    obj.is_published = not obj.is_published
    obj.save(update_fields=['is_published', 'modified_time'])
    state = '已发布' if obj.is_published else '已下架'
    messages.success(request, f'项目「{obj}」{state}。')
    return redirect(reverse('manage:project_list') + f'?{request.GET.urlencode()}')


