from django.urls import path
from . import views

app_name = 'badmintok_api'

urlpatterns = [
    path('home/', views.home, name='home'),
    path('posts/', views.post_list, name='post_list'),
    path('posts/hot/', views.hot_posts, name='hot_posts'),
    path('posts/<str:slug>/', views.post_detail, name='post_detail'),
    path('banners/', views.banner_list, name='banner_list'),
    path('notices/', views.notice_list, name='notice_list'),
    path('notices/<int:notice_id>/', views.notice_detail, name='notice_detail'),
]

