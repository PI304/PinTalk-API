from rest_framework import serializers

from apps.user.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "profile_name",
            "description",
            "access_key",
            "secret_key",
            "service_name",
            "service_expl",
            "service_domain",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "service_name",
            "service_expl",
            "access_key",
            "secret_key",
            "is_deleted",
            "created_at",
            "updated_at",
        ]


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "email",
            "profile_name",
            "description",
            "service_name",
            "service_expl",
            "service_domain",
        ]
        read_only_fields = [
            "email",
            "profile_name",
            "description",
            "service_name",
            "service_expl",
            "service_domain",
        ]
