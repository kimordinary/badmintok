from django.urls import path
from . import views

app_name = "community"

urlpatterns = [
    path("", views.PostListView.as_view(), name="list"),
    path("create/", views.PostCreateView.as_view(), name="create"),
    path("upload-image/", views.upload_image_for_editorjs, name="upload_image"),
    # 워드프레스 스타일 배드민톡 에디터
    path("badmintok/editor/", views.badmintok_post_editor, name="badmintok_editor"),
    path("badmintok/editor/<int:post_id>/", views.badmintok_post_editor, name="badmintok_editor_update"),
    path("badmintok/image-upload/", views.badmintok_post_image_upload, name="badmintok_image_upload"),
    # 커뮤니티 게시글 이미지 업로드 (일반 사용자용)
    path("post-image-upload/", views.community_image_upload, name="community_image_upload"),
    # 댓글 관련 URL
    path("comment/<int:comment_id>/like/", views.CommentLikeView.as_view(), name="comment_like"),
    path("comment/<int:comment_id>/delete/", views.CommentDeleteView.as_view(), name="comment_delete"),
    # 슬러그 기반 URL (한글 지원) - 맨 아래에 배치
    path("<str:slug>/", views.PostDetailView.as_view(), name="detail"),
    path("<str:slug>/update/", views.PostUpdateView.as_view(), name="update"),
    path("<str:slug>/delete/", views.PostDeleteView.as_view(), name="delete"),
    path("<str:slug>/like/", views.PostLikeView.as_view(), name="like"),
    path("<str:slug>/comment/create/", views.CommentCreateView.as_view(), name="comment_create"),
]

