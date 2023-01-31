"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.views import get_schema_view
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import api_view

api_info = openapi.Info(
    title="PinTalk - API Doc",
    default_version="v1",
    description="PinTalk Application을 위한 API 문서\nAcceptHeader Versioning 을 사용합니다.",
    terms_of_service="https://www.google.com/policies/terms/",
    contact=openapi.Contact(email="earthlyz9.dev@gmail.com"),
)

SchemaView = get_schema_view(
    api_info,
    public=True,
    permission_classes=([permissions.AllowAny]),
    validators=["flex"],
    urlconf="config.api_urls_v1",
)


@api_view(["GET"])
def hello_world(request: Request) -> Response:
    return Response("Go to '/api/swagger' or '/api/redoc' for api documentation")


urlpatterns = [
    path("", hello_world),
    path("admin/", admin.site.urls),
    path("auth/", include("apps.user.auth_urls")),
    path("users/", include("apps.user.urls")),
    path("chat/", include("apps.chat.urls")),
    path("api-auth/", include("rest_framework.urls")),
]

urlpatterns += [
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)/$",
        SchemaView.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    re_path(
        r"^swagger/$",
        SchemaView.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    re_path(
        r"^redoc/$",
        SchemaView.with_ui("redoc", cache_timeout=0),
        name="schema-redoc-ui",
    ),
]
