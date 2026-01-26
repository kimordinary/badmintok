from django.urls import path
from . import views

app_name = 'contests_api'

urlpatterns = [
    # 대회 목록 및 상세
    path('', views.contest_list, name='contest_list'),

    # 카테고리
    path('categories/', views.category_list, name='category_list'),

    # 인기 대회
    path('hot/', views.hot_contests, name='hot_contests'),

    # 대회 상세 및 좋아요 (반드시 마지막에 위치)
    path('<slug:slug>/', views.contest_detail, name='contest_detail'),
    path('<slug:slug>/like/', views.contest_like, name='contest_like'),
]
