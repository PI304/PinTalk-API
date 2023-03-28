import json
import os
import uuid
from datetime import datetime
from io import StringIO
from typing import Union, List
from dotenv import load_dotenv

import redis
import shortuuid
from rest_framework.request import Request

from apps.chat.models import Chatroom, ChatMessage
from apps.chat.serializers import (
    ChatMessageInMemorySerializer,
    ChatMessageSerializer,
    ChatroomSerializer,
)
from config.exceptions import InvalidInputException

load_dotenv()


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
            rd = redis.StrictRedis(host=os.environ.get("REDIS_HOST"), port=6379, db=0)
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
    def delete_chatroom_messages_mem(room_name: str, redis_conn=None) -> None:
        if redis_conn is None:
            rd = redis.StrictRedis(host=os.environ.get("REDIS_HOST"), port=6379, db=0)
        else:
            rd = redis_conn

        rd.zremrangebyrank("chat_" + room_name, 0, -1)

    @staticmethod
    def save_message(
        chatroom_id: int,
        msg_obj: dict,
    ) -> dict:
        serializer = ChatMessageSerializer(data=msg_obj)
        if serializer.is_valid(raise_exception=True):
            serializer.save(chatroom_id=chatroom_id)

        return serializer.data

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


class ChatroomStatusService:
    @staticmethod
    def save_status_in_mem(msg_obj: dict, group_name: str, redis_conn) -> None:
        if redis_conn is None:
            rd = redis.StrictRedis(host=os.environ.get("REDIS_HOST"), port=6379, db=0)
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
            rd = redis.StrictRedis(host=os.environ.get("REDIS_HOST"), port=6379, db=0)
        else:
            rd = redis_conn

        rd.delete(group_name)
