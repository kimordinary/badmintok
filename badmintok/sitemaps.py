from datetime import datetime

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from .models import Notice
from community.sitemaps import (
    CommunityPostSitemap,
    BadmintokPostSitemap,
    MemberReviewPostSitemap,
    BadmintokTagSitemap,
)
from band.sitemaps import (
    BandSitemap,
    BandPostSitemap,
)
from contests.sitemaps import (
    ContestSitemap,
)


# 정적 페이지별 메타 (priority, changefreq, lastmod)
# lastmod는 페이지별 실제 의미가 있는 날짜를 고정값으로 박음
# (오늘 날짜로 매번 갱신하면 구글이 거짓 신선도로 판단해 신뢰도 하락)
# 약관/개인정보 마지막 개정일 (KST aware datetime, 자정 기준)
_PRIVACY_TERMS_LASTMOD = timezone.make_aware(datetime(2026, 1, 10, 0, 0, 0))

_STATIC_META = {
    'home':        {'priority': 1.0, 'changefreq': 'daily',   'lastmod': None},   # 동적 — 아래에서 계산
    'privacy':     {'priority': 0.3, 'changefreq': 'yearly',  'lastmod': _PRIVACY_TERMS_LASTMOD},
    'terms':       {'priority': 0.3, 'changefreq': 'yearly',  'lastmod': _PRIVACY_TERMS_LASTMOD},
    'notice_list': {'priority': 0.5, 'changefreq': 'weekly',  'lastmod': None},   # 동적 — 아래
}


class StaticViewSitemap(Sitemap):
    """정적 페이지 사이트맵.

    페이지별 priority/changefreq/lastmod를 다르게 적용.
    - 약관/개인정보: 실제 개정일 고정값
    - 홈/공지 목록: 해당 영역 최신 콘텐츠의 updated_at
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
        meta = _STATIC_META[item]
        if meta['lastmod'] is not None:
            return meta['lastmod']
        # 동적 페이지: 해당 영역 최신 콘텐츠 updated_at
        if item == 'home':
            from community.models import Post
            now = timezone.now()
            p = Post.objects.filter(
                is_deleted=False, is_draft=False, published_at__lte=now,
            ).order_by('-updated_at').first()
            return p.updated_at if p else None
        if item == 'notice_list':
            n = Notice.objects.order_by('-updated_at').first()
            return n.updated_at if n else None
        return None


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

    # 콘텐츠 (?tab=·?category= 같은 쿼리스트링 URL은 의도적으로 제외)
    'community_posts':      CommunityPostSitemap,
    'badmintok_posts':      BadmintokPostSitemap,
    'badmintok_tags':       BadmintokTagSitemap,
    'member_reviews':       MemberReviewPostSitemap,
    'bands':                BandSitemap,
    'band_posts':           BandPostSitemap,
    'contests':             ContestSitemap,
}
