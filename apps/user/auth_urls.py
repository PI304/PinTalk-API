from django.urls import path
from . import auth_views

urlpatterns = [
    path("signup/", auth_views.BasicSignUpView.as_view(), name="basic-signup"),
    path("login/", auth_views.BasicSignInView.as_view(), name="basic-login"),
    path("logout/", auth_views.BasicSignOutView.as_view(), name="basic-logout"),
    path("leave/", auth_views.SecessionView.as_view(), name="basic-leave"),
    path("restore/", auth_views.RestoreView.as_view(), name="basic-restore"),
]
urlpatterns += [
    path("token/refresh/", auth_views.TokenRefreshView.as_view(), name="token-refresh"),
]

urlpatterns += [
    path(
        "check-email/",
        auth_views.CheckDuplicateUsernameView.as_view(),
        name="check-email",
    ),
    path(
        "email-verification/",
        auth_views.EmailVerification.as_view(),
        name="verify-email",
    ),
    path(
        "email-confirmation/", auth_views.EmailConfirmation.as_view(), name="activate"
    ),
    path(
        "password-change/",
        auth_views.PasswordChangeView.as_view(),
        name="password-change",
    ),
    path(
        "password-reset/", auth_views.PasswordResetView.as_view(), name="password-reset"
    ),
]
