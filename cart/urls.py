from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.detail, name="detail"),
    path("add/<slug:slug>/", views.add, name="add"),
    path("update/<slug:slug>/", views.update, name="update"),
    path("remove/<slug:slug>/", views.remove, name="remove"),
]
