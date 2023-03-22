import datetime
import string
import uuid
import base64
import secrets
import random

import shortuuid
from rest_framework.request import Request
from rest_framework_simplejwt.tokens import RefreshToken

from apps.user.models import User


class UserService(object):
    def __init__(self, user: User, request: Request):
        self.user = user
        self.request = request

    def deactivate_user(self):
        self.user.is_deleted = True
        self.user.updated_at = datetime.datetime.now()
        self.user.save(updated_field=["is_deleted", "updated_at"])
        return self.user

    @staticmethod
    def generate_access_key():
        return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode("utf8").rstrip("=\n")

    @staticmethod
    def generate_secret_key():
        return secrets.token_hex(32)

    @staticmethod
    def generate_random_code(number_of_strings, length_of_string):
        for x in range(number_of_strings):
            return "".join(
                random.choice(string.ascii_letters + string.digits)
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
