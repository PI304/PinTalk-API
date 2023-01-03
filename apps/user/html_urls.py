from django.urls import path, include
from django.views.generic import RedirectView

from .html_views import home_view, profile_view

urlpatterns = [
    path("", RedirectView.as_view(url="/account/login/")),
    path("account/", include("allauth.urls")),
    path("home/", home_view, name="home"),
    path("profile/", profile_view, name="profile"),
]