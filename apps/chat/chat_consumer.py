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

        if isinstance(self.user, AnonymousUser):
            # Check Origin
            host = await self.get_host_by_origin_header()
            self.user_type = UserType.GUEST
            self.host = host
        else:
            self.user_type = UserType.USER

        # Check Chatroom
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "chat_%s" % self.room_name

        chatroom = await self.get_chatroom_instance()
        self.chatroom = chatroom
        if chatroom.is_closed:
            # chatroom 이 종료된 상태일 때
            await self.reopen_chatroom()

        if self.user_type == UserType.GUEST:
            self.user = chatroom.guest

        self.conn = redis.StrictRedis(host="localhost", port=6379, db=0)

        try:
            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            if self.user_type == UserType.GUEST:
                print(f"Anonymous guest <{self.user}> joined the chat room")
            else:
                print(f"Registered user <{self.user.email}> joined the chat room")

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
                self.room_group_name, self.conn, content.get("datetime", None)
            )
            for m in past_messages:
                await self.channel_layer.group_send(self.room_group_name, m)
        elif content["type"] == "chat_message":
            saved_message = ChatroomService.save_msg_in_mem(
                content, self.room_group_name, self.conn
            )

            # Send message to room group
            await self.channel_layer.group_send(self.room_group_name, saved_message)

            await self.save_message_db(saved_message)

        elif content["type"] == "notice":
            pass

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send_json(event)

    async def notice(self, event):
        # Send message to WebSocket
        await self.send_json(event)

    async def request(self, event):
        await self.send_json(event)

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

    @database_sync_to_async
    def save_latest_message(self) -> None:
        latest_message = ChatroomService.get_latest_message(
            self.room_group_name, self.conn
        )

        if self.user_type == UserType.GUEST:
            ChatroomService.save_latest_message(
                self.chatroom, latest_message, is_guest=True
            )
        else:
            ChatroomService.save_latest_message(self.chatroom, latest_message)

    @database_sync_to_async
    def save_message_db(self, msg_obj: dict) -> None:
        ChatroomService.save_message(self.chatroom.id, msg_obj)

    @database_sync_to_async
    def reopen_chatroom(self) -> None:

        self.chatroom.is_closed = False
        self.chatroom.updated_at = datetime.datetime.now()
        self.chatroom.save(update_fields=["is_closed", "updated_at"])

    @database_sync_to_async
    def get_chatroom_instance(self) -> Chatroom:
        try:
            chatroom = get_object_or_404(Chatroom, name=self.room_name)
        except Http404:
            raise DenyConnection("Cannot get Chatroom instance by provided room name")

        return chatroom
