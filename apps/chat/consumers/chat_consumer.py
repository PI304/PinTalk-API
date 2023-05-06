import logging
from typing import Union

from dotenv import load_dotenv

from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection

from datetime import datetime
from django.http import Http404

from apps.chat.consumers.base_consumer import BaseJsonConsumer, UserType
from apps.chat.models import Chatroom
from apps.chat.serializers import ChatroomSerializer
from apps.chat.services import ChatConsumerService
from config.exceptions import InvalidInputException

load_dotenv()

logger = logging.getLogger("pintalk")


class ChatConsumer(BaseJsonConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__("room_name", "chat", *args, **kwargs)

    async def connect(self):
        await super().connect()

        # 유효한 chatroom name 인지 확인
        chatroom = await self.get_chatroom_instance()
        if chatroom is None:
            raise DenyConnection("invalid chatroom name")
        self.chatroom = chatroom
        self.host = self.chatroom.host

        # (유효하다면) User 의 경우 chatroom 이 is_closed = True 이면 DenyConnection
        if self.user_type == UserType.USER and self.chatroom.is_closed:
            raise DenyConnection("this chatroom is closed")

        # (유효하다면) Guest 의 경우 origin 확인하고 is_closed = True 면 False 로 바꿈
        if self.user_type == UserType.GUEST:
            is_valid_guest = await self.check_valid_guest()
            if not is_valid_guest:
                raise DenyConnection("Guest's origin not valid")
            logger.info("anonymous user's origin verified")

            self.guest = self.chatroom.guest
            if self.chatroom.is_closed:
                await self.reopen_chatroom()

        self.service = ChatConsumerService(
            self.room_group_name, self.chatroom, self.redis_conn
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
                logger.info(f"Registered user <{self.user}> joined the chat room")

            # latest messages, max 50
            past_messages = self.service.get_past_messages()

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "data": past_messages,
                    "type": "chat_message",
                    "for_host": bool(self.user_type.value),
                },
            )

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
                    is_ascending=False,
                    starting_point=content.get("message", None),
                )
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "data": past_messages,
                        "type": "chat_message",
                        "for_host": self.user_type.value,
                    },
                )
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
        if "data" in event:
            if (
                event["for_host"] == self.user_type.value
                and self.user_type == UserType.USER
            ):
                del event["for_host"]
                await self.send_json(event)
            elif (
                event["for_host"] == self.user_type.value
                and self.user_type == UserType.GUEST
            ):
                del event["for_host"]
                await self.send_json(event)
        else:
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
        data = {"is_closed": True}
        serializer = ChatroomSerializer(self.chatroom, data=data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save(updated_at=datetime.now(), closed_at=datetime.now())

        self.save_latest_message()
        self.service.delete_chatroom_messages_mem()

    @database_sync_to_async
    def get_chatroom_instance(self) -> Union[Chatroom, None]:
        try:
            chatroom = (
                Chatroom.objects.filter(name=self.room_name)
                .select_related("host")
                .get()
            )
            return chatroom
        except Http404:
            return None

    @database_sync_to_async
    def reopen_chatroom(self):
        data = {"is_closed": False, "closed_at": None}
        serializer = ChatroomSerializer(self.chatroom, data=data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save(updated_at=datetime.now())
