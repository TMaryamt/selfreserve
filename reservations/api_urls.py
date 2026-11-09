from django.urls import path

from . import api_views

urlpatterns = [
    path("profile/", api_views.SelfProfileView.as_view()),
    path("menu/", api_views.MenuView.as_view()),
    path("foods/", api_views.FoodsView.as_view()),
    path("preferences/", api_views.PreferencesView.as_view()),
    path("reservations/", api_views.ReservationsView.as_view()),
    path("reserve/", api_views.ReserveView.as_view()),
    path("cancel/", api_views.CancelView.as_view()),
]