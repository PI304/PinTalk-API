import datetime
import string
import uuid
import base64
import secrets
import random
from typing import Type

import jwt
import shortuuid
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from jwt import InvalidTokenError
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.user.models import User
from config.exceptions import InternalServerError


class UserService(object):
    def __init__(self, user: User, request: Request):
        self.user = user
        self.request = request

    def deactivate_user(self):
        self.user.is_deleted = True
        self.user.deleted_at = datetime.datetime.now()
        self.user.save(update_fields=["is_deleted", "deleted_at"])
        return self.user

    def activate_user(self):
        self.user.is_deleted = False
        self.user.deleted_at = None
        self.user.save(update_fields=["is_deleted", "deleted_at"])
        return self.user

    @staticmethod
    def generate_access_key():
        return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode("utf8").rstrip("=\n")

    @staticmethod
    def generate_secret_key():
        return secrets.token_hex(32)

    @staticmethod
    def generate_random_code(
        number_of_strings, length_of_string, use_special_case: bool = False
    ):
        for x in range(number_of_strings):
            if not use_special_case:
                return "".join(
                    random.choice(string.ascii_letters + string.digits)
                    for _ in range(length_of_string)
                )
            else:
                return "".join(
                    random.choice(string.ascii_letters + string.digits + "~.!@#^_-,?")
                    for _ in range(length_of_string)
                )

    @staticmethod
    def generate_tokens(user: User):
        refresh = RefreshToken.for_user(user)
        # print(refresh)

        return str(refresh.access_token), str(refresh)

    @staticmethod
    def generate_uuid():
        return shortuuid.uuid()

    @staticmethod
    def blacklist_token(token: str) -> None:
        RefreshToken(token).blacklist()

    @staticmethod
    def authenticate_refresh_token(request: Request) -> Type[int]:
        refresh_token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"]) or None

        if refresh_token is None:
            raise AuthenticationFailed("Refresh token is not in cookie")

        try:
            decoded_jwt = jwt.decode(
                jwt=refresh_token,
                key=settings.SIMPLE_JWT["SIGNING_KEY"],
                algorithms=["HS256"],
            )
        except InvalidTokenError as e:
            raise AuthenticationFailed("refresh token invalid. Login again")

        UserService.blacklist_token(refresh_token)

        try:
            outstanding_token = get_object_or_404(OutstandingToken, token=refresh_token)
        except Http404:
            raise InternalServerError()

        return outstanding_token.user_id
