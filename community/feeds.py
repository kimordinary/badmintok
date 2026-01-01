from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
import re
from .models import Post


class CommunityPostFeed(Feed):
    """동호인톡 게시글 RSS 피드"""
    title = "배드민톡 - 동호인톡"
    link = "/community/"
    description = "배드민톡 동호인톡 최신 게시글"
    
    def items(self):
        """최신 게시글 20개"""
        now = timezone.now()
        return Post.objects.filter(
            source=Post.Source.COMMUNITY,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')[:20]
    
    def item_title(self, item):
        """게시글 제목"""
        return item.title
    
    def item_description(self, item):
        """게시글 내용 요약 (HTML 태그 제거)"""
        if item.content:
            # HTML 태그 제거
            text = strip_tags(item.content)
            # 줄바꿈 제거 및 공백 정리
            text = re.sub(r'\s+', ' ', text).strip()
            # 200자로 제한
            return text[:200] + '...' if len(text) > 200 else text
        return ""
    
    def item_link(self, item):
        """게시글 상세 URL"""
        return reverse('community:detail', args=[item.slug])
    
    def item_pubdate(self, item):
        """게시글 발행일"""
        return item.published_at or item.created_at
    
    def item_author_name(self, item):
        """작성자 이름"""
        return item.author.activity_name if item.author else ""


class BadmintokPostFeed(Feed):
    """배드민톡 게시글 RSS 피드"""
    title = "배드민톡 - 배드민톡"
    link = "/badmintok/"
    description = "배드민톡 최신 게시글 (뉴스, 리뷰, 피드)"
    
    def items(self):
        """최신 게시글 20개"""
        now = timezone.now()
        return Post.objects.filter(
            source=Post.Source.BADMINTOK,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')[:20]
    
    def item_title(self, item):
        """게시글 제목"""
        return item.title
    
    def item_description(self, item):
        """게시글 내용 요약 (HTML 태그 제거)"""
        if item.content:
            # HTML 태그 제거
            text = strip_tags(item.content)
            # 줄바꿈 제거 및 공백 정리
            text = re.sub(r'\s+', ' ', text).strip()
            # 200자로 제한
            return text[:200] + '...' if len(text) > 200 else text
        return ""
    
    def item_link(self, item):
        """게시글 상세 URL"""
        return reverse('badmintok_detail', args=[item.slug])
    
    def item_pubdate(self, item):
        """게시글 발행일"""
        return item.published_at or item.created_at
    
    def item_author_name(self, item):
        """작성자 이름"""
        return item.author.activity_name if item.author else ""


class MemberReviewPostFeed(Feed):
    """동호인 리뷰 게시글 RSS 피드"""
    title = "배드민톡 - 동호인 리뷰"
    link = "/community/"
    description = "배드민톡 동호인 리뷰 최신 게시글"
    
    def items(self):
        """최신 게시글 20개"""
        now = timezone.now()
        return Post.objects.filter(
            source=Post.Source.MEMBER_REVIEWS,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')[:20]
    
    def item_title(self, item):
        """게시글 제목"""
        return item.title
    
    def item_description(self, item):
        """게시글 내용 요약 (HTML 태그 제거)"""
        if item.content:
            # HTML 태그 제거
            text = strip_tags(item.content)
            # 줄바꿈 제거 및 공백 정리
            text = re.sub(r'\s+', ' ', text).strip()
            # 200자로 제한
            return text[:200] + '...' if len(text) > 200 else text
        return ""
    
    def item_link(self, item):
        """게시글 상세 URL"""
        return reverse('community:detail', args=[item.slug])
    
    def item_pubdate(self, item):
        """게시글 발행일"""
        return item.published_at or item.created_at
    
    def item_author_name(self, item):
        """작성자 이름"""
        return item.author.activity_name if item.author else ""

