from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
import re
from community.models import Post
from band.models import Band, BandPost
from contests.models import Contest


class AllPostsFeed(Feed):
    """모든 게시글을 통합한 RSS 피드"""
    title = "배드민톡 - 전체 피드"
    link = "/"
    description = "배드민톡의 모든 콘텐츠를 한눈에 - 동호인톡, 배드민톡, 동호인 리뷰, 소모임, 대회 정보"
    
    def items(self):
        """모든 게시글을 최신순으로 통합"""
        now = timezone.now()
        
        # 동호인톡 게시글
        community_posts = Post.objects.filter(
            source=Post.Source.COMMUNITY,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')[:10]
        
        # 배드민톡 게시글
        badmintok_posts = Post.objects.filter(
            source=Post.Source.BADMINTOK,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')[:10]
        
        # 동호인 리뷰
        member_reviews = Post.objects.filter(
            source=Post.Source.MEMBER_REVIEWS,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')[:10]
        
        # 밴드 게시글
        band_posts = BandPost.objects.filter(
            band__is_public=True,
            band__is_approved=True,
            band__deletion_requested=False
        ).select_related('band', 'author').order_by('-created_at')[:10]
        
        # 대회 정보
        contests = Contest.objects.select_related('category', 'sponsor').order_by('-created_at')[:10]
        
        # 모든 아이템을 하나의 리스트로 합치기
        all_items = []
        
        # 각 아이템에 타입 정보 추가
        for post in community_posts:
            post.item_type = 'community'
            all_items.append(post)
        
        for post in badmintok_posts:
            post.item_type = 'badmintok'
            all_items.append(post)
        
        for post in member_reviews:
            post.item_type = 'member_review'
            all_items.append(post)
        
        for post in band_posts:
            post.item_type = 'band_post'
            all_items.append(post)
        
        for contest in contests:
            contest.item_type = 'contest'
            all_items.append(contest)
        
        # 최신순으로 정렬 (created_at 기준)
        all_items.sort(key=lambda x: x.created_at, reverse=True)
        
        # 최신 30개만 반환
        return all_items[:30]
    
    def item_title(self, item):
        """아이템 제목"""
        if hasattr(item, 'item_type'):
            if item.item_type == 'band_post':
                return f"[소모임] {item.title or item.content[:50] if item.content else ''}"
            elif item.item_type == 'contest':
                return f"[대회] {item.title}"
            elif item.item_type == 'community':
                return f"[동호인톡] {item.title}"
            elif item.item_type == 'badmintok':
                return f"[배드민톡] {item.title}"
            elif item.item_type == 'member_review':
                return f"[동호인 리뷰] {item.title}"
        return getattr(item, 'title', str(item))
    
    def item_description(self, item):
        """아이템 설명"""
        if hasattr(item, 'item_type'):
            if item.item_type == 'band_post':
                if item.content:
                    text = item.content[:200]
                    return text + '...' if len(item.content) > 200 else text
                return ""
            elif item.item_type == 'contest':
                description_parts = []
                if item.get_period_display():
                    description_parts.append(f"대회 기간: {item.get_period_display()}")
                if item.get_location_display():
                    description_parts.append(f"장소: {item.get_location_display()}")
                if item.description:
                    description_parts.append(item.description[:150])
                return " | ".join(description_parts) if description_parts else ""
            else:
                # Post 객체인 경우
                if hasattr(item, 'content') and item.content:
                    text = strip_tags(item.content)
                    text = re.sub(r'\s+', ' ', text).strip()
                    return text[:200] + '...' if len(text) > 200 else text
        return ""
    
    def item_link(self, item):
        """아이템 링크"""
        if hasattr(item, 'item_type'):
            if item.item_type == 'band_post':
                return reverse('band:post_detail', args=[item.band_id, item.id])
            elif item.item_type == 'contest':
                return reverse('contests:detail', args=[item.slug])
            elif item.item_type == 'badmintok':
                return reverse('badmintok_detail', args=[item.slug])
            else:
                # community, member_review
                return reverse('community:detail', args=[item.slug])
        return "/"
    
    def item_pubdate(self, item):
        """발행일"""
        if hasattr(item, 'published_at') and item.published_at:
            return item.published_at
        return item.created_at
    
    def item_author_name(self, item):
        """작성자"""
        if hasattr(item, 'author') and item.author:
            return item.author.activity_name
        elif hasattr(item, 'created_by') and item.created_by:
            return item.created_by.activity_name
        return ""

