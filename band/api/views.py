from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Prefetch, Count, Case, When, F, Value, IntegerField
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from band.models import (
    Band, BandMember, BandPost, BandPostImage, BandComment,
    BandPostLike, BandCommentLike,
    BandVote, BandVoteOption, BandVoteChoice,
    BandSchedule, BandScheduleImage, BandScheduleApplication, BandBookmark
)
from .serializers import (
    BandListSerializer, BandDetailSerializer,
    BandPostListSerializer, BandPostDetailSerializer,
    BandScheduleListSerializer, BandScheduleDetailSerializer,
    BandCreateSerializer, BandUpdateSerializer,
    BandMemberSerializer, BandPostCreateSerializer, BandPostUpdateSerializer,
    BandCommentSerializer, BandCommentCreateSerializer,
    BandVoteSerializer, BandVoteOptionSerializer,
    BandScheduleCreateSerializer, BandScheduleApplicationSerializer,
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
    ).select_related('created_by', 'created_by__profile').prefetch_related('members', 'bookmarks', 'posts')

    # 필터링
    # 유형 필터 (band_type 필드)
    band_type = request.GET.get('band_type', '')
    if band_type:
        bands = bands.filter(band_type=band_type)

    # 카테고리/유형 필터 (band_type 기준)
    category_type = request.GET.get('type', '')
    if category_type:
        bands = bands.filter(band_type=category_type)

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
        ).select_related('created_by', 'created_by__profile').prefetch_related('members', 'bookmarks', 'posts'),
        id=band_id
    )

    serializer = BandDetailSerializer(band, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
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
    ).select_related('author', 'author__profile', 'band').prefetch_related(
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
        BandPost.objects.filter(band_id=band_id).select_related('author', 'author__profile', 'band').prefetch_related(
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
    ).select_related('band', 'created_by', 'created_by__profile').prefetch_related(
        Prefetch('images', queryset=BandScheduleImage.objects.order_by('order')),
        'applications'
    ).order_by('-start_datetime')

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
        BandSchedule.objects.filter(band_id=band_id).select_related('band', 'created_by', 'created_by__profile').prefetch_related(
            Prefetch('images', queryset=BandScheduleImage.objects.order_by('order')),
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
    ).select_related('created_by', 'created_by__profile').prefetch_related('members', 'bookmarks', 'posts').annotate(
        member_count_annotated=Count('members')
    ).order_by('-member_count_annotated', '-created_at')[:10]

    serializer = BandListSerializer(bands, many=True, context={'request': request})
    return Response({
        'results': serializer.data
    }, status=status.HTTP_200_OK)


# ========== 밴드 생성/수정 ==========

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_create(request):
    """밴드 생성 API"""
    serializer = BandCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    band_type = serializer.validated_data.get('band_type', 'group')

    # flash는 기존 group/club의 owner만 생성 가능
    if band_type == 'flash':
        is_owner = BandMember.objects.filter(
            user=request.user, role='owner', status='active',
            band__band_type__in=['group', 'club']
        ).exists()
        if not is_owner:
            return Response(
                {'error': '번개는 모임/동호회 방장만 생성할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        band = serializer.save(created_by=request.user, is_approved=True)
    else:
        # group/club은 관리자 승인 대기
        band = serializer.save(created_by=request.user, is_approved=False)

    # 생성자를 owner 멤버로 추가
    BandMember.objects.create(
        band=band, user=request.user, role='owner', status='active'
    )

    return Response({
        'message': '밴드가 생성되었습니다.' if band.is_approved else '밴드가 생성되었습니다. 관리자 승인 후 공개됩니다.',
        'id': band.id
    }, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def band_update(request, band_id):
    """밴드 수정 API"""
    band = get_object_or_404(Band, id=band_id)

    # owner/admin 권한 확인
    member = BandMember.objects.filter(
        band=band, user=request.user, role__in=['owner', 'admin'], status='active'
    ).first()
    if not member:
        return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = BandUpdateSerializer(band, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()
    return Response({'message': '밴드가 수정되었습니다.'}, status=status.HTTP_200_OK)


# ========== 가입/탈퇴 ==========

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_join(request, band_id):
    """밴드 가입 신청 API"""
    band = get_object_or_404(Band, id=band_id, is_approved=True, deletion_requested=False)

    # 이미 멤버인지 확인
    existing = BandMember.objects.filter(band=band, user=request.user).first()
    if existing:
        if existing.status == 'active':
            return Response({'error': '이미 멤버입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        if existing.status == 'pending':
            return Response({'error': '이미 가입 신청 중입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        if existing.status == 'banned':
            return Response({'error': '차단된 멤버입니다.'}, status=status.HTTP_403_FORBIDDEN)

    # 가입 승인 필요 여부에 따라 상태 결정
    if band.join_approval_required:
        member_status = 'pending'
        message = '가입 신청이 완료되었습니다. 승인을 기다려주세요.'
    else:
        member_status = 'active'
        message = '가입이 완료되었습니다.'

    BandMember.objects.create(
        band=band, user=request.user, role='member', status=member_status
    )

    return Response({'message': message}, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_leave(request, band_id):
    """밴드 탈퇴 API"""
    band = get_object_or_404(Band, id=band_id)

    member = BandMember.objects.filter(
        band=band, user=request.user, status='active'
    ).first()
    if not member:
        return Response({'error': '멤버가 아닙니다.'}, status=status.HTTP_400_BAD_REQUEST)

    if member.role == 'owner':
        return Response({'error': '방장은 탈퇴할 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    member.delete()
    return Response({'message': '탈퇴가 완료되었습니다.'}, status=status.HTTP_200_OK)


# ========== 멤버 관리 ==========

@api_view(['GET'])
@permission_classes([AllowAny])
def band_member_list(request, band_id):
    """밴드 멤버 목록 API"""
    band = get_object_or_404(Band, id=band_id)

    base_qs = BandMember.objects.filter(
        band=band
    ).select_related('user', 'user__profile').annotate(
        role_order=Case(
            When(role='owner', then=Value(0)),
            When(role='admin', then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    ).order_by('role_order', 'joined_at')

    active_members = base_qs.filter(status='active')
    pending_members = base_qs.filter(status='pending')

    active_serializer = BandMemberSerializer(active_members, many=True, context={'request': request})
    pending_serializer = BandMemberSerializer(pending_members, many=True, context={'request': request})

    return Response({
        'results': active_serializer.data,
        'active_members': active_serializer.data,
        'pending_members': pending_serializer.data,
    }, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_member_approve(request, band_id, member_id):
    """멤버 승인 API"""
    band = get_object_or_404(Band, id=band_id)

    # owner/admin 권한 확인
    manager = BandMember.objects.filter(
        band=band, user=request.user, role__in=['owner', 'admin'], status='active'
    ).first()
    if not manager:
        return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    member = get_object_or_404(BandMember, id=member_id, band=band, status='pending')
    member.status = 'active'
    member.save(update_fields=['status'])

    return Response({'message': '멤버가 승인되었습니다.'}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_member_reject(request, band_id, member_id):
    """멤버 거절 API"""
    band = get_object_or_404(Band, id=band_id)

    manager = BandMember.objects.filter(
        band=band, user=request.user, role__in=['owner', 'admin'], status='active'
    ).first()
    if not manager:
        return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    member = get_object_or_404(BandMember, id=member_id, band=band, status='pending')
    member.delete()

    return Response({'message': '가입이 거절되었습니다.'}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_member_kick(request, band_id, member_id):
    """멤버 추방 API"""
    band = get_object_or_404(Band, id=band_id)

    manager = BandMember.objects.filter(
        band=band, user=request.user, role__in=['owner', 'admin'], status='active'
    ).first()
    if not manager:
        return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    member = get_object_or_404(BandMember, id=member_id, band=band, status='active')

    # owner는 추방 불가
    if member.role == 'owner':
        return Response({'error': '방장은 추방할 수 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    # admin은 owner만 추방 가능
    if member.role == 'admin' and manager.role != 'owner':
        return Response({'error': '관리자는 방장만 추방할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

    member.status = 'banned'
    member.save(update_fields=['status'])

    return Response({'message': '멤버가 추방되었습니다.'}, status=status.HTTP_200_OK)


# ========== 게시글 CRUD ==========

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_post_create(request, band_id):
    """게시글 작성 API"""
    band = get_object_or_404(Band, id=band_id)

    serializer = BandPostCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    post_type = serializer.validated_data.get('post_type', 'general')

    # 멤버 확인 (FAQ/질문 게시글은 비멤버도 작성 가능)
    member = BandMember.objects.filter(
        band=band, user=request.user, status='active'
    ).first()
    if not member and post_type != 'question':
        return Response({'error': '멤버만 게시글을 작성할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

    # is_pinned, is_notice는 owner/admin만 설정 가능
    is_pinned = serializer.validated_data.get('is_pinned', False)
    is_notice = serializer.validated_data.get('is_notice', False)
    if (is_pinned or is_notice) and (not member or member.role not in ['owner', 'admin']):
        return Response(
            {'error': '고정/공지는 방장 또는 관리자만 설정할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )

    image_ids = serializer.validated_data.pop('image_ids', [])

    post = BandPost.objects.create(
        band=band,
        author=request.user,
        **serializer.validated_data
    )

    # 이미지 연결
    if image_ids:
        BandPostImage.objects.filter(
            id__in=image_ids, post__isnull=True
        ).update(post=post)

    detail_serializer = BandPostDetailSerializer(post, context={'request': request})
    return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def band_post_update(request, band_id, post_id):
    """게시글 수정 API"""
    post = get_object_or_404(BandPost, id=post_id, band_id=band_id)

    if post.author != request.user:
        return Response({'error': '작성자만 수정할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = BandPostUpdateSerializer(data=request.data, partial=True)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    image_ids = serializer.validated_data.pop('image_ids', None)

    for key, value in serializer.validated_data.items():
        setattr(post, key, value)
    post.save()

    # 이미지 업데이트
    if image_ids is not None:
        # 기존 이미지 연결 해제
        post.images.update(post=None)
        # 새 이미지 연결
        BandPostImage.objects.filter(
            id__in=image_ids
        ).update(post=post)

    detail_serializer = BandPostDetailSerializer(post, context={'request': request})
    return Response(detail_serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_post_delete(request, band_id, post_id):
    """게시글 삭제 API"""
    post = get_object_or_404(BandPost, id=post_id, band_id=band_id)

    # 작성자 또는 owner/admin만 삭제 가능
    if post.author != request.user:
        is_manager = BandMember.objects.filter(
            band_id=band_id, user=request.user,
            role__in=['owner', 'admin'], status='active'
        ).exists()
        if not is_manager:
            return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    post.delete()
    return Response({'message': '게시글이 삭제되었습니다.'}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_post_like(request, band_id, post_id):
    """게시글 좋아요 토글 API"""
    post = get_object_or_404(BandPost, id=post_id, band_id=band_id)

    like = BandPostLike.objects.filter(post=post, user=request.user).first()
    if like:
        like.delete()
        post.like_count = max(0, post.like_count - 1)
        post.save(update_fields=['like_count'])
        return Response({'message': '좋아요가 취소되었습니다.', 'is_liked': False, 'like_count': post.like_count})
    else:
        BandPostLike.objects.create(post=post, user=request.user)
        post.like_count += 1
        post.save(update_fields=['like_count'])
        return Response({'message': '좋아요를 눌렀습니다.', 'is_liked': True, 'like_count': post.like_count})


# ========== 댓글 ==========

@api_view(['GET'])
@permission_classes([AllowAny])
def band_comment_list(request, band_id, post_id):
    """댓글 목록 API"""
    post = get_object_or_404(BandPost, id=post_id, band_id=band_id)

    # 최상위 댓글만 조회 (대댓글은 serializer에서 nested)
    comments = BandComment.objects.filter(
        post=post, parent__isnull=True
    ).select_related('author', 'author__profile').prefetch_related(
        Prefetch('replies', queryset=BandComment.objects.select_related('author', 'author__profile'))
    ).order_by('created_at')

    serializer = BandCommentSerializer(comments, many=True, context={'request': request})
    return Response({'results': serializer.data}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_comment_create(request, band_id, post_id):
    """댓글 작성 API"""
    band = get_object_or_404(Band, id=band_id)
    post = get_object_or_404(BandPost, id=post_id, band=band)

    # 멤버 확인 (FAQ/질문 게시글은 비멤버도 댓글 작성 가능)
    if post.post_type != 'question':
        is_member = BandMember.objects.filter(
            band=band, user=request.user, status='active'
        ).exists()
        if not is_member:
            return Response({'error': '멤버만 댓글을 작성할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = BandCommentCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    parent_id = serializer.validated_data.get('parent_id')
    parent = None
    if parent_id:
        parent = get_object_or_404(BandComment, id=parent_id, post=post)

    comment = BandComment.objects.create(
        post=post,
        author=request.user,
        content=serializer.validated_data['content'],
        parent=parent
    )

    # 댓글 수 업데이트
    post.comment_count = post.comments.count()
    post.save(update_fields=['comment_count'])

    result_serializer = BandCommentSerializer(comment, context={'request': request})
    return Response(result_serializer.data, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_comment_update(request, comment_id):
    """댓글 수정 API"""
    comment = get_object_or_404(BandComment, id=comment_id)

    if comment.author != request.user:
        return Response({'error': '작성자만 수정할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

    content = request.data.get('content')
    if not content:
        return Response({'error': '내용을 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

    comment.content = content
    comment.save(update_fields=['content', 'updated_at'])

    serializer = BandCommentSerializer(comment, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_comment_delete(request, comment_id):
    """댓글 삭제 API"""
    comment = get_object_or_404(BandComment, id=comment_id)
    post = comment.post

    # FAQ(질문) 게시글 댓글은 모임장(owner)만 삭제 가능
    if post.post_type == 'question':
        is_owner = BandMember.objects.filter(
            band=post.band, user=request.user,
            role='owner', status='active'
        ).exists()
        if not is_owner:
            return Response({'error': 'FAQ 답변은 모임장만 삭제할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)
    else:
        # 일반 게시글: 작성자 또는 owner/admin만 삭제 가능
        if comment.author != request.user:
            is_manager = BandMember.objects.filter(
                band=post.band, user=request.user,
                role__in=['owner', 'admin'], status='active'
            ).exists()
            if not is_manager:
                return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    comment.delete()

    # 댓글 수 업데이트
    post.comment_count = post.comments.count()
    post.save(update_fields=['comment_count'])

    return Response({'message': '댓글이 삭제되었습니다.'}, status=status.HTTP_200_OK)


# ========== 투표 ==========

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_vote_create(request, band_id):
    """투표 게시글 생성 API"""
    band = get_object_or_404(Band, id=band_id)

    # owner/admin 권한 확인
    member = BandMember.objects.filter(
        band=band, user=request.user, role__in=['owner', 'admin'], status='active'
    ).first()
    if not member:
        return Response({'error': '방장 또는 관리자만 투표를 생성할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

    title = request.data.get('title', '')
    content = request.data.get('content', '')
    vote_title = request.data.get('vote_title', '')
    options = request.data.get('options', [])
    is_multiple_choice = request.data.get('is_multiple_choice', False)
    end_datetime = request.data.get('end_datetime')

    if not vote_title:
        return Response({'error': '투표 제목을 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(options) < 2:
        return Response({'error': '옵션을 2개 이상 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

    # 게시글 생성
    post = BandPost.objects.create(
        band=band,
        author=request.user,
        title=title or vote_title,
        content=content,
        post_type='vote'
    )

    # 투표 생성
    vote = BandVote.objects.create(
        post=post,
        title=vote_title,
        is_multiple_choice=is_multiple_choice,
        end_datetime=end_datetime
    )

    # 옵션 생성
    for idx, option_text in enumerate(options):
        BandVoteOption.objects.create(
            vote=vote,
            option_text=option_text,
            order_index=idx
        )

    detail_serializer = BandPostDetailSerializer(post, context={'request': request})
    return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_vote_participate(request, band_id, post_id):
    """투표 참여 API"""
    band = get_object_or_404(Band, id=band_id)
    post = get_object_or_404(BandPost, id=post_id, band=band, post_type='vote')

    # 멤버 확인
    is_member = BandMember.objects.filter(
        band=band, user=request.user, status='active'
    ).exists()
    if not is_member:
        return Response({'error': '멤버만 투표할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        vote = post.vote
    except BandVote.DoesNotExist:
        return Response({'error': '투표 정보가 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

    # 마감 확인
    if vote.end_datetime and vote.end_datetime < timezone.now():
        return Response({'error': '투표가 마감되었습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    option_ids = request.data.get('option_ids', [])
    if not option_ids:
        return Response({'error': '옵션을 선택해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

    if not vote.is_multiple_choice and len(option_ids) > 1:
        return Response({'error': '단일 선택 투표입니다.'}, status=status.HTTP_400_BAD_REQUEST)

    # 기존 선택 삭제
    old_choices = BandVoteChoice.objects.filter(vote=vote, user=request.user)
    old_option_ids = list(old_choices.values_list('option_id', flat=True))
    old_choices.delete()

    # 기존 옵션 vote_count 감소
    BandVoteOption.objects.filter(id__in=old_option_ids).update(
        vote_count=F('vote_count') - 1
    )

    # 새로운 선택 생성
    valid_options = BandVoteOption.objects.filter(vote=vote, id__in=option_ids)
    for option in valid_options:
        BandVoteChoice.objects.create(vote=vote, option=option, user=request.user)

    # 새 옵션 vote_count 증가
    valid_options.update(vote_count=F('vote_count') + 1)

    vote_serializer = BandVoteSerializer(vote, context={'request': request})
    return Response(vote_serializer.data, status=status.HTTP_200_OK)


# ========== 일정 ==========

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_schedule_create(request, band_id):
    """일정 생성 API"""
    band = get_object_or_404(Band, id=band_id)

    # owner/admin 권한 확인
    member = BandMember.objects.filter(
        band=band, user=request.user, role__in=['owner', 'admin'], status='active'
    ).first()
    if not member:
        return Response({'error': '방장 또는 관리자만 일정을 생성할 수 있습니다.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = BandScheduleCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    schedule = serializer.save(band=band, created_by=request.user)

    detail_serializer = BandScheduleDetailSerializer(schedule, context={'request': request})
    return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_schedule_apply(request, band_id, schedule_id):
    """일정 참가 신청 API"""
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band_id=band_id)

    # 이미 신청했는지 확인
    existing = schedule.applications.filter(user=request.user).first()
    if existing and existing.status in ['pending', 'approved']:
        return Response({'error': '이미 신청하셨습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    # 마감일 확인
    if schedule.application_deadline and schedule.application_deadline < timezone.now():
        return Response({'error': '신청 마감일이 지났습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    # 모집 마감 확인
    if schedule.is_closed:
        return Response({'error': '모집이 마감되었습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    # 정원 확인
    if schedule.max_participants and schedule.current_participants >= schedule.max_participants:
        return Response({'error': '참가 인원이 마감되었습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    notes = request.data.get('notes', '')

    # 승인 필요 여부에 따라 상태 결정
    if schedule.requires_approval:
        initial_status = 'pending'
        message = '참가 신청이 완료되었습니다. 승인을 기다려주세요.'
    else:
        initial_status = 'approved'
        message = '참가 신청이 완료되었습니다.'

    if existing and existing.status in ['rejected', 'cancelled']:
        # 기존 신청 재활용
        existing.status = initial_status
        existing.notes = notes
        existing.reviewed_at = timezone.now() if not schedule.requires_approval else None
        existing.reviewed_by = None
        existing.rejection_reason = ''
        existing.save()
    else:
        # 새 신청
        BandScheduleApplication.objects.create(
            schedule=schedule,
            user=request.user,
            status=initial_status,
            notes=notes
        )

    # 자동승인 시 참가 인원 증가
    if initial_status == 'approved':
        schedule.current_participants += 1
        schedule.save(update_fields=['current_participants'])

    return Response({'message': message}, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_schedule_cancel(request, band_id, schedule_id):
    """일정 참가 취소 API"""
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band_id=band_id)

    application = schedule.applications.filter(user=request.user).first()
    if not application:
        return Response({'error': '신청 내역이 없습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    if application.status not in ['pending', 'approved']:
        return Response({'error': '취소할 수 없는 상태입니다.'}, status=status.HTTP_400_BAD_REQUEST)

    was_approved = application.status == 'approved'
    application.status = 'cancelled'
    application.reviewed_at = timezone.now()
    application.save()

    # 승인 상태였다면 참가 인원 감소
    if was_approved:
        schedule.current_participants = max(0, schedule.current_participants - 1)
        schedule.save(update_fields=['current_participants'])

    return Response({'message': '참가 신청이 취소되었습니다.'}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_schedule_toggle_close(request, band_id, schedule_id):
    """일정 마감 토글 API"""
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band_id=band_id)

    # owner/admin 권한 확인
    member = BandMember.objects.filter(
        band_id=band_id, user=request.user,
        role__in=['owner', 'admin'], status='active'
    ).first()
    if not member:
        return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    schedule.is_closed = not schedule.is_closed
    schedule.save(update_fields=['is_closed'])

    message = '모집이 마감되었습니다.' if schedule.is_closed else '모집이 다시 열렸습니다.'
    return Response({
        'message': message,
        'is_closed': schedule.is_closed
    }, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_schedule_application_approve(request, band_id, schedule_id, application_id):
    """일정 신청 승인 API"""
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band_id=band_id)

    # owner/admin 권한 확인
    manager = BandMember.objects.filter(
        band_id=band_id, user=request.user,
        role__in=['owner', 'admin'], status='active'
    ).first()
    if not manager:
        return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    application = get_object_or_404(
        BandScheduleApplication, id=application_id, schedule=schedule, status='pending'
    )

    # 정원 확인
    if schedule.max_participants and schedule.current_participants >= schedule.max_participants:
        return Response({'error': '참가 인원이 마감되었습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    application.status = 'approved'
    application.reviewed_at = timezone.now()
    application.reviewed_by = request.user
    application.save(update_fields=['status', 'reviewed_at', 'reviewed_by'])

    # 참가 인원 증가
    schedule.current_participants += 1
    schedule.save(update_fields=['current_participants'])

    return Response({'message': '신청이 승인되었습니다.'}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_schedule_application_reject(request, band_id, schedule_id, application_id):
    """일정 신청 거절 API"""
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band_id=band_id)

    # owner/admin 권한 확인
    manager = BandMember.objects.filter(
        band_id=band_id, user=request.user,
        role__in=['owner', 'admin'], status='active'
    ).first()
    if not manager:
        return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    application = get_object_or_404(
        BandScheduleApplication, id=application_id, schedule=schedule, status='pending'
    )

    rejection_reason = request.data.get('rejection_reason', '')

    application.status = 'rejected'
    application.reviewed_at = timezone.now()
    application.reviewed_by = request.user
    application.rejection_reason = rejection_reason
    application.save(update_fields=['status', 'reviewed_at', 'reviewed_by', 'rejection_reason'])

    return Response({'message': '신청이 거절되었습니다.'}, status=status.HTTP_200_OK)


# ========== 댓글 좋아요 ==========

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_comment_like(request, comment_id):
    """댓글 좋아요 토글 API"""
    comment = get_object_or_404(BandComment, id=comment_id)

    like = BandCommentLike.objects.filter(comment=comment, user=request.user).first()
    if like:
        like.delete()
        comment.like_count = max(0, comment.like_count - 1)
        comment.save(update_fields=['like_count'])
        return Response({'message': '좋아요가 취소되었습니다.', 'is_liked': False, 'like_count': comment.like_count})
    else:
        BandCommentLike.objects.create(comment=comment, user=request.user)
        comment.like_count += 1
        comment.save(update_fields=['like_count'])
        return Response({'message': '좋아요를 눌렀습니다.', 'is_liked': True, 'like_count': comment.like_count})


# ========== 일정 수정/삭제 ==========

@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def band_schedule_update(request, band_id, schedule_id):
    """일정 수정 API"""
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band_id=band_id)

    # 생성자 또는 owner/admin만 수정 가능
    is_creator = schedule.created_by == request.user
    is_manager = BandMember.objects.filter(
        band_id=band_id, user=request.user,
        role__in=['owner', 'admin'], status='active'
    ).exists()
    if not is_creator and not is_manager:
        return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = BandScheduleCreateSerializer(schedule, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    serializer.save()

    detail_serializer = BandScheduleDetailSerializer(schedule, context={'request': request})
    return Response(detail_serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_schedule_delete(request, band_id, schedule_id):
    """일정 삭제 API"""
    schedule = get_object_or_404(BandSchedule, id=schedule_id, band_id=band_id)

    # 생성자 또는 owner/admin만 삭제 가능
    is_creator = schedule.created_by == request.user
    is_manager = BandMember.objects.filter(
        band_id=band_id, user=request.user,
        role__in=['owner', 'admin'], status='active'
    ).exists()
    if not is_creator and not is_manager:
        return Response({'error': '권한이 없습니다.'}, status=status.HTTP_403_FORBIDDEN)

    schedule.delete()
    return Response({'message': '일정이 삭제되었습니다.'}, status=status.HTTP_200_OK)
