"""
博客表单:评论提交、搜索。
"""

from django import forms


class CommentForm(forms.Form):
    """访客评论表单:昵称、邮箱、网站(可选)、评论内容。"""

    author = forms.CharField(
        label='昵称', max_length=64,
        widget=forms.TextInput(attrs={
            'class': 'form-input', 'placeholder': '你的昵称', 'required': True,
        }),
    )
    email = forms.EmailField(
        label='邮箱', max_length=128,
        widget=forms.EmailInput(attrs={
            'class': 'form-input', 'placeholder': 'your@email.com', 'required': True,
        }),
        help_text='邮箱不会公开展示,仅用于生成头像。',
    )
    website = forms.URLField(
        label='网站', required=False, max_length=200,
        widget=forms.URLInput(attrs={
            'class': 'form-input', 'placeholder': 'https://(可选)',
        }),
    )
    content = forms.CharField(
        label='评论', max_length=1000,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea', 'placeholder': '说点什么……支持 Markdown',
            'rows': 4, 'required': True,
        }),
    )


class SearchForm(forms.Form):
    """全站搜索表单。"""

    q = forms.CharField(
        label='搜索', max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'search-input', 'placeholder': '搜索文章……',
            'autocomplete': 'off',
        }),
    )
