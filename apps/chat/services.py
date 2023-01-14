import json
import uuid
from datetime import datetime
from typing import Union

import shortuuid
from rest_framework.request import Request

from apps.chat.models import Chatroom, ChatMessage
from apps.chat.serializers import ChatMessageInMemorySerializer


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
    def save_msg_in_mem(msg_obj: dict, group_name: str, redis_conn):
        serializer = ChatMessageInMemorySerializer(data=msg_obj)
        if serializer.is_valid(raise_exception=True):
            data = serializer.data
            print(data)
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
