from django.urls import path, include
from django.views.generic import RedirectView

from .html_views import chatroom_view

urlpatterns = [
    path("", chatroom_view),
]
