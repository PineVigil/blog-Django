"""
自建后台(/dijia/)使用的表单:文章、分类、标签、评论审核。

设计要点:
- 文章表单覆盖后台所需的全部字段(标题/正文/封面/分类/标签/发布设置)
- 正文用 Textarea,不在前端做 Markdown 渲染,保存原文由前台渲染
- MD 上传单独一个表单,只接文件 + 元信息(分类/标签/发布设置)
- 不暴露 author 字段,由视图层自动填充当前登录用户
- slug 字段默认允许中英文混合(模型用 allow_unicode 生成,表单也需对应放宽校验)
"""

import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_str

from .models import (
    BackgroundImage,
    Category,
    Collection,
    Post,
    Project,
    ProjectCategory,
    SiteConfig,
    Tag,
)


def validate_unicode_slug(value):
    """宽松 slug 校验,与模型层 slugify(allow_unicode=True) 对齐。

    允许:中英文/字母/数字/下划线/连字符。空格和中文句号不允许。
    这比 Django 默认 validate_slug 更宽泛,但排除空格、换行、% 等可能破坏 URL 结构的字符。
    """
    v = smart_str(value or '')
    if v == '':
        return  # 允许空(表单层留空由模型 save 自动生成)
    if any(ch in v for ch in ' \t\n\r/#?&=%<>|"'):
        raise ValidationError(
            '不能包含空格、换行以及 # / ? & = % < > | " 等 URL 敏感字符。'
        )
    # 进一步用正则:允许任意 Unicode 字母/数字 + - _ + 中文
    if not re.match(r'^[\w\u4e00-\u9fff\-]+$', v, re.UNICODE):
        raise ValidationError(
            '只能包含中文、字母、数字、下划线(_)、连字符(-)。'
        )


