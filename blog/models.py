"""
博客数据模型:Category / Tag / Post / Comment。

设计要点:
- slug 字段用于 SEO 友好 URL,自动从 name/title 生成
- Post.content 存 Markdown 原文,渲染由 utils.render_markdown 完成
- 浏览量、评论数通过属性方法动态计算
- 软删除(发布开关 is_published),不真正物理删除
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class PublishedManager(models.Manager):
    """只返回已发布文章的查询管理器。"""

    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


class TimeStampedModel(models.Model):
    """所有模型的抽象基类:提供创建/修改时间。"""

    created_time = models.DateTimeField('创建时间', auto_now_add=True, db_index=True)
    modified_time = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        abstract = True


class Category(TimeStampedModel):
    """文章分类:一对多关联 Post。"""

    name = models.CharField('名称', max_length=64, unique=True)
    # allow_unicode=True:允许中文/非 ASCII 字符作为 URL 别名,
    # 模型层本身也用 slugify(allow_unicode=True) 生成。
    slug = models.SlugField(
        'URL 别名', max_length=80, unique=True, blank=True, allow_unicode=True,
    )
    description = models.CharField('描述', max_length=200, blank=True, default='')

    objects = models.Manager()

    class Meta:
        verbose_name = '分类'
        verbose_name_plural = '分类'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True) or f'cat-{self.pk or Category.objects.count() + 1}'
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:category', kwargs={'slug': self.slug})

    @property
    def post_count(self):
        return self.posts.filter(is_published=True).count()


class Tag(TimeStampedModel):
    """文章标签:多对多关联 Post。"""

    name = models.CharField('名称', max_length=32, unique=True)
    slug = models.SlugField(
        'URL 别名', max_length=48, unique=True, blank=True, allow_unicode=True,
    )

    objects = models.Manager()

    class Meta:
        verbose_name = '标签'
        verbose_name_plural = '标签'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True) or f'tag-{self.pk or Tag.objects.count() + 1}'
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:tag', kwargs={'slug': self.slug})

    @property
    def post_count(self):
        return self.posts.filter(is_published=True).count()


class Collection(TimeStampedModel):
    """
    合集:把多篇文章(读书笔记)按顺序归到一个主题下。

    与分类/标签的区别:分类是"横向标签式"归并(读书/技术/生活),合集是"纵向系列式"归并
    (毛选笔记第 1 篇→第 2 篇……)。一篇文章同时属于一个分类和最多一个合集。
    """

    name = models.CharField('合集名', max_length=120, unique=True)
    slug = models.SlugField(
        'URL 别名', max_length=140, unique=True, blank=True, allow_unicode=True,
    )
    description = models.CharField('简介', max_length=300, blank=True, default='')
    cover = models.ImageField(
        '合集封面', upload_to='collections/', blank=True, null=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='collections', verbose_name='作者',
    )
    is_published = models.BooleanField('已发布', default=True, db_index=True)

    objects = models.Manager()

    class Meta:
        verbose_name = '合集'
        verbose_name_plural = '合集'
        ordering = ['-modified_time']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or 'collection'
            slug = base
            i = 2
            while Collection.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{i}'
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:collection_detail', kwargs={'slug': self.slug})

    @property
    def post_count(self):
        return self.posts.filter(is_published=True).count()

    @property
    def posts_ordered(self):
        """合集内的文章顺序:先按 order_in_collection,再按发布时间。"""
        return (
            self.posts.filter(is_published=True)
            .order_by(F('order_in_collection').asc(nulls_last=True), 'published_time')
        )

    def get_post_position(self, post):
        """返回某篇文章在合集中是第几篇(1 起),不在此合集中返回 None。
        同时返回 (prev_post, next_post) 用于翻页导航。"""
        if post.collection_id != self.pk:
            return None, None, None
        qs = list(self.posts_ordered)
        pks = [p.pk for p in qs]
        try:
            idx = pks.index(post.pk)
        except ValueError:
            return None, None, None
        prev_post = qs[idx - 1] if idx > 0 else None
        next_post = qs[idx + 1] if idx + 1 < len(qs) else None
        return idx + 1, prev_post, next_post


class ProjectCategory(TimeStampedModel):
    """项目分类:如 算法 / 网页组件 / 工具库 / 游戏 / 站点 / 数据 / 其他。"""

    name = models.CharField('名称', max_length=64, unique=True)
    slug = models.SlugField(
        'URL 别名', max_length=80, unique=True, blank=True, allow_unicode=True,
    )
    sort_order = models.PositiveSmallIntegerField(
        '排序', default=0, help_text='数字越小越靠前',
    )

    objects = models.Manager()

    class Meta:
        verbose_name = '项目分类'
        verbose_name_plural = '项目分类'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or 'project-category'
            slug = base
            i = 2
            while ProjectCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{i}'
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def project_count(self):
        return self.projects.filter(is_published=True).count()


class Project(TimeStampedModel):
    """项目展示:名称 + 简介 + 跳转链接,按分类分组(仿 passer-by.com/project.html)。"""

    name = models.CharField('项目名称', max_length=200, db_index=True)
    slug = models.SlugField(
        'URL 别名', max_length=220, unique=True, blank=True, allow_unicode=True,
    )
    description = models.CharField('简介', max_length=300, blank=True, default='')
    url = models.URLField(
        '项目链接', max_length=300,
        help_text='「查看项目」跳转地址,支持 https:// 外链或 /xxx/ 站内路径。',
    )
    cover = models.ImageField(
        '封面/图标', upload_to='projects/', blank=True, null=True,
        help_text='可选,建议正方形,展示在项目卡片上。',
    )
    category = models.ForeignKey(
        ProjectCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='projects', verbose_name='分类',
    )
    sort_order = models.PositiveSmallIntegerField(
        '排序', default=0, help_text='数字越小越靠前',
    )
    is_published = models.BooleanField('已发布', default=True, db_index=True)

    objects = models.Manager()
    published = PublishedManager()

    class Meta:
        verbose_name = '项目'
        verbose_name_plural = '项目'
        ordering = ['sort_order', '-created_time']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name, allow_unicode=True) or 'project'
            slug = base
            i = 2
            while Project.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{i}'
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Post(TimeStampedModel):
    """文章主体模型。"""

    title = models.CharField('标题', max_length=200, db_index=True)
    slug = models.SlugField(
        'URL 别名', max_length=220, unique=True, blank=True, allow_unicode=True,
    )
    content = models.TextField('正文(Markdown)')
    excerpt = models.CharField('摘要', max_length=220, blank=True, default='')
    cover = models.ImageField('封面图', upload_to='covers/', blank=True, null=True)

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='posts', verbose_name='分类',
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts', verbose_name='标签')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='posts', verbose_name='作者',
    )
    collection = models.ForeignKey(
        Collection, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='posts', verbose_name='所属合集',
    )
    order_in_collection = models.PositiveSmallIntegerField(
        '在合集中的序号', blank=True, null=True,
        help_text='不填则按发布时间自动排;手动填 1、2、3……可自由指定顺序。',
        validators=[MinValueValidator(1), MaxValueValidator(9999)],
    )

    views = models.PositiveIntegerField('浏览量', default=0)
    is_published = models.BooleanField('已发布', default=True, db_index=True)
    is_pinned = models.BooleanField('置顶', default=False, db_index=True)
    published_time = models.DateTimeField('发布时间', default=timezone.now, db_index=True)

    # 管理器:published 仅返回已发布;objects 返回全部(后台用)
    objects = models.Manager()
    published = PublishedManager()

    class Meta:
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-is_pinned', '-published_time', '-created_time']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # 自动生成 slug
        if not self.slug:
            base = slugify(self.title, allow_unicode=True) or 'post'
            slug = base
            i = 2
            # 处理 slug 唯一冲突
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{i}'
                i += 1
            self.slug = slug
        # 自动生成摘要
        if not self.excerpt:
            from blog.utils import make_excerpt
            self.excerpt = make_excerpt(self.content, length=200)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})

    @property
    def rendered_content(self):
        """渲染后的 HTML 正文(不缓存到库,每次调用即时渲染,utils 内部有 LRU 缓存)。"""
        from blog.utils import render_markdown
        return render_markdown(self.content)

    @property
    def reading_minutes(self):
        from blog.utils import reading_time
        return reading_time(self.content)

    @property
    def comment_count(self):
        return self.comments.filter(is_approved=True).count()

    def increase_views(self):
        """浏览量 +1,使用 F() 避免并发竞态。"""
        from django.db.models import F
        Post.objects.filter(pk=self.pk).update(views=F('views') + 1)
        # 刷新实例内存中的值
        self.views += 1


class Comment(TimeStampedModel):
    """评论:关联 Post,支持简单审核机制。"""

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name='文章')
    author = models.CharField('昵称', max_length=64)
    email = models.EmailField('邮箱')
    website = models.URLField('网站', blank=True, default='')
    content = models.TextField('评论内容', max_length=1000)
    is_approved = models.BooleanField('已审核', default=False, db_index=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='replies', verbose_name='父评论',
    )

    objects = models.Manager()

    class Meta:
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['created_time']

    def __str__(self):
        return f'{self.author} → {self.post.title[:20]}'

    @property
    def avatar_hash(self):
        """生成头像 hash(用于 gravatar 等头像服务)。"""
        import hashlib
        return hashlib.md5(self.email.strip().lower().encode('utf-8')).hexdigest()


# ============================================================================
# 首页 Hero 配置(单例)
# ============================================================================

class BackgroundImage(TimeStampedModel):
    """Hero 可选背景图库:可上传多张,通过 is_active 标记当前使用的那张。"""

    title = models.CharField('标题', max_length=120, blank=True, default='')
    image = models.ImageField('图片', upload_to='hero/bg/')
    is_active = models.BooleanField('当前启用', default=False, db_index=True)
    uploaded_at = models.DateTimeField('上传时间', auto_now_add=True)

    objects = models.Manager()

    class Meta:
        verbose_name = 'Hero 背景图'
        verbose_name_plural = 'Hero 背景图'
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title or f'背景图 #{self.pk}'

    def save(self, *args, **kwargs):
        # 同一时间只允许一张 is_active=True
        if self.is_active:
            BackgroundImage.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class SiteConfig(models.Model):
    """站点首页 Hero 配置(单例:全站只保留一条记录)。"""

    ANIMATION_CHOICES = (
        ('char_rise', '逐字上升(默认)'),
        ('fade_up', '整块淡入上移'),
        ('typewriter', '打字机'),
        ('glitch', '故障抖动'),
        ('slide_reveal', '滑入遮罩揭示'),
    )
    BG_TYPE_CHOICES = (
        ('none', '无背景(纯色)'),
        ('blob', '光晕 blob(默认)'),
        ('image', '静态图片'),
        ('video', '动态视频'),
    )
    HEADER_COLOR_MODE_CHOICES = (
        ('auto', '自动(从壁纸取色)'),
        ('manual', '手动指定颜色'),
    )

    hero_eyebrow = models.CharField(
        '眉标文字', max_length=120, default='Journal · 站名',
        help_text='Hero 顶部小字,可用 "Journal · 站名" 占位。',
    )
    hero_title = models.CharField(
        '主标题', max_length=200, default='文字,是思想的栖息地。',
        help_text='Hero 大标题。如需高亮某个词,请在"高亮词"字段填写该词(须与本字段中出现的词一致)。',
    )
    hero_accent_word = models.CharField(
        '高亮词', max_length=60, blank=True, default='思想',
        help_text='标题中要高亮(强调色 + 斜体)的词;留空则不高亮。该词必须在主标题中出现。',
    )
    hero_subtitle = models.TextField(
        '副标题', blank=True, default='记录代码、思考与生活的个人空间。',
    )
    hero_animation_choice = models.CharField(
        '入场动画', max_length=20, choices=ANIMATION_CHOICES, default='char_rise',
    )
    hero_bg_type = models.CharField(
        '背景类型', max_length=10, choices=BG_TYPE_CHOICES, default='blob',
    )
    hero_bg_image = models.ForeignKey(
        BackgroundImage, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='site_configs', verbose_name='背景图片',
        help_text='背景类型选"静态图片"时使用。也可在 BackgroundImage 列表里点"设为当前"。',
    )
    hero_bg_video = models.FileField(
        '背景视频', upload_to='hero/bg/', blank=True, null=True,
        help_text='背景类型选"动态视频"时使用。建议 mp4/webm,体积 < 5MB。',
    )
    hero_bg_overlay = models.FloatField(
        '背景遮罩透明度', default=0.35,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text='0~1 之间的数值,用于压暗背景图/视频以突出文字。0=无遮罩,1=全黑。',
    )
    hero_cta_text = models.CharField(
        '主按钮文字', max_length=40, default='开始阅读',
    )
    hero_cta_link = models.CharField(
        '主按钮链接', max_length=200, default='#posts',
        help_text='主按钮跳转地址。可用 #posts 锚点,或 /archive/ 等绝对路径。',
    )

    # ---------- 顶栏配色 ----------
    header_color_mode = models.CharField(
        '顶栏配色模式', max_length=10, choices=HEADER_COLOR_MODE_CHOICES, default='auto',
        help_text='自动: 从当前壁纸提取主色,自动选深/浅文字保证对比。手动: 用下方指定颜色作顶栏背景色。',
    )
    header_color = models.CharField(
        '顶栏背景色', max_length=7, blank=True, default='',
        help_text='仅「手动」模式生效。格式 #RRGGBB,建议取壁纸中的一个主色调。',
    )
    header_text_color = models.CharField(
        '顶栏文字颜色', max_length=7, blank=True, default='',
        help_text='仅「手动」模式生效,可选。格式 #RRGGBB。留空则按背景色自动选深/浅文字。',
    )

    # ---------- 文章阅读风格 ----------
    POST_STYLE_CHOICES = (
        ('default', '默认(站点编辑风格)'),
        ('github', 'GitHub README 风格'),
    )
    post_style = models.CharField(
        '文章阅读风格', max_length=10, choices=POST_STYLE_CHOICES, default='default',
        help_text='文章详情页正文的默认阅读风格。访客仍可在文章页顶部手动切换并记忆到本地。',
    )

    # ---------- 首页文字大小(单位 px,留空使用默认) ----------
    hero_eyebrow_fs = models.PositiveIntegerField(
        'Hero 眉标字号', blank=True, null=True, default=None,
        help_text='Hero 顶部小字(如 "Journal · 站名")的字号,单位 px。默认 18,留空用默认。',
    )
    hero_title_fs = models.PositiveIntegerField(
        'Hero 主标题字号', blank=True, null=True, default=None,
        help_text='Hero 大标题的字号,单位 px。默认 56,留空用默认。',
    )
    hero_subtitle_fs = models.PositiveIntegerField(
        'Hero 副标题字号', blank=True, null=True, default=None,
        help_text='Hero 副标题的字号,单位 px。默认 18,留空用默认。',
    )
    hero_meta_fs = models.PositiveIntegerField(
        'Hero 底部信息字号', blank=True, null=True, default=None,
        help_text='Hero 底部信息条(文章数/滚屏提示)的字号,单位 px。默认 12,留空用默认。',
    )
    card_big_fs = models.PositiveIntegerField(
        '卡片大数字字号', blank=True, null=True, default=None,
        help_text='功能卡片大数字(时钟时间/天气温度/统计数字)的字号,单位 px。默认 40,留空用默认。',
    )
    card_text_fs = models.PositiveIntegerField(
        '卡片正文字号', blank=True, null=True, default=None,
        help_text='功能卡片正文(导航/天气描述/热门标题/金句等)的字号,单位 px。默认 15,留空用默认。',
    )
    post_title_fs = models.PositiveIntegerField(
        '文章标题字号', blank=True, null=True, default=None,
        help_text='首页文章列表标题的字号,单位 px。默认 23,留空用默认。',
    )
    post_excerpt_fs = models.PositiveIntegerField(
        '文章摘要字号', blank=True, null=True, default=None,
        help_text='首页文章列表摘要的字号,单位 px。默认 15,留空用默认。',
    )
    post_meta_fs = models.PositiveIntegerField(
        '文章元信息字号', blank=True, null=True, default=None,
        help_text='首页文章列表元信息(日期/分类等)的字号,单位 px。默认 12,留空用默认。',
    )

    # ---------- 关于页 ----------
    about_markdown = models.TextField(
        '关于页内容(Markdown)', blank=True, default='',
        help_text='前台 /about/ 页面正文,支持 Markdown。留空则显示模板内置的默认关于内容。',
    )

    objects = models.Manager()

    class Meta:
        verbose_name = '站点 Hero 配置'
        verbose_name_plural = '站点 Hero 配置'

    def __str__(self):
        return '站点 Hero 配置'

    def save(self, *args, **kwargs):
        # 单例:只允许一条记录,新建时把已存在的清掉 pk 强制更新
        if not self.pk and SiteConfig.objects.exists():
            self.pk = SiteConfig.objects.first().pk
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        """获取全局唯一的 SiteConfig 实例(不存在则用默认值创建一条)。"""
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj
