from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings


class RefreshTokenAuthentication(JWTAuthentication):
    def authenticate(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"]) or None

        if refresh_token is None:
            raise AuthenticationFailed("Refresh token is not in cookie")

        validated_token = self.get_validated_token(refresh_token)
        return self.get_user(validated_token), validated_token
