"""
后台管理配置。

后台访问路径在 toflower_blog/urls.py 中配置为 /dijia(而非默认 /admin)。
此处注册 Category / Tag / Post / Comment 四个模型,并定制列表、过滤器、批量操作。
"""

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import (
    BackgroundImage,
    Category,
    Comment,
    Post,
    Project,
    ProjectCategory,
    SiteConfig,
    Tag,
)
from toflower_blog import settings as project_settings


# ============================================================================
# 自定义后台站点标题(对应 settings.SITE_CONFIG 中的设定)
# ============================================================================

admin.site.site_header = project_settings.admin_site_header
admin.site.site_title = project_settings.admin_site_title
admin.site.index_title = project_settings.admin_index_title


# ============================================================================
# 自定义批量操作
# ============================================================================

@admin.action(description=_('标记为已发布'))
def make_published(modeladmin, request, queryset):
    queryset.update(is_published=True)


@admin.action(description=_('下架(取消发布)'))
def make_unpublished(modeladmin, request, queryset):
    queryset.update(is_published=False)


@admin.action(description=_('置顶'))
def make_pinned(modeladmin, request, queryset):
    queryset.update(is_pinned=True)


@admin.action(description=_('取消置顶'))
def make_unpinned(modeladmin, request, queryset):
    queryset.update(is_pinned=False)


@admin.action(description=_('审核通过'))
def approve_comments(modeladmin, request, queryset):
    queryset.update(is_approved=True)


@admin.action(description=_('取消审核'))
def unapprove_comments(modeladmin, request, queryset):
    queryset.update(is_approved=False)


# ============================================================================
# ModelAdmin 注册
# ============================================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'description', 'post_count', 'created_time')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

    def post_count(self, obj):
        return obj.post_count
    post_count.short_description = '文章数'


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'post_count', 'created_time')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

    def post_count(self, obj):
        return obj.post_count
    post_count.short_description = '文章数'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'author', 'category', 'is_pinned', 'is_published',
        'views', 'comment_count', 'published_time',
    )
    list_filter = ('is_published', 'is_pinned', 'category', 'tags', 'created_time')
    search_fields = ('title', 'slug', 'content', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    date_hierarchy = 'published_time'
    ordering = ('-is_pinned', '-published_time')
    actions = [make_published, make_unpublished, make_pinned, make_unpinned]
    readonly_fields = ('views', 'created_time', 'modified_time')

    fieldsets = (
        (_('基本信息'), {
            'fields': ('title', 'slug', 'author', 'category', 'tags'),
        }),
        (_('正文'), {
            'fields': ('content', 'excerpt', 'cover'),
            'description': _('正文支持 Markdown 语法。代码块使用 ``` 包裹,例如 ```python ... ```'),
        }),
        (_('发布设置'), {
            'fields': ('is_published', 'is_pinned', 'published_time'),
        }),
        (_('统计信息'), {
            'fields': ('views', 'created_time', 'modified_time'),
            'classes': ('collapse',),
        }),
    )

    def comment_count(self, obj):
        return obj.comment_count
    comment_count.short_description = '评论数'

    def save_model(self, request, obj, form, change):
        """保存时自动填充作者为当前登录用户。"""
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'email', 'post_link', 'is_approved', 'created_time')
    list_filter = ('is_approved', 'created_time')
    search_fields = ('author', 'email', 'content', 'post__title')
    actions = [approve_comments, unapprove_comments]
    ordering = ('-created_time',)

    def post_link(self, obj):
        url = obj.post.get_absolute_url() if obj.post_id else None
        if url:
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.post.title[:30])
        return '—'
    post_link.short_description = '文章'


# ============================================================================
# 项目 / 项目分类
# ============================================================================

@admin.register(ProjectCategory)
class ProjectCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order', 'project_count', 'created_time')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('sort_order', 'name')

    def project_count(self, obj):
        return obj.project_count
    project_count.short_description = '项目数'


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'url', 'is_published', 'sort_order', 'created_time')
    list_filter = ('is_published', 'category')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_published', 'sort_order')
    ordering = ('sort_order', '-created_time')
    actions = [make_published, make_unpublished]


# ============================================================================
# Hero 背景图管理(列表显示缩略图 + "设为当前"按钮)
# ============================================================================

