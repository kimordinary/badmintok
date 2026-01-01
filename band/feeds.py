from django.contrib.syndication.views import Feed
from django.urls import reverse
from .models import Band, BandPost


class BandFeed(Feed):
    """밴드(소모임) RSS 피드"""
    title = "배드민톡 - 소모임"
    link = "/band/"
    description = "배드민톡 소모임 최신 정보"
    
    def items(self):
        """최신 밴드 20개"""
        return Band.objects.filter(
            is_public=True,
            is_approved=True,
            deletion_requested=False
        ).select_related('created_by').order_by('-created_at')[:20]
    
    def item_title(self, item):
        """밴드 이름"""
        return item.name
    
    def item_description(self, item):
        """밴드 설명"""
        if item.detailed_description:
            return item.detailed_description[:200] + '...' if len(item.detailed_description) > 200 else item.detailed_description
        return item.description or ""
    
    def item_link(self, item):
        """밴드 상세 URL"""
        return reverse('band:detail', args=[item.id])
    
    def item_pubdate(self, item):
        """밴드 생성일"""
        return item.created_at
    
    def item_author_name(self, item):
        """밴드 생성자"""
        return item.created_by.activity_name if item.created_by else ""


class BandPostFeed(Feed):
    """밴드 게시글 RSS 피드"""
    title = "배드민톡 - 소모임 게시글"
    link = "/band/"
    description = "배드민톡 소모임 최신 게시글"
    
    def items(self):
        """최신 밴드 게시글 20개"""
        return BandPost.objects.filter(
            band__is_public=True,
            band__is_approved=True,
            band__deletion_requested=False
        ).select_related('band', 'author').order_by('-created_at')[:20]
    
    def item_title(self, item):
        """게시글 제목"""
        return item.title or item.content[:50] + '...' if item.content else ""
    
    def item_description(self, item):
        """게시글 내용"""
        if item.content:
            return item.content[:200] + '...' if len(item.content) > 200 else item.content
        return ""
    
    def item_link(self, item):
        """게시글 상세 URL"""
        return reverse('band:post_detail', args=[item.band_id, item.id])
    
    def item_pubdate(self, item):
        """게시글 작성일"""
        return item.created_at
    
    def item_author_name(self, item):
        """작성자 이름"""
        return item.author.activity_name if item.author else ""

