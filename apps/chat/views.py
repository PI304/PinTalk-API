from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, mixins
from rest_framework.exceptions import ValidationError, NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chat.models import Chatroom
from apps.chat.serializers import ChatroomSerializer
from apps.chat.services import ChatroomService
from apps.user.models import User
from config.exceptions import InstanceNotFound

access_key_param = openapi.Parameter(
    "X-ChatBox-Access-Key",
    openapi.IN_HEADER,
    description="service access key",
    type=openapi.TYPE_STRING,
)
secret_key_param = openapi.Parameter(
    "X-ChatBox-Secret-Key",
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
        responses={
            200: openapi.Response("Success", ChatroomSerializer),
            404: "Not found",
        },
    ),
)
class ChatroomListView(generics.ListAPIView):
    serializer_class = ChatroomSerializer
    queryset = Chatroom.objects.all()

    def get_queryset(self):
        try:
            user = get_object_or_404(User, access_key=self.kwargs.get("access_key"))
        except Http404:
            raise InstanceNotFound("User with the provided id does not exist")

        queryset = self.queryset.filter(host__access_key=user.access_key).order_by(
            "-latest_msg__created_at"
        )
        return queryset


class ChatroomClientCreateView(generics.GenericAPIView):
    serializer_class = ChatroomSerializer
    queryset = Chatroom.objects.all()

    @swagger_auto_schema(
        tags=["client"],
        operation_summary="Open chatroom (client side)",
        operation_description="Make a new chatroom with guest's name (채팅방 새로 생성)",
        manual_parameters=[access_key_param, secret_key_param],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["serviceName", "guest"],
            properties={
                "serviceName": openapi.Schema(
                    type=openapi.TYPE_STRING, description="등록한 서비스의 정확한 이름"
                ),
                "guest": openapi.Schema(
                    type=openapi.TYPE_STRING, description="게스트가 입력한 채팅명"
                ),
            },
        ),
        responses={
            201: openapi.Response("Success", ChatroomSerializer),
            401: "User not registered",
        },
    )
    def post(self, request, *args, **kwargs):
        access_key = request.headers["X-ChatBox-Access-Key"]
        secret_key = request.headers["X-ChatBox-Secret-Key"]
        try:
            host_user = get_object_or_404(
                User,
                access_key=access_key,
                secret_key=secret_key,
                service_name=request.data.get("service_name"),
            )
        except Http404:
            raise NotAuthenticated("User not registered")

        serializer = self.get_serializer(data={"guest": request.data.get("guest")})
        if serializer.is_valid(raise_exception=True):
            # django channels group name only accepts ASCII alphanumeric, hyphens, underscores, or periods
            # max length 100
            serializer.save(
                host_id=host_user.id,
                name=ChatroomService.generate_chatroom_uuid(),  # length 22
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        tags=["client"],
        operation_summary="Reenter (get) chatroom (client side)",
        operation_description="Reenter an existing chatroom",
        manual_parameters=[access_key_param, secret_key_param, guest_name_param],
        responses={
            200: openapi.Response("Success", ChatroomSerializer),
            401: "User not registered",
            404: "No previous chatroom record",
        },
    ),
)
class ChatroomClientRetrieveView(generics.RetrieveAPIView):
    serializer_class = ChatroomSerializer
    queryset = Chatroom.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["guest"]

    def get_queryset(self):
        access_key = self.request.headers["X-ChatBox-Access-Key"]
        secret_key = self.request.headers["X-ChatBox-Secret-Key"]
        try:
            host_user = get_object_or_404(
                User,
                access_key=access_key,
                secret_key=secret_key,
            )
        except Http404:
            raise NotAuthenticated("User not registered")
        return self.queryset.filter(host_id=host_user.id)

    def get_object(self):
        queryset = self.get_queryset()
        return queryset.filter(guest=self.kwargs.get("guest")).first()


class ChatroomDestroyView(generics.DestroyAPIView):
    serializer_class = ChatroomSerializer
    queryset = Chatroom.objects.all()

    def get_object(self):
        try:
            chatroom = get_object_or_404(
                Chatroom, host_id=self.kwargs.get("pk"), guest=self.kwargs.get("guest")
            )
        except Http404:
            raise InstanceNotFound(
                "Chatroom with the provided id and guest name does not exist"
            )

        return chatroom

    def perform_destroy(self, instance):
        ChatroomService.delete_chatroom_mem(instance.name)
        instance.delete()


class ChatroomExportView(APIView):
    pass