@admin.register(BackgroundImage)
class BackgroundImageAdmin(admin.ModelAdmin):
    list_display = ('thumbnail_preview', 'title', 'is_active_badge', 'uploaded_at', 'set_active_button')
    list_display_links = ('title',)
    search_fields = ('title',)
    list_filter = ('is_active',)
    ordering = ('-uploaded_at',)
    readonly_fields = ('uploaded_at', 'is_active')

    fieldsets = (
        (_('图片信息'), {
            'fields': ('title', 'image'),
        }),
        (_('状态'), {
            'fields': ('is_active', 'uploaded_at'),
            'description': _('"当前启用"通过列表页"设为当前"按钮切换,此处只读显示。'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request)

    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:96px;height:54px;object-fit:cover;border-radius:4px;'
                'border:1px solid #ddd;" alt="预览" />',
                obj.image.url,
            )
        return '—'
    thumbnail_preview.short_description = '预览'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<strong style="color:#0a7d24;">● 当前启用</strong>')
        return format_html('<span style="color:#999;">○ 未启用</span>')
    is_active_badge.short_description = '状态'

    def set_active_button(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#999;">已是当前</span>')
        url = reverse('admin:blog_backgroundimage_set_active', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="padding:4px 12px;">设为当前</a>', url
        )
    set_active_button.short_description = '操作'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<path:object_id>/set-active/',
                self.admin_site.admin_view(self.set_active_view),
                name='blog_backgroundimage_set_active',
            ),
        ]
        return custom + urls

    def set_active_view(self, request, object_id):
        from .models import BackgroundImage
        obj = BackgroundImage.objects.get(pk=object_id)
        obj.is_active = True
        obj.save()
        self.message_user(request, f'已将「{obj}」设为当前启用的背景图。')
        return redirect(reverse('admin:blog_backgroundimage_changelist'))


# ============================================================================
# 站点 Hero 配置(单例:只允许一条记录)
# ============================================================================

@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    """单例管理:禁止新增/删除,只允许编辑唯一一条记录。"""

    list_display = ('__str__', 'hero_animation_choice', 'hero_bg_type', 'hero_accent_word')
    fieldsets = (
        (_('文字内容'), {
            'fields': ('hero_eyebrow', 'hero_title', 'hero_accent_word', 'hero_subtitle'),
            'description': _('"高亮词"必须出现在"主标题"中,否则不会产生高亮效果。'),
        }),
        (_('动画 & 背景'), {
            'fields': ('hero_animation_choice', 'hero_bg_type', 'hero_bg_overlay',
                       'hero_bg_image', 'hero_bg_video'),
            'description': _('背景类型为 image 时使用"背景图片";为 video 时使用"背景视频"。'),
        }),
        (_('主按钮(CTA)'), {
            'fields': ('hero_cta_text', 'hero_cta_link'),
        }),
        (_('顶栏配色'), {
            'fields': ('header_color_mode', 'header_color', 'header_text_color'),
            'description': _('自动模式从壁纸主色自动配深/浅文字;手动模式用指定颜色作顶栏背景,可选指定文字颜色。'),
        }),
        (_('文章阅读风格'), {
            'fields': ('post_style',),
            'description': _('文章详情页正文的默认阅读风格;访客仍可在文章页顶部手动切换并记忆到本地。'),
        }),
    )

    def has_add_permission(self, request):
        # 已存在记录时禁止新增
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        # 仍返回全部(只有一条),但避免误显示
        return super().get_queryset(request)

    def response_add(self, request, obj, post_url_continue=None):
        # 新增后直接跳回 changelist(单例,不会再新增)
        return redirect(reverse('admin:blog_siteconfig_changelist'))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # 若访问的 id 不存在,但存在记录,则重定向到正确 id
        if not SiteConfig.objects.filter(pk=object_id).exists():
            solo = SiteConfig.get_solo()
            return redirect(reverse('admin:blog_siteconfig_change', args=[solo.pk]))
        return super().change_view(request, object_id, form_url, extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        # 若已有记录,新增按钮跳转到编辑页
        if SiteConfig.objects.exists():
            solo = SiteConfig.objects.first()
            return redirect(reverse('admin:blog_siteconfig_change', args=[solo.pk]))
        return super().add_view(request, form_url, extra_context)
