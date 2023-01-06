import datetime

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.response import Response

from apps.user.models import User
from apps.user.serializers import UserSerializer


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
