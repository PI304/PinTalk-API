import datetime

from django.http import Http404
from django.shortcuts import get_object_or_404
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response

from apps.user.models import User
from apps.user.serializers import UserSerializer, ClientSerializer
from config.exceptions import InstanceNotFound


class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()


class UserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    allowed_methods = ["PATCH", "GET"]

    @swagger_auto_schema(
        operation_summary="Update user profile",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "profileName": openapi.Schema(
                    type=openapi.TYPE_STRING, description="채팅 프로필 이름"
                ),
                "description": openapi.Schema(
                    type=openapi.TYPE_STRING, description="채팅 프로필 상태 메세지"
                ),
                "serviceDomain": openapi.Schema(
                    type=openapi.TYPE_STRING, description="운영하려는 사이트의 도메인"
                ),
                "profileImage": openapi.Schema(
                    type=openapi.TYPE_FILE, description="프로필 사진"
                ),
            },
        ),
        responses={
            200: openapi.Response("user", UserSerializer),
            400: "Passwords doesn't match",
        },
    )
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save(updated_at=datetime.datetime.now())

        return Response(serializer.data, status=status.HTTP_200_OK)


class ClientView(generics.RetrieveAPIView):
    serializer_class = ClientSerializer
    queryset = User.objects.all()

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

    @swagger_auto_schema(
        operation_summary="Fetch host data (for client side)",
        manual_parameters=[access_key_param, secret_key_param],
        responses={
            200: openapi.Response("user", UserSerializer),
            400: "Passwords doesn't match",
        },
    )
    def get(self, request, *args, **kwargs) -> Response:
        access_key = request.headers["X-ChatBox-Access-Key"]
        secret_key = request.headers["X-ChatBox-Secret-Key"]

        try:
            instance = get_object_or_404(
                User, access_key=access_key, secret_key=secret_key
            )
        except Http404:
            raise AuthenticationFailed("Invalid access key or secret key")

        serializer = self.get_serializer(instance)

        return Response(serializer.data, status=status.HTTP_200_OK)
