from django.urls import path
from .views import (
    ChatroomListView,
    ChatroomDestroyView,
    ChatroomExportView,
    ChatroomClientCreateView,
    ChatroomClientRetrieveView,
)

urlpatterns = [
    path("client/", ChatroomClientCreateView.as_view(), name="create-chatroom"),
    path(
        "client/<str:guest>",
        ChatroomClientRetrieveView.as_view(),
        name="create-chatroom",
    ),
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