class PostForm(forms.ModelForm):
    """文章新建/编辑表单。"""

    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'tag-checkbox-group'}),
        label='标签',
    )

    class Meta:
        model = Post
        fields = [
            'title', 'slug', 'content', 'excerpt', 'cover',
            'category', 'tags', 'collection', 'order_in_collection',
            'is_published', 'is_pinned', 'published_time',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '文章标题'}),
            'slug': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '留空自动生成',
                'autocomplete': 'off',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-textarea form-content',
                'placeholder': '支持 Markdown 语法……',
                'rows': 18,
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-textarea', 'rows': 2,
                'placeholder': '留空将自动从正文截取',
            }),
            'cover': forms.ClearableFileInput(attrs={'class': 'form-file'}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'collection': forms.Select(attrs={'class': 'form-input'}),
            'order_in_collection': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '1', 'max': '9999', 'step': '1',
                'placeholder': '留空按发布时间排',
            }),
            'published_time': forms.DateTimeInput(attrs={
                'class': 'form-input', 'type': 'datetime-local',
            }),
        }
        labels = {
            'slug': 'URL 别名',
            'cover': '封面图',
            'category': '分类',
            'collection': '所属合集',
            'order_in_collection': '合集内序号',
            'published_time': '发布时间',
        }
        help_texts = {
            'slug': '留空则根据标题自动生成。允许中文、字母、数字、下划线、连字符。',
            'excerpt': '为空时自动从正文提取前 200 字。',
            'collection': '把这篇文章放进一个合集(比如「毛选读书笔记」),用于按顺序阅读同主题的多篇。',
            'order_in_collection': '可选,1、2、3……指定在合集里的阅读顺序,不填则按发布时间自动排。',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # published_time 在表单中以 datetime-local 输入,需要去掉秒并按本地时间格式化
        if self.instance and self.instance.pk and self.instance.published_time:
            self.initial['published_time'] = self.instance.published_time.strftime(
                '%Y-%m-%dT%H:%M'
            )
        # 分类下拉按名称排序
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['category'].empty_label = '—— 不选择 ——'
        # 合集下拉按名称排序
        self.fields['collection'].queryset = Collection.objects.all().order_by('name')
        self.fields['collection'].empty_label = '—— 不放入合集 ——'
        # SlugField 自带的 validate_slug 只允许 ASCII 字符,
        # 与模型 save() 中 slugify(allow_unicode=True) 的结果不兼容,
        # 这里替换为宽松的 Unicode 校验(允许中文/字母/数字/-/_)。
        self.fields['slug'].validators = [validate_unicode_slug]


class PostUploadMDForm(forms.Form):
    """通过 .md 文件上传创建文章。

    - 文件:仅接受 .md / .markdown 扩展名
    - 标题:由首行 H1 智能解析,无则用文件名(去掉扩展名)
    - 正文:md 文件原文
    - 其余元信息(分类/标签/发布设置)在表单中手动选择
    """

    md_file = forms.FileField(
        label='.md 文件',
        widget=forms.FileInput(attrs={
            'class': 'form-file', 'accept': '.md,.markdown,text/markdown',
        }),
        help_text='上传后:标题取首行 H1 或文件名,正文为文件原文。',
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        required=False, empty_label='—— 不选择 ——',
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='分类',
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(), required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'tag-checkbox-group'}),
        label='标签',
    )
    collection = forms.ModelChoiceField(
        queryset=Collection.objects.all().order_by('name'),
        required=False, empty_label='—— 不放入合集 ——',
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='所属合集',
    )
    order_in_collection = forms.IntegerField(
        required=False, min_value=1, max_value=9999,
        widget=forms.NumberInput(attrs={
            'class': 'form-input', 'min': '1', 'max': '9999', 'step': '1',
            'placeholder': '留空按发布时间排',
        }),
        label='合集内序号',
        help_text='可选,1、2、3……指定在合集里的阅读顺序,不填则按发布时间自动排。',
    )
    cover = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-file'}),
        label='封面图',
    )
    is_published = forms.BooleanField(required=False, initial=True, label='已发布')
    is_pinned = forms.BooleanField(required=False, initial=False, label='置顶')
    published_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-input', 'type': 'datetime-local',
        }),
        label='发布时间(留空=当前时间)',
    )

    def clean_md_file(self):
        f = self.cleaned_data['md_file']
        name = (f.name or '').lower()
        if not (name.endswith('.md') or name.endswith('.markdown')):
            raise forms.ValidationError('仅支持 .md / .markdown 文件。')
        # 读取文本(以 UTF-8 优先,失败回退 GB18030 兼容 Windows 记事本)
        raw = f.read()
        if isinstance(raw, bytes):
            for enc in ('utf-8-sig', 'utf-8', 'gb18030', 'utf-16'):
                try:
                    text = raw.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                text = raw.decode('utf-8', errors='replace')
        else:
            text = raw
        # 限制单文件 2MB
        if len(raw if isinstance(raw, bytes) else raw.encode('utf-8')) > 2 * 1024 * 1024:
            raise forms.ValidationError('文件过大,请控制在 2MB 以内。')
        # 把解析结果挂到 cleaned_data 上,供视图直接使用
        self.parsed_title, self.parsed_content = parse_md_for_post(text, f.name)
        return f


