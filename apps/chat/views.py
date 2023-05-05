import time
import urllib
from datetime import datetime
from io import StringIO
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import quote

from django.db.models import QuerySet
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema, no_body
from rest_framework import generics, status, mixins, permissions
from rest_framework.exceptions import ValidationError, NotAuthenticated
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.models import Chatroom, ChatMessage
from apps.chat.serializers import (
    ChatroomSerializer,
    ChatroomClientSerializer,
    ChatMessageSerializer,
    SimpleChatroomSerializer,
)
from apps.chat.services import ChatroomService
from apps.user.models import User
from config.exceptions import (
    InstanceNotFound,
    UnprocessableException,
    InvalidInputException,
)
from config.permissions import HostOnly, ClientWithHeadersOnly
from utils.random_nickname import generate_random_nickname

access_key_param = openapi.Parameter(
    "X-PinTalk-Access-Key",
    openapi.IN_HEADER,
    description="service access key",
    type=openapi.TYPE_STRING,
)
secret_key_param = openapi.Parameter(
    "X-PinTalk-Secret-Key",
    openapi.IN_HEADER,
    description="service secret key",
    type=openapi.TYPE_STRING,
)
guest_name_param = openapi.Parameter(
    "guest",
    openapi.IN_QUERY,
    description="name of the guest",
    type=openapi.TYPE_STRING,
)


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_summary="Get user's chatroom list",
        operation_description="요청을 보내는 유저의 모든 채팅방을 가져옵니다",
        responses={
            404: "Not found",
        },
    ),
)
class ChatroomListView(generics.ListAPIView):
    serializer_class = SimpleChatroomSerializer
    queryset = Chatroom.objects.all()

    def get_queryset(self):
        queryset = self.queryset.filter(host_id=self.request.user.id).order_by(
            "-updated_at"
        )
        return queryset


