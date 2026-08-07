"""
自建后台(/dijia/)路由。

URL 命名空间:manage
所有视图均要求登录(login_required),登录页 /dijia/login/。
"""

from django.urls import path

from . import manage_views

app_name = 'manage'

urlpatterns = [
    # 仪表盘
    path('', manage_views.dashboard, name='dashboard'),

    # 登录 / 登出
    path('login/', manage_views.login_view, name='login'),
    path('logout/', manage_views.logout_view, name='logout'),

    # 文章 ============================================================
    path('posts/', manage_views.post_list, name='post_list'),
    path('posts/new/', manage_views.post_create, name='post_create'),
    path('posts/upload-md/', manage_views.post_upload_md, name='post_upload_md'),
    path('posts/upload-zip/', manage_views.post_upload_zip, name='post_upload_zip'),
    path('posts/<int:pk>/edit/', manage_views.post_update, name='post_update'),
    path('posts/<int:pk>/delete/', manage_views.post_delete, name='post_delete'),
    path(
        'posts/<int:pk>/toggle/<str:field>/',
        manage_views.post_toggle,
        name='post_toggle',
    ),

    # 分类 ============================================================
    path('categories/', manage_views.category_list, name='category_list'),
    path('categories/new/', manage_views.category_create, name='category_create'),
    path(
        'categories/<int:pk>/edit/',
        manage_views.category_update,
        name='category_update',
    ),
    path(
        'categories/<int:pk>/delete/',
        manage_views.category_delete,
        name='category_delete',
    ),

    # 标签 ============================================================
    path('tags/', manage_views.tag_list, name='tag_list'),
    path('tags/new/', manage_views.tag_create, name='tag_create'),
    path('tags/<int:pk>/edit/', manage_views.tag_update, name='tag_update'),
    path('tags/<int:pk>/delete/', manage_views.tag_delete, name='tag_delete'),

    # 评论 ============================================================
    path('comments/', manage_views.comment_list, name='comment_list'),
    path(
        'comments/<int:pk>/toggle-approve/',
        manage_views.comment_toggle_approve,
        name='comment_toggle_approve',
    ),
    path(
        'comments/<int:pk>/delete/',
        manage_views.comment_delete,
        name='comment_delete',
    ),

    # Hero 配置 =======================================================
    path('hero/', manage_views.hero_edit, name='hero_edit'),

    # 关于页 ==========================================================
    path('about/', manage_views.about_edit, name='about_edit'),

    # 背景图库 =======================================================
    path('backgrounds/', manage_views.background_list, name='background_list'),
    path('backgrounds/new/', manage_views.background_new, name='background_new'),
    path(
        'backgrounds/<int:pk>/edit/',
        manage_views.background_edit,
        name='background_update',
    ),
    path(
        'backgrounds/<int:pk>/delete/',
        manage_views.background_delete,
        name='background_delete',
    ),
    path(
        'backgrounds/<int:pk>/set-active/',
        manage_views.background_set_active,
        name='background_set_active',
    ),

    # 合集 ===========================================================
    path('collections/', manage_views.collection_list, name='collection_list'),
    path('collections/new/', manage_views.collection_new, name='collection_new'),
    path(
        'collections/<int:pk>/edit/',
        manage_views.collection_update,
        name='collection_update',
    ),
    path(
        'collections/<int:pk>/delete/',
        manage_views.collection_delete,
        name='collection_delete',
    ),
    path(
        'collections/<int:pk>/toggle-publish/',
        manage_views.collection_toggle_publish,
        name='collection_toggle_publish',
    ),
    path(
        'collections/<int:collection_pk>/remove-post/<int:post_pk>/',
        manage_views.collection_remove_post,
        name='collection_remove_post',
    ),
    path(
        'collections/<int:collection_pk>/add-post/<int:post_pk>/',
        manage_views.collection_add_post,
        name='collection_add_post',
    ),
    path(
        'collections/<int:pk>/reorder/',
        manage_views.collection_reorder,
        name='collection_reorder',
    ),

    # 项目 ===========================================================
    path('projects/', manage_views.project_list, name='project_list'),
    path('projects/new/', manage_views.project_create, name='project_create'),
    path(
        'projects/<int:pk>/edit/',
        manage_views.project_update,
        name='project_update',
    ),
    path(
        'projects/<int:pk>/delete/',
        manage_views.project_delete,
        name='project_delete',
    ),
    path(
        'projects/<int:pk>/toggle-publish/',
        manage_views.project_toggle_publish,
        name='project_toggle_publish',
    ),

    # 项目分类 =======================================================
    path(
        'project-categories/',
        manage_views.project_category_list,
        name='project_category_list',
    ),
    path(
        'project-categories/new/',
        manage_views.project_category_create,
        name='project_category_create',
    ),
    path(
        'project-categories/<int:pk>/edit/',
        manage_views.project_category_update,
        name='project_category_update',
    ),
    path(
        'project-categories/<int:pk>/delete/',
        manage_views.project_category_delete,
        name='project_category_delete',
    ),
]
