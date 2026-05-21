from django.urls import path

from . import views

app_name = "centers_api"

urlpatterns = [
    path("", views.center_list, name="center_list"),
    path("create/", views.center_create, name="center_create"),
    path("<int:center_id>/", views.center_detail, name="center_detail"),
    path("<int:center_id>/bookmark/", views.center_bookmark_toggle, name="center_bookmark_toggle"),
]
