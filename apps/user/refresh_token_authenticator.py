import jwt
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings


class RefreshTokenAuthentication(JWTAuthentication):
    def authenticate(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"]) or None

        if refresh_token is None:
            raise AuthenticationFailed("Refresh token is not in cookie")

        decoded_jwt = jwt.decode(
            jwt=refresh_token,
            key=settings.SIMPLE_JWT["SIGNING_KEY"],
            algorithms=["HS256"],
        )

        try:
            user = self.user_model.objects.get(
                **{settings.SIMPLE_JWT["USER_ID_FIELD"]: decoded_jwt.get("user_id")}
            )
        except self.user_model.DoesNotExist:
            raise AuthenticationFailed("User not found", code="user_not_found")

        if not user.is_active:
            raise AuthenticationFailed("User is inactive", code="user_inactive")

        return user, refresh_token
