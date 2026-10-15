from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("checkout/<str:order_number>/", views.checkout, name="checkout"),
    path("verify/<str:order_number>/", views.verify, name="verify"),
    path("failed/<str:order_number>/", views.failed, name="failed"),
    path("webhook/", views.webhook, name="webhook"),
]
