from django.urls import path, include
from . import views

app_name = 'api'

# Badmintok API URLs
badmintok_patterns = [
    path('posts/', views.post_list, name='badmintok_post_list'),
    path('posts/<str:slug>/', views.post_detail, name='badmintok_post_detail'),
    path('hot-posts/', views.hot_posts, name='badmintok_hot_posts'),
]

urlpatterns = [
    # 통합 홈 (모든 최신 게시물)
    path('', views.home, name='home'),

    # Badmintok API
    path('badmintok/', include(badmintok_patterns)),

    # Community API (외부 앱)
    path('community/', include('community.api.urls', namespace='community_api')),

    # Contests API (외부 앱)
    path('contests/', include('contests.api.urls', namespace='contests_api')),

    # Bands API (외부 앱)
    path('bands/', include('band.api.urls', namespace='band_api')),

    # 공통 리소스
    path('banners/', views.banner_list, name='banner_list'),
    path('notices/', views.notice_list, name='notice_list'),
    path('notices/<int:notice_id>/', views.notice_detail, name='notice_detail'),
]
