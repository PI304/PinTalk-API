import logging
from datetime import datetime
from typing import Union

from channels.db import database_sync_to_async
from channels.exceptions import DenyConnection
from rest_framework.exceptions import ValidationError

from apps.chat.consumers.base_consumer import BaseJsonConsumer
from apps.chat.consumers.chat_consumer import UserType
from apps.chat.serializers import ChatMessageInMemorySerializer
from apps.chat.services import StatusConsumerService
from apps.user.models import User

logger = logging.getLogger("pintalk")


class ActiveStatusConsumer(BaseJsonConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__("user_uuid", "status", *args, **kwargs)

    async def connect(self):
        await super().connect()

        if self.user_type == UserType.USER:
            if self.user.uuid != self.room_name:
                logger.info("user uuid mismatch")
                await self.deny_connection(4004)
            if not self.user.configs.use_online_status:
                logger.info("online status function deactivated")
                await self.deny_connection(4009)
        else:
            existing_user = await self.get_user_instance()
            if existing_user is None:
                logger.info("user uuid invalid")
                await self.deny_connection(4004)

            self.host = existing_user
            is_valid_guest = await self.check_valid_guest()
            if not is_valid_guest:
                logger.info("Guest's origin not valid")
                await self.deny_connection(4003)

            if not self.host.configs.use_online_status:
                logger.info("online status function deactivated")
                await self.deny_connection(4009)

            logger.info("anonymous user's origin verified")

        self.service = StatusConsumerService(self.room_group_name, self.redis_conn)

        try:
            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            if self.user_type == UserType.GUEST:
                logger.info(f"Anonymous guest <{self.user}> listening to host status")

                latest_status = self.service.get_latest_status()
                if latest_status is not None:
                    await self.channel_layer.group_send(
                        self.room_group_name, latest_status
                    )
            else:
                logger.info(f"Registered user <{self.user.email}> has logged in")

                status_message = self.status_message(True, True)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    self.service.update_status_in_mem(status_message),
                )

        except Exception as e:
            print(e)
            raise DenyConnection(e)

    async def disconnect(self, close_code):
        # host 가 disconnect 하는 경우 notice 메시지 전송
        if self.user_type == UserType.USER:
            status_message = self.status_message(False, True)
            await self.channel_layer.group_send(
                self.room_group_name, self.service.update_status_in_mem(status_message)
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
        # not allowed to send message from client side
        if content["type"]:
            await self.close(code=4003)

    # Receive message from room group
    async def notice(self, event):
        # Send message to WebSocket
        if self.user_type == UserType.GUEST and event["is_host"]:
            await self.send_json(event)
        elif self.user_type == UserType.USER and not event["is_host"]:
            await self.send_json(event)

    async def serialize_content(self, content) -> None:
        serializer = ChatMessageInMemorySerializer(data=content)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            return await self.close(code=4000)

    @staticmethod
    def status_message(is_online: bool, is_host: bool):
        status = "offline"

        if is_online:
            status = "online"

        return {
            "type": "notice",
            "is_host": is_host,
            "message": status,
            "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
        }

    @database_sync_to_async
    def get_user_instance(self) -> Union[User, None]:
        try:
            user = (
                User.objects.select_related("configs")
                .filter(uuid=self.room_name)
                .first()
            )
            return user
        except User.DoesNotExist:
            return None
