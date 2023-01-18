import json
import uuid
from datetime import datetime
from typing import Union, List

import redis
import shortuuid
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.request import Request

from apps.chat.models import Chatroom, ChatMessage
from apps.chat.serializers import ChatMessageInMemorySerializer, ChatMessageSerializer
from config.exceptions import InstanceNotFound


class ChatroomService(object):
    def __init__(
        self,
        request: Union[Request, None] = None,
        chatroom: Union[Chatroom, None] = None,
    ):
        self.request = request
        self.chatroom = chatroom

    @staticmethod
    def generate_chatroom_uuid() -> str:
        u = uuid.uuid1()
        s = shortuuid.encode(u)
        return s

    @staticmethod
    def save_msg_in_mem(msg_obj: dict, group_name: str, redis_conn) -> ChatMessage:
        serializer = ChatMessageInMemorySerializer(data=msg_obj)
        if serializer.is_valid(raise_exception=True):
            data = serializer.data
            json_msg = json.dumps(data, ensure_ascii=False).encode("utf-8")
            redis_conn.zadd(
                group_name,
                {
                    json_msg: datetime.fromtimestamp(data["timestamp"]).strftime(
                        "%Y%m%d%H%M%S"
                    )
                },
            )
            return serializer.validated_data

    @staticmethod
    def get_past_messages(
        group_name: str, redis_conn, starting_point: Union[int, None] = None
    ) -> List[dict]:
        if starting_point is None:
            from_time = datetime.now().strftime("%Y%m%d%H%M%S")
        else:
            from_time = datetime.fromtimestamp(starting_point - 1)

        a_week = str(int(from_time) - 7000000)
        messages = redis_conn.zrangebyscore(group_name, a_week, from_time, 0, 50)

        decoded_messages: List[dict] = []

        for m in messages:
            json_dict = m.decode("utf-8")
            decoded_messages.append(dict(json.loads(json_dict)))
        return decoded_messages

    @staticmethod
    def get_latest_message(group_name: str, redis_conn) -> dict:
        latest_message = redis_conn.zrevrangebyscore(
            group_name, datetime.now().strftime("%Y%m%d%H%M%S"), "-9999999999", 0, 1
        )
        json_dict = latest_message[0].decode("utf-8")
        return dict(json.loads(json_dict))

    @staticmethod
    def delete_chatroom_mem(room_name: str, redis_conn=None) -> None:
        if redis_conn is None:
            rd = redis.StrictRedis(host="localhost", port=6379, db=0)
        else:
            rd = redis_conn

        rd.delete("chat_" + room_name)

    @staticmethod
    def save_message(room_name: str, msg_obj: dict) -> Chatroom:
        try:
            chatroom = get_object_or_404(Chatroom, name=room_name)
        except Http404:
            raise InstanceNotFound("chatroom with the provided name does not exist")

        data = {
            "message": msg_obj["message"],
            "is_host": msg_obj["is_host"],
        }

        serializer = ChatMessageSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(chatroom_id=chatroom.id)

        chatroom.latest_msg_id = serializer.data.get("id")
        chatroom.updated_at = timezone.now()
        chatroom.save(update_fields=["latest_msg", "updated_at"])

        return chatroom
