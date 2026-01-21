from django.urls import path
from . import views

app_name = "band"

urlpatterns = [
    # 밴드 목록 및 생성
    path("", views.band_list, name="list"),
    path("create/", views.band_create, name="create"),
    
    # 밴드 상세 및 관리
    path("<int:band_id>/", views.band_detail, name="detail"),
    path("<int:band_id>/update/", views.band_update, name="update"),
    path("<int:band_id>/join/", views.band_join, name="join"),
    path("<int:band_id>/leave/", views.band_leave, name="leave"),
    path("<int:band_id>/bookmark/", views.band_bookmark_toggle, name="bookmark_toggle"),
    path("<int:band_id>/delete-request/", views.band_delete_request, name="delete_request"),
    path("<int:band_id>/member-management/", views.member_management, name="member_management"),
    path("<int:band_id>/members/<int:member_id>/approve/", views.member_approve, name="member_approve"),
    path("<int:band_id>/members/<int:member_id>/reject/", views.member_reject, name="member_reject"),
    path("<int:band_id>/members/<int:member_id>/kick/", views.member_kick, name="member_kick"),
    
    # 게시글
    path("<int:band_id>/posts/create/", views.post_create, name="post_create"),
    path("<int:band_id>/posts/image-upload/", views.post_image_upload, name="post_image_upload"),
    path("<int:band_id>/posts/<int:post_id>/", views.post_detail, name="post_detail"),
    path("<int:band_id>/posts/<int:post_id>/update/", views.post_update, name="post_update"),
    path("<int:band_id>/posts/<int:post_id>/delete/", views.post_delete, name="post_delete"),
    path("<int:band_id>/posts/<int:post_id>/like/", views.post_like, name="post_like"),
    
    # 댓글
    path("<int:band_id>/posts/<int:post_id>/comments/create/", views.comment_create, name="comment_create"),
    path("<int:band_id>/posts/<int:post_id>/comments/<int:comment_id>/update/", views.comment_update, name="comment_update"),
    path("<int:band_id>/posts/<int:post_id>/comments/<int:comment_id>/delete/", views.comment_delete, name="comment_delete"),
    
    # 투표
    path("<int:band_id>/votes/create/", views.vote_create, name="vote_create"),
    path("<int:band_id>/posts/<int:post_id>/vote/", views.vote_participate, name="vote_participate"),
    
    # 일정
    path("<int:band_id>/schedules/create/", views.schedule_create, name="schedule_create"),
    path("<int:band_id>/schedules/<int:schedule_id>/update/", views.schedule_update, name="schedule_update"),
    path("<int:band_id>/schedules/<int:schedule_id>/delete/", views.schedule_delete, name="schedule_delete"),
    path("<int:band_id>/schedules/<int:schedule_id>/", views.schedule_detail, name="schedule_detail"),
    path("<int:band_id>/schedules/<int:schedule_id>/apply/", views.schedule_apply, name="schedule_apply"),
    path("<int:band_id>/schedules/<int:schedule_id>/cancel/", views.schedule_application_cancel, name="schedule_application_cancel"),
    path("<int:band_id>/schedules/<int:schedule_id>/applications/<int:application_id>/approve/",
         views.schedule_application_approve, name="schedule_application_approve"),
    path("<int:band_id>/schedules/<int:schedule_id>/applications/<int:application_id>/reject/",
         views.schedule_application_reject, name="schedule_application_reject"),
    path("<int:band_id>/schedules/<int:schedule_id>/toggle-close/",
         views.schedule_toggle_close, name="schedule_toggle_close"),
]

