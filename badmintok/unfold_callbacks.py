"""Unfold Admin 콜백 함수"""

from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def environment_callback(request):
    """환경 표시 콜백"""
    if settings.DEBUG:
        return ["개발", "warning"]
    return ["운영", "success"]


def dashboard_callback(request, context):
    """대시보드 콜백 - 통계 및 최근 활동 데이터"""
    from django.db.models import Count, Q
    from accounts.models import User
    from contests.models import Contest
    from community.models import Post
    from band.models import Band
    from badmintok.models import VisitorLog

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today_start - timedelta(days=7)
    month_ago = today_start - timedelta(days=30)

    # 실제 사용자 필터 (봇 제외)
    real_user_filter = (
        Q(device_type__in=['desktop', 'mobile', 'tablet']) &
        (Q(user__is_staff=False) | Q(user__isnull=True))
    )

    # === 통계 데이터 ===

    # 사용자 통계
    total_users = User.objects.filter(is_active=True).count()
    new_users_today = User.objects.filter(date_joined__gte=today_start).count()
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()

    # 방문자 통계
    today_visitors = VisitorLog.objects.filter(
        visited_at__gte=today_start
    ).filter(real_user_filter).values('session_key').distinct().count()

    today_pageviews = VisitorLog.objects.filter(
        visited_at__gte=today_start
    ).filter(real_user_filter).count()

    # 대회 통계
    total_contests = Contest.objects.count()
    upcoming_contests = Contest.objects.filter(schedule_start__gte=now.date()).count()

    # 게시글 통계
    total_posts = Post.objects.filter(is_deleted=False, is_draft=False).count()
    new_posts_week = Post.objects.filter(
        is_deleted=False,
        is_draft=False,
        created_at__gte=week_ago
    ).count()

    # 밴드 통계
    total_bands = Band.objects.count()
    pending_bands = Band.objects.filter(
        band_type__in=['group', 'club'],
        is_approved=False
    ).count()

    # === 최근 활동 ===

    # 최근 가입한 사용자
    recent_users = User.objects.filter(
        is_active=True
    ).order_by('-date_joined')[:5].values('email', 'activity_name', 'date_joined')

    # 최근 등록된 대회
    recent_contests = Contest.objects.order_by('-created_at')[:5].values(
        'id', 'title', 'schedule_start', 'region', 'created_at'
    )

    # 최근 게시글
    recent_posts = Post.objects.filter(
        is_deleted=False,
        is_draft=False
    ).order_by('-created_at')[:5].values(
        'id', 'title', 'author__activity_name', 'source', 'created_at'
    )

    # 승인 대기 중인 밴드
    pending_bands_list = Band.objects.filter(
        band_type__in=['group', 'club'],
        is_approved=False
    ).order_by('-created_at')[:5].values(
        'id', 'name', 'band_type', 'created_by__activity_name', 'created_at'
    )

    # context에 데이터 추가
    context.update({
        # 통계 카드 데이터
        "stats": {
            "users": {
                "total": total_users,
                "today": new_users_today,
                "week": new_users_week,
            },
            "visitors": {
                "today": today_visitors,
                "pageviews": today_pageviews,
            },
            "contests": {
                "total": total_contests,
                "upcoming": upcoming_contests,
            },
            "posts": {
                "total": total_posts,
                "week": new_posts_week,
            },
            "bands": {
                "total": total_bands,
                "pending": pending_bands,
            },
        },
        # 최근 활동 데이터
        "recent": {
            "users": list(recent_users),
            "contests": list(recent_contests),
            "posts": list(recent_posts),
            "pending_bands": list(pending_bands_list),
        },
    })

    return context
