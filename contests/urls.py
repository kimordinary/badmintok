from django.urls import path

from .views import ContestDetailView, ContestListView, contest_like

app_name = "contests"

urlpatterns = [
    path("", ContestListView.as_view(), name="list"),
    path("<slug:slug>/", ContestDetailView.as_view(), name="detail"),
    path("<slug:slug>/like/", contest_like, name="like"),
]
