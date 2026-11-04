from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer


class SafeTokenRefreshSerializer(TokenRefreshSerializer):
    """삭제된 사용자의 refresh 토큰을 500이 아니라 401로 거절한다.

    simplejwt 5.5.1의 TokenRefreshSerializer.validate는 사용자를
    objects.get으로 찾으면서 DoesNotExist를 처리하지 않는다.
    """

    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except get_user_model().DoesNotExist:
            raise AuthenticationFailed(
                self.error_messages["no_active_account"], "no_active_account"
            )
