from django.urls import path
from .views import UserDetailView, UserListView, ClientProfileView, UserConfigView

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("<int:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("<int:user_id>/configs/", UserConfigView.as_view(), name="user-config"),
    path("client/", ClientProfileView.as_view(), name="client-profile"),
]
