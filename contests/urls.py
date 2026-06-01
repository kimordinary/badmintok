from django.urls import path, register_converter
from django.views.generic.base import RedirectView

from .views import ContestDetailView, ContestListView, ContestArchiveView, ContestPreviewView, contest_like


class UnicodeSlugConverter:
    """한글을 포함한 유니코드 슬러그를 지원하는 컨버터"""
    regex = r'[-\w]+'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value


register_converter(UnicodeSlugConverter, 'unicode_slug')

app_name = "contests"

urlpatterns = [
    # 리디자인 승격: 목록 정식 URL은 새 디자인(ContestPreviewView)이 담당.
    # 기존 ContestListView는 롤백 대비로 코드만 보존(라우트 없음).
    path("", ContestPreviewView.as_view(), name="list"),
    # 구 미리보기 URL → 정식 URL로 영구 리다이렉트 (외부 공유 링크 대비)
    path("preview/", RedirectView.as_view(pattern_name="contests:list", permanent=True)),
    path("archive/", ContestArchiveView.as_view(), name="archive"),
    path("<unicode_slug:slug>/", ContestDetailView.as_view(), name="detail"),
    path("<unicode_slug:slug>/like/", contest_like, name="like"),
]
