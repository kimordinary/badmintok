from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from .models import Post


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


class BadmintokTagSitemap(Sitemap):
    """배드민톡 브랜드 태그 아카이브 사이트맵.

    글이 하나라도 있는 활성 태그만 등록 (thin content 방지).
    """
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        from .models import Tag
        now = timezone.now()
        return Tag.objects.filter(
            source="badmintok", is_active=True,
            posts__source=Post.Source.BADMINTOK,
            posts__is_deleted=False, posts__is_draft=False,
            posts__published_at__lte=now,
        ).distinct().order_by("display_order", "name")

    def location(self, obj):
        return reverse("badmintok_tag", args=[obj.slug])

    def lastmod(self, obj):
        now = timezone.now()
        p = obj.posts.filter(
            is_deleted=False, is_draft=False, published_at__lte=now,
        ).order_by("-updated_at").first()
        return p.updated_at if p else None


# 카테고리 허브 sitemap (?tab= / ?category=)은 의도적으로 제거:
# - 구글이 쿼리스트링 URL을 카노니컬 후보로 안 잡고 색인 효과 미미
# - 메인 페이지(/badmintok/, /community/) 사이트맵으로 충분
