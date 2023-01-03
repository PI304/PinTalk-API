from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/chat/(?P<host_name>\w+)/(?P<guest_name>\w+)/$",
        consumers.ChatConsumer.as_asgi(),
    ),
]
