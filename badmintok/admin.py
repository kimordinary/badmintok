from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import json

from .models import BadmintokBanner, Notice, VisitorLog, OutboundClick


@admin.register(BadmintokBanner)
class BadmintokBannerAdmin(admin.ModelAdmin):
    list_display = ("id", "image_preview", "title", "link_url", "is_active", "display_order", "created_at", "edit_button", "delete_button")
    list_editable = ("is_active", "display_order")
    search_fields = ("title", "alt_text", "link_url")
    list_filter = ("is_active",)
    ordering = ("display_order", "id")

    def image_preview(self, obj):
        """배너 이미지 미리보기"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 100px; object-fit: contain;" />',
                obj.image.url
            )
        return "-"
    image_preview.short_description = "이미지 미리보기"

    def edit_button(self, obj):
        """수정 버튼"""
        url = reverse('admin:badmintok_badmintokbanner_change', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="padding: 5px 10px; background-color: #417690; color: white; text-decoration: none; border-radius: 4px;">수정</a>',
            url
        )
    edit_button.short_description = "수정"

    def delete_button(self, obj):
        """삭제 버튼"""
        url = reverse('admin:badmintok_badmintokbanner_delete', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="padding: 5px 10px; background-color: #ba2121; color: white; text-decoration: none; border-radius: 4px;">삭제</a>',
            url
        )
    delete_button.short_description = "삭제"

    fieldsets = (
        ("배너 정보", {
            "fields": ("title", "image", "alt_text", "link_url")
        }),
        ("설정", {
            "fields": ("is_active", "display_order")
        }),
        ("날짜 정보", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    readonly_fields = ("created_at", "updated_at")


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "is_pinned", "view_count", "created_at")
    list_editable = ("is_pinned",)
    search_fields = ("title", "content")
    list_filter = ("is_pinned", "created_at")
    ordering = ("-is_pinned", "-created_at")
    readonly_fields = ("view_count", "created_at", "updated_at")
    
    fieldsets = (
        ("기본 정보", {
            "fields": ("title", "content", "author")
        }),
        ("설정", {
            "fields": ("is_pinned",)
        }),
        ("통계", {
            "fields": ("view_count",)
        }),
        ("날짜 정보", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(VisitorLog)
class VisitorLogAdmin(admin.ModelAdmin):
    """방문 로그 Admin"""
    list_display = ("visited_at", "url_path", "user", "device_type", "referer_domain", "ip_address")
    list_filter = ("device_type", "visited_at")
    search_fields = ("url_path", "referer", "ip_address", "user__email", "user__activity_name")
    readonly_fields = ("visited_at", "user", "session_key", "ip_address", "url_path", "referer", "referer_domain", "user_agent", "device_type")
    date_hierarchy = "visited_at"
    list_per_page = 50

    def has_add_permission(self, request):
        """추가 권한 제거 (자동으로만 생성)"""
        return False


@admin.register(OutboundClick)
class OutboundClickAdmin(admin.ModelAdmin):
    """외부 링크 클릭 Admin"""
    list_display = ("clicked_at", "destination_domain", "link_type", "source_url", "user", "device_type")
    list_filter = ("link_type", "device_type", "clicked_at")
    search_fields = ("destination_url", "destination_domain", "link_text", "source_url", "user__email", "user__activity_name")
    readonly_fields = ("clicked_at", "user", "session_key", "ip_address", "destination_url", "destination_domain", "link_text", "link_type", "source_url", "user_agent", "device_type")
    date_hierarchy = "clicked_at"
    list_per_page = 50

    def has_add_permission(self, request):
        """추가 권한 제거 (자동으로만 생성)"""
        return False


class BadmintokAdminSite(admin.AdminSite):
    """커스텀 Admin 사이트 - 통계 대시보드 추가"""

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('statistics/', self.admin_view(self.statistics_view), name='statistics'),
        ]
        return custom_urls + urls

    def statistics_view(self, request):
        """젯팩 스타일 통계 대시보드"""
        # 기간 파라미터 받기 (기본값: 7일)
        period = request.GET.get('period', '7')
        try:
            period_days = int(period)
            if period_days not in [1, 7, 30]:
                period_days = 7
        except ValueError:
            period_days = 7

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)
        week_start = today_start - timedelta(days=7)
        month_start = today_start - timedelta(days=30)

        # 선택된 기간의 시작일
        period_start = today_start - timedelta(days=period_days)

        # 오늘 방문자 수 (고유 세션)
        today_visitors = VisitorLog.objects.filter(
            visited_at__gte=today_start
        ).values('session_key').distinct().count()

        # 어제 방문자 수
        yesterday_visitors = VisitorLog.objects.filter(
            visited_at__gte=yesterday_start,
            visited_at__lt=today_start
        ).values('session_key').distinct().count()

        # 이번 주 방문자 수
        week_visitors = VisitorLog.objects.filter(
            visited_at__gte=week_start
        ).values('session_key').distinct().count()

        # 이번 달 방문자 수
        month_visitors = VisitorLog.objects.filter(
            visited_at__gte=month_start
        ).values('session_key').distinct().count()

        # 오늘 페이지뷰
        today_pageviews = VisitorLog.objects.filter(
            visited_at__gte=today_start
        ).count()

        # 어제 페이지뷰
        yesterday_pageviews = VisitorLog.objects.filter(
            visited_at__gte=yesterday_start,
            visited_at__lt=today_start
        ).count()

        # 최근 7일 일별 방문자 수 (차트용)
        daily_stats = []
        for i in range(6, -1, -1):
            day_start = today_start - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            visitors = VisitorLog.objects.filter(
                visited_at__gte=day_start,
                visited_at__lt=day_end
            ).values('session_key').distinct().count()
            pageviews = VisitorLog.objects.filter(
                visited_at__gte=day_start,
                visited_at__lt=day_end
            ).count()
            daily_stats.append({
                'date': day_start.strftime('%m/%d'),
                'visitors': visitors,
                'pageviews': pageviews,
            })

        # 오늘 시간대별 방문자 수 (차트용)
        hourly_stats = []
        for hour in range(24):
            hour_start = today_start + timedelta(hours=hour)
            hour_end = hour_start + timedelta(hours=1)
            visitors = VisitorLog.objects.filter(
                visited_at__gte=hour_start,
                visited_at__lt=hour_end
            ).values('session_key').distinct().count()
            hourly_stats.append({
                'hour': f'{hour:02d}:00',
                'visitors': visitors,
            })

        # 상위 페이지 (선택된 기간)
        top_pages = VisitorLog.objects.filter(
            visited_at__gte=period_start
        ).values('url_path').annotate(
            views=Count('id')
        ).order_by('-views')[:10]

        # 상위 유입 경로 (선택된 기간)
        top_referrers = VisitorLog.objects.filter(
            visited_at__gte=period_start,
            referer_domain__isnull=False
        ).exclude(
            referer_domain=''
        ).values('referer_domain').annotate(
            visits=Count('id')
        ).order_by('-visits')[:10]

        # 디바이스 통계 (선택된 기간)
        device_stats = VisitorLog.objects.filter(
            visited_at__gte=period_start
        ).values('device_type').annotate(
            count=Count('id')
        ).order_by('-count')

        # 외부 링크 클릭 통계 (선택된 기간)
        top_outbound_clicks = OutboundClick.objects.filter(
            clicked_at__gte=period_start
        ).values('destination_domain', 'link_type').annotate(
            clicks=Count('id')
        ).order_by('-clicks')[:10]

        # 전체 통계
        from community.models import Post, Comment
        from band.models import Band, BandPost
        from contests.models import Contest
        from django.contrib.auth import get_user_model
        User = get_user_model()

        total_users = User.objects.count()
        total_posts = Post.objects.filter(is_deleted=False).count()
        total_comments = Comment.objects.filter(is_deleted=False).count()
        total_bands = Band.objects.count()
        total_contests = Contest.objects.count()

        context = {
            'site_header': '배드민톡 통계',
            'site_title': '통계 대시보드',
            'today_visitors': today_visitors,
            'yesterday_visitors': yesterday_visitors,
            'week_visitors': week_visitors,
            'month_visitors': month_visitors,
            'today_pageviews': today_pageviews,
            'yesterday_pageviews': yesterday_pageviews,
            'daily_stats_json': json.dumps(daily_stats),
            'hourly_stats_json': json.dumps(hourly_stats),
            'top_pages': top_pages,
            'top_referrers': top_referrers,
            'device_stats': device_stats,
            'top_outbound_clicks': top_outbound_clicks,
            'total_users': total_users,
            'total_posts': total_posts,
            'total_comments': total_comments,
            'total_bands': total_bands,
            'total_contests': total_contests,
            # 변화율 계산
            'visitors_change': self._calculate_change(today_visitors, yesterday_visitors),
            'pageviews_change': self._calculate_change(today_pageviews, yesterday_pageviews),
            # 선택된 기간
            'selected_period': period_days,
        }

        return render(request, 'admin/statistics.html', context)

    def _calculate_change(self, current, previous):
        """변화율 계산 (%)"""
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)