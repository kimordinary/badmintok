from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import json
import hashlib

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

    def _extract_search_terms(self, referer):
        """유입 URL에서 검색어 추출 (Google, Naver, Daum 등)"""
        from urllib.parse import urlparse, parse_qs

        if not referer:
            return None

        try:
            parsed = urlparse(referer)
            domain = parsed.netloc.lower()
            query_params = parse_qs(parsed.query)

            # Google (q 파라미터)
            if 'google' in domain and 'q' in query_params:
                return query_params['q'][0]

            # Naver (query 파라미터)
            if 'naver' in domain and 'query' in query_params:
                return query_params['query'][0]

            # Daum (q 파라미터)
            if 'daum' in domain and 'q' in query_params:
                return query_params['q'][0]

            # Bing (q 파라미터)
            if 'bing' in domain and 'q' in query_params:
                return query_params['q'][0]

        except Exception:
            pass

        return None

    def _get_cache_key(self, period, date_str):
        """캐시 키 생성"""
        key = f"stats_{period}_{date_str}"
        return hashlib.md5(key.encode()).hexdigest()

    def statistics_view(self, request):
        """Jetpack 스타일 통계 대시보드 (최적화 버전)"""
        from datetime import datetime

        # 기간 파라미터: day, week, month, year (기본값: week)
        period = request.GET.get('period', 'week')

        # 기간별 일수 매핑
        period_days_map = {
            'day': 1,
            'week': 7,
            'month': 30,
            'year': 365
        }

        if period not in period_days_map:
            period = 'week'

        period_days = period_days_map[period]

        # 날짜 파라미터 (선택된 날짜, 기본값: 오늘)
        date_param = request.GET.get('date', '')

        now = timezone.now()

        if date_param:
            try:
                # YYYY-MM-DD 형식으로 파싱
                selected_date = datetime.strptime(date_param, '%Y-%m-%d')
                selected_date = timezone.make_aware(selected_date.replace(hour=0, minute=0, second=0, microsecond=0))
            except ValueError:
                selected_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            selected_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 캐시 확인 (오늘 데이터가 아닌 경우만 캐시 사용)
        cache_key = self._get_cache_key(period, selected_date.strftime('%Y-%m-%d'))
        is_today = selected_date.date() == now.date()

        if not is_today:
            cached_data = cache.get(cache_key)
            if cached_data:
                return render(request, 'admin/statistics_jetpack.html', cached_data)

        # 기간 시작일/종료일 계산
        if period == 'day':
            period_start = selected_date
            period_end = selected_date + timedelta(days=1)
            chart_days = 1
        elif period == 'week':
            period_start = selected_date - timedelta(days=6)
            period_end = selected_date + timedelta(days=1)
            chart_days = 7
        elif period == 'month':
            period_start = selected_date - timedelta(days=29)
            period_end = selected_date + timedelta(days=1)
            chart_days = 30
        else:  # year
            period_start = selected_date - timedelta(days=364)
            period_end = selected_date + timedelta(days=1)
            chart_days = 365

        # 이전/다음 날짜 계산
        if period == 'day':
            prev_date = (selected_date - timedelta(days=1)).strftime('%Y-%m-%d')
            next_date = (selected_date + timedelta(days=1)).strftime('%Y-%m-%d')
        elif period == 'week':
            prev_date = (selected_date - timedelta(days=7)).strftime('%Y-%m-%d')
            next_date = (selected_date + timedelta(days=7)).strftime('%Y-%m-%d')
        elif period == 'month':
            prev_date = (selected_date - timedelta(days=30)).strftime('%Y-%m-%d')
            next_date = (selected_date + timedelta(days=30)).strftime('%Y-%m-%d')
        else:  # year
            prev_date = (selected_date - timedelta(days=365)).strftime('%Y-%m-%d')
            next_date = (selected_date + timedelta(days=365)).strftime('%Y-%m-%d')

        # 현재 날짜 표시 형식
        if period == 'day':
            date_display = selected_date.strftime('%Y년 %m월 %d일')
        elif period == 'week':
            week_start = selected_date - timedelta(days=6)
            date_display = f"{week_start.strftime('%Y년 %m월 %d일')} - {selected_date.strftime('%m월 %d일')}"
        elif period == 'month':
            month_start = selected_date - timedelta(days=29)
            date_display = f"{month_start.strftime('%Y년 %m월 %d일')} - {selected_date.strftime('%m월 %d일')}"
        else:  # year
            year_start = selected_date - timedelta(days=364)
            date_display = f"{year_start.strftime('%Y년 %m월 %d일')} - {selected_date.strftime('%m월 %d일')}"

        # 실제 사용자만 필터링 (봇 및 스태프 제외)
        real_user_filter = (
            Q(device_type__in=['desktop', 'mobile', 'tablet']) &
            (Q(user__is_staff=False) | Q(user__isnull=True))
        )

        # 기간 내 기본 쿼리셋 (재사용)
        base_queryset = VisitorLog.objects.filter(
            visited_at__gte=period_start,
            visited_at__lt=period_end
        ).filter(real_user_filter)

        # === 1. 선택된 기간 통계 ===
        # 방문자 수 (고유 세션)
        period_visitors = base_queryset.values('session_key').distinct().count()

        # 페이지뷰
        period_pageviews = base_queryset.count()

        # === 2. 차트 데이터 (단일 쿼리로 일별 집계) ===
        # 일별 페이지뷰 집계
        daily_pageviews = base_queryset.annotate(
            date=TruncDate('visited_at')
        ).values('date').annotate(
            views=Count('id')
        ).order_by('date')

        # 일별 방문자 수 집계 (고유 세션)
        daily_visitors = base_queryset.annotate(
            date=TruncDate('visited_at')
        ).values('date', 'session_key').distinct().values('date').annotate(
            visitors=Count('session_key')
        ).order_by('date')

        # 딕셔너리로 변환하여 빠른 조회
        pageviews_dict = {item['date']: item['views'] for item in daily_pageviews}
        visitors_dict = {item['date']: item['visitors'] for item in daily_visitors}

        # 차트 데이터 생성 (빈 날짜도 포함)
        chart_data = []
        for i in range(chart_days - 1, -1, -1):
            day = (selected_date - timedelta(days=i)).date()

            # 날짜 포맷 설정
            if period == 'year':
                date_label = day.strftime('%y/%m/%d')
            else:
                date_label = day.strftime('%m/%d')

            chart_data.append({
                'label': date_label,
                'visitors': visitors_dict.get(day, 0),
                'views': pageviews_dict.get(day, 0),
            })

        # === 3. 상위 게시물/페이지 ===
        top_pages = base_queryset.values('url_path').annotate(
            views=Count('id')
        ).order_by('-views')[:15]

        # === 4. 유입 경로 (Referrers) ===
        top_referrers = base_queryset.filter(
            referer_domain__isnull=False
        ).exclude(
            referer_domain=''
        ).values('referer_domain').annotate(
            visits=Count('id')
        ).order_by('-visits')[:15]

        # === 5. 검색어 추출 (최적화: 검색 엔진 도메인만 필터링 + 제한) ===
        search_engine_domains = ['google', 'naver', 'daum', 'bing']
        search_referer_q = Q()
        for domain in search_engine_domains:
            search_referer_q |= Q(referer_domain__icontains=domain)

        # 검색 엔진에서 유입된 로그만 가져오기 (최대 1000개로 제한)
        search_logs = base_queryset.filter(
            referer__isnull=False
        ).filter(search_referer_q).exclude(
            referer=''
        ).values_list('referer', flat=True)[:1000]

        search_terms_count = {}
        for referer in search_logs:
            term = self._extract_search_terms(referer)
            if term:
                search_terms_count[term] = search_terms_count.get(term, 0) + 1

        # 상위 검색어 정렬
        top_search_terms = sorted(
            [{'term': k, 'count': v} for k, v in search_terms_count.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:15]

        # === 6. 외부 링크 클릭 (Outbound Clicks) ===
        top_outbound_clicks = OutboundClick.objects.filter(
            clicked_at__gte=period_start,
            clicked_at__lt=period_end,
            device_type__in=['desktop', 'mobile', 'tablet']
        ).filter(
            Q(user__is_staff=False) | Q(user__isnull=True)
        ).values('destination_domain').annotate(
            clicks=Count('id')
        ).order_by('-clicks')[:15]

        context = {
            'site_header': '배드민톡 통계',
            'site_title': 'Jetpack 스타일 통계',
            # 기간 정보
            'period': period,
            'period_days': period_days,
            # 날짜 네비게이션
            'selected_date': selected_date.strftime('%Y-%m-%d'),
            'date_display': date_display,
            'prev_date': prev_date,
            'next_date': next_date,
            # 주요 지표
            'period_visitors': period_visitors,
            'period_pageviews': period_pageviews,
            # 차트 데이터
            'chart_data_json': json.dumps(chart_data),
            # 상위 페이지
            'top_pages': top_pages,
            # 유입 경로
            'top_referrers': top_referrers,
            # 검색어
            'top_search_terms': top_search_terms,
            # 외부 링크 클릭
            'top_outbound_clicks': top_outbound_clicks,
        }

        # 캐시 저장 (오늘 데이터가 아닌 경우, 1시간 캐시)
        if not is_today:
            cache.set(cache_key, context, 3600)

        return render(request, 'admin/statistics_jetpack.html', context)

    def _calculate_change(self, current, previous):
        """변화율 계산 (%)"""
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100, 1)