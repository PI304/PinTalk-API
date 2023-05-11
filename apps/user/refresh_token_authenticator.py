import jwt
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken


class RefreshTokenAuthentication(JWTAuthentication):
    def authenticate(self, request):
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"]) or None

        if refresh_token is None:
            raise AuthenticationFailed("Refresh token is not in cookie")

        token_obj = RefreshToken(refresh_token)
        try:
            token_obj.check_blacklist()
        except TokenError as e:
            # token is blacklisted -> invalid
            raise AuthenticationFailed("invalid refresh token")

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

        # blacklist validated token -> no longer able to use this token
        token_obj.blacklist()

        return user, refresh_token
