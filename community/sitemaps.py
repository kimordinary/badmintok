from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from .models import Post, Category


def _latest_updated_at(qs):
    """주어진 쿼리셋의 가장 최근 updated_at 반환. 없으면 None."""
    obj = qs.order_by("-updated_at").first()
    return obj.updated_at if obj else None


class CommunityPostSitemap(Sitemap):
    """동호인톡 게시글 사이트맵"""
    changefreq = "daily"
    priority = 0.7

    def items(self):
        now = timezone.now()
        return Post.objects.filter(
            source=Post.Source.COMMUNITY,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')

    def location(self, obj):
        return reverse('community:detail', args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at or obj.published_at or obj.created_at


class BadmintokPostSitemap(Sitemap):
    """배드민톡 게시글 사이트맵"""
    changefreq = "daily"
    priority = 0.8

    def items(self):
        now = timezone.now()
        return Post.objects.filter(
            source=Post.Source.BADMINTOK,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')

    def location(self, obj):
        return reverse('badmintok_detail', args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at or obj.published_at or obj.created_at


class MemberReviewPostSitemap(Sitemap):
    """동호인 리뷰 게시글 사이트맵"""
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        now = timezone.now()
        return Post.objects.filter(
            source=Post.Source.MEMBER_REVIEWS,
            is_deleted=False,
            is_draft=False,
            published_at__lte=now
        ).select_related('author', 'category').order_by('-created_at')

    def location(self, obj):
        return reverse('community:detail', args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at or obj.published_at or obj.created_at


class CommunityListSitemap(Sitemap):
    """동호인톡 목록 페이지 사이트맵"""
    changefreq = "daily"
    priority = 0.9   # 카테고리 허브 페이지 — 높임

    def items(self):
        return [True]

    def location(self, obj):
        return reverse('community:list')

    def lastmod(self, obj):
        now = timezone.now()
        return _latest_updated_at(Post.objects.filter(
            source=Post.Source.COMMUNITY,
            is_deleted=False, is_draft=False, published_at__lte=now,
        ))


class BadmintokListSitemap(Sitemap):
    """배드민톡 목록 페이지 사이트맵 (/badmintok/)"""
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return [True]

    def location(self, obj):
        return reverse('badmintok')

    def lastmod(self, obj):
        now = timezone.now()
        return _latest_updated_at(Post.objects.filter(
            source=Post.Source.BADMINTOK,
            is_deleted=False, is_draft=False, published_at__lte=now,
        ))


# === 카테고리 허브 페이지 (메인 카테고리만) ===

# 콘텐츠 있을 때만 sitemap에 포함하기 위한 헬퍼
def _category_has_content(category, source):
    now = timezone.now()
    return Post.objects.filter(
        source=source,
        is_deleted=False, is_draft=False, published_at__lte=now,
    ).filter(category__slug=category.slug).exists()


class BadmintokCategorySitemap(Sitemap):
    """배드민톡 메인 카테고리 페이지 (?tab=news/reviews/brand/feed)"""
    changefreq = "daily"
    priority = 0.8

    def items(self):
        # 메인(parent 없음) + 활성 + source=BADMINTOK + 콘텐츠 1개 이상
        qs = Category.objects.filter(
            source=Category.Source.BADMINTOK,
            parent__isnull=True,
            is_active=True,
        ).order_by('display_order')
        return [c for c in qs if _category_has_content(c, Post.Source.BADMINTOK)]

    def location(self, obj):
        return f"{reverse('badmintok')}?tab={obj.slug}"

    def lastmod(self, obj):
        now = timezone.now()
        return _latest_updated_at(Post.objects.filter(
            source=Post.Source.BADMINTOK,
            is_deleted=False, is_draft=False, published_at__lte=now,
            category__slug=obj.slug,
        ))


class CommunityCategorySitemap(Sitemap):
    """동호인톡 메인 카테고리 페이지 (?category=free/review/community-reviews)"""
    changefreq = "daily"
    priority = 0.8

    def items(self):
        qs = Category.objects.filter(
            source=Category.Source.COMMUNITY,
            parent__isnull=True,
            is_active=True,
        ).order_by('display_order')
        return [c for c in qs if _category_has_content(c, Post.Source.COMMUNITY)]

    def location(self, obj):
        return f"{reverse('community:list')}?category={obj.slug}"

    def lastmod(self, obj):
        now = timezone.now()
        return _latest_updated_at(Post.objects.filter(
            source=Post.Source.COMMUNITY,
            is_deleted=False, is_draft=False, published_at__lte=now,
            category__slug=obj.slug,
        ))
