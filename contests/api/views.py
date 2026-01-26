from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from datetime import date, timedelta

from contests.models import Contest, ContestCategory, ContestSchedule, ContestImage
from .serializers import (
    ContestListSerializer, ContestDetailSerializer,
    ContestCategorySerializer
)


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
            Q(event_division__icontains=search)
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
