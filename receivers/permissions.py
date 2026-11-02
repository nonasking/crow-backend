"""
SMS 웹훅 공유 시크릿 검증.

웹훅은 JWT를 쓸 수 없는 SMS 포워더 앱이 호출하므로, 미리 공유한 토큰으로
요청 출처를 확인한다. 토큰은 `X-Webhook-Token` 헤더로 보내는 것을 권장하고,
헤더를 설정할 수 없는 포워더를 위해 `?token=` 쿼리 파라미터도 받는다.
(쿼리 파라미터는 접근 로그에 남을 수 있으므로 가능하면 헤더를 쓴다.)
"""

import hmac
import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)

WEBHOOK_TOKEN_HEADER = "X-Webhook-Token"
WEBHOOK_TOKEN_QUERY_PARAM = "token"


class HasWebhookToken(BasePermission):
    """`SMS_WEBHOOK_TOKEN`과 일치하는 토큰이 있는 요청만 허용한다.

    `SMS_WEBHOOK_TOKEN`이 비어 있으면 검증을 건너뛰고 경고만 남긴다.
    배포와 포워더 설정 변경 사이에 수신이 끊기지 않도록 하기 위한 단계적
    도입용이며, 운영 환경에는 반드시 값을 설정해야 한다.
    """

    message = "웹훅 토큰이 없거나 일치하지 않습니다"

    def has_permission(self, request, view) -> bool:
        expected = getattr(settings, "SMS_WEBHOOK_TOKEN", "")
        if not expected:
            logger.warning(
                "SMS_WEBHOOK_TOKEN is not set; the SMS webhook accepts unauthenticated requests"
            )
            return True

        provided = request.headers.get(WEBHOOK_TOKEN_HEADER) or request.query_params.get(
            WEBHOOK_TOKEN_QUERY_PARAM, ""
        )
        return hmac.compare_digest(provided.encode(), expected.encode())
