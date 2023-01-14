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


class ChatMessageInMemorySerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["chat_message", "notice"])
    message = serializers.CharField(max_length=1000, min_length=1)
    is_host = serializers.BooleanField()
    timestamp = serializers.IntegerField()

    class Meta:
        fields = ["type", "message", "is_host", "timestamp"]
