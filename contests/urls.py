from django.urls import path, register_converter

from .views import ContestDetailView, ContestListView, ContestArchiveView, contest_like


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
    path("", ContestListView.as_view(), name="list"),
    path("archive/", ContestArchiveView.as_view(), name="archive"),
    path("<unicode_slug:slug>/", ContestDetailView.as_view(), name="detail"),
    path("<unicode_slug:slug>/like/", contest_like, name="like"),
]
