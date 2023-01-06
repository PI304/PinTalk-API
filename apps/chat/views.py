from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError, NotAuthenticated
from rest_framework.response import Response

from apps.chat.models import Chatroom
from apps.chat.serializers import ChatroomSerializer
from apps.user.models import User
from config.exceptions import InstanceNotFound


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
class ChatroomView(generics.ListCreateAPIView):
    serializer_class = ChatroomSerializer
    queryset = Chatroom.objects.all()

    def get_queryset(self):
        # TODO: 마지막 메시지 기준으로 내림차순 정렬

        try:
            user = get_object_or_404(User, id=self.kwargs.get("pk"))
        except Http404:
            raise InstanceNotFound("User with the proviede id does not exist")

        queryset = self.queryset.filter(host_id=user.id)
        return queryset

    @swagger_auto_schema(
        operation_summary="Open chatroom",
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
        if (
            not request.headers["X-ChatBox-Access-Key"]
            or not request.headers["X-ChatBox-Secret-Key"]
        ):
            raise ValidationError(
                "'X-ChatBox-Access-Key' and 'X-ChatBox-Secret-Key' header must be present"
            )
        access_key = request.headers["X-ChatBox-Access-Key"]
        secret_key = request.headers["X-ChatBox-Secret-Key"]
        try:
            host_user = get_object_or_404(
                User,
                id=kwargs.get("pk"),
                access_key=access_key,
                secret_key=secret_key,
                service_name=request.data.get("service_name"),
            )
        except Http404:
            raise NotAuthenticated("User not registered")

        serializer = self.get_serializer(data={"guest": request.data.get("guest")})
        if serializer.is_valid(raise_exception=True):
            serializer.save(
                host_id=host_user.id,
                name=f"{host_user.service_name}:{request.data.get('guest')}",
            )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