class PostUploadZipForm(forms.Form):
    """通过 .zip 压缩包上传创建文章(自动托管本地资源)。

    zip 内应包含:
    - 一个 .md / .markdown 文件(多个时取根目录第一个)
    - md 中引用的资源(图片 / Word / PDF 等),保留目录结构

    后台处理:
    - 解压资源到 media/post_assets/<pk>/
    - 改写 md 中"相对路径"链接为 /media/post_assets/<pk>/...
    - 外链(http/https/mailto/tel/data/#//)保持不动
    """

    zip_file = forms.FileField(
        label='.zip 压缩包',
        widget=forms.FileInput(attrs={
            'class': 'form-file', 'accept': '.zip,application/zip',
        }),
        help_text='zip 内含 .md + 引用的资源(图片/Word/PDF)。本地相对路径自动改写为站内 URL,外链保留。',
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all().order_by('name'),
        required=False, empty_label='—— 不选择 ——',
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='分类',
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(), required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'tag-checkbox-group'}),
        label='标签',
    )
    collection = forms.ModelChoiceField(
        queryset=Collection.objects.all().order_by('name'),
        required=False, empty_label='—— 不放入合集 ——',
        widget=forms.Select(attrs={'class': 'form-input'}),
        label='所属合集',
    )
    order_in_collection = forms.IntegerField(
        required=False, min_value=1, max_value=9999,
        widget=forms.NumberInput(attrs={
            'class': 'form-input', 'min': '1', 'max': '9999', 'step': '1',
            'placeholder': '留空按发布时间排',
        }),
        label='合集内序号',
        help_text='可选,1、2、3……指定在合集里的阅读顺序,不填则按发布时间自动排。',
    )
    cover = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-file'}),
        label='封面图(可选)',
    )
    is_published = forms.BooleanField(required=False, initial=True, label='已发布')
    is_pinned = forms.BooleanField(required=False, initial=False, label='置顶')
    published_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-input', 'type': 'datetime-local',
        }),
        label='发布时间(留空=当前时间)',
    )

    def clean_zip_file(self):
        import zipfile
        f = self.cleaned_data['zip_file']
        name = (f.name or '').lower()
        if not name.endswith('.zip'):
            raise forms.ValidationError('仅支持 .zip 文件。')
        # zip 本体限制 20MB(解压后在视图中另有总大小校验)
        if f.size > 20 * 1024 * 1024:
            raise forms.ValidationError('zip 文件过大,请控制在 20MB 以内。')
        # 校验是合法 zip(读取后记得复位指针)
        f.seek(0)
        if not zipfile.is_zipfile(f):
            raise forms.ValidationError('不是合法的 zip 文件。')
        f.seek(0)
        return f


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '分类名称'}),
            'slug': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '留空自动生成',
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '一句话描述(可选)',
            }),
        }
        labels = {'slug': 'URL 别名', 'description': '描述'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 放宽 slug 校验,允许中文(与模型 allow_unicode slugify 一致)
        self.fields['slug'].validators = [validate_unicode_slug]


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '标签名称'}),
            'slug': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '留空自动生成',
            }),
        }
        labels = {'slug': 'URL 别名'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 放宽 slug 校验,允许中文(与模型 allow_unicode slugify 一致)
        self.fields['slug'].validators = [validate_unicode_slug]


class ProjectCategoryForm(forms.ModelForm):
    """项目分类表单(建、改共用)。"""

    class Meta:
        model = ProjectCategory
        fields = ['name', 'slug', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '如:工具库 / 游戏 / 站点',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '留空自动生成', 'autocomplete': 'off',
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '0', 'step': '1',
            }),
        }
        labels = {'slug': 'URL 别名', 'sort_order': '排序'}
        help_texts = {
            'slug': '留空则根据名称自动生成。允许中文、字母、数字、下划线、连字符。',
            'sort_order': '数字越小越靠前,分类按此排序展示。',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].validators = [validate_unicode_slug]


class ProjectForm(forms.ModelForm):
    """项目表单(建、改共用)。"""

    class Meta:
        model = Project
        fields = ['name', 'slug', 'description', 'url', 'cover', 'category',
                  'sort_order', 'is_published']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '项目名称',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '留空自动生成', 'autocomplete': 'off',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea', 'rows': 3,
                'placeholder': '一句话介绍这个项目,会显示在项目卡片上。',
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-input', 'placeholder': 'https://example.com/ 或 /tools/xxx/',
            }),
            'cover': forms.ClearableFileInput(attrs={'class': 'form-file'}),
            'category': forms.Select(attrs={'class': 'form-input'}),
            'sort_order': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '0', 'step': '1',
            }),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        labels = {
            'slug': 'URL 别名',
            'url': '项目链接',
            'cover': '封面/图标',
            'category': '分类',
            'sort_order': '排序',
            'is_published': '已发布',
        }
        help_texts = {
            'slug': '留空则根据项目名自动生成。允许中文、字母、数字、下划线、连字符。',
            'description': '可选,一句话介绍,前台项目卡片上展示。',
            'url': '必填。「查看项目」按钮跳转的地址。',
            'category': '可选,归属到某个项目分类下;不选则归入「未分类」。',
            'sort_order': '数字越小越靠前。',
            'is_published': '不勾选则前台项目页不展示。',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].validators = [validate_unicode_slug]
        self.fields['category'].queryset = ProjectCategory.objects.all().order_by(
            'sort_order', 'name'
        )
        self.fields['category'].empty_label = '—— 不选择(归入未分类) ——'


# ============================================================================
# MD 智能解析:从 Markdown 文本提取 (title, content)
# ============================================================================