class ChatroomClientCreateView(generics.GenericAPIView):
    serializer_class = ChatroomClientSerializer
    queryset = Chatroom.objects.all()
    permission_classes = [permissions.AllowAny, ClientWithHeadersOnly]

    @swagger_auto_schema(
        tags=["client"],
        operation_summary="Create chatroom (client side)",
        operation_description="Make a new chatroom with a random guest nickname and saves the chatroom uuid in cookie",
        manual_parameters=[access_key_param, secret_key_param],
        request_body=no_body,
        responses={
            201: openapi.Response("Success", ChatroomClientSerializer),
            401: "User not registered",
            409: "Chatroom with the provided guest name already exists",
        },
    )
    def post(self, request, *args, **kwargs):
        access_key = request.headers["X-PinTalk-Access-Key"]
        secret_key = request.headers["X-PinTalk-Secret-Key"]
        try:
            host_user = get_object_or_404(
                User,
                access_key=access_key,
                secret_key=secret_key,
            )
        except Http404:
            raise NotAuthenticated("User not registered")

        guest_name = generate_random_nickname()

        serializer = self.get_serializer(data={"guest": guest_name})
        if serializer.is_valid(raise_exception=True):
            # django channels group name only accepts ASCII alphanumeric, hyphens, underscores, or periods
            # max length 100
            serializer.save(
                host_id=host_user.id,
                name=ChatroomService.generate_chatroom_uuid(),  # length 22
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(
    name="patch",
    decorator=swagger_auto_schema(
        tags=["client"],
        operation_summary="Resume closed chatroom (for client)",
        operation_description="No body data. Make websocket connection after re-opening this chatroom",
        responses={
            200: openapi.Response("Success", ChatroomClientSerializer),
            404: "Chatroom with provided name does not exist",
        },
    ),
)
class ChatroomClientResumeView(generics.UpdateAPIView):
    queryset = Chatroom.objects.all()
    serializer_class = ChatroomClientSerializer
    allowed_methods = ["PATCH"]

    def get_object(self):
        instance = self.queryset.filter(name=self.kwargs.get("room_name")).first()
        if instance in None:
            raise InstanceNotFound("Chatroom with provided name does not exist")
        return instance

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = {"is_deleted": False, "deleted_at": None}
        serializer = self.get_serializer(instance, data=data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save(updated_at=timezone.now())

        message_obj = {
            "type": "notice",
            "message": "Resumed",
            "timestamp": time.mktime(datetime.today().timetuple()),
        }

        ChatroomService.save_msg_in_mem(message_obj, "chat_" + instance.name)
        return Response(serializer.data, status=status.HTTP_200_OK)


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_summary="Retrieve chatroom data",
        responses={200: openapi.Response("ok", ChatroomClientSerializer)},
    ),
)
class ChatroomDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ChatroomClientSerializer
    queryset = Chatroom.objects.all()
    permission_classes = [HostOnly]
    allowed_methods = ["GET", "DELETE"]

    @swagger_auto_schema(
        operation_summary="Immediately deletes a chatroom",
        operation_description="즉시 대화방을 내역을 삭제합니다. 채팅방을 삭제하기 위해선 우선 채팅방을 종료해야 합니다.",
        responses={204: "deleted"},
    )
    def delete(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        instance: Chatroom = self.get_object()
        if not instance.is_closed:
            raise UnprocessableException("chatroom should be closed before deletion")
        instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ChatroomExportView(APIView):
    @swagger_auto_schema(
        operation_summary="Download chat messages from a chatroom as txt format",
        operation_description="txt 파일 포맷으로 특정 채팅방의 채팅 내역을 다운로드 받습니다",
    )
    def get(self, request: Request, pk: int, format=None) -> HttpResponse:
        queryset = Chatroom.objects.select_related("host").filter(id=pk)

        if len(queryset) == 0:
            raise InstanceNotFound("chatroom with the provided id does not exist")
        instance = queryset.first()

        service = ChatroomService(request, instance)
        content: str = service.get_file_text()

        filename = f'{instance.guest}_{datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}'

        encoded_filename = urllib.parse.quote(filename.encode("utf-8"))

        response = HttpResponse(
            content=content,
            content_type="application/octet-stream",
            status=200,
        )
        response.headers[
            "Content-Disposition"
        ] = "attachment; filename*=utf-8''{}.txt".format(encoded_filename)

        return response


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_summary="Get chatroom messages (with pagination)",
        operation_description="DB 에 저장된 메시지 내역을 가져옵니다. 종료된 채팅일 경우와 레디스에서 제공하는 메시지보다 이전의 메시지가 필요한 경우 사용합니다.",
        manual_parameters=[
            openapi.Parameter(
                "id",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="chatroom id",
            ),
            openapi.Parameter(
                "offset",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="어디서부터 가져올 것인지 (몇 개를 뛰어넘을 것인지)",
            ),
            openapi.Parameter(
                "limit",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="몇 개 가져올 것인지",
            ),
        ],
    ),
)
class ChatroomMessageView(generics.ListAPIView):
    queryset = ChatMessage.objects.all()
    serializer_class = ChatMessageSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self) -> QuerySet:
        return (
            self.queryset.select_related("chatroom")
            .filter(chatroom_id=self.kwargs.get("pk"))
            .all()
            .order_by("-datetime")
        )


class ChatroomRestoreView(generics.UpdateAPIView):
    queryset = Chatroom.objects.all()
    serializer_class = SimpleChatroomSerializer
    allowed_methods = ["PATCH"]

    @swagger_auto_schema(
        operation_summary="Restore closed chatroom",
        operation_description="Request body should be empty",
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT),
        responses={200: openapi.Response("restored", SimpleChatroomSerializer)},
    )
    def patch(self, request, *args, **kwargs) -> Response:
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data={"is_closed": True, "closed_at": None}, partial=True
        )
        if serializer.is_valid(raise_exception=True):
            serializer.save(updated_at=datetime.now())

        return Response(serializer.data)
