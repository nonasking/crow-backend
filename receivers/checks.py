"""receivers 앱 system check."""

from django.conf import settings
from django.core.checks import Warning, register


@register()
def check_sms_webhook_token(app_configs, **kwargs):
    """운영(DEBUG=False)에서 웹훅 토큰이 비어 있으면 기동 시점에 경고한다.

    토큰이 비어 있으면 HasWebhookToken이 검증을 건너뛰므로, 설정을 빠뜨린 채
    배포해도 웹훅은 계속 열려 있다. 요청마다 남는 로그보다 먼저 드러나게 한다.
    """
    if settings.DEBUG or getattr(settings, "SMS_WEBHOOK_TOKEN", ""):
        return []
    return [
        Warning(
            "SMS_WEBHOOK_TOKEN is not set; /receivers/webhook/ accepts unauthenticated requests.",
            hint="Set SMS_WEBHOOK_TOKEN and send it from the SMS forwarder as X-Webhook-Token.",
            id="receivers.W001",
        )
    ]
