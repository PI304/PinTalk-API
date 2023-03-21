import datetime

from rest_framework import serializers

from apps.chat.models import Chatroom, ChatMessage
from apps.user.serializers import UserSerializer, ClientSerializer


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "chatroom", "message", "is_host", "datetime"]
        read_only_fields = ["id", "chatroom"]


class SimpleChatroomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chatroom
        fields = [
            "id",
            "host",
            "guest",
            "name",
            "latest_msg",
            "last_checked_at",
            "is_closed",
            "closed_at",
            "is_fixed",
            "fixed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "host",
            "name",
            "latest_msg",
            "last_checked_at",
            "closed_at",
            "fixed_at",
            "created_at",
            "updated_at",
        ]


class ChatroomSerializer(serializers.ModelSerializer):
    host = UserSerializer(read_only=True)

    class Meta:
        model = Chatroom
        fields = [
            "id",
            "host",
            "guest",
            "name",
            "latest_msg",
            "last_checked_at",
            "is_closed",
            "closed_at",
            "is_fixed",
            "fixed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "host",
            "name",
            "latest_msg",
            "last_checked_at",
            "closed_at",
            "fixed_at",
            "created_at",
            "updated_at",
        ]


class ChatroomClientSerializer(serializers.ModelSerializer):
    host = ClientSerializer(read_only=True)

    class Meta:
        model = Chatroom
        fields = [
            "host",
            "guest",
            "name",
            "is_closed",
            "closed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "host",
            "name",
            "is_closed",
            "closed_at",
            "created_at",
            "updated_at",
        ]


class ChatMessageInMemorySerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=["chat_message", "notice", "request", "status"]
    )
    message = serializers.CharField(max_length=1000, min_length=1)
    is_host = serializers.BooleanField()
    datetime = serializers.CharField(max_length=19)

    class Meta:
        fields = ["type", "message", "is_host", "datetime"]

    def validate_datetime(self, value):
        try:
            datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            raise ValueError("Incorrect data format, should be YYYY-MM-DDTHH:MM:SS")
        return value
