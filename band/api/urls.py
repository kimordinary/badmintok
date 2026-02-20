from django.urls import path
from . import views

app_name = 'band_api'

urlpatterns = [
    # 밴드 목록 및 상세
    path('', views.band_list, name='band_list'),
    path('hot/', views.hot_bands, name='hot_bands'),
    path('create/', views.band_create, name='band_create'),
    path('<int:band_id>/', views.band_detail, name='band_detail'),
    path('<int:band_id>/update/', views.band_update, name='band_update'),
    path('<int:band_id>/bookmark/', views.band_bookmark, name='band_bookmark'),
    path('<int:band_id>/join/', views.band_join, name='band_join'),
    path('<int:band_id>/leave/', views.band_leave, name='band_leave'),

    # 멤버 관리
    path('<int:band_id>/members/', views.band_member_list, name='band_member_list'),
    path('<int:band_id>/members/<int:member_id>/approve/', views.band_member_approve, name='band_member_approve'),
    path('<int:band_id>/members/<int:member_id>/reject/', views.band_member_reject, name='band_member_reject'),
    path('<int:band_id>/members/<int:member_id>/kick/', views.band_member_kick, name='band_member_kick'),

    # 밴드 게시글
    path('<int:band_id>/posts/', views.band_post_list, name='band_post_list'),
    path('<int:band_id>/posts/create/', views.band_post_create, name='band_post_create'),
    path('<int:band_id>/posts/<int:post_id>/', views.band_post_detail, name='band_post_detail'),
    path('<int:band_id>/posts/<int:post_id>/update/', views.band_post_update, name='band_post_update'),
    path('<int:band_id>/posts/<int:post_id>/delete/', views.band_post_delete, name='band_post_delete'),
    path('<int:band_id>/posts/<int:post_id>/like/', views.band_post_like, name='band_post_like'),

    # 댓글
    path('<int:band_id>/posts/<int:post_id>/comments/', views.band_comment_list, name='band_comment_list'),
    path('<int:band_id>/posts/<int:post_id>/comments/create/', views.band_comment_create, name='band_comment_create'),
    path('comments/<int:comment_id>/update/', views.band_comment_update, name='band_comment_update'),
    path('comments/<int:comment_id>/delete/', views.band_comment_delete, name='band_comment_delete'),

    # 투표
    path('<int:band_id>/votes/create/', views.band_vote_create, name='band_vote_create'),
    path('<int:band_id>/posts/<int:post_id>/vote/', views.band_vote_participate, name='band_vote_participate'),

    # 밴드 일정
    path('<int:band_id>/schedules/', views.band_schedule_list, name='band_schedule_list'),
    path('<int:band_id>/schedules/create/', views.band_schedule_create, name='band_schedule_create'),
    path('<int:band_id>/schedules/<int:schedule_id>/', views.band_schedule_detail, name='band_schedule_detail'),
    path('<int:band_id>/schedules/<int:schedule_id>/apply/', views.band_schedule_apply, name='band_schedule_apply'),
    path('<int:band_id>/schedules/<int:schedule_id>/cancel/', views.band_schedule_cancel, name='band_schedule_cancel'),
    path('<int:band_id>/schedules/<int:schedule_id>/toggle-close/', views.band_schedule_toggle_close, name='band_schedule_toggle_close'),
]
