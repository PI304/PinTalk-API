import logging
import os
import redis

from enum import Enum

from dotenv import load_dotenv
from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.shortcuts import get_object_or_404

from apps.user.models import User

load_dotenv()
logger = logging.getLogger("pintalk")


class UserType(Enum):
    GUEST = 0
    USER = 1


class BaseJsonConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, url_kwargs, name_prefix, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url_kwargs = url_kwargs
        self.name_prefix = name_prefix

    async def connect(self):
        self.user = self.scope["user"]
        self.host = None

        if isinstance(self.user, AnonymousUser):
            self.user_type = UserType.GUEST
        else:
            self.user_type = UserType.USER

        self.room_name = self.scope["url_route"]["kwargs"][self.url_kwargs]
        self.room_group_name = f"{self.name_prefix}_{self.room_name}"

        # more actions here
        self.redis_conn = redis.StrictRedis(
            host=os.environ.get("REDIS_HOST"), port=6379, db=0
        )

    async def disconnect(self, close_code):
        try:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
        except Exception as e:
            print("Failed to leave group")

    async def receive_json(self, content, **kwargs):
        pass

    @database_sync_to_async
    def check_valid_guest(self) -> bool:
        origin = None
        for header_tuple in self.scope["headers"]:
            if bytes("origin", "utf-8") in header_tuple:
                origin = header_tuple[1].decode("utf-8").split("//")[1]

        if not origin:
            raise DenyConnection("Origin header missing")

        try:
            registered_user = get_object_or_404(
                User, service_domain=origin, id=self.host.id
            )
            return True
        except Http404:
            return False
