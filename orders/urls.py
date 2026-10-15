from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("", views.history, name="history"),
    path("<str:order_number>/", views.detail, name="detail"),
    path("<str:order_number>/cancel/", views.cancel, name="cancel"),
    path("<int:pk>/confirmation/", views.confirmation, name="confirmation"),
]
