from django.urls import path
from . import views

app_name = "notifications_api"

urlpatterns = [
    path("", views.notification_list, name="notification_list"),
    path("<int:notification_id>/read/", views.notification_read, name="notification_read"),
    path("read-all/", views.notification_read_all, name="notification_read_all"),
    path("unread-count/", views.notification_unread_count, name="notification_unread_count"),
]
