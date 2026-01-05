from django.urls import path
from . import views

app_name = 'accounts_api'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('refresh/', views.refresh_token, name='refresh'),
    path('user/', views.user_info, name='user_info'),
    path('kakao/', views.kakao_login, name='kakao_login'),
]

