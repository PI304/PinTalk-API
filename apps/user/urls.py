from django.urls import path
from .views import UserDetailView, UserListView, ClientProfileView

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("client/", ClientProfileView.as_view(), name="client-profile"),
]
