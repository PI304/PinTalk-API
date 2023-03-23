import logging

from enum import Enum

from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.shortcuts import get_object_or_404

from apps.user.models import User

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

        if isinstance(self.user, AnonymousUser):
            # Check Origin
            host = await self.get_host_by_origin_header()
            logger.info("anonymous user's origin verified")
            self.user_type = UserType.GUEST
            self.host = host
        else:
            self.user_type = UserType.USER

        self.room_name = self.scope["url_route"]["kwargs"][self.url_kwargs]
        self.room_group_name = f"{self.name_prefix}_{self.room_name}"

        # more actions here

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
    def get_host_by_origin_header(self):
        origin = None
        for header_tuple in self.scope["headers"]:
            if bytes("origin", "utf-8") in header_tuple:
                origin = header_tuple[1].decode("utf-8").split("//")[1]

        if not origin:
            raise DenyConnection("Origin header missing")

        try:
            registered_user = get_object_or_404(User, service_domain=origin)
        except Http404:
            raise DenyConnection("Request origin not registered")
        return registered_user
