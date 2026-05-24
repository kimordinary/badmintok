from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from .models import Notice
from community.sitemaps import (
    CommunityPostSitemap,
    BadmintokPostSitemap,
    MemberReviewPostSitemap,
    CommunityListSitemap,
    BadmintokListSitemap,
    BadmintokCategorySitemap,
    CommunityCategorySitemap,
)
from band.sitemaps import (
    BandSitemap,
    BandPostSitemap,
    BandListSitemap,
)
from contests.sitemaps import (
    ContestSitemap,
    ContestListSitemap,
)


# 페이지별 메타 (priority, changefreq) — 페이지 특성에 맞게 분기
_STATIC_META = {
    'home':        {'priority': 1.0, 'changefreq': 'daily'},
    'privacy':     {'priority': 0.3, 'changefreq': 'yearly'},
    'terms':       {'priority': 0.3, 'changefreq': 'yearly'},
    'notice_list': {'priority': 0.5, 'changefreq': 'weekly'},
}


class StaticViewSitemap(Sitemap):
    """정적 페이지 사이트맵.

    페이지별 priority/changefreq를 다르게 적용하고 lastmod도 매 빌드 시점으로 채움.
    """
    def items(self):
        return list(_STATIC_META.keys())

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return _STATIC_META[item]['priority']

    def changefreq(self, item):
        return _STATIC_META[item]['changefreq']

    def lastmod(self, item):
        # 정적 페이지(약관/개인정보)는 거의 안 바뀌지만 lastmod 자체가 없으면
        # 구글이 신선도 판단을 못 함 — 매 빌드 시점 KST 자정으로 채움
        return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


class NoticeSitemap(Sitemap):
    """공지사항 사이트맵"""
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Notice.objects.order_by('-created_at')

    def location(self, obj):
        return reverse('notice_detail', args=[obj.id])

    def lastmod(self, obj):
        return obj.updated_at or obj.created_at


# 사이트맵 딕셔너리 - 모든 사이트맵을 통합
sitemaps = {
    # 정적 페이지
    'static': StaticViewSitemap,
    'notices': NoticeSitemap,

    # Community 앱
    'community_posts': CommunityPostSitemap,
    'badmintok_posts': BadmintokPostSitemap,
    'member_reviews': MemberReviewPostSitemap,
    'community_list': CommunityListSitemap,
    'badmintok_list': BadmintokListSitemap,
    'badmintok_categories': BadmintokCategorySitemap,    # 신규: 배드민톡 메인 4 카테고리
    'community_categories': CommunityCategorySitemap,    # 신규: 동호인톡 메인 3 카테고리

    # Band 앱
    'bands': BandSitemap,
    'band_posts': BandPostSitemap,
    'band_list': BandListSitemap,

    # Contests 앱
    'contests': ContestSitemap,
    'contest_list': ContestListSitemap,
}
