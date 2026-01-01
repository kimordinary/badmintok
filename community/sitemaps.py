from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from .models import Post


class CommunityPostSitemap(Sitemap):
    """동호인톡 게시글 사이트맵"""
    changefreq = "daily"
    priority = 0.7
    
    def items(self):
        """공개된 동호인톡 게시글만 포함"""
        now = timezone.now()
        return Post.objects.filter(
            source=Post.Source.COMMUNITY,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')
    
    def location(self, obj):
        """게시글 상세 URL"""
        return reverse('community:detail', args=[obj.slug])
    
    def lastmod(self, obj):
        """마지막 수정일"""
        return obj.updated_at or obj.published_at or obj.created_at


class BadmintokPostSitemap(Sitemap):
    """배드민톡 게시글 사이트맵"""
    changefreq = "daily"
    priority = 0.8
    
    def items(self):
        """공개된 배드민톡 게시글만 포함"""
        now = timezone.now()
        return Post.objects.filter(
            source=Post.Source.BADMINTOK,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')
    
    def location(self, obj):
        """배드민톡 게시글 상세 URL"""
        return reverse('badmintok_detail', args=[obj.slug])
    
    def lastmod(self, obj):
        """마지막 수정일"""
        return obj.updated_at or obj.published_at or obj.created_at


class MemberReviewPostSitemap(Sitemap):
    """동호인 리뷰 게시글 사이트맵"""
    changefreq = "weekly"
    priority = 0.7
    
    def items(self):
        """공개된 동호인 리뷰 게시글만 포함"""
        now = timezone.now()
        return Post.objects.filter(
            source=Post.Source.MEMBER_REVIEWS,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')
    
    def location(self, obj):
        """동호인 리뷰 게시글 상세 URL"""
        return reverse('community:detail', args=[obj.slug])
    
    def lastmod(self, obj):
        """마지막 수정일"""
        return obj.updated_at or obj.published_at or obj.created_at


class CommunityListSitemap(Sitemap):
    """동호인톡 목록 페이지 사이트맵"""
    changefreq = "daily"
    priority = 0.6
    
    def items(self):
        """목록 페이지는 하나만"""
        return [True]
    
    def location(self, obj):
        """동호인톡 목록 URL"""
        return reverse('community:list')

