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
from apps.chat.serializers import (
    ChatMessageInMemorySerializer,
    ChatMessageSerializer,
    ChatroomSerializer,
)
from config.exceptions import InvalidInputException


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
    def save_msg_in_mem(msg_obj: dict, group_name: str, redis_conn=None) -> ChatMessage:
        if redis_conn is None:
            rd = redis.StrictRedis(host="localhost", port=6379, db=0)
        else:
            rd = redis_conn

        serializer = ChatMessageInMemorySerializer(data=msg_obj)
        if serializer.is_valid(raise_exception=True):
            data = serializer.data
            json_msg = json.dumps(data, ensure_ascii=False).encode("utf-8")
            score = data["datetime"].replace("-", "").replace("T", "").replace(":", "")
            rd.zadd(
                group_name,
                {json_msg: score},
            )
            return serializer.validated_data

    @staticmethod
    def get_past_messages(
        group_name: str, redis_conn, starting_point: Union[str, None] = None
    ) -> List[dict]:
        if starting_point is None:
            from_score = datetime.now().strftime("%Y%m%d%H%M%S")
            a_week = str(int(from_score) - 7000000)
        else:
            try:
                from_score = datetime.strptime(starting_point, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                raise InvalidInputException(
                    "Incorrect data format, should be YYYY-MM-DDTHH:MM:SS"
                )

            from_score = int(str(from_score)) - 1
            a_week = str(from_score - 7000000)

        messages = redis_conn.zrangebyscore(group_name, a_week, from_score, 0, 50)

        decoded_messages: List[dict] = []

        for m in messages:
            json_dict = m.decode("utf-8")
            decoded_messages.append(dict(json.loads(json_dict)))
        return decoded_messages

    @staticmethod
    def get_latest_message(group_name: str, redis_conn) -> Union[None, dict]:
        latest_message = redis_conn.zrevrangebyscore(
            group_name,
            datetime.now().strftime("%Y%m%d%H%M%S"),
            "-9999999999",
            start=0,
            num=1,
        )
        if len(latest_message) == 0:
            return None
        else:
            json_dict = latest_message[0].decode("utf-8")
            return dict(json.loads(json_dict))

    @staticmethod
    def save_latest_message(
        chatroom: Chatroom, latest_msg_obj: dict, is_guest: bool = False
    ) -> dict:
        data = dict(
            latest_msg_at=latest_msg_obj.get("datetime"),
            latest_msg=latest_msg_obj.get("message"),
        )
        if not is_guest:
            data["last_checked_at"] = datetime.now()

        serializer = ChatroomSerializer(chatroom, data=data, partial=True)

        if serializer.is_valid(raise_exception=True):
            serializer.save(updated_at=datetime.now())

        print(serializer.data)
        return serializer.data

    @staticmethod
    def delete_chatroom_mem(room_name: str, redis_conn=None) -> None:
        if redis_conn is None:
            rd = redis.StrictRedis(host="localhost", port=6379, db=0)
        else:
            rd = redis_conn

        rd.delete("chat_" + room_name)

    @staticmethod
    def save_message(
        chatroom_id: int,
        msg_obj: dict,
    ) -> dict:
        serializer = ChatMessageSerializer(data=msg_obj)
        if serializer.is_valid(raise_exception=True):
            serializer.save(chatroom_id=chatroom_id)

        return serializer.data


class ChatroomStatusService:
    @staticmethod
    def save_status_in_mem(msg_obj: dict, group_name: str, redis_conn) -> None:
        if redis_conn is None:
            rd = redis.StrictRedis(host="localhost", port=6379, db=0)
        else:
            rd = redis_conn

        json_msg = json.dumps(msg_obj, ensure_ascii=False).encode("utf-8")
        rd.zadd(
            group_name,
            {
                json_msg: datetime.fromtimestamp(msg_obj["timestamp"]).strftime(
                    "%Y%m%d%H%M%S"
                )
            },
        )

    @staticmethod
    def delete_status_room_mem(group_name: str, redis_conn=None) -> None:
        if redis_conn is None:
            rd = redis.StrictRedis(host="localhost", port=6379, db=0)
        else:
            rd = redis_conn

        rd.delete(group_name)
