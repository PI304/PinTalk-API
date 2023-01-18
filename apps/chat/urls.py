from django.urls import path
from .views import (
    ChatroomListView,
    ChatroomDestroyView,
    ChatroomExportView,
    ChatroomCreateView,
)

urlpatterns = [
    path("client/", ChatroomCreateView.as_view(), name="chatroom-list"),
    path(
        "<str:access_key>/chatrooms/", ChatroomListView.as_view(), name="chatroom-list"
    ),
    path(
        "chatrooms/<str:room_name>/",
        ChatroomDestroyView.as_view(),
        name="leave-chatroom",
    ),
    path(
        "chatrooms/<str:room_name>/export",
        ChatroomExportView.as_view(),
        name="export-chatroom-messages",
    ),
]
