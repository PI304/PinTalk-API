from django.urls import path
from .views import ChatroomCreateView

urlpatterns = [
    path("chatroom/", ChatroomCreateView.as_view(), name="chatroom"),
]
