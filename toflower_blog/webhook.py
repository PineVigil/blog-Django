"""
GitHub Webhook 自动部署视图。

接收 GitHub 仓库推送事件,校验签名后触发部署脚本。

安全说明:
- 使用 GitHub Webhook secret 进行 HMAC-SHA256 签名校验
- 仅接受 push 事件
- secret 从环境变量 WEBHOOK_SECRET 读取,未配置时拒绝所有请求
"""

import hashlib
import hmac
import os
import subprocess

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# 部署脚本路径(与 settings.BASE_DIR 关联)
DEPLOY_SCRIPT = str(settings.BASE_DIR / 'scripts' / 'deploy.sh')


def _verify_signature(request):
    """校验 GitHub 请求签名。返回 True/False。"""
    secret = os.environ.get('WEBHOOK_SECRET', '')
    if not secret:
        return False

    signature = request.headers.get('X-Hub-Signature-256', '')
    if not signature.startswith('sha256='):
        return False

    # GitHub 使用原始 body 计算签名,不能用 request.body 被解析后的内容
    payload = request.body
    expected = 'sha256=' + hmac.new(
        secret.encode('utf-8'), payload, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


@csrf_exempt
@require_POST
def github_webhook(request):
    """GitHub Webhook 入口:https://toflower.fun/webhook/deploy/"""
    # 1. 校验事件类型
    event = request.headers.get('X-GitHub-Event', '')
    if event != 'push':
        return JsonResponse({'status': 'ignored', 'reason': 'not a push event'}, status=200)

    # 2. 校验签名
    if not _verify_signature(request):
        return HttpResponse('Invalid signature', status=403)

    # 3. 检查分支(main)
    try:
        import json
        payload = json.loads(request.body)
        ref = payload.get('ref', '')
        if not ref.endswith('/main'):
            return JsonResponse({'status': 'ignored', 'reason': 'not main branch'}, status=200)
    except Exception:
        return HttpResponse('Bad payload', status=400)

    # 4. 异步触发部署脚本(避免阻塞 webhook 响应)
    #    项目目录/venv 均属 www 用户,gunicorn 以 www 运行,脚本直接以 www 权限执行即可
    try:
        subprocess.Popen(
            ['/bin/bash', DEPLOY_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=lambda: os.setsid(),
        )
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'deploying'}, status=202)
