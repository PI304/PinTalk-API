from enum import Enum

from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.shortcuts import get_object_or_404

from apps.user.models import User


class UserType(Enum):
    GUEST = 0
    USER = 1


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        # Check Origin
        user = await self.get_user_by_origin_header()
        self.origin = user.service_domain
        # Check user
        if isinstance(self.user, AnonymousUser):
            # Guest
            self.user_type = UserType.GUEST
            # Check guest name
            query_string = self.scope["query_string"].decode("utf-8")
            if "name=" not in query_string:
                raise DenyConnection("Query string for 'name' missing")
            self.user = query_string.split("=")[1]

            print(f"Anonymous guest <{self.user}> joined the chat room")
        else:
            # Registered User
            self.user_type = UserType.USER
            self.user = self.scope["user"]

            print(f"Registered user <{self.user.email}> joined the chat room")

        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "chat_%s" % self.room_name

        try:
            # Join room group

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
        except Exception as e:
            print("Websocket Connection Failed")

    async def disconnect(self, close_code):
        try:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
        except Exception as e:
            print("Failed to leave group")

    # Receive message from WebSocket
    async def receive_json(self, content, **kwargs):
        print("save here")
        message = content["message"]

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", "message": message}
        )

    # Receive message from room group
    async def chat_message(self, event):
        print("do not save here")
        # Send message to WebSocket
        await self.send_json(event)

    @database_sync_to_async
    def get_user_by_origin_header(self):
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
