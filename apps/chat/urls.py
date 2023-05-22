from django.urls import path
from apps.chat import views

urlpatterns = [
    path("", views.ChatroomClientCreateView.as_view(), name="create-chatroom"),
    path("chatrooms/", views.ChatroomListView.as_view(), name="chatroom-list"),
    path(
        "chatrooms/<int:pk>/chat-messages/",
        views.ChatroomMessageView.as_view(),
        name="chatroom-messages",
    ),
    path(
        "chatrooms/<int:pk>/",
        views.ChatroomDetailView.as_view(),
        name="chatroom-detail",
    ),
    path(
        "chatrooms/<int:pk>/download/",
        views.ChatroomExportView.as_view(),
        name="export-chatroom-messages",
    ),
    path(
        "chatrooms/<int:pk>/restore/",
        views.ChatroomRestoreView.as_view(),
        name="restore-chatroom",
    ),
]
