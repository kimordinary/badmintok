from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # 홈
    path('', views.home, name='home'),

    # 게시물
    path('posts/', views.post_list, name='post_list'),
    path('posts/<str:slug>/', views.post_detail, name='post_detail'),
    path('hot-posts/', views.hot_posts, name='hot_posts'),

    # 배너
    path('banners/', views.banner_list, name='banner_list'),

    # 공지사항
    path('notices/', views.notice_list, name='notice_list'),
    path('notices/<int:notice_id>/', views.notice_detail, name='notice_detail'),
]
