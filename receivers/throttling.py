"""SMS 웹훅 rate limit."""

from rest_framework.throttling import SimpleRateThrottle


class SMSWebhookThrottle(SimpleRateThrottle):
    """호출자와 무관하게 하나의 버킷을 쓰는 웹훅 throttle.

    웹훅을 부르는 쪽은 포워더 앱 하나뿐이라 IP로 나눌 이유가 없다. 게다가
    IP 기반 키는 프록시 설정(NUM_PROXIES) 없이는 X-Forwarded-For 문자열 전체가
    키가 되어, 요청마다 XFF를 바꾸면 매번 새 버킷이 생겨 우회된다.

    캐시가 LocMemCache라 카운트는 gunicorn 워커마다 따로 쌓인다.
    실제 한도는 워커 수 × rate다.
    """

    scope = "sms_webhook"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": "global"}
