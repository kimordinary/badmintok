from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Contest


class ContestSitemap(Sitemap):
    """대회 사이트맵"""
    changefreq = "weekly"
    priority = 0.8
    
    def items(self):
        """모든 대회 포함"""
        return Contest.objects.select_related('category', 'sponsor').order_by('-created_at')
    
    def location(self, obj):
        """대회 상세 URL"""
        return reverse('contests:detail', args=[obj.slug])
    
    def lastmod(self, obj):
        """마지막 수정일"""
        return obj.updated_at or obj.created_at


class ContestListSitemap(Sitemap):
    """대회 목록 페이지 사이트맵"""
    changefreq = "daily"
    priority = 0.7
    
    def items(self):
        """목록 페이지는 하나만"""
        return [True]
    
    def location(self, obj):
        """대회 목록 URL"""
        return reverse('contests:list')

