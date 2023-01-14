from django.urls import path
from .views import UserDetailView, UserListView, ClientView

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("client/", ClientView.as_view(), name="client"),
]
