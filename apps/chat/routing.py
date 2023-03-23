from django.urls import re_path
from . import chat_consumer, status_consumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_name>[-\w]+)/$", chat_consumer.ChatConsumer.as_asgi()),
    re_path(
        r"ws/status/(?P<user_uuid>[-\w]+)/$",
        status_consumer.ActiveStatusConsumer.as_asgi(),
    ),
]
