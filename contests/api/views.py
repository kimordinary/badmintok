from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes, parser_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.throttling import UserRateThrottle
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from datetime import date, timedelta

from contests.models import Contest, ContestCategory, ContestSchedule, ContestImage, ContestPrize
from .serializers import (
    ContestListSerializer, ContestDetailSerializer,
    ContestCategorySerializer,
    ContestWriteSerializer, ContestImageWriteSerializer,
    ContestScheduleWriteSerializer, ContestPrizeWriteSerializer,
)


class ContestWriteThrottle(UserRateThrottle):
    """업로더 전용 throttle (시간당 100 요청)"""
    scope = 'contest_write'


@api_view(['GET'])
@permission_classes([AllowAny])
def contest_list(request):
    """대회 목록 API"""
    # 기본 쿼리셋
    contests = Contest.objects.all().select_related(
        'category', 'sponsor'
    ).prefetch_related(
        Prefetch('images', queryset=ContestImage.objects.order_by('order')),
        Prefetch('schedules', queryset=ContestSchedule.objects.order_by('date')),
        'likes'
    )

    # 필터링
    # 분류 필터
    category = request.GET.get('category', '')
    if category:
        try:
            category_obj = ContestCategory.objects.get(name=category)
            contests = contests.filter(category=category_obj)
        except ContestCategory.DoesNotExist:
            pass

    # 지역 필터
    region = request.GET.get('region', '')
    if region:
        contests = contests.filter(region=region)

    # 승급 대회 필터
    is_qualifying = request.GET.get('is_qualifying', '')
    if is_qualifying in ['true', 'True', '1']:
        contests = contests.filter(is_qualifying=True)
    elif is_qualifying in ['false', 'False', '0']:
        contests = contests.filter(is_qualifying=False)

    # 검색
    search = request.GET.get('search', '')
    if search:
        contests = contests.filter(
            Q(title__icontains=search) |
            Q(region_detail__icontains=search) |
            Q(competition_type__icontains=search)
        )

    # 정렬
    order = request.GET.get('order', 'upcoming')
    if order == 'popular':
        # 인기순: 좋아요 많은 순
        contests = contests.order_by('-view_count', 'schedule_start')
    elif order == 'recent':
        # 최신순: 등록일 기준
        contests = contests.order_by('-created_at')
    else:
        # upcoming (기본값): 대회 시작일 기준
        contests = contests.order_by('schedule_start', '-created_at')

    # 월별 필터 (예: schedule_month=2026-04)
    schedule_month = request.GET.get('schedule_month', '')
    if schedule_month:
        try:
            parts = schedule_month.split('-')
            y, m = int(parts[0]), int(parts[1])
            month_start = date(y, m, 1)
            if m == 12:
                month_end = date(y + 1, 1, 1)
            else:
                month_end = date(y, m + 1, 1)
            # 해당 월에 걸치는 대회 (시작일이 해당 월이거나, 기간이 해당 월을 포함)
            contests = contests.filter(
                schedule_start__lt=month_end,
            ).filter(
                Q(schedule_end__gte=month_start) |
                Q(schedule_end__isnull=True, schedule_start__gte=month_start)
            )
        except (ValueError, IndexError):
            pass

    # 기간 필터
    period = request.GET.get('period', '')
    today = date.today()
    if period == 'ongoing':
        # 진행 중인 대회
        contests = contests.filter(
            schedule_start__lte=today,
            schedule_end__gte=today
        )
    elif period == 'upcoming':
        # 예정된 대회 (앞으로 30일 이내)
        end_date = today + timedelta(days=30)
        contests = contests.filter(
            schedule_start__gt=today,
            schedule_start__lte=end_date
        )
    elif period == 'past':
        # 지난 대회
        contests = contests.filter(
            Q(schedule_end__lt=today) |
            Q(schedule_end__isnull=True, schedule_start__lt=today)
        )

    # 종료된 대회 기본 숨김 (include_ended=true 시 전체 반환)
    # period=past로 과거 대회를 명시적으로 요청한 경우엔 이 필터 건너뜀
    include_ended = request.GET.get('include_ended', '').lower() == 'true'
    if not include_ended and period != 'past':
        contests = contests.filter(
            Q(schedule_end__gte=today) |
            Q(schedule_end__isnull=True, schedule_start__gte=today)
        )

    # 페이지네이션
    page_number = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 10)
    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        if page_size < 1:
            page_size = 10
    except (ValueError, TypeError):
        page_size = 10

    paginator = Paginator(contests, page_size)
    page_obj = paginator.get_page(page_number)

    serializer = ContestListSerializer(page_obj, many=True, context={'request': request})

    return Response({
        'count': paginator.count,
        'page_size': page_size,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'results': serializer.data,
        'next': page_obj.next_page_number() if page_obj.has_next() else None,
        'previous': page_obj.previous_page_number() if page_obj.has_previous() else None,
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def contest_detail(request, slug):
    """대회 상세 API"""
    contest = get_object_or_404(
        Contest.objects.select_related('category', 'sponsor').prefetch_related(
            Prefetch('images', queryset=ContestImage.objects.order_by('order')),
            Prefetch('schedules', queryset=ContestSchedule.objects.order_by('date')),
            'prizes',
            'likes'
        ),
        slug=slug
    )

    # 조회수 증가
    contest.view_count += 1
    contest.save(update_fields=['view_count'])

    serializer = ContestDetailSerializer(contest, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def contest_like(request, slug):
    """대회 좋아요 API"""
    contest = get_object_or_404(Contest, slug=slug)

    if contest.likes.filter(id=request.user.id).exists():
        # 좋아요 취소
        contest.likes.remove(request.user)
        return Response({'message': '좋아요가 취소되었습니다.', 'is_liked': False}, status=status.HTTP_200_OK)
    else:
        # 좋아요 추가
        contest.likes.add(request.user)
        return Response({'message': '좋아요가 추가되었습니다.', 'is_liked': True}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    """대회 분류 목록 API"""
    categories = ContestCategory.objects.all().order_by('name')
    serializer = ContestCategorySerializer(categories, many=True)
    return Response({
        'categories': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def hot_contests(request):
    """인기 대회 TOP 10 API"""
    today = date.today()
    end_date = today + timedelta(days=60)

    contests = Contest.objects.filter(
        schedule_start__gte=today,
        schedule_start__lte=end_date
    ).select_related(
        'category', 'sponsor'
    ).prefetch_related(
        Prefetch('images', queryset=ContestImage.objects.order_by('order')),
        'likes'
    ).order_by('-view_count', 'schedule_start')[:10]

    serializer = ContestListSerializer(contests, many=True, context={'request': request})
    return Response({
        'results': serializer.data
    }, status=status.HTTP_200_OK)


# ======================================================================
# 업로더 API (IsAdminUser + throttle)
# ======================================================================


@api_view(['POST'])
@permission_classes([IsAdminUser])
@throttle_classes([ContestWriteThrottle])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def contest_create(request):
    """대회 생성"""
    serializer = ContestWriteSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    contest = serializer.save()
    return Response(
        {
            'id': contest.id,
            'slug': contest.slug,
            'is_test': contest.is_test,
            'url': request.build_absolute_uri(f'/badminton-tournament/{contest.slug}/'),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAdminUser])
@throttle_classes([ContestWriteThrottle])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def contest_update(request, slug):
    """대회 수정 (보완 병합)"""
    contest = get_object_or_404(Contest, slug=slug)
    partial = request.method == 'PATCH'
    serializer = ContestWriteSerializer(contest, data=request.data, partial=partial, context={'request': request})
    serializer.is_valid(raise_exception=True)
    contest = serializer.save()
    return Response(
        {'id': contest.id, 'slug': contest.slug},
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([IsAdminUser])
@throttle_classes([ContestWriteThrottle])
@parser_classes([MultiPartParser, FormParser])
def contest_image_upload(request, slug):
    """대회 이미지 1장 업로드 (여러 번 호출하여 다중 업로드)"""
    contest = get_object_or_404(Contest, slug=slug)
    data = request.data.copy()
    serializer = ContestImageWriteSerializer(data=data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    image = serializer.save(contest=contest)
    return Response(
        ContestImageWriteSerializer(image, context={'request': request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
@throttle_classes([ContestWriteThrottle])
@parser_classes([MultiPartParser, FormParser])
def contest_pdf_upload(request, slug):
    """대회 요강 PDF 업로드"""
    contest = get_object_or_404(Contest, slug=slug)
    pdf_file = request.data.get('pdf_file')
    if not pdf_file:
        return Response({'error': 'pdf_file 필드가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
    contest.pdf_file = pdf_file
    contest.save(update_fields=['pdf_file', 'updated_at'])
    pdf_url = request.build_absolute_uri(contest.pdf_file.url) if contest.pdf_file else None
    return Response({'slug': contest.slug, 'pdf_url': pdf_url}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminUser])
@throttle_classes([ContestWriteThrottle])
def contest_schedule_create(request, slug):
    """대회 경기 일정 생성 (1건)"""
    contest = get_object_or_404(Contest, slug=slug)
    serializer = ContestScheduleWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    schedule = serializer.save(contest=contest)
    return Response(ContestScheduleWriteSerializer(schedule).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAdminUser])
@throttle_classes([ContestWriteThrottle])
def contest_prize_create(request, slug):
    """대회 조별 입상상품 생성 (1건)"""
    contest = get_object_or_404(Contest, slug=slug)
    serializer = ContestPrizeWriteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    prize = serializer.save(contest=contest)
    return Response(ContestPrizeWriteSerializer(prize).data, status=status.HTTP_201_CREATED)
