from rest_framework import serializers

from apps.chat.models import Chatroom, ChatMessage
from apps.user.serializers import UserSerializer


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "chatroom", "message", "is_host", "created_at", "updated_at"]
        read_only_fields = [
            "id",
            "chatroom",
            "message",
            "is_host",
            "created_at",
            "updated_at",
        ]


class ChatroomSerializer(serializers.ModelSerializer):
    host = UserSerializer(read_only=True)
    # last_message = ChatMessageSerializer(read_only=True)

    class Meta:
        model = Chatroom
        fields = ["id", "host", "guest", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "host", "name", "created_at", "updated_at"]
