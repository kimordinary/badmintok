from django.urls import path
from . import views

app_name = 'band_api'

urlpatterns = [
    # 밴드 목록 및 상세
    path('', views.band_list, name='band_list'),
    path('<int:band_id>/', views.band_detail, name='band_detail'),
    path('<int:band_id>/bookmark/', views.band_bookmark, name='band_bookmark'),

    # 밴드 게시글
    path('<int:band_id>/posts/', views.band_post_list, name='band_post_list'),
    path('<int:band_id>/posts/<int:post_id>/', views.band_post_detail, name='band_post_detail'),

    # 밴드 일정
    path('<int:band_id>/schedules/', views.band_schedule_list, name='band_schedule_list'),
    path('<int:band_id>/schedules/<int:schedule_id>/', views.band_schedule_detail, name='band_schedule_detail'),

    # 인기 밴드
    path('hot/', views.hot_bands, name='hot_bands'),
]
