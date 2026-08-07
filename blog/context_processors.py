"""
模板上下文处理器:向所有模板注入站点配置与常用变量。
"""

import json

from django.conf import settings

from .models import SiteConfig


def _build_hero_config():
    """从单例 SiteConfig 构造 hero_config 字典,供模板渲染。

    任何异常(如未迁移)都回退到安全默认值,保证站点不报错。
    """
    defaults = {
        'hero_eyebrow': 'Journal · 站名',
        'hero_title': '文字,是思想的栖息地。',
        'hero_accent_word': '思想',
        'hero_subtitle': '记录代码、思考与生活的个人空间。',
        'hero_animation_choice': 'char_rise',
        'hero_bg_type': 'blob',
        'hero_bg_image_url': '',
        'hero_bg_video_url': '',
        'hero_bg_overlay': 0.35,
        'hero_cta_text': '开始阅读',
        'hero_cta_link': '#posts',
        'header_color_mode': 'auto',
        'header_color': '',
        'header_text_color': '',
        'post_style': 'default',
    }
    try:
        cfg = SiteConfig.get_solo()
    except Exception:
        return defaults

    # 背景图:优先取 hero_bg_image 外键,否则取 is_active 的 BackgroundImage
    bg_image_url = ''
    if cfg.hero_bg_image_id:
        bg_image_url = cfg.hero_bg_image.image.url if cfg.hero_bg_image else ''
    if not bg_image_url:
        active = cfg.hero_bg_image
        if not active:
            try:
                from .models import BackgroundImage
                active = BackgroundImage.objects.filter(is_active=True).first()
            except Exception:
                active = None
        if active and active.image:
            bg_image_url = active.image.url

    bg_video_url = ''
    if cfg.hero_bg_video:
        try:
            bg_video_url = cfg.hero_bg_video.url
        except Exception:
            bg_video_url = ''

    return {
        'hero_eyebrow': cfg.hero_eyebrow or defaults['hero_eyebrow'],
        'hero_title': cfg.hero_title or defaults['hero_title'],
        'hero_accent_word': cfg.hero_accent_word or '',
        'hero_subtitle': cfg.hero_subtitle or defaults['hero_subtitle'],
        'hero_animation_choice': cfg.hero_animation_choice or defaults['hero_animation_choice'],
        'hero_bg_type': cfg.hero_bg_type or defaults['hero_bg_type'],
        'hero_bg_image_url': bg_image_url,
        'hero_bg_video_url': bg_video_url,
        'hero_bg_overlay': cfg.hero_bg_overlay if cfg.hero_bg_overlay is not None else defaults['hero_bg_overlay'],
        'hero_cta_text': cfg.hero_cta_text or defaults['hero_cta_text'],
        'hero_cta_link': cfg.hero_cta_link or defaults['hero_cta_link'],
        'header_color_mode': cfg.header_color_mode or defaults['header_color_mode'],
        'header_color': cfg.header_color or defaults['header_color'],
        'header_text_color': cfg.header_text_color or defaults['header_text_color'],
        'post_style': cfg.post_style or defaults['post_style'],
    }


# 首页各区域文字大小字段(单位 px,留空表示使用 CSS 默认值)
FONT_SIZE_FIELDS = (
    'hero_eyebrow_fs', 'hero_title_fs', 'hero_subtitle_fs', 'hero_meta_fs',
    'card_big_fs', 'card_text_fs',
    'post_title_fs', 'post_excerpt_fs', 'post_meta_fs',
)


def _build_font_sizes():
    """读取 SiteConfig 中已填写的字号(px),构造 {字段名: 值} 字典供模板注入 CSS 变量。"""
    try:
        cfg = SiteConfig.get_solo()
    except Exception:
        return {}
    result = {}
    for f in FONT_SIZE_FIELDS:
        val = getattr(cfg, f, None)
        if val:
            result[f] = int(val)
    return result


def site_settings(request):
    """注入 SITE_CONFIG 内容 + SITE_* 变量 + hero_config 字典。"""
    fs = _build_font_sizes()
    return {
        'site': settings.SITE_CONFIG,
        'SITE_NAME': settings.SITE_CONFIG['SITE_NAME'],
        'SITE_TITLE': settings.SITE_CONFIG['SITE_TITLE'],
        'SITE_DESC': settings.SITE_CONFIG['SITE_DESC'],
        'SITE_DOMAIN': settings.SITE_CONFIG['SITE_DOMAIN'],
        'SITE_AUTHOR': settings.SITE_CONFIG['SITE_AUTHOR'],
        'SITE_EMAIL': settings.SITE_CONFIG['SITE_EMAIL'],
        'SITE_ICP': settings.SITE_CONFIG['SITE_ICP'],
        'ADMIN_PATH': settings.SITE_CONFIG['ADMIN_PATH'],
        'hero_config': _build_hero_config(),
        'font_sizes': fs,
        'font_sizes_json': json.dumps(fs),
        'STATIC_VERSION': getattr(settings, 'STATIC_VERSION', '1'),
    }
