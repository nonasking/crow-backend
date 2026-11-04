from django.urls import path

from .views.login_view import LoginView
from .views.logout_view import LogoutView
from .views.me_view import MeView
from .views.refresh_view import RefreshView

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
]
