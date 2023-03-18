import datetime
from urllib.parse import unquote, quote
from enum import Enum

import redis
from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.chat.models import Chatroom
from apps.chat.serializers import ChatMessageSerializer
from apps.chat.services import ChatroomService
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

        # Check Chatroom
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "chat_%s" % self.room_name

        chatroom = await self.get_chatroom_instance()

        if chatroom.is_closed:
            # chatroom 이 종료된 상태일 때
            await self.reopen_chatroom(chatroom)

        # Check user
        if isinstance(self.user, AnonymousUser):
            # Guest
            self.user_type = UserType.GUEST
            self.user = chatroom.guest
            self.host = user

            print(f"Anonymous guest <{self.user}> joined the chat room")
        else:
            # Registered User
            self.user_type = UserType.USER
            self.user = self.scope["user"]

            print(f"Registered user <{self.user.email}> joined the chat room")

        self.conn = redis.StrictRedis(host="localhost", port=6379, db=0)

        try:
            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # latest messages, max 50
            past_messages = ChatroomService.get_past_messages(
                self.room_group_name, self.conn
            )

            for m in past_messages:
                await self.channel_layer.group_send(self.room_group_name, m)

        except Exception as e:
            print(e)
            raise DenyConnection(e)

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.save_latest_message()

        try:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
        except Exception as e:
            print("Failed to leave group")

    # Receive message from WebSocket
    async def receive_json(self, content, **kwargs):
        if content["type"] == "request":
            past_messages = ChatroomService.get_past_messages(
                self.room_group_name, self.conn, int(content["timestamp"] / 1000)
            )
            for m in past_messages:
                await self.channel_layer.group_send(self.room_group_name, m)
        elif content["type"] == "chat_message" or content["type"] == "notice":
            content["timestamp"] = int(content["timestamp"] / 1000)
            saved_message = ChatroomService.save_msg_in_mem(
                content, self.room_group_name, self.conn
            )

            # Send message to room group
            await self.channel_layer.group_send(self.room_group_name, saved_message)

            if content["type"] == "chat_message":
                await self.save_message_db(saved_message)

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send_json(event)

    async def notice(self, event):
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

    @database_sync_to_async
    def save_latest_message(self) -> None:
        room_name = self.room_group_name.split("_")[1]
        latest_message = ChatroomService.get_latest_message(
            self.room_group_name, self.conn
        )

        ChatroomService.save_message(room_name, latest_message)

    @database_sync_to_async
    def save_message_db(self, msg_obj: dict) -> None:
        ChatroomService.save_message(self.room_group_name.split("_")[1], msg_obj)

    @database_sync_to_async
    def reopen_chatroom(self, instance: Chatroom) -> None:
        instance.is_closed = False
        instance.updated_at = datetime.datetime.now()
        instance.save(update_fields=["isclosed", "updated_at"])

    @database_sync_to_async
    def get_chatroom_instance(self) -> Chatroom:
        try:
            chatroom = get_object_or_404(Chatroom, name=self.room_name)
        except Http404:
            raise DenyConnection("Cannot get Chatroom instance by provided room name")

        return chatroom
