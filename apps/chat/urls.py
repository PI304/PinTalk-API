from django.urls import path
from .views import ChatroomView

urlpatterns = [
    path("<int:pk>/chatrooms/", ChatroomView.as_view(), name="chatroom"),
]
