from django.urls import path
from .views import (
    ChatroomListView,
    ChatroomDetailView,
    ChatroomExportView,
    ChatroomClientCreateView,
    # ChatroomClientRetrieveView,
    ChatroomClientResumeView,
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
        name="leave-chatroom",
    ),
    # path(
    #     "chatrooms/<int:pk>/",
    #     ChatroomResumeView.as_view(),
    #     name="leave-chatroom",
    # ),
    path(
        "chatrooms/<int:pk>/download",
        ChatroomExportView.as_view(),
        name="export-chatroom-messages",
    ),
]
