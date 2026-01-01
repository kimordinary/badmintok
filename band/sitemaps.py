from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Band, BandPost


class BandSitemap(Sitemap):
    """밴드(소모임) 사이트맵"""
    changefreq = "weekly"
    priority = 0.7
    
    def items(self):
        """공개되고 승인된 밴드만 포함"""
        return Band.objects.filter(
            is_public=True,
            is_approved=True,
            deletion_requested=False
        ).select_related('created_by').order_by('-created_at')
    
    def location(self, obj):
        """밴드 상세 URL"""
        return reverse('band:detail', args=[obj.id])
    
    def lastmod(self, obj):
        """마지막 수정일"""
        return obj.updated_at or obj.created_at


class BandPostSitemap(Sitemap):
    """밴드 게시글 사이트맵"""
    changefreq = "daily"
    priority = 0.6
    
    def items(self):
        """공개된 밴드의 게시글만 포함"""
        return BandPost.objects.filter(
            band__is_public=True,
            band__is_approved=True,
            band__deletion_requested=False
        ).select_related('band', 'author').order_by('-created_at')
    
    def location(self, obj):
        """밴드 게시글 상세 URL"""
        return reverse('band:post_detail', args=[obj.band_id, obj.id])
    
    def lastmod(self, obj):
        """마지막 수정일"""
        return obj.updated_at or obj.created_at


class BandListSitemap(Sitemap):
    """밴드 목록 페이지 사이트맵"""
    changefreq = "daily"
    priority = 0.6
    
    def items(self):
        """목록 페이지는 하나만"""
        return [True]
    
    def location(self, obj):
        """밴드 목록 URL"""
        return reverse('band:list')

