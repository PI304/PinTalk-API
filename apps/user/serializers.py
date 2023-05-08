import uuid

from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from apps.user.models import User, UserConfiguration


class UserSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False, use_url=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "uuid",
            "profile_name",
            "description",
            "access_key",
            "secret_key",
            "service_name",
            "service_expl",
            "service_domain",
            "profile_image",
            "password",
            "is_deleted",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uuid",
            "access_key",
            "secret_key",
            "is_deleted",
            "deleted_at",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data.get("password"))
        return super(UserSerializer, self).create(validated_data)


class UserConfigurationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserConfiguration
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "user"]


class SimpleUserConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserConfiguration
        fields = ["use_online_status"]
        read_only_fields = ["id", "created_at", "updated_at", "user"]


class ClientSerializer(serializers.ModelSerializer):
    configs = SimpleUserConfigurationSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "uuid",
            "profile_name",
            "description",
            "service_name",
            "profile_image",
            "configs",
        ]
        read_only_fields = [
            "email",
            "uuid",
            "profile_name",
            "description",
            "service_name",
            "profile_image",
            "configs",
        ]
