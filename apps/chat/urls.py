from django.urls import path
from .views import ChatroomView, ChatroomDestroyView

urlpatterns = [
    path("<str:access_key>/chatrooms/", ChatroomView.as_view(), name="chatroom"),
    path(
        "<int:pk>/chatrooms/<str:guest_name>/",
        ChatroomDestroyView.as_view(),
        name="leave_chatroom",
    ),
]
