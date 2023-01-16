from django.urls import path
from .views import ChatroomView, ChatroomDestroyView, ChatroomExportView

urlpatterns = [
    path("<str:access_key>/chatrooms/", ChatroomView.as_view(), name="chatroom"),
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
