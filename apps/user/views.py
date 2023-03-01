import datetime

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from apps.user.models import User
from apps.user.serializers import UserSerializer, ClientSerializer
from config.permissions import AuthenticatedClientOnly


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_summary="Get user list (for test only)",
        responses={
            200: openapi.Response("Success", UserSerializer),
            404: "Not found",
        },
    ),
)
class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_summary="Get user by id",
        responses={
            200: openapi.Response("Success", UserSerializer),
            404: "Not found",
        },
    ),
)
class UserDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    allowed_methods = ["PATCH", "GET"]
    parser_classes = [MultiPartParser, FormParser, CamelCaseJSONParser]

    @swagger_auto_schema(
        operation_summary="Update user profile",
        operation_description="Use multipart/form-data type for profile images",
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


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        tags=["client"],
        operation_summary="Fetch host data (for client side)",
        manual_parameters=[
            openapi.Parameter(
                "X-PinTalk-Access-Key",
                openapi.IN_HEADER,
                description="service access key",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "X-PinTalk-Secret-Key",
                openapi.IN_HEADER,
                description="service secret key",
                type=openapi.TYPE_STRING,
            ),
        ],
        responses={
            200: openapi.Response("user", UserSerializer),
            400: "Passwords doesn't match",
        },
    ),
)
class ClientProfileView(generics.RetrieveAPIView):
    permission_classes = [AuthenticatedClientOnly]
    serializer_class = ClientSerializer
    queryset = User.objects.all()

    def get_object(self):
        access_key = self.request.headers.get("X-PinTalk-Access-Key", None)
        secret_key = self.request.headers.get("X-PinTalk-Secret-Key", None)

        try:
            obj = get_object_or_404(User, access_key=access_key, secret_key=secret_key)
        except Http404:
            raise AuthenticationFailed("invalid access_key or secret_key")

        self.check_object_permissions(self.request, obj)

        return obj
