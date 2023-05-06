import json
import os
import uuid
from datetime import datetime
from typing import Union, List, Optional
from dotenv import load_dotenv

import redis
import shortuuid
from redis.client import Redis
from rest_framework.request import Request

from apps.chat.models import Chatroom, ChatMessage
from apps.chat.serializers import (
    ChatMessageInMemorySerializer,
    ChatMessageSerializer,
    ChatroomSerializer,
)
from config.exceptions import InvalidInputException

load_dotenv()


class RedisService:
    def __init__(self, redis_conn: Redis):
        self.redis_conn = redis_conn

    def get_latest_obj(self, key: str) -> Union[dict, None]:
        latest_message = self.redis_conn.zrevrangebyscore(
            key,
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

    def save_obj(self, key: str, msg_obj: dict) -> dict:
        serializer = ChatMessageInMemorySerializer(data=msg_obj)
        if serializer.is_valid(raise_exception=True):
            data = serializer.data
            json_msg = json.dumps(data, ensure_ascii=False).encode("utf-8")
            score = self.datetime_str_to_score_format(data["datetime"])
            self.redis_conn.zadd(
                key,
                {json_msg: score},
            )
            return serializer.validated_data

    def empty_sorted_set(self, key: str) -> None:
        self.redis_conn.zremrangebyrank(key, 0, -1)

    def remove_key(self, key: str) -> None:
        self.redis_conn.delete(key)

    @staticmethod
    def datetime_str_to_score_format(datetime_str: str) -> str:
        try:
            datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            raise ValueError("Incorrect data format, should be YYYY-MM-DDTHH:MM:SS")

        return datetime_str.replace("-", "").replace("T", "").replace(":", "")


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

    def get_file_text(self) -> str:
        msg_data = ""
        if self.chatroom.is_closed:
            messages = ChatMessage.objects.filter(chatroom_id=self.chatroom.id).values()
        else:
            messages = self._get_all_messages_in_mem()

        for m in messages:
            if self.chatroom.is_closed:
                row_data = f"[{m.get('datetime')}"
            else:
                row_data = f"[{m.get('datetime').replace('T', ' ')}"

            if m.get("is_host"):
                row_data += f" {self.chatroom.host.profile_name}] {m.get('message')}\n"
            else:
                row_data += f" {self.chatroom.guest}] {m.get('message')}\n"

            msg_data += row_data

        return msg_data

    def _get_all_messages_in_mem(self):
        group_name = f"chat_{self.chatroom.name}"
        redis_conn = redis.StrictRedis(
            host=os.environ.get("REDIS_HOST"), port=6379, db=0
        )

        messages = redis_conn.zrange(group_name, 0, -1, withscores=True)

        decoded_messages: List[dict] = []

        for m in messages:
            json_dict = m[0].decode("utf-8")
            decoded_messages.append(dict(json.loads(json_dict)))
        return decoded_messages


class ChatConsumerService:
    def __init__(
        self, group_name: str, chatroom: Chatroom, redis_conn: Optional[Redis]
    ):
        self.redis_service = RedisService(redis_conn)
        self.group_name = group_name
        self.chatroom = chatroom
        if redis_conn is None:
            self.redis_conn = redis.StrictRedis(
                host=os.environ.get("REDIS_HOST"), port=6379, db=0
            )
        else:
            self.redis_conn = redis_conn

    def save_msg_in_mem(self, msg_obj: dict) -> dict:
        return self.redis_service.save_obj(self.group_name, msg_obj)

    def get_past_messages(
        self,
        is_ascending: bool = True,
        starting_point: Optional[str] = None,
    ) -> List[dict]:
        if starting_point is None:
            base_score = datetime.now().strftime("%Y%m%d%H%M%S")
        else:
            try:
                starting_datetime = datetime.strptime(
                    starting_point, "%Y-%m-%dT%H:%M:%S"
                )
                base_score = starting_datetime.strftime("%Y%m%d%H%M%S")
                base_score = str(int(base_score) - 1)
            except ValueError:
                raise InvalidInputException(
                    "Incorrect data format, should be YYYY-MM-DDTHH:MM:SS"
                )

        messages = self.redis_conn.zrevrangebyscore(
            self.group_name, base_score, "-inf", withscores=True, start=0, num=50
        )
        if is_ascending:
            messages = sorted(messages, key=lambda x: x[1])
        decoded_messages: List[dict] = []

        for m in messages:
            json_str = m[0].decode(
                "utf-8"
            )  # zrevrangebyscore 의 아이템은 (value, score) 형태이므로 m[0]
            decoded_messages.append(dict(json.loads(json_str)))
        return decoded_messages

    def get_latest_message(self) -> Union[None, dict]:
        return self.redis_service.get_latest_obj(self.group_name)

    def save_latest_message_db(
        self, latest_msg_obj: dict, is_guest: bool = False
    ) -> dict:
        data = dict(
            latest_msg_at=latest_msg_obj.get("datetime"),
            latest_msg=latest_msg_obj.get("message"),
        )
        if not is_guest:
            data["last_checked_at"] = datetime.now()

        serializer = ChatroomSerializer(self.chatroom, data=data, partial=True)

        if serializer.is_valid(raise_exception=True):
            serializer.save(updated_at=datetime.now())

        return serializer.data

    def delete_chatroom_messages_mem(self) -> None:
        self.redis_service.remove_key(self.group_name)

    def save_chat_message_db(self, msg_obj: dict) -> dict:
        serializer = ChatMessageSerializer(data=msg_obj)
        if serializer.is_valid(raise_exception=True):
            serializer.save(chatroom_id=self.chatroom.id)

        return serializer.data


class StatusConsumerService:
    def __init__(self, group_name: str, redis_conn: Optional[Redis]):
        self.redis_service = RedisService(redis_conn)
        self.group_name = group_name
        if redis_conn is None:
            self.redis_conn = redis.StrictRedis(
                host=os.environ.get("REDIS_HOST"), port=6379, db=0
            )
        else:
            self.redis_conn = redis_conn

    def get_latest_status(self) -> Union[None, dict]:
        return self.redis_service.get_latest_obj(self.group_name)

    def update_status_in_mem(self, msg_obj: dict) -> dict:
        self.redis_service.empty_sorted_set(self.group_name)
        return self.redis_service.save_obj(self.group_name, msg_obj)

    def delete_status_room_mem(self) -> None:
        self.redis_service.remove_key(self.group_name)
