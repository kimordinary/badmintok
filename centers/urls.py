from django.urls import path

from . import views

app_name = "center"

urlpatterns = [
    path("", views.center_list, name="list"),
    path("create/", views.center_create, name="create"),
    path("<int:center_id>/", views.center_detail, name="detail"),
    path("<int:center_id>/update/", views.center_update, name="update"),
    path("<int:center_id>/delete/", views.center_delete, name="delete"),
    path("<int:center_id>/bookmark/", views.center_bookmark_toggle, name="bookmark_toggle"),
]
