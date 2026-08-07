"""
初始化示例数据:分类、标签、文章、评论。

用法:
    python manage.py init_sample_data
"""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from blog.models import Category, Comment, Post, Tag


SAMPLE_CATEGORIES = ['技术笔记', '生活随笔', '读书', '旅行']
SAMPLE_TAGS = ['Django', 'Python', 'MySQL', '前端', '随笔', '工具', '效率', '思考']
SAMPLE_POSTS = [
    {
        'title': '欢迎来到 toflower 博客',
        'category': '生活随笔',
        'tags': ['随笔'],
        'pinned': True,
        'content': """# 欢迎来到 toflower

这是一个使用 **Django 5.2 LTS** 构建的个人博客,追求纯白简约的设计风格。

## 这里会有什么

- 技术笔记:编程中遇到的问题与解决方案
- 生活随笔:日常的思考与记录
- 读书心得:读过的书与摘抄
- 旅行日志:走过的地方

## 一段代码示例

```python
def hello(name: str = 'world') -> str:
    \"\"\"一个简单的问候函数。\"\"\"
    return f'Hello, {name}!'


if __name__ == '__main__':
    print(hello('toflower'))
```

## 一段引用

> 简单是终极的复杂。
> —— 达·芬奇

希望你喜欢这里。如想订阅更新,可前往 [RSS](/feed/rss/) 订阅。
""",
    },
    {
        'title': 'Django 5.2 LTS 新特性速览',
        'category': '技术笔记',
        'tags': ['Django', 'Python'],
        'content': """# Django 5.2 LTS 新特性

Django 5.2 作为新的长期支持版本(LTS),带来了一系列改进。

## 数据库连接池

Django 5.0+ 内置了持久连接池,通过 `CONN_MAX_AGE` 与 `CONN_HEALTH_CHECKS` 配置:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'CONN_MAX_AGE': 60,            # 连接复用 60 秒
        'CONN_HEALTH_CHECKS': True,    # 复用前健康检查
    }
}
```

## 异步视图与 ORM

异步支持进一步完善,可在视图层使用 `async def`:

```python
async def async_view(request):
    data = await MyModel.objects.afilter(is_published=True)
    return JsonResponse({'count': len(data)})
```

## 模板小改进

- `{% load %}` 支持从应用目录加载,简化模板书写
- 表单渲染更灵活

## 小结

LTS 版本意味着至少 3 年的安全更新,适合长期项目。
""",
    },
    {
        'title': 'MySQL 5.7 字符集与 utf8mb4 配置',
        'category': '技术笔记',
        'tags': ['MySQL', 'Django'],
        'content': """# MySQL 5.7 与 utf8mb4

为支持完整的 Unicode(包括 emoji),数据库应使用 `utf8mb4` 而非 `utf8`。

## 配置方法

在 `my.cnf` 中:

```ini
[mysqld]
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
```

## Django 侧配置

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}
```

## 注意事项

1. `utf8mb4` 单字符最长 4 字节,索引列长度需 ≤ 191(对于 InnoDB 默认 row_format)
2. `STRICT_TRANS_TABLES` 让数据截断时报错而非静默,避免数据丢失
3. 迁移前确保所有表已转换字符集
""",
    },
    {
        'title': '纯白简约 Web 设计的几个原则',
        'category': '读书',
        'tags': ['前端', '思考'],
        'content': """# 纯白简约设计的几个原则

## 1. 大量留白

留白不是浪费,而是呼吸感。内容区 720px 居中,左右大量空白,让阅读舒适。

## 2. 黑白灰三色

- **黑色** `#1a1a1a`:正文文字
- **灰色** `#666` / `#999`:辅助文字、分隔线
- **白色** `#fff`:背景

避免使用过多颜色,让内容本身成为主角。

## 3. 字体克制

使用系统字体栈,既保证加载速度,又与各平台原生风格一致:

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
             "PingFang SC", "Microsoft YaHei", sans-serif;
```

## 4. 微圆角与极淡阴影

- 圆角:`8px`,不大不小
- 阴影:`0 1px 3px rgba(0,0,0,0.04)`,几乎不可见

## 5. 一切过渡为内容服务

动画只用于反馈(hover、淡入),不用来炫技。
""",
    },
    {
        'title': '我的开发工具清单(2026 版)',
        'category': '生活随笔',
        'tags': ['工具', '效率'],
        'content': """# 我的开发工具清单(2026 版)

## 编辑器

- **VS Code**:日常项目主力
- **Vim**:服务器编辑配置

## 终端

- **Windows Terminal**:多标签 + PowerShell
- **zsh + oh-my-zsh**:Linux/Mac 上更顺手

## 数据库

- **DBeaver**:跨平台 GUI 客户端,支持 MySQL/PG/SQLite
- **mycli**:命令行 MySQL 客户端,自动补全很爽

## 效率工具

- **Obsidian**:本地 Markdown 笔记
- **uBlock Origin**:浏览器去广告
- **1Password**:密码管理

## 部署

- **Nginx**:反向代理 + 静态资源
- **Gunicorn**:Python WSGI 服务器
- **systemd**:进程守护

工具是手段,不是目的。挑一套用着顺手的,长期用下去。
""",
    },
    {
        'title': '关于阅读的几点体会',
        'category': '读书',
        'tags': ['思考', '随笔'],
        'content': """# 关于阅读的几点体会

## 不追求快

读得快不是本事,读得懂、用得上才是。一年读 100 本却记不住,不如读 10 本吃透。

## 做笔记

读完一本书,合上书写下三句话:
1. 这本书讲了什么
2. 它改变了我的什么想法
3. 我打算怎么用

## 反复读

经典值得反复读。《如何阅读一本书》《思考,快与慢》这种书,读一遍是浪费。

## 不功利

不是每本书都要有用。读小说、读诗,本身就是生活的一部分。
""",
    },
]


