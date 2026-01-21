from django.urls import path
from . import views

app_name = 'community_api'

urlpatterns = [
    # 게시물
    path('posts/create/', views.post_create, name='post_create'),
    path('posts/', views.post_list, name='post_list'),
    path('posts/<str:slug>/', views.post_detail, name='post_detail'),
    path('posts/<str:slug>/like/', views.post_like, name='post_like'),
    path('posts/<str:slug>/update/', views.post_update, name='post_update'),
    path('posts/<str:slug>/delete/', views.post_delete, name='post_delete'),
    
    # 댓글
    path('posts/<str:slug>/comments/', views.comment_list, name='comment_list'),
    path('posts/<str:slug>/comments/create/', views.comment_create, name='comment_create'),
    path('comments/<int:comment_id>/', views.comment_update, name='comment_update'),
    path('comments/<int:comment_id>/delete/', views.comment_delete, name='comment_delete'),
    path('comments/<int:comment_id>/like/', views.comment_like, name='comment_like'),
    
    # 이미지 업로드
    path('images/upload/', views.image_upload, name='image_upload'),
    
    # 카테고리
    path('categories/', views.category_list, name='category_list'),
]
