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
from django.contrib.sitemaps.views import sitemap
from django.contrib.syndication.views import Feed
from django.urls import include, path
from django.shortcuts import redirect
from django.views.generic import TemplateView
from . import views
from .sitemaps import sitemaps
from community import admin_uploads
from community.feeds import CommunityPostFeed, BadmintokPostFeed, MemberReviewPostFeed
from band.feeds import BandFeed, BandPostFeed
from contests.feeds import ContestFeed
from .feeds import AllPostsFeed
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
    # 외부 링크 클릭 추적 API
    path("api/track-click/", views.track_outbound_click, name="track_outbound_click"),
    # SEO 관련
    path("robots.txt", views.robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    # RSS 피드
    path("rss", AllPostsFeed(), name="rss_all"),  # 통합 RSS 피드
    path("rss/community/", CommunityPostFeed(), name="rss_community"),
    path("rss/badmintok/", BadmintokPostFeed(), name="rss_badmintok"),
    path("rss/member-reviews/", MemberReviewPostFeed(), name="rss_member_reviews"),
    path("rss/band/", BandFeed(), name="rss_band"),
    path("rss/band-posts/", BandPostFeed(), name="rss_band_posts"),
    path("rss/contests/", ContestFeed(), name="rss_contests"),
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
