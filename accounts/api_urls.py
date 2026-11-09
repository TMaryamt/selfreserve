from django.urls import path

from . import api_views

urlpatterns = [
    path("register/", api_views.RegisterView.as_view()),
    path("login/", api_views.LoginView.as_view()),
    path("logout/", api_views.LogoutView.as_view()),
    path("me/", api_views.MeView.as_view()),
    path("forgot-password/", api_views.ForgotPasswordView.as_view()),
    path("reset-password/", api_views.ResetPasswordView.as_view()),
]