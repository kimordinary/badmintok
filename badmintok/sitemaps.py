from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Notice
from community.sitemaps import (
    CommunityPostSitemap,
    BadmintokPostSitemap,
    MemberReviewPostSitemap,
    CommunityListSitemap
)
from band.sitemaps import (
    BandSitemap,
    BandPostSitemap,
    BandListSitemap
)
from contests.sitemaps import (
    ContestSitemap,
    ContestListSitemap
)


class StaticViewSitemap(Sitemap):
    """정적 페이지 사이트맵"""
    changefreq = "monthly"
    priority = 0.5
    
    def items(self):
        """정적 페이지 목록"""
        return [
            'home',
            'badmintok',
            'privacy',
            'terms',
            'notice_list',
        ]
    
    def location(self, item):
        """각 정적 페이지의 URL"""
        return reverse(item)


class NoticeSitemap(Sitemap):
    """공지사항 사이트맵"""
    changefreq = "weekly"
    priority = 0.6
    
    def items(self):
        """모든 공지사항 포함"""
        return Notice.objects.select_related('author').only(
            'id', 'updated_at', 'created_at'
        ).order_by('-created_at')
    
    def location(self, obj):
        """공지사항 상세 URL"""
        return reverse('notice_detail', args=[obj.id])
    
    def lastmod(self, obj):
        """마지막 수정일"""
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
    
    # Band 앱
    'bands': BandSitemap,
    'band_posts': BandPostSitemap,
    'band_list': BandListSitemap,
    
    # Contests 앱
    'contests': ContestSitemap,
    'contest_list': ContestListSitemap,
}
