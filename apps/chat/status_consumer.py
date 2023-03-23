from datetime import datetime

from channels.exceptions import DenyConnection
from rest_framework.exceptions import ValidationError

from apps.chat.base_consumer import BaseJsonConsumer
from apps.chat.chat_consumer import UserType
from apps.chat.serializers import ChatMessageInMemorySerializer


class ActiveStatusConsumer(BaseJsonConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__("user_uuid", "status", *args, **kwargs)

    async def connect(self):
        await super().connect()

        try:
            # Join room group
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            if self.user_type == UserType.GUEST:
                print(f"Anonymous guest <{self.user}> listening to host status")

            else:
                print(f"Registered user <{self.user.email}> has logged in")

                # Host online
                host_online_msg = {
                    "type": "notice",
                    "is_host": True,
                    "message": "online",
                    "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                }
                await self.channel_layer.group_send(
                    self.room_group_name, host_online_msg
                )

        except Exception as e:
            print(e)
            raise DenyConnection(e)

    async def disconnect(self, close_code):
        # host 가 disconnect 하는 경우 notice 메시지 전송
        if self.user_type == UserType.USER:
            host_offline_msg = {
                "type": "notice",
                "is_host": True,
                "message": "offline",
                "datetime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            }
            await self.channel_layer.group_send(self.room_group_name, host_offline_msg)

        try:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )
        except Exception as e:
            print("Failed to leave group")

    # Receive message from WebSocket
    # content: 보낸 사람이 쓴 websocket 메시지
    async def receive_json(self, content, **kwargs):
        if content["type"] != "notice":
            # protocol error
            return await self.close(code=4000)

        await self.serialize_content(content)
        await self.channel_layer.group_send(self.room_group_name, content)
        print("received", self.user_type)

    # Receive message from room group
    async def notice(self, event):
        # Send message to WebSocket
        # host 가 접속해있는 상황에서 guest 가 접속
        print("notice event", self.user_type)
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
