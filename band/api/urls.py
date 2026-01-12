from django.urls import path
from . import views

app_name = 'band_api'

urlpatterns = [
    # 밴드
    path('bands/', views.band_list, name='band_list'),
    path('bands/<int:band_id>/', views.band_detail, name='band_detail'),
    path('bands/create/', views.band_create, name='band_create'),
    path('bands/<int:band_id>/update/', views.band_update, name='band_update'),
    path('bands/<int:band_id>/join/', views.band_join, name='band_join'),
    path('bands/<int:band_id>/leave/', views.band_leave, name='band_leave'),
    path('bands/<int:band_id>/members/', views.band_members, name='band_members'),
    
    # 밴드 게시글
    path('bands/<int:band_id>/posts/', views.band_post_list, name='band_post_list'),
    path('bands/<int:band_id>/posts/<int:post_id>/', views.band_post_detail, name='band_post_detail'),
    path('bands/<int:band_id>/posts/create/', views.band_post_create, name='band_post_create'),
    path('bands/<int:band_id>/posts/<int:post_id>/update/', views.band_post_update, name='band_post_update'),
    path('bands/<int:band_id>/posts/<int:post_id>/delete/', views.band_post_delete, name='band_post_delete'),
    path('bands/<int:band_id>/posts/<int:post_id>/like/', views.band_post_like, name='band_post_like'),
    
    # 밴드 댓글
    path('bands/<int:band_id>/posts/<int:post_id>/comments/', views.band_comment_list, name='band_comment_list'),
    path('bands/<int:band_id>/posts/<int:post_id>/comments/create/', views.band_comment_create, name='band_comment_create'),
    path('comments/<int:comment_id>/', views.band_comment_update, name='band_comment_update'),
    path('comments/<int:comment_id>/delete/', views.band_comment_delete, name='band_comment_delete'),
    path('comments/<int:comment_id>/like/', views.band_comment_like, name='band_comment_like'),
]
