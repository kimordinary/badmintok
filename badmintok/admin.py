from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import timedelta
import json
import hashlib
from unfold.admin import ModelAdmin

from .models import BadmintokBanner, Banner, Notice, VisitorLog, OutboundClick, YoutubeVideo, AppDownloadClick
from .fields import (
    get_unconverted_images_stats,
    convert_existing_image_to_webp,
    is_convertible,
    get_all_image_fields_info,
)


@admin.register(BadmintokBanner)
class BadmintokBannerAdmin(ModelAdmin):
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


@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = (
        "id", "image_preview", "title", "is_active", "display_status",
        "order", "start_date", "end_date", "created_at"
    )
    list_editable = ("is_active", "order")
    list_filter = ("is_active", "start_date", "end_date")
    search_fields = ("title", "link_url")
    ordering = ("order", "-created_at")

    def image_preview(self, obj):
        """배너 이미지 미리보기"""
        if obj.mobile_image:
            return format_html(
                '<img src="{}" style="max-width: 150px; max-height: 80px; object-fit: contain;" />',
                obj.mobile_image.url
            )
        return "-"
    image_preview.short_description = "이미지"

    def display_status(self, obj):
        """현재 노출 상태 표시"""
        if obj.is_currently_active:
            return format_html('<span style="color: #10b981;">● 노출중</span>')
        elif not obj.is_active:
            return format_html('<span style="color: #9ca3af;">● 비활성</span>')
        else:
            return format_html('<span style="color: #f59e0b;">● 기간외</span>')
    display_status.short_description = "노출 상태"

    fieldsets = (
        ("배너 정보", {
            "fields": ("title", "mobile_image", "link_url")
        }),
        ("노출 설정", {
            "fields": ("is_active", "order", ("start_date", "end_date"))
        }),
        ("날짜 정보", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    readonly_fields = ("created_at", "updated_at")


@admin.register(Notice)
class NoticeAdmin(ModelAdmin):
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


@admin.register(YoutubeVideo)
class YoutubeVideoAdmin(ModelAdmin):
    list_display = ['title', 'video_id', 'is_active', 'order', 'created_at']
    list_editable = ['is_active', 'order']
    list_filter = ['is_active']
    search_fields = ['title', 'youtube_url']
    readonly_fields = ['video_id', 'thumbnail_url', 'created_at', 'updated_at']

    fieldsets = (
        ("영상 정보", {
            "fields": ("title", "youtube_url", "description")
        }),
        ("자동 생성 필드", {
            "fields": ("video_id", "thumbnail_url"),
            "classes": ("collapse",),
            "description": "유튜브 URL에서 자동으로 추출됩니다."
        }),
        ("설정", {
            "fields": ("is_active", "order")
        }),
        ("날짜 정보", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


@admin.register(VisitorLog)
class VisitorLogAdmin(ModelAdmin):
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


@admin.register(AppDownloadClick)
class AppDownloadClickAdmin(ModelAdmin):
    """앱 다운로드 클릭 Admin"""
    list_display = ("created_at", "os", "referrer_path", "user", "ip_address")
    list_filter = ("os", "created_at")
    search_fields = ("referrer_path", "ip_address", "user__email", "user__activity_name")
    readonly_fields = ("created_at", "os", "referrer_path", "user", "user_agent", "ip_address")
    date_hierarchy = "created_at"
    list_per_page = 50

    def has_add_permission(self, request):
        return False


@admin.register(OutboundClick)
class OutboundClickAdmin(ModelAdmin):
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


# 헬퍼 함수들
def _extract_search_terms(referer):
    """유입 URL에서 검색어 추출 (Google, Naver, Daum 등)"""
    from urllib.parse import urlparse, parse_qs

    if not referer:
        return None

    try:
        parsed = urlparse(referer)
        domain = parsed.netloc.lower()
        query_params = parse_qs(parsed.query)

        if 'google' in domain and 'q' in query_params:
            return query_params['q'][0]

        if 'naver' in domain and 'query' in query_params:
            return query_params['query'][0]

        if 'daum' in domain and 'q' in query_params:
            return query_params['q'][0]

        if 'bing' in domain and 'q' in query_params:
            return query_params['q'][0]

    except Exception:
        pass

    return None


def _get_cache_key(period, date_str, source='all'):
    """캐시 키 생성"""
    key = f"stats_{period}_{date_str}_{source}"
    return hashlib.md5(key.encode()).hexdigest()


def _calculate_change(current, previous):
    """변화율 계산 (%)"""
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100, 1)


def statistics_view(request):
    """Jetpack 스타일 통계 대시보드 (최적화 버전)"""
    from datetime import datetime

    period = request.GET.get('period', 'day')

    period_days_map = {
        'day': 1,
        'week': 7,
        'month': 30,
        'year': 365
    }

    if period not in period_days_map:
        period = 'week'

    period_days = period_days_map[period]

    date_param = request.GET.get('date', '')

    # KST 기준으로 '오늘 0시'를 계산해야 일별 통계가 한국 날짜와 일치
    now = timezone.localtime()

    if date_param:
        try:
            selected_date = datetime.strptime(date_param, '%Y-%m-%d')
            selected_date = timezone.make_aware(selected_date.replace(hour=0, minute=0, second=0, microsecond=0))
        except ValueError:
            selected_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        selected_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 출처(웹/앱) 필터 — ?source=all|web|app (기본 all)
    source_param = request.GET.get('source', 'all')
    if source_param not in ('all', 'web', 'app'):
        source_param = 'all'

    cache_key = _get_cache_key(period, selected_date.strftime('%Y-%m-%d'), source_param)
    is_today = selected_date.date() == now.date()

    # 캐시 조회 (오늘이든 과거든 일단 확인)
    cached_data = cache.get(cache_key)
    if cached_data:
        return render(request, 'admin/statistics_jetpack.html', cached_data)

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
    else:
        period_start = selected_date - timedelta(days=364)
        period_end = selected_date + timedelta(days=1)
        chart_days = 365

    if period == 'day':
        prev_date = (selected_date - timedelta(days=1)).strftime('%Y-%m-%d')
        next_date = (selected_date + timedelta(days=1)).strftime('%Y-%m-%d')
    elif period == 'week':
        prev_date = (selected_date - timedelta(days=7)).strftime('%Y-%m-%d')
        next_date = (selected_date + timedelta(days=7)).strftime('%Y-%m-%d')
    elif period == 'month':
        prev_date = (selected_date - timedelta(days=30)).strftime('%Y-%m-%d')
        next_date = (selected_date + timedelta(days=30)).strftime('%Y-%m-%d')
    else:
        prev_date = (selected_date - timedelta(days=365)).strftime('%Y-%m-%d')
        next_date = (selected_date + timedelta(days=365)).strftime('%Y-%m-%d')

    if period == 'day':
        date_display = selected_date.strftime('%Y년 %m월 %d일')
    elif period == 'week':
        week_start = selected_date - timedelta(days=6)
        date_display = f"{week_start.strftime('%Y년 %m월 %d일')} - {selected_date.strftime('%m월 %d일')}"
    elif period == 'month':
        month_start = selected_date - timedelta(days=29)
        date_display = f"{month_start.strftime('%Y년 %m월 %d일')} - {selected_date.strftime('%m월 %d일')}"
    else:
        year_start = selected_date - timedelta(days=364)
        date_display = f"{year_start.strftime('%Y년 %m월 %d일')} - {selected_date.strftime('%m월 %d일')}"

    real_user_filter = (
        Q(device_type__in=['desktop', 'mobile', 'tablet']) &
        (Q(user__is_staff=False) | Q(user__isnull=True))
    )

    base_queryset = VisitorLog.objects.filter(
        visited_at__gte=period_start,
        visited_at__lt=period_end
    ).filter(real_user_filter)
    if source_param != 'all':
        base_queryset = base_queryset.filter(source=source_param)

    period_visitors = base_queryset.values('session_key').distinct().count()
    period_pageviews = base_queryset.count()

    prev_period_start = period_start - timedelta(days=chart_days)
    prev_period_end = period_start

    prev_base_queryset = VisitorLog.objects.filter(
        visited_at__gte=prev_period_start,
        visited_at__lt=prev_period_end
    ).filter(real_user_filter)
    if source_param != 'all':
        prev_base_queryset = prev_base_queryset.filter(source=source_param)

    prev_visitors = prev_base_queryset.values('session_key').distinct().count()
    prev_pageviews = prev_base_queryset.count()

    visitors_change = _calculate_change(period_visitors, prev_visitors)
    pageviews_change = _calculate_change(period_pageviews, prev_pageviews)

    # === 신규 가입자 (단일 쿼리로 현재+이전 기간 일괄 처리) ===
    from django.contrib.auth import get_user_model
    User = get_user_model()

    all_signups = list(User.objects.filter(
        is_active=True,
        date_joined__gte=prev_period_start,
        date_joined__lt=period_end,
    ).values_list('date_joined', flat=True))

    period_signups = sum(1 for d in all_signups if d >= period_start)
    prev_signups = sum(1 for d in all_signups if d < period_start)
    signups_change = _calculate_change(period_signups, prev_signups)

    signups_dict = {}
    for d in all_signups:
        if d >= period_start:
            day = timezone.localtime(d).date()
            signups_dict[day] = signups_dict.get(day, 0) + 1

    # === 출처 분리 카운트 (전체 필터일 때만 의미 있음) ===
    web_qs = VisitorLog.objects.filter(
        visited_at__gte=period_start, visited_at__lt=period_end,
        source=VisitorLog.SOURCE_WEB,
    ).filter(real_user_filter)
    app_qs = VisitorLog.objects.filter(
        visited_at__gte=period_start, visited_at__lt=period_end,
        source=VisitorLog.SOURCE_APP,
    ).filter(real_user_filter)
    source_stats = {
        'web': {
            'visitors': web_qs.values('session_key').distinct().count(),
            'pageviews': web_qs.count(),
        },
        'app': {
            'visitors': app_qs.values('session_key').distinct().count(),
            'pageviews': app_qs.count(),
        },
    }

    # === 신규 vs 재방문 (subquery로 IN 리스트 회피) ===
    period_session_keys_subq = base_queryset.values('session_key').distinct()
    returning_count = VisitorLog.objects.filter(
        session_key__in=period_session_keys_subq,
        visited_at__lt=period_start,
    ).filter(real_user_filter).values('session_key').distinct().count()
    new_count = max(0, period_visitors - returning_count)
    visitor_segment_stats = {
        'new': new_count,
        'returning': returning_count,
        'new_pct': round(new_count / period_visitors * 100, 1) if period_visitors else 0,
        'returning_pct': round(returning_count / period_visitors * 100, 1) if period_visitors else 0,
    }

    # === 디바이스 분포 ===
    device_rows = base_queryset.values('device_type').annotate(visits=Count('id'))
    device_total = sum(row['visits'] for row in device_rows) or 1
    _device_labels = {'desktop': '데스크탑', 'mobile': '모바일', 'tablet': '태블릿'}
    device_stats = []
    for key in ('mobile', 'desktop', 'tablet'):
        v = next((r['visits'] for r in device_rows if r['device_type'] == key), 0)
        device_stats.append({
            'key': key,
            'label': _device_labels[key],
            'visits': v,
            'pct': round(v / device_total * 100, 1),
        })

    # === 유입 채널 분류 ===
    SEARCH_DOMAINS = ('google', 'naver', 'daum', 'bing', 'yahoo')
    SOCIAL_DOMAINS = ('facebook', 'instagram', 'youtube', 'twitter', 't.co',
                      'kakao', 'cafe.naver', 'tistory', 'threads')

    def _categorize_channel(domain):
        if not domain:
            return 'direct'
        d = domain.lower()
        if any(s in d for s in SEARCH_DOMAINS):
            return 'search'
        if any(s in d for s in SOCIAL_DOMAINS):
            return 'social'
        return 'referral'

    channel_counts = {'direct': 0, 'search': 0, 'social': 0, 'referral': 0}
    for row in base_queryset.values('referer_domain').annotate(visits=Count('id')):
        channel_counts[_categorize_channel(row['referer_domain'])] += row['visits']
    channel_total = sum(channel_counts.values()) or 1
    _channel_labels = {
        'direct': '직접 방문',
        'search': '검색 엔진',
        'social': '소셜',
        'referral': '레퍼럴',
    }
    channel_stats = [
        {
            'key': k,
            'label': _channel_labels[k],
            'visits': channel_counts[k],
            'pct': round(channel_counts[k] / channel_total * 100, 1),
        }
        for k in ('direct', 'search', 'social', 'referral')
    ]

    daily_pageviews = base_queryset.annotate(
        date=TruncDate('visited_at')
    ).values('date').annotate(
        views=Count('id')
    ).order_by('date')

    daily_visitors = base_queryset.annotate(
        date=TruncDate('visited_at')
    ).values('date', 'session_key').distinct().values('date').annotate(
        visitors=Count('session_key')
    ).order_by('date')

    pageviews_dict = {item['date']: item['views'] for item in daily_pageviews}
    visitors_dict = {item['date']: item['visitors'] for item in daily_visitors}

    daily_app_clicks_qs = AppDownloadClick.objects.filter(
        created_at__gte=period_start,
        created_at__lt=period_end,
    ).filter(Q(user__is_staff=False) | Q(user__isnull=True)).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(count=Count('id')).order_by('date')
    app_clicks_dict = {item['date']: item['count'] for item in daily_app_clicks_qs}

    chart_data = []
    for i in range(chart_days - 1, -1, -1):
        day = (selected_date - timedelta(days=i)).date()

        if period == 'year':
            date_label = day.strftime('%y/%m/%d')
        else:
            date_label = day.strftime('%m/%d')

        day_views = pageviews_dict.get(day, 0)
        day_clicks = app_clicks_dict.get(day, 0)
        day_ctr = round(day_clicks / day_views * 100, 2) if day_views else 0

        chart_data.append({
            'label': date_label,
            'visitors': visitors_dict.get(day, 0),
            'views': day_views,
            'signups': signups_dict.get(day, 0),
            'ctr': day_ctr,
        })

    top_pages = list(base_queryset.values('url_path').annotate(
        views=Count('id')
    ).order_by('-views')[:15])

    # 인기 페이지 url_path → 사람이 읽는 제목 매핑 (표시용; 집계는 url_path 그대로)
    import re as _re
    from urllib.parse import unquote as _unquote
    _static_titles = {
        '/': '홈',
        '/badminton-tournament/': '전국 배드민턴 대회 목록',
        '/badminton-tournament/archive/': '대회 아카이브',
    }
    _detail_re = _re.compile(r'^/badminton-tournament/([^/]+)/$')
    _slugs = set()
    for _p in top_pages:
        _m = _detail_re.match(_p['url_path'])
        if _m and _p['url_path'] not in _static_titles:
            _slugs.add(_m.group(1)); _slugs.add(_unquote(_m.group(1)))
    _titles = {}
    if _slugs:
        from contests.models import Contest
        for _slug, _title in Contest.objects.filter(slug__in=list(_slugs)).values_list('slug', 'title'):
            _titles[_slug] = _title
    for _p in top_pages:
        _up = _p['url_path']
        if _up in _static_titles:
            _p['title'] = _static_titles[_up]
        elif _up.startswith('app://'):
            _p['title'] = '[앱] ' + _up[len('app://'):]
        else:
            _m = _detail_re.match(_up)
            _p['title'] = (_titles.get(_m.group(1)) or _titles.get(_unquote(_m.group(1))) or _up) if _m else _up

    top_referrers = list(base_queryset.filter(
        referer_domain__isnull=False
    ).exclude(
        referer_domain=''
    ).exclude(
        referer_domain__icontains='badmintok'  # self-referral(내부 이동) 제외 — 외부 유입원만
    ).values('referer_domain').annotate(
        visits=Count('id')
    ).order_by('-visits')[:15])

    search_engine_domains = ['google', 'naver', 'daum', 'bing']
    search_referer_q = Q()
    for domain in search_engine_domains:
        search_referer_q |= Q(referer_domain__icontains=domain)

    search_logs = base_queryset.filter(
        referer__isnull=False
    ).filter(search_referer_q).exclude(
        referer=''
    ).values_list('referer', flat=True)[:1000]

    search_terms_count = {}
    for referer in search_logs:
        term = _extract_search_terms(referer)
        if term:
            search_terms_count[term] = search_terms_count.get(term, 0) + 1

    top_search_terms = sorted(
        [{'term': k, 'count': v} for k, v in search_terms_count.items()],
        key=lambda x: x['count'],
        reverse=True
    )[:15]

    top_outbound_clicks = list(OutboundClick.objects.filter(
        clicked_at__gte=period_start,
        clicked_at__lt=period_end,
        device_type__in=['desktop', 'mobile', 'tablet']
    ).filter(
        Q(user__is_staff=False) | Q(user__isnull=True)
    ).values('destination_domain').annotate(
        clicks=Count('id')
    ).order_by('-clicks')[:15])

    # 앱 다운로드 클릭 통계 (운영자 제외)
    app_download_qs = AppDownloadClick.objects.filter(
        created_at__gte=period_start,
        created_at__lt=period_end,
    ).filter(Q(user__is_staff=False) | Q(user__isnull=True))
    app_download_total = app_download_qs.count()
    app_download_by_os = {
        row['os']: row['count']
        for row in app_download_qs.values('os').annotate(count=Count('id'))
    }
    prev_app_download_total = AppDownloadClick.objects.filter(
        created_at__gte=prev_period_start,
        created_at__lt=prev_period_end,
    ).filter(Q(user__is_staff=False) | Q(user__isnull=True)).count()
    current_ctr = (round(app_download_total / period_pageviews * 100, 2)
                   if period_pageviews else 0)
    prev_ctr = (round(prev_app_download_total / prev_pageviews * 100, 2)
                if prev_pageviews else 0)
    app_download_stats = {
        'total': app_download_total,
        'ios': app_download_by_os.get('ios', 0),
        'android': app_download_by_os.get('android', 0),
        'other': app_download_by_os.get('other', 0),
        # CTA 클릭률: 페이지뷰 대비 다운로드 클릭 비율
        'click_rate_pct': current_ctr,
        'click_rate_change': _calculate_change(current_ctr, prev_ctr),
        'impressions': period_pageviews,
    }

    context = {
        'site_header': '배드민톡 통계',
        'site_title': 'Jetpack 스타일 통계',
        'period': period,
        'period_days': period_days,
        'chart_days': chart_days,
        'source_param': source_param,
        'source_stats': source_stats,
        'visitor_segment_stats': visitor_segment_stats,
        'device_stats': device_stats,
        'channel_stats': channel_stats,
        'selected_date': selected_date.strftime('%Y-%m-%d'),
        'date_display': date_display,
        'prev_date': prev_date,
        'next_date': next_date,
        'today_date': now.strftime('%Y-%m-%d'),
        'now': now,
        'period_visitors': period_visitors,
        'period_pageviews': period_pageviews,
        'period_signups': period_signups,
        'visitors_change': visitors_change,
        'pageviews_change': pageviews_change,
        'signups_change': signups_change,
        'chart_data_json': json.dumps(chart_data),
        'top_pages': top_pages,
        'top_referrers': top_referrers,
        'top_search_terms': top_search_terms,
        'top_outbound_clicks': top_outbound_clicks,
        'app_download_stats': app_download_stats,
    }

    # 오늘은 5분, 과거는 24시간 캐시
    cache.set(cache_key, context, 300 if is_today else 86400)

    return render(request, 'admin/statistics_jetpack.html', context)


# ===== WebP 이미지 관리 뷰 =====

def image_management_view(request):
    """WebP 이미지 변환 관리 페이지"""
    stats = get_unconverted_images_stats()

    # 통계 요약
    total_images = sum(s['total'] for s in stats.values())
    total_unconverted = sum(s['unconverted'] for s in stats.values())
    total_converted = sum(s['converted'] for s in stats.values())

    context = {
        'site_header': '이미지 WebP 변환 관리',
        'site_title': '이미지 관리',
        'stats': stats,
        'total_images': total_images,
        'total_unconverted': total_unconverted,
        'total_converted': total_converted,
        'conversion_rate': round((total_converted / total_images * 100) if total_images > 0 else 0, 1),
    }

    return render(request, 'admin/image_management.html', context)


def get_unconverted_images_list(request):
    """특정 모델/필드의 미변환 이미지 목록 반환"""
    from django.apps import apps

    app = request.GET.get('app')
    model_name = request.GET.get('model')
    field_name = request.GET.get('field')
    page = int(request.GET.get('page', 1))
    per_page = 20

    if not all([app, model_name, field_name]):
        return JsonResponse({'error': '필수 파라미터가 없습니다.'}, status=400)

    try:
        model_class = apps.get_model(app, model_name)
    except LookupError:
        return JsonResponse({'error': '모델을 찾을 수 없습니다.'}, status=404)

    # 미변환 이미지 조회
    queryset = model_class.objects.exclude(**{f"{field_name}__exact": ''})
    queryset = queryset.exclude(**{f"{field_name}__isnull": True})

    unconverted_items = []
    for obj in queryset.iterator():
        field_value = getattr(obj, field_name)
        if field_value and field_value.name and is_convertible(field_value.name):
            try:
                file_size = field_value.size
            except Exception:
                file_size = 0

            unconverted_items.append({
                'id': obj.pk,
                'filename': field_value.name,
                'size': file_size,
                'size_display': _format_file_size(file_size),
                'url': field_value.url if hasattr(field_value, 'url') else '',
            })

    # 페이지네이션
    total = len(unconverted_items)
    start = (page - 1) * per_page
    end = start + per_page
    items = unconverted_items[start:end]

    return JsonResponse({
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
    })


@require_POST
def convert_single_image(request):
    """단일 이미지 WebP 변환"""
    from django.apps import apps

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON 파싱 오류'}, status=400)

    app = data.get('app')
    model_name = data.get('model')
    field_name = data.get('field')
    pk = data.get('id')

    if not all([app, model_name, field_name, pk]):
        return JsonResponse({'error': '필수 파라미터가 없습니다.'}, status=400)

    try:
        model_class = apps.get_model(app, model_name)
        obj = model_class.objects.get(pk=pk)
    except LookupError:
        return JsonResponse({'error': '모델을 찾을 수 없습니다.'}, status=404)
    except model_class.DoesNotExist:
        return JsonResponse({'error': '객체를 찾을 수 없습니다.'}, status=404)

    result = convert_existing_image_to_webp(obj, field_name)

    return JsonResponse(result)


@require_POST
def convert_bulk_images(request):
    """일괄 이미지 WebP 변환 (선택 변환 또는 전체 변환)"""
    from django.apps import apps

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON 파싱 오류'}, status=400)

    app = data.get('app')
    model_name = data.get('model')
    field_name = data.get('field')
    limit = data.get('limit', 10)  # 한 번에 변환할 최대 개수
    selected_ids = data.get('ids')  # 특정 ID 목록 (선택 변환용)

    if not all([app, model_name, field_name]):
        return JsonResponse({'error': '필수 파라미터가 없습니다.'}, status=400)

    try:
        model_class = apps.get_model(app, model_name)
    except LookupError:
        return JsonResponse({'error': '모델을 찾을 수 없습니다.'}, status=404)

    converted = 0
    failed = 0
    total_old_size = 0
    total_new_size = 0
    results = []

    # 특정 ID가 지정된 경우 (선택 변환)
    if selected_ids and isinstance(selected_ids, list):
        queryset = model_class.objects.filter(pk__in=selected_ids)
        for obj in queryset:
            field_value = getattr(obj, field_name)
            if field_value and field_value.name and is_convertible(field_value.name):
                result = convert_existing_image_to_webp(obj, field_name)
                results.append({
                    'id': obj.pk,
                    **result
                })

                if result['success']:
                    converted += 1
                    total_old_size += result.get('old_size', 0)
                    total_new_size += result.get('new_size', 0)
                else:
                    failed += 1
    else:
        # 전체 변환 (limit 적용)
        queryset = model_class.objects.exclude(**{f"{field_name}__exact": ''})
        queryset = queryset.exclude(**{f"{field_name}__isnull": True})

        for obj in queryset.iterator():
            if converted >= limit:
                break

            field_value = getattr(obj, field_name)
            if field_value and field_value.name and is_convertible(field_value.name):
                result = convert_existing_image_to_webp(obj, field_name)
                results.append({
                    'id': obj.pk,
                    **result
                })

                if result['success']:
                    converted += 1
                    total_old_size += result.get('old_size', 0)
                    total_new_size += result.get('new_size', 0)
                else:
                    failed += 1

    return JsonResponse({
        'converted': converted,
        'failed': failed,
        'total_old_size': total_old_size,
        'total_new_size': total_new_size,
        'saved_size': total_old_size - total_new_size,
        'saved_display': _format_file_size(total_old_size - total_new_size),
        'results': results,
    })


def _format_file_size(size_bytes):
    """파일 크기를 읽기 좋은 형식으로 변환"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# 커스텀 Admin Site에 통계 뷰 추가
original_get_urls = admin.site.get_urls


def custom_get_urls():
    custom_urls = [
        path('statistics/', admin.site.admin_view(statistics_view), name='statistics'),
        path('image-management/', admin.site.admin_view(image_management_view), name='image_management'),
        path('api/images/list/', admin.site.admin_view(get_unconverted_images_list), name='api_images_list'),
        path('api/images/convert/', admin.site.admin_view(convert_single_image), name='api_images_convert'),
        path('api/images/convert-bulk/', admin.site.admin_view(convert_bulk_images), name='api_images_convert_bulk'),
    ]
    return custom_urls + original_get_urls()


# 커스텀 URL 적용
admin.site.get_urls = custom_get_urls
