import logging
import datetime
from dotenv import load_dotenv

from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection

from django.http import Http404
from django.shortcuts import get_object_or_404

from apps.chat.consumers.base_consumer import BaseJsonConsumer, UserType
from apps.chat.models import Chatroom
from apps.chat.services import ChatroomService, ChatConsumerService
from config.exceptions import InvalidInputException

load_dotenv()

logger = logging.getLogger("pintalk")


class ChatConsumer(BaseJsonConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__("room_name", "chat", *args, **kwargs)

    async def connect(self):
        await super().connect()

        try:
            chatroom = await self.get_chatroom_instance()
            if chatroom.is_closed:
                # chatroom 이 종료된 상태일 때 연결을 거부함
                raise DenyConnection("this chatroom is closed")
            else:
                self.chatroom = chatroom
                self.service = ChatConsumerService(
                    self.room_group_name, self.chatroom, self.redis_conn
                )
                if self.user_type == UserType.GUEST:
                    self.user = chatroom.guest
        except Http404:
            raise DenyConnection("chatroom does not exist")

        logger.info("chatroom instance valid")

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
            past_messages = self.service.get_past_messages()
            for m in past_messages:
                await self.channel_layer.group_send(self.room_group_name, m)

        except Exception as e:
            print(e)
            raise DenyConnection(e)

    async def disconnect(self, close_code):
        if hasattr(self, "service") and hasattr(self, "room_group_name"):
            await self.save_latest_message()

        await super().disconnect(close_code)

    # Receive message from WebSocket
    async def receive_json(self, content, **kwargs):
        if content["type"] == "request":
            try:
                past_messages = self.service.get_past_messages(
                    content.get("message", None)
                )
                for m in past_messages:
                    await self.channel_layer.group_send(self.room_group_name, m)
            except InvalidInputException:
                await self.close(4000)

        elif content["type"] == "chat_message":
            saved_message = self.service.save_msg_in_mem(content)

            # Send message to room group
            await self.channel_layer.group_send(self.room_group_name, saved_message)

            await self.save_message_db(saved_message)

        elif content["type"] == "notice" and content["message"] == "close":
            await self.close_chatroom()

            logger.info("chatroom closed")
            content["message"] = "closed"
            await self.channel_layer.group_send(self.room_group_name, content)
            await self.close()

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
        latest_message = self.service.get_latest_message()
        if latest_message is not None:
            if self.user_type == UserType.GUEST:
                self.service.save_latest_message_db(latest_message, is_guest=True)
            else:
                self.service.save_latest_message_db(latest_message, is_guest=False)
        else:
            pass

    @database_sync_to_async
    def save_message_db(self, msg_obj: dict) -> None:
        self.service.save_chat_message_db(msg_obj)

    @database_sync_to_async
    def close_chatroom(self) -> None:
        self.chatroom.is_closed = True
        self.chatroom.closed_at = datetime.datetime.now()
        self.chatroom.updated_at = datetime.datetime.now()
        self.chatroom.save(update_fields=["is_closed", "closed_at", "updated_at"])

        self.save_latest_message()
        self.service.delete_chatroom_messages_mem()

    @database_sync_to_async
    def get_chatroom_instance(self) -> Chatroom:
        chatroom = get_object_or_404(Chatroom, name=self.room_name)

        return chatroom
