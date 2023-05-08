import django
from channels.exceptions import DenyConnection
import logging

django.setup()

from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken
from jwt import decode as jwt_decode

from apps.user.models import User

logger = logging.getLogger("pintalk")


@database_sync_to_async
def get_user(validated_token):
    try:
        user = User.objects.select_related("configs").get(id=validated_token["user_id"])
        return user
    except User.DoesNotExist:
        raise AuthenticationFailed()


class JwtAuthMiddleware(BaseMiddleware):
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Close old database connections to prevent usage of timed out connections
        close_old_connections()

        # Get token if exists
        qs: dict = parse_qs(scope["query_string"].decode("utf8"))

        if "token" in qs:
            logger.info("user with token attempting to connect to websocket server")
            # Get token
            token = qs["token"][0].replace("/", ".")
            try:
                # This will automatically validate the token and raise an error if token is invalid
                UntypedToken(token)
            except (InvalidToken, TokenError) as e:
                # Token is invalid
                print(e)
                logger.info("token invalid or expired")
                raise DenyConnection()

            else:
                # if token is valid, decode
                decoded_data = jwt_decode(
                    token, settings.SIMPLE_JWT["SIGNING_KEY"], algorithms=["HS256"]
                )
                scope["user"] = await get_user(validated_token=decoded_data)
                logger.info("registered user accepted")

        else:
            scope["user"] = AnonymousUser()
            logger.info("anonymous user accepted")

        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(AuthMiddlewareStack(inner))
