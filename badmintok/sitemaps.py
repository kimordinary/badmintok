from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from .models import Notice
from community.sitemaps import (
    CommunityPostSitemap,
    BadmintokPostSitemap,
    MemberReviewPostSitemap,
    BadmintokCategorySitemap,
    CommunityCategorySitemap,
)
from band.sitemaps import (
    BandSitemap,
    BandPostSitemap,
)
from contests.sitemaps import (
    ContestSitemap,
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


# 각 섹션 허브 URL 매핑 (URL name → 메타)
_HUB_META = {
    'community:list': {'priority': 0.9, 'changefreq': 'daily'},
    'badmintok':      {'priority': 0.9, 'changefreq': 'daily'},
    'band:list':      {'priority': 0.9, 'changefreq': 'daily'},
    'contests:list':  {'priority': 0.9, 'changefreq': 'daily'},
}


class HubSitemap(Sitemap):
    """섹션 허브(목록) 페이지 통합 사이트맵.

    각 섹션 목록 페이지를 sub-sitemap 1개당 1 URL로 분리하는 건 무의미하므로
    한 개의 sitemap-hubs.xml 로 통합한다.
    """
    def items(self):
        return list(_HUB_META.keys())

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return _HUB_META[item]['priority']

    def changefreq(self, item):
        return _HUB_META[item]['changefreq']

    def lastmod(self, item):
        """해당 섹션 최신 콘텐츠의 updated_at."""
        from community.models import Post
        from band.models import Band
        from contests.models import Contest
        now = timezone.now()

        if item == 'community:list':
            qs = Post.objects.filter(source=Post.Source.COMMUNITY,
                                     is_deleted=False, is_draft=False, published_at__lte=now)
        elif item == 'badmintok':
            qs = Post.objects.filter(source=Post.Source.BADMINTOK,
                                     is_deleted=False, is_draft=False, published_at__lte=now)
        elif item == 'band:list':
            qs = Band.objects.filter(is_public=True, is_approved=True, deletion_requested=False)
        elif item == 'contests:list':
            qs = Contest.objects.all()
        else:
            return None
        obj = qs.order_by('-updated_at').first()
        return obj.updated_at if obj else None


# 사이트맵 딕셔너리
sitemaps = {
    # 정적/허브 페이지 (1 URL짜리는 묶음)
    'static':    StaticViewSitemap,           # /, /privacy/, /terms/, /notices/
    'hubs':      HubSitemap,                  # /community/, /badmintok/, /band/, /badminton-tournament/
    'notices':   NoticeSitemap,

    # 콘텐츠
    'community_posts':      CommunityPostSitemap,
    'badmintok_posts':      BadmintokPostSitemap,
    'member_reviews':       MemberReviewPostSitemap,
    'badmintok_categories': BadmintokCategorySitemap,
    'community_categories': CommunityCategorySitemap,
    'bands':                BandSitemap,
    'band_posts':           BandPostSitemap,
    'contests':             ContestSitemap,
}