def parse_md_for_post(text: str, filename: str = ''):
    """从 Markdown 文本提取标题与正文。

    规则:
    - 若文本首行(允许前导空行/空白)是 H1 (# 标题),则取其为标题,
      并从正文中移除该 H1 行,避免与 title 字段重复。
    - 否则标题取文件名(去掉扩展名)。
    - 正文始终返回完整原文(若移除 H1,则去掉该行及其后的空行)。
    """
    if not text:
        return ('', '')

    lines = text.splitlines()
    title = ''
    cut_from = 0  # 从第几行开始是真正的内容

    # 跳过前导空行,寻找第一个非空行
    idx = 0
    while idx < len(lines) and not lines[idx].strip():
        idx += 1

    if idx < len(lines):
        first = lines[idx].strip()
        # 匹配 H1: # 标题  或  #标题
        if first.startswith('#'):
            rest = first.lstrip('#').strip()
            if rest:
                title = rest
                cut_from = idx + 1
                # 同时吃掉 H1 后紧跟的空行
                while cut_from < len(lines) and not lines[cut_from].strip():
                    cut_from += 1

    if not title:
        # 用文件名(去扩展名)兜底
        import os
        base = os.path.splitext(os.path.basename(filename or ''))[0]
        title = base or '未命名文章'

    content = '\n'.join(lines[cut_from:]).strip() if cut_from else text.strip()
    return (title, content)


# ============================================================================
# 首页 Hero 配置 & 背景图
# ============================================================================