class Command(BaseCommand):
    help = '初始化博客示例数据(分类、标签、文章、评论)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='清空现有 Post/Category/Tag/Comment 后再创建',
        )

    def handle(self, *args, **options):
        reset = options['reset']
        if reset:
            Comment.objects.all().delete()
            Post.objects.all().delete()
            Tag.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING('已清空现有数据'))

        # 确保至少有一个作者(取第一个超级用户,否则创建默认)
        User = get_user_model()
        author = User.objects.filter(is_superuser=True).first()
        if not author:
            author = User.objects.create_user(
                username='toflower', password='toflower123',
                email='admin@toflower.fun', is_staff=True, is_superuser=True,
            )
            self.stdout.write(self.style.SUCCESS(f'创建默认用户: {author.username} / toflower123'))

        # 创建分类
        cat_map = {}
        for name in SAMPLE_CATEGORIES:
            cat, _ = Category.objects.get_or_create(name=name, defaults={'description': f'{name}相关'})
            cat_map[name] = cat

        # 创建标签
        tag_map = {}
        for name in SAMPLE_TAGS:
            tag, _ = Tag.objects.get_or_create(name=name)
            tag_map[name] = tag

        # 创建文章
        now = timezone.now()
        for i, p in enumerate(SAMPLE_POSTS):
            post, created = Post.objects.get_or_create(
                title=p['title'],
                defaults={
                    'content': p['content'],
                    'category': cat_map.get(p['category']),
                    'author': author,
                    'is_published': True,
                    'is_pinned': p.get('pinned', False),
                    'published_time': now - timedelta(days=len(SAMPLE_POSTS) - i, hours=random.randint(0, 12)),
                    'views': random.randint(20, 500),
                },
            )
            if created:
                for tag_name in p['tags']:
                    post.tags.add(tag_map[tag_name])
                self.stdout.write(self.style.SUCCESS(f'创建文章: {post.title}'))

                # 给前两篇加示例评论
                if i < 2:
                    Comment.objects.create(
                        post=post, author='访客A', email='visitor.a@example.com',
                        content='写得很好,学习了!',
                        is_approved=True,
                        created_time=post.published_time + timedelta(hours=2),
                    )
                    Comment.objects.create(
                        post=post, author='访客B', email='visitor.b@example.com',
                        content='请问代码块用的什么高亮库?',
                        is_approved=True,
                        created_time=post.published_time + timedelta(hours=5),
                    )

        # 创建 about flatpage(可选)
        try:
            from django.contrib.flatpages.models import FlatPage
            FlatPage.objects.get_or_create(
                url='/about/',
                defaults={
                    'title': '关于',
                    'content': """# 关于 toflower

你好,这里是 **toflower** 的个人博客。

## 联系方式

- 邮箱:admin@toflower.fun
- RSS:[/feed/rss/](/feed/rss/)

## 这个站点

- 框架:Django 5.2 LTS
- 数据库:MySQL 5.7
- 服务器:Nginx + Gunicorn
- 设计:纯白简约,手写 CSS

欢迎常来。
""",
                },
            )
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS('示例数据初始化完成 ✓'))
