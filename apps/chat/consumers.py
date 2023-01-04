import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
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
        message = content["message"]

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name, {"type": "chat_message", "message": message}
        )

    # Receive message from room group
    async def chat_message(self, event):
        print("save")
        # Send message to WebSocket
        await self.send_json(event)
