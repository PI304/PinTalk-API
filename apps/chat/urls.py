from django.urls import path
from .views import (
    ChatroomListView,
    ChatroomDetailView,
    ChatroomExportView,
    ChatroomClientCreateView,
    ChatroomMessageView,
)

urlpatterns = [
    path("", ChatroomClientCreateView.as_view(), name="create-chatroom"),
    path("chatrooms/", ChatroomListView.as_view(), name="chatroom-list"),
    path(
        "chatrooms/<int:pk>/chat-messages/",
        ChatroomMessageView.as_view(),
        name="chatroom-messages",
    ),
    path(
        "chatrooms/<int:pk>/",
        ChatroomDetailView.as_view(),
        name="chatroom-detail",
    ),
    path(
        "chatrooms/<int:pk>/download/",
        ChatroomExportView.as_view(),
        name="export-chatroom-messages",
    ),
]
