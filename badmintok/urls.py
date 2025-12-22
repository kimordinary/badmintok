"""
URL configuration for badmintok project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.shortcuts import redirect
from django.views.generic import TemplateView
from . import views
from community import admin_uploads
from accounts.views import privacy_policy, terms_of_service

urlpatterns = [
    # Admin에서 사용하는 에디터 이미지 업로드 엔드포인트 (admin 기본 URL보다 먼저 선언)
    path("admin/quill-upload/", admin_uploads.quill_image_upload, name="admin_quill_upload"),
    path("admin/editorjs-upload/", admin_uploads.editorjs_image_upload, name="admin_editorjs_upload"),
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("badminton-tournament/", include(("contests.urls", "contests"), namespace="contests")),
    path("badmintok/", views.badmintok, name="badmintok"),
    path("badmintok/create/", views.badmintok_create, name="badmintok_create"),
    path("badmintok/<str:slug>/", views.badmintok_detail, name="badmintok_detail"),
    # 기존 뉴스/리뷰 URL은 통합 페이지로 리다이렉트
    path("news/", views.news_redirect, name="news"),
    path("reviews/", views.reviews_redirect, name="reviews"),
    path("member-reviews/", lambda request: redirect("community:list"), name="member_reviews"),
    path("member-reviews/create/", lambda request: redirect("community:create"), name="member_reviews_create"),
    path("community/", include(("community.urls", "community"), namespace="community")),
    path("band/", include(("band.urls", "band"), namespace="band")),
    # path(
    #     "shop/",
    #     TemplateView.as_view(template_name="shop/index.html"),
    #     name="shop",
    # ),
    # SEO를 위한 상위 레벨 URL
    path("privacy/", privacy_policy, name="privacy"),
    path("terms/", terms_of_service, name="terms"),
    path("notices/", views.notice_list, name="notice_list"),
    path("notices/<int:notice_id>/", views.notice_detail, name="notice_detail"),
    path("accounts/", include("accounts.urls", namespace="accounts")),
]

if settings.DEBUG:
    # 미디어 파일 서빙
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # 정적 파일 서빙 (개발 환경)
    # STATICFILES_DIRS의 각 디렉토리를 직접 서빙
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    urlpatterns += staticfiles_urlpatterns()
    # STATICFILES_DIRS의 각 경로를 명시적으로 서빙
    for static_dir in settings.STATICFILES_DIRS:
        urlpatterns += static(settings.STATIC_URL, document_root=static_dir)
