from django.urls import path
from . import views

app_name = 'contests_api'

urlpatterns = [
    # 대회 목록 및 상세
    path('', views.contest_list, name='contest_list'),

    # 대회 생성 (업로더 API)
    path('create/', views.contest_create, name='contest_create'),

    # 카테고리
    path('categories/', views.category_list, name='category_list'),

    # 인기 대회
    path('hot/', views.hot_contests, name='hot_contests'),

    # 대회 상세 및 좋아요 (반드시 마지막에 위치)
    # slug에 한글이 포함되므로 str 사용 (Django slug 컨버터는 ASCII만 매칭)
    path('<str:slug>/', views.contest_detail, name='contest_detail'),
    path('<str:slug>/update/', views.contest_update, name='contest_update'),
    path('<str:slug>/like/', views.contest_like, name='contest_like'),

    # 업로더 API — 대회 하위 리소스
    path('<str:slug>/images/', views.contest_image_upload, name='contest_image_upload'),
    path('<str:slug>/pdf/', views.contest_pdf_upload, name='contest_pdf_upload'),
    path('<str:slug>/schedules/', views.contest_schedule_create, name='contest_schedule_create'),
    path('<str:slug>/prizes/', views.contest_prize_create, name='contest_prize_create'),
]
