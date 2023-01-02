import uuid
import base64
import secrets
from rest_framework.request import Request

from apps.user.models import User


class UserService(object):
    def __init__(self, user: User, request: Request):
        self.user = user
        self.request = request

    @staticmethod
    def generate_access_key():
        return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf8').rstrip('=\n')

    @staticmethod
    def generate_secret_key():
        return secrets.token_hex(32)