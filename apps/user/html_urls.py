from django.urls import path, include
from .html_views import home_view, profile_view

urlpatterns = [
    path("", include("allauth.urls")),
    path("home", home_view, name="home"),
    path("profile", profile_view, name="profile"),
]