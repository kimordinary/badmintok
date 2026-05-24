from datetime import date

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Contest


class ContestSitemap(Sitemap):
    """대회 사이트맵.

    종료된 대회는 priority/changefreq를 낮춰 크롤링 부하를 줄이되,
    아카이브 가치를 위해 sitemap에는 유지한다.
    """

    def items(self):
        return Contest.objects.select_related('category', 'sponsor').order_by('-created_at')

    def location(self, obj):
        return reverse('contests:detail', args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at or obj.created_at

    def priority(self, obj):
        # 종료된 대회는 우선순위 낮춤
        end = obj.schedule_end or obj.schedule_start
        if end and end < date.today():
            return 0.3
        return 0.8

    def changefreq(self, obj):
        end = obj.schedule_end or obj.schedule_start
        if end and end < date.today():
            return "yearly"   # 종료된 대회는 거의 안 바뀜
        return "weekly"


class ContestListSitemap(Sitemap):
    """대회 목록 페이지 사이트맵 (/badminton-tournament/) — 카테고리 허브"""
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return [True]

    def location(self, obj):
        return reverse('contests:list')

    def lastmod(self, obj):
        c = Contest.objects.order_by('-updated_at').first()
        return c.updated_at if c else None
