from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Prefetch, Count
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator

from band.models import (
    Band, BandMember, BandPost, BandPostImage,
    BandSchedule, BandScheduleImage, BandScheduleApplication, BandBookmark
)
from .serializers import (
    BandListSerializer, BandDetailSerializer,
    BandPostListSerializer, BandPostDetailSerializer,
    BandScheduleListSerializer, BandScheduleDetailSerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])
def band_list(request):
    """밴드 목록 API"""
    # 기본 쿼리셋: 승인된 공개 밴드만
    bands = Band.objects.filter(
        is_approved=True,
        is_public=True,
        deletion_requested=False
    ).select_related('created_by').prefetch_related('members', 'bookmarks', 'posts')

    # 필터링
    # 유형 필터
    band_type = request.GET.get('band_type', '')
    if band_type:
        bands = bands.filter(band_type=band_type)

    # 지역 필터
    region = request.GET.get('region', '')
    if region:
        bands = bands.filter(region=region)

    # 검색
    search = request.GET.get('search', '')
    if search:
        bands = bands.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(detailed_description__icontains=search)
        )

    # 정렬
    order = request.GET.get('order', 'recent')
    if order == 'popular':
        # 인기순: 멤버 수 기준
        bands = bands.annotate(member_count_annotated=Count('members')).order_by('-member_count_annotated', '-created_at')
    elif order == 'name':
        # 이름순
        bands = bands.order_by('name')
    else:
        # recent (기본값): 최신순
        bands = bands.order_by('-created_at')

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

    paginator = Paginator(bands, page_size)
    page_obj = paginator.get_page(page_number)

    serializer = BandListSerializer(page_obj, many=True, context={'request': request})

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
def band_detail(request, band_id):
    """밴드 상세 API"""
    band = get_object_or_404(
        Band.objects.filter(
            is_approved=True,
            is_public=True,
            deletion_requested=False
        ).select_related('created_by').prefetch_related('members', 'bookmarks', 'posts'),
        id=band_id
    )

    serializer = BandDetailSerializer(band, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_bookmark(request, band_id):
    """밴드 북마크 API"""
    band = get_object_or_404(Band, id=band_id)

    bookmark = BandBookmark.objects.filter(band=band, user=request.user).first()
    if bookmark:
        # 북마크 취소
        bookmark.delete()
        return Response({
            'message': '북마크가 취소되었습니다.',
            'is_bookmarked': False
        }, status=status.HTTP_200_OK)
    else:
        # 북마크 추가
        BandBookmark.objects.create(band=band, user=request.user)
        return Response({
            'message': '북마크가 추가되었습니다.',
            'is_bookmarked': True
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def band_post_list(request, band_id):
    """밴드 게시글 목록 API"""
    band = get_object_or_404(Band, id=band_id)

    posts = BandPost.objects.filter(
        band=band
    ).select_related('author', 'band').prefetch_related(
        Prefetch('images', queryset=BandPostImage.objects.order_by('order_index'))
    ).order_by('-is_pinned', '-is_notice', '-created_at')

    # 게시글 유형 필터
    post_type = request.GET.get('post_type', '')
    if post_type:
        posts = posts.filter(post_type=post_type)

    # 검색
    search = request.GET.get('search', '')
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | Q(content__icontains=search)
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

    paginator = Paginator(posts, page_size)
    page_obj = paginator.get_page(page_number)

    serializer = BandPostListSerializer(page_obj, many=True, context={'request': request})

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
def band_post_detail(request, band_id, post_id):
    """밴드 게시글 상세 API"""
    post = get_object_or_404(
        BandPost.objects.filter(band_id=band_id).select_related('author', 'band').prefetch_related(
            Prefetch('images', queryset=BandPostImage.objects.order_by('order_index'))
        ),
        id=post_id
    )

    # 조회수 증가
    post.view_count += 1
    post.save(update_fields=['view_count'])

    serializer = BandPostDetailSerializer(post, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def band_schedule_list(request, band_id):
    """밴드 일정 목록 API"""
    band = get_object_or_404(Band, id=band_id)

    schedules = BandSchedule.objects.filter(
        band=band
    ).select_related('band', 'created_by').prefetch_related(
        Prefetch('images', queryset=BandScheduleImage.objects.order_by('order_index')),
        'applications'
    ).order_by('start_datetime')

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

    paginator = Paginator(schedules, page_size)
    page_obj = paginator.get_page(page_number)

    serializer = BandScheduleListSerializer(page_obj, many=True, context={'request': request})

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
def band_schedule_detail(request, band_id, schedule_id):
    """밴드 일정 상세 API"""
    schedule = get_object_or_404(
        BandSchedule.objects.filter(band_id=band_id).select_related('band', 'created_by').prefetch_related(
            Prefetch('images', queryset=BandScheduleImage.objects.order_by('order_index')),
            'applications'
        ),
        id=schedule_id
    )

    serializer = BandScheduleDetailSerializer(schedule, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def hot_bands(request):
    """인기 밴드 TOP 10 API"""
    bands = Band.objects.filter(
        is_approved=True,
        is_public=True,
        deletion_requested=False
    ).select_related('created_by').prefetch_related('members', 'bookmarks', 'posts').annotate(
        member_count_annotated=Count('members')
    ).order_by('-member_count_annotated', '-created_at')[:10]

    serializer = BandListSerializer(bands, many=True, context={'request': request})
    return Response({
        'results': serializer.data
    }, status=status.HTTP_200_OK)
