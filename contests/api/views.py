from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import date

from contests.models import Contest, ContestCategory, Sponsor
from .serializers import (
    ContestListSerializer, ContestDetailSerializer,
    ContestCategorySerializer, SponsorSerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])
def contest_list(request):
    """대회 목록 API"""
    contests = Contest.objects.all().select_related('category', 'sponsor').prefetch_related('images', 'likes')
    
    # 카테고리 필터링
    category = request.GET.get('category', '')
    if category:
        try:
            category_id = int(category)
            contests = contests.filter(category_id=category_id)
        except (ValueError, TypeError):
            pass
    
    # 검색
    search = request.GET.get('search', '')
    if search:
        contests = contests.filter(
            Q(title__icontains=search) | Q(region_detail__icontains=search)
        )
    
    # 승급/비승급 필터링
    qualifying_list = request.GET.getlist('qualifying')
    if qualifying_list:
        if len(qualifying_list) == 1:
            if 'true' in qualifying_list:
                contests = contests.filter(is_qualifying=True)
            elif 'false' in qualifying_list:
                contests = contests.filter(is_qualifying=False)
    
    # 스폰서 필터링
    sponsor_list = request.GET.getlist('sponsor')
    if sponsor_list:
        sponsor_ids = []
        for sponsor_value in sponsor_list:
            try:
                sponsor_id = int(sponsor_value)
                sponsor_ids.append(sponsor_id)
            except (ValueError, TypeError):
                try:
                    sponsor_obj = Sponsor.objects.get(name=sponsor_value)
                    sponsor_ids.append(sponsor_obj.id)
                except Sponsor.DoesNotExist:
                    pass
        if sponsor_ids:
            contests = contests.filter(sponsor_id__in=sponsor_ids)
    
    # 지역 필터링
    region = request.GET.get('region', '')
    if region:
        contests = contests.filter(region=region)
    
    # 날짜 필터링 (시작일 기준)
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        try:
            date_from_obj = date.fromisoformat(date_from)
            contests = contests.filter(schedule_start__gte=date_from_obj)
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            date_to_obj = date.fromisoformat(date_to)
            contests = contests.filter(schedule_start__lte=date_to_obj)
        except (ValueError, TypeError):
            pass
    
    # 정렬
    ordering = request.GET.get('ordering', '-schedule_start')
    if ordering:
        # 보안을 위해 허용된 필드만 정렬 가능
        allowed_orderings = [
            'schedule_start', '-schedule_start',
            'created_at', '-created_at',
            'registration_start', '-registration_start'
        ]
        if ordering in allowed_orderings:
            contests = contests.order_by(ordering)
        else:
            contests = contests.order_by('-schedule_start')
    else:
        contests = contests.order_by('-schedule_start')
    
    # 페이지네이션
    page_number = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 20)
    try:
        page_size = int(page_size)
        if page_size > 100:
            page_size = 100
        if page_size < 1:
            page_size = 20
    except (ValueError, TypeError):
        page_size = 20
    
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
            'schedules', 'images', 'likes'
        ),
        slug=slug
    )
    
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
def sponsor_list(request):
    """스폰서 목록 API"""
    sponsors = Sponsor.objects.all().order_by('name')
    
    serializer = SponsorSerializer(sponsors, many=True)
    return Response({
        'sponsors': serializer.data
    }, status=status.HTTP_200_OK)
