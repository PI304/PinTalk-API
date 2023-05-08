import datetime

from django.db.models import QuerySet
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status, permissions
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404 as _get_object_or_404

from apps.user.models import User, UserConfiguration
from apps.user.serializers import (
    UserSerializer,
    ClientSerializer,
    UserConfigurationSerializer,
)
from config.permissions import (
    RequestUserOnly,
    AuthorizedOriginOnly,
)


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

    @swagger_auto_schema(
        operation_summary="Update user profile",
        operation_description="Use multipart/form-data type for profile images",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "serviceName": openapi.Schema(
                    type=openapi.TYPE_STRING, description="서비스 이름"
                ),
                "serviceExpl": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="서비스 설명, 최대 200자",
                ),
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
            200: openapi.Response("user", ClientSerializer),
            400: "Passwords doesn't match",
        },
    ),
)
class ClientProfileView(generics.RetrieveAPIView):
    permission_classes = [AuthorizedOriginOnly]
    serializer_class = ClientSerializer
    queryset = User.objects.all()

    def get_object(self):
        access_key = self.request.headers.get("X-PinTalk-Access-Key", None)
        secret_key = self.request.headers.get("X-PinTalk-Secret-Key", None)

        try:
            obj = (
                self.get_queryset()
                .filter(access_key=access_key, secret_key=secret_key)
                .first()
            )
        except User.DoesNotExist:
            raise AuthenticationFailed("invalid access_key or secret_key")

        self.check_object_permissions(self.request, obj)

        return obj


@method_decorator(
    name="patch",
    decorator=swagger_auto_schema(
        operation_summary="Updates user's configuration",
        operation_description="유저의 환경설정을 조작합니다",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "use_online_status": openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="온라인 접속 여부를 표시할 지 선택",
                    default=True,
                )
            },
        ),
        responses={200: openapi.Response("updated", UserConfigurationSerializer)},
    ),
)
class UserConfigView(generics.UpdateAPIView):
    allowed_methods = ["PATCH"]
    serializer_class = UserConfigurationSerializer
    queryset = UserConfiguration.objects.all()
    permission_classes = [RequestUserOnly]
    lookup_field = "user_id"

    def get_queryset(self):
        return self.queryset.select_related("user").all()

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field

        queryset = self.filter_queryset(self.get_queryset())

        filter_kwargs = {self.lookup_field: self.kwargs[lookup_url_kwarg]}
        obj = _get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj
