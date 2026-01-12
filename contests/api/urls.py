from django.urls import path
from . import views

app_name = 'contests_api'

urlpatterns = [
    # 대회
    path('contests/', views.contest_list, name='contest_list'),
    path('contests/<str:slug>/', views.contest_detail, name='contest_detail'),
    path('contests/<str:slug>/like/', views.contest_like, name='contest_like'),
    
    # 대회 분류
    path('categories/', views.category_list, name='category_list'),
    
    # 스폰서
    path('sponsors/', views.sponsor_list, name='sponsor_list'),
]
