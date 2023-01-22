import copy
import time
from datetime import datetime
from typing import Union
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
from rest_framework.exceptions import ValidationError

from apps.chat.chat_consumer import UserType
from apps.chat.models import Chatroom
from apps.chat.serializers import ChatMessageSerializer
from apps.chat.services import ChatroomService, ChatroomStatusService
from apps.user.models import User


class ActiveStatusConsumer(AsyncJsonWebsocketConsumer):

    online_message = {
        "type": "status",
        "status": "Online",
        "timestamp": Union[None, float],
    }

    offline_message = {
        "type": "status",
        "status": "Offline",
        "timestamp": Union[None, float],
    }

    async def connect(self):
        self.user = self.scope["user"]

        # Check Origin
        user = await self.get_user_by_origin_header()
        self.origin = user.service_domain

        # Check user
        if isinstance(self.user, AnonymousUser):
            # Guest
            self.user_type = UserType.GUEST
            self.host = user

            print(f"Anonymous guest <{self.user}> joined the chat room")
        else:
            # Registered User
            self.user_type = UserType.USER
            self.user = self.scope["user"]

            print(f"Registered user <{self.user.email}> joined the chat room")

        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "status_%s" % self.room_name
        self.conn = redis.StrictRedis(host="localhost", port=6379, db=0)

        try:
            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            if self.user_type == UserType.USER:
                message = copy.deepcopy(self.online_message)
                message["timestamp"] = time.mktime(datetime.today().timetuple())

                await self.channel_layer.group_send(self.room_group_name, message)
                ChatroomStatusService.save_status_in_mem(
                    message, self.room_group_name, self.conn
                )
            else:  # Guest 일 때
                await self.check_host_status()

        except Exception as e:
            print(e)
            raise DenyConnection(e)

    async def disconnect(self, close_code):
        if self.user_type == UserType.USER:
            message = copy.deepcopy(self.offline_message)
            await self.channel_layer.group_send(self.room_group_name, message)
            ChatroomStatusService.delete_status_room_mem(
                self.room_group_name, self.conn
            )

        try:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
        except Exception as e:
            print("Failed to leave group")

    # Receive message from WebSocket
    async def receive_json(self, content, **kwargs):
        if content["type"] == "status" and self.user_type == UserType.GUEST:
            await self.check_host_status()
        else:
            raise DenyConnection("only 'status' type can be accepted by guest")

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send_json(event)

    # Receive message from room group
    async def notice(self, event):
        # Send message to WebSocket
        await self.send_json(event)

    async def status(self, event):
        # Send message to WebSocket
        await self.send_json(event)

    # used by user type 'GUEST'
    async def check_host_status(self):
        # latest status log in redis mem
        status_log: dict = ChatroomService.get_latest_message(
            self.room_group_name, self.conn
        )

        # Offline
        if status_log is None:
            message = copy.deepcopy(self.offline_message)
            message["timestamp"] = time.mktime(datetime.today().timetuple())

            await self.channel_layer.group_send(self.room_group_name, message)
        else:  # Online
            if status_log["status"] == "Online":
                await self.channel_layer.group_send(self.room_group_name, status_log)

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
