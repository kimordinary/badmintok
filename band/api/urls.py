from django.urls import path
from . import views
from . import match_views

app_name = 'band_api'

urlpatterns = [
    # 밴드 목록 및 상세
    path('', views.band_list, name='band_list'),
    path('hot/', views.hot_bands, name='hot_bands'),
    path('my-joined/', views.my_joined_bands, name='my_joined_bands'),
    path('my-created/', views.my_created_bands, name='my_created_bands'),
    path('my-bookmarks/', views.my_bookmarked_bands, name='my_bookmarked_bands'),
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
    path('<int:band_id>/posts/<int:post_id>/answer/', views.band_post_answer, name='band_post_answer'),

    # 댓글
    path('<int:band_id>/posts/<int:post_id>/comments/', views.band_comment_list, name='band_comment_list'),
    path('<int:band_id>/posts/<int:post_id>/comments/create/', views.band_comment_create, name='band_comment_create'),
    path('comments/<int:comment_id>/update/', views.band_comment_update, name='band_comment_update'),
    path('comments/<int:comment_id>/delete/', views.band_comment_delete, name='band_comment_delete'),
    path('comments/<int:comment_id>/like/', views.band_comment_like, name='band_comment_like'),

    # 투표
    path('<int:band_id>/votes/create/', views.band_vote_create, name='band_vote_create'),
    path('<int:band_id>/posts/<int:post_id>/vote/', views.band_vote_participate, name='band_vote_participate'),

    # 이미지 업로드
    path('images/upload/', views.image_upload, name='image_upload'),

    # 밴드 일정
    path('<int:band_id>/schedules/', views.band_schedule_list, name='band_schedule_list'),
    path('<int:band_id>/schedules/create/', views.band_schedule_create, name='band_schedule_create'),
    path('<int:band_id>/schedules/<int:schedule_id>/', views.band_schedule_detail, name='band_schedule_detail'),
    path('<int:band_id>/schedules/<int:schedule_id>/update/', views.band_schedule_update, name='band_schedule_update'),
    path('<int:band_id>/schedules/<int:schedule_id>/delete/', views.band_schedule_delete, name='band_schedule_delete'),
    path('<int:band_id>/schedules/<int:schedule_id>/apply/', views.band_schedule_apply, name='band_schedule_apply'),
    path('<int:band_id>/schedules/<int:schedule_id>/cancel/', views.band_schedule_cancel, name='band_schedule_cancel'),
    path('<int:band_id>/schedules/<int:schedule_id>/toggle-close/', views.band_schedule_toggle_close, name='band_schedule_toggle_close'),
    path('<int:band_id>/schedules/<int:schedule_id>/notices/', views.band_schedule_notice_send, name='band_schedule_notice_send'),
    path('<int:band_id>/schedules/<int:schedule_id>/applications/<int:application_id>/', views.band_schedule_application_detail, name='band_schedule_application_detail'),
    path('<int:band_id>/schedules/<int:schedule_id>/applications/<int:application_id>/approve/', views.band_schedule_application_approve, name='band_schedule_application_approve'),
    path('<int:band_id>/schedules/<int:schedule_id>/applications/<int:application_id>/reject/', views.band_schedule_application_reject, name='band_schedule_application_reject'),
    path('<int:band_id>/schedules/<int:schedule_id>/applications/<int:application_id>/promote/', views.band_schedule_application_promote, name='band_schedule_application_promote'),
    path('<int:band_id>/schedules/<int:schedule_id>/applications/<int:application_id>/kick/', views.band_schedule_application_kick, name='band_schedule_application_kick'),
    path('<int:band_id>/schedules/<int:schedule_id>/applications/<int:application_id>/demote/', views.band_schedule_application_demote, name='band_schedule_application_demote'),

    # 대진 (matchmaking)
    path('match/schedules/<int:schedule_id>/start/', match_views.start_session, name='match_start'),
    path('match/<int:session_id>/', match_views.session_state, name='match_state'),
    path('match/<int:session_id>/mode/', match_views.set_mode, name='match_set_mode'),
    path('match/<int:session_id>/preset/', match_views.set_preset, name='match_set_preset'),
    path('match/<int:session_id>/participants/<int:pid>/attendance/',
         match_views.set_attendance, name='match_attendance'),
    path('match/<int:session_id>/courts/<int:index>/fill/', match_views.fill_court, name='match_fill'),
    path('match/<int:session_id>/courts/<int:index>/end/', match_views.end_court, name='match_end_court'),
    path('match/<int:session_id>/courts/<int:index>/coach/', match_views.set_coach, name='match_set_coach'),
    # 코트 설정(추가/이름·제거) + 임시 인원 추가
    path('match/<int:session_id>/courts/', match_views.add_court, name='match_court_add'),
    path('match/<int:session_id>/courts/<int:index>/', match_views.court_detail, name='match_court_detail'),
    path('match/<int:session_id>/participants/', match_views.add_participant, name='match_participant_add'),
    path('match/<int:session_id>/participants/<int:pid>/', match_views.edit_participant, name='match_participant_edit'),
    path('match/<int:session_id>/participants/sync/', match_views.sync_participants, name='match_participant_sync'),
    path('match/<int:session_id>/matches/<int:match_id>/', match_views.edit_match, name='match_edit'),
    path('match/<int:session_id>/end/', match_views.end_session, name='match_end_session'),

    # 대진 — 참가자 본인용 (앱)
    path('match/schedules/<int:schedule_id>/me/', match_views.my_status_by_schedule, name='match_my_status_by_schedule'),
    path('match/<int:session_id>/me/', match_views.my_status, name='match_my_status'),
    path('match/<int:session_id>/me/checkin/', match_views.my_checkin, name='match_my_checkin'),

    # 대진 — 파트너 (신청·승인·쌍)
    path('match/<int:session_id>/partner-requests/', match_views.list_partner_requests, name='match_partner_requests'),
    path('match/<int:session_id>/partner-requests/create/', match_views.request_partner, name='match_partner_request_create'),
    path('match/<int:session_id>/partner-requests/<int:req_id>/approve/', match_views.approve_partner_request, name='match_partner_approve'),
    path('match/<int:session_id>/partner-requests/<int:req_id>/reject/', match_views.reject_partner_request, name='match_partner_reject'),
    path('match/<int:session_id>/pairs/', match_views.pairs, name='match_pairs'),
    path('match/<int:session_id>/pairs/<int:pair_id>/', match_views.delete_pair, name='match_pair_delete'),

    # 대진 — 예약 경기(이후 예정)
    path('match/<int:session_id>/reservations/', match_views.create_reservation, name='match_reservation_create'),
    path('match/<int:session_id>/reservations/<int:reservation_id>/', match_views.delete_reservation, name='match_reservation_delete'),
]