class SiteConfigForm(forms.ModelForm):
    """站点 Hero 配置编辑表单(单例,不允许新增/删除)。"""

    class Meta:
        model = SiteConfig
        fields = [
            'hero_eyebrow', 'hero_title', 'hero_accent_word', 'hero_subtitle',
            'hero_animation_choice', 'hero_bg_type', 'hero_bg_overlay',
            'hero_bg_image', 'hero_bg_video',
            'hero_cta_text', 'hero_cta_link',
            'header_color_mode', 'header_color', 'header_text_color',
            'post_style',
            'hero_eyebrow_fs', 'hero_title_fs', 'hero_subtitle_fs', 'hero_meta_fs',
            'card_big_fs', 'card_text_fs',
            'post_title_fs', 'post_excerpt_fs', 'post_meta_fs',
        ]
        widgets = {
            'hero_eyebrow': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': 'Journal · 站名',
            }),
            'hero_title': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '文字,是思想的栖息地。',
            }),
            'hero_accent_word': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '思想',
            }),
            'hero_subtitle': forms.Textarea(attrs={
                'class': 'form-textarea', 'rows': 2,
                'placeholder': '记录代码、思考与生活的个人空间。',
            }),
            'hero_animation_choice': forms.Select(attrs={'class': 'form-select'}),
            'hero_bg_type': forms.Select(attrs={'class': 'form-select'}),
            'hero_bg_overlay': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '0', 'max': '1', 'step': '0.05',
            }),
            'hero_bg_image': forms.Select(attrs={'class': 'form-select'}),
            'hero_bg_video': forms.ClearableFileInput(attrs={'class': 'form-file'}),
            'hero_cta_text': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '开始阅读',
            }),
            'hero_cta_link': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '#posts 或 /archive/',
            }),
            'header_color_mode': forms.Select(attrs={'class': 'form-select'}),
            'header_color': forms.TextInput(attrs={
                'type': 'color', 'class': 'form-input form-color',
            }),
            'header_text_color': forms.TextInput(attrs={
                'type': 'color', 'class': 'form-input form-color',
            }),
            'post_style': forms.Select(attrs={'class': 'form-select'}),
            # 首页文字大小(px),留空 = 使用主题默认
            'hero_eyebrow_fs': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '8', 'max': '200', 'placeholder': '默认 18',
            }),
            'hero_title_fs': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '8', 'max': '200', 'placeholder': '默认 56',
            }),
            'hero_subtitle_fs': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '8', 'max': '200', 'placeholder': '默认 18',
            }),
            'hero_meta_fs': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '8', 'max': '200', 'placeholder': '默认 12',
            }),
            'card_big_fs': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '8', 'max': '200', 'placeholder': '默认 40',
            }),
            'card_text_fs': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '8', 'max': '200', 'placeholder': '默认 15',
            }),
            'post_title_fs': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '8', 'max': '200', 'placeholder': '默认 23',
            }),
            'post_excerpt_fs': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '8', 'max': '200', 'placeholder': '默认 15',
            }),
            'post_meta_fs': forms.NumberInput(attrs={
                'class': 'form-input', 'min': '8', 'max': '200', 'placeholder': '默认 12',
            }),
        }
        labels = {
            'hero_eyebrow': '眉标文字',
            'hero_title': '主标题',
            'hero_accent_word': '高亮词',
            'hero_subtitle': '副标题',
            'hero_animation_choice': '入场动画',
            'hero_bg_type': '背景类型',
            'hero_bg_overlay': '背景遮罩透明度',
            'hero_bg_image': '背景图片',
            'hero_bg_video': '背景视频',
            'hero_cta_text': '主按钮文字',
            'hero_cta_link': '主按钮链接',
            'header_color_mode': '顶栏配色模式',
            'header_color': '顶栏背景色',
            'header_text_color': '顶栏文字颜色',
            'post_style': '文章阅读风格',
            # 首页文字大小(px)
            'hero_eyebrow_fs': 'Hero 眉标字号(px)',
            'hero_title_fs': 'Hero 主标题字号(px)',
            'hero_subtitle_fs': 'Hero 副标题字号(px)',
            'hero_meta_fs': 'Hero 底部信息字号(px)',
            'card_big_fs': '卡片大数字字号(px)',
            'card_text_fs': '卡片正文字号(px)',
            'post_title_fs': '文章标题字号(px)',
            'post_excerpt_fs': '文章摘要字号(px)',
            'post_meta_fs': '文章元信息字号(px)',
        }
        help_texts = {
            'hero_accent_word': '须出现在主标题中,留空则不高亮。',
            'hero_bg_overlay': '0~1 的数字,建议 0.2~0.5 之间。',
            'hero_bg_image': '可先在"背景图库"里上传,再在这里选择。',
            'hero_bg_video': '建议 mp4/webm 格式,体积 < 5MB。',
            'hero_cta_link': '支持 #posts 锚点或 /archive/ 等绝对路径,或外部 https:// 链接。',
            'header_color_mode': '自动模式会根据壁纸主色自动选择深/浅文字,保证对比度;手动模式使用你指定的颜色。',
            'header_color': '格式 #RRGGBB。建议从当前壁纸里取一个主色调,顶栏滚动后会用该颜色作背景。',
            'header_text_color': '格式 #RRGGBB,可选。留空则按背景色自动选深/浅文字;填写后顶栏文字固定用该颜色。',
            'post_style': '文章详情页正文的默认阅读风格;访客仍可在文章页顶部手动切换。',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 背景图片下拉按上传时间倒序,空选项 = 不选择
        self.fields['hero_bg_image'].queryset = (
            BackgroundImage.objects.all().order_by('-uploaded_at')
        )
        self.fields['hero_bg_image'].empty_label = '—— 不选(用上传时间最新的或无) ——'


class BackgroundImageForm(forms.ModelForm):
    """Hero 背景图上传/编辑表单。"""

    class Meta:
        model = BackgroundImage
        fields = ['title', 'image', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '标题(可选,方便区分)',
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'form-file'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        labels = {
            'title': '标题', 'image': '图片', 'is_active': '设为当前启用',
        }
        help_texts = {
            'is_active': '同一时间只会保留一张启用图。',
        }


class AboutForm(forms.ModelForm):
    """关于页内容编辑表单(基于 SiteConfig 单例)。"""

    class Meta:
        model = SiteConfig
        fields = ['about_markdown']
        widgets = {
            'about_markdown': forms.Textarea(attrs={
                'class': 'form-textarea form-content',
                'placeholder': '# 关于\n\n支持 Markdown:标题、列表、引用、链接……',
                'rows': 18,
            }),
        }
        labels = {
            'about_markdown': '关于页正文(Markdown)',
        }
        help_texts = {
            'about_markdown': '前台 /about/ 页面展示这段内容。留空则显示模板内置的默认关于页。',
        }


class CollectionForm(forms.ModelForm):
    """合集表单(建合集、改合集共用)。"""

    class Meta:
        model = Collection
        fields = ['name', 'slug', 'description', 'cover', 'is_published']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '合集名,如:毛选读书笔记',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-input', 'placeholder': '留空自动生成', 'autocomplete': 'off',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea', 'rows': 3,
                'placeholder': '一句话介绍这个合集,会显示在合集详情页顶部。',
            }),
            'cover': forms.ClearableFileInput(attrs={'class': 'form-file'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        labels = {
            'slug': 'URL 别名',
            'cover': '合集封面',
            'is_published': '已发布',
        }
        help_texts = {
            'slug': '留空则根据合集名自动生成。允许中文、字母、数字、下划线、连字符。',
            'description': '合集详情页 Hero 区会显示这段简介。',
            'is_published': '不勾选则前台合集列表页不展示。',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].validators = [validate_unicode_slug]


