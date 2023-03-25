import logging
import datetime
import os
from dotenv import load_dotenv

import redis
from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection

from django.http import Http404
from django.shortcuts import get_object_or_404

from apps.chat.base_consumer import BaseJsonConsumer, UserType
from apps.chat.models import Chatroom
from apps.chat.services import ChatroomService

load_dotenv()

logger = logging.getLogger("pintalk")


class ChatConsumer(BaseJsonConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__("room_name", "chat", *args, **kwargs)

    async def connect(self):
        await super().connect()

        try:
            chatroom = await self.get_chatroom_instance()
            self.chatroom = chatroom
        except Http404:
            await self.close(code=4004)

        logger.info("chatroom instance valid")

        if chatroom.is_closed:
            # chatroom 이 종료된 상태일 때
            await self.reopen_chatroom()

        if self.user_type == UserType.GUEST:
            self.user = chatroom.guest

        self.conn = redis.StrictRedis(
            host=os.environ.get("REDIS_HOST"), port=6379, db=0
        )

        try:
            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            if self.user_type == UserType.GUEST:
                print(f"Anonymous guest <{self.user}> joined the chat room")
                logger.info(f"Anonymous guest <{self.user}> joined the chat room")
            else:
                print(f"Registered user <{self.user.email}> joined the chat room")
                logger.info(f"Anonymous guest <{self.user}> joined the chat room")

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

        await super().disconnect(close_code)

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
            logger.info("chatroom closed")
            await self.channel_layer.group_send(self.room_group_name, content)
            await self.close_chatroom()

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send_json(event)

    async def notice(self, event):
        # Send message to WebSocket
        await self.send_json(event)
        await self.close(1000)
        logger.info("websocket closed due to chatroom closure")

    async def request(self, event):
        await self.send_json(event)

    @database_sync_to_async
    def save_latest_message(self) -> None:
        latest_message = ChatroomService.get_latest_message(
            self.room_group_name, self.conn
        )
        if latest_message is not None:
            if self.user_type == UserType.GUEST:
                ChatroomService.save_latest_message(
                    self.chatroom, latest_message, is_guest=True
                )
            else:
                ChatroomService.save_latest_message(self.chatroom, latest_message)
        else:
            pass

    @database_sync_to_async
    def save_message_db(self, msg_obj: dict) -> None:
        ChatroomService.save_message(self.chatroom.id, msg_obj)

    @database_sync_to_async
    def reopen_chatroom(self) -> None:

        self.chatroom.is_closed = False
        self.chatroom.closed_at = None
        self.chatroom.updated_at = datetime.datetime.now()
        self.chatroom.save(update_fields=["is_closed", "closed_at", "updated_at"])

    @database_sync_to_async
    def close_chatroom(self) -> None:
        self.chatroom.is_closed = True
        self.chatroom.closed_at = datetime.datetime.now()
        self.chatroom.updated_at = datetime.datetime.now()
        self.chatroom.save(update_fields=["is_closed", "closed_at", "updated_at"])

        self.save_latest_message()
        ChatroomService.delete_chatroom_messages_mem(self.room_name)

    @database_sync_to_async
    def get_chatroom_instance(self) -> Chatroom:
        chatroom = get_object_or_404(Chatroom, name=self.room_name)

        return chatroom
