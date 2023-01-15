import json
import uuid
from datetime import datetime
from typing import Union, List

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

    @staticmethod
    def get_past_messages(
        group_name: str, redis_conn, starting_point: Union[int, None] = None
    ):
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
    def get_latest_message(group_name: str, redis_conn):
        latest_message = redis_conn.zrevrangebyscore(
            group_name, datetime.now().strftime("%Y%m%d%H%M%S"), "-9999999999", 0, 1
        )
        json_dict = latest_message[0].decode("utf-8")
        return dict(json.loads(json_dict))
