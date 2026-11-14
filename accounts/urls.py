from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password, name='forgot-password'),
    path('password-reset-sent/', views.password_reset_sent, name='password-reset-sent'),
    path('reset-password/<uuid:reset_id>/', views.reset_password, name='reset-password'),
    path('api/login/', api_views.api_login, name='api-login'),
]