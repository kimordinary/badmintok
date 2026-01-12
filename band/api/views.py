from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Count, Prefetch
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator

from band.models import Band, BandMember, BandPost, BandPostImage, BandComment, BandPostLike, BandCommentLike
from .serializers import (
    BandListSerializer, BandDetailSerializer, BandCreateSerializer, BandUpdateSerializer,
    BandPostListSerializer, BandPostDetailSerializer, BandPostCreateSerializer, BandPostUpdateSerializer,
    BandCommentSerializer, BandCommentCreateSerializer, BandCommentUpdateSerializer,
    BandMemberSerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])
def band_list(request):
    """밴드 목록 API"""
    band_type = request.GET.get('type', '')
    region = request.GET.get('region', '')
    search = request.GET.get('search', '')
    
    # 기본 필터: 공개된 밴드
    bands = Band.objects.filter(is_public=True)
    
    # 로그인한 사용자가 만든 밴드는 공개되지 않아도 보이도록
    if request.user.is_authenticated:
        bands = Band.objects.filter(
            Q(is_public=True) | Q(created_by=request.user)
        )
    
    # 타입 필터
    if band_type:
        bands = bands.filter(band_type=band_type)
    
    # 지역 필터
    if region and region != 'all':
        bands = bands.filter(region=region)
    
    # 검색
    if search:
        bands = bands.filter(Q(name__icontains=search) | Q(description__icontains=search))
    
    # 승인된 밴드만 (번개는 승인 없이도 표시)
    if band_type in ['group', 'club']:
        if request.user.is_authenticated:
            bands = bands.filter(Q(is_approved=True) | Q(created_by=request.user))
        else:
            bands = bands.filter(is_approved=True)
    
    bands = bands.select_related('created_by').prefetch_related('members').order_by('-created_at')
    
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
    # 공개된 밴드 또는 본인이 만든 밴드
    if request.user.is_authenticated:
        band = get_object_or_404(
            Band.objects.filter(Q(is_public=True) | Q(created_by=request.user)),
            id=band_id
        )
    else:
        band = get_object_or_404(Band.objects.filter(is_public=True), id=band_id)
    
    serializer = BandDetailSerializer(band, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_create(request):
    """밴드 생성 API"""
    serializer = BandCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        band = serializer.save()
        response_serializer = BandDetailSerializer(band, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def band_update(request, band_id):
    """밴드 수정 API"""
    band = get_object_or_404(Band, id=band_id)
    
    # 모임장 또는 관리자만 수정 가능
    member = band.members.filter(user=request.user).first()
    if not member or member.role not in [BandMember.Role.OWNER, BandMember.Role.ADMIN]:
        return Response(
            {'error': '밴드를 수정할 권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    partial = request.method == 'PATCH'
    serializer = BandUpdateSerializer(band, data=request.data, partial=partial, context={'request': request})
    
    if serializer.is_valid():
        band = serializer.save()
        response_serializer = BandDetailSerializer(band, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_join(request, band_id):
    """밴드 가입 API"""
    band = get_object_or_404(Band, id=band_id)
    
    # 이미 멤버인지 확인
    existing_member = band.members.filter(user=request.user).first()
    if existing_member:
        if existing_member.status == BandMember.Status.ACTIVE:
            return Response(
                {'error': '이미 가입한 밴드입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif existing_member.status == BandMember.Status.PENDING:
            return Response(
                {'error': '가입 승인 대기 중입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # 가입 승인 필요 여부 확인
    if band.join_approval_required:
        status_value = BandMember.Status.PENDING
    else:
        status_value = BandMember.Status.ACTIVE
    
    BandMember.objects.create(
        band=band,
        user=request.user,
        role=BandMember.Role.MEMBER,
        status=status_value
    )
    
    return Response({'message': '밴드 가입 신청이 완료되었습니다.'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_leave(request, band_id):
    """밴드 탈퇴 API"""
    band = get_object_or_404(Band, id=band_id)
    
    member = band.members.filter(user=request.user).first()
    if not member:
        return Response(
            {'error': '가입하지 않은 밴드입니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 모임장은 탈퇴 불가
    if member.role == BandMember.Role.OWNER:
        return Response(
            {'error': '모임장은 탈퇴할 수 없습니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    member.delete()
    
    return Response({'message': '밴드에서 탈퇴했습니다.'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def band_members(request, band_id):
    """밴드 멤버 목록 API"""
    band = get_object_or_404(Band, id=band_id)
    
    # 공개된 밴드 또는 본인이 멤버인 밴드만 조회 가능
    if not band.is_public:
        if not request.user.is_authenticated or not band.members.filter(user=request.user).exists():
            return Response(
                {'error': '멤버 목록을 조회할 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    members = band.members.filter(status=BandMember.Status.ACTIVE).select_related('user').order_by('-role', 'joined_at')
    
    serializer = BandMemberSerializer(members, many=True, context={'request': request})
    return Response({
        'count': members.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def band_post_list(request, band_id):
    """밴드 게시글 목록 API"""
    band = get_object_or_404(Band, id=band_id)
    
    # 공개된 밴드 또는 본인이 멤버인 밴드만 조회 가능
    if not band.is_public:
        if not request.user.is_authenticated or not band.members.filter(user=request.user, status=BandMember.Status.ACTIVE).exists():
            return Response(
                {'error': '게시글을 조회할 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    posts = BandPost.objects.filter(band=band).select_related('author').prefetch_related(
        Prefetch('images', queryset=BandPostImage.objects.order_by('order_index')),
        'likes'
    ).order_by('-is_pinned', '-is_notice', '-created_at')
    
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
    band = get_object_or_404(Band, id=band_id)
    
    # 공개된 밴드 또는 본인이 멤버인 밴드만 조회 가능
    if not band.is_public:
        if not request.user.is_authenticated or not band.members.filter(user=request.user, status=BandMember.Status.ACTIVE).exists():
            return Response(
                {'error': '게시글을 조회할 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    post = get_object_or_404(
        BandPost.objects.filter(band=band).select_related('author').prefetch_related(
            Prefetch('images', queryset=BandPostImage.objects.order_by('order_index')),
            'likes'
        ),
        id=post_id
    )
    
    # 조회수 증가
    post.view_count += 1
    post.save(update_fields=['view_count'])
    
    serializer = BandPostDetailSerializer(post, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_post_create(request, band_id):
    """밴드 게시글 생성 API"""
    band = get_object_or_404(Band, id=band_id)
    
    # 멤버만 게시글 작성 가능
    if not band.members.filter(user=request.user, status=BandMember.Status.ACTIVE).exists():
        return Response(
            {'error': '밴드 멤버만 게시글을 작성할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = BandPostCreateSerializer(data=request.data, context={'request': request, 'band': band})
    
    if serializer.is_valid():
        post = serializer.save()
        response_serializer = BandPostDetailSerializer(post, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def band_post_update(request, band_id, post_id):
    """밴드 게시글 수정 API"""
    band = get_object_or_404(Band, id=band_id)
    post = get_object_or_404(BandPost.objects.filter(band=band), id=post_id)
    
    # 작성자 또는 관리자만 수정 가능
    member = band.members.filter(user=request.user).first()
    if post.author != request.user and (not member or member.role not in [BandMember.Role.OWNER, BandMember.Role.ADMIN]):
        return Response(
            {'error': '게시글을 수정할 권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    partial = request.method == 'PATCH'
    serializer = BandPostUpdateSerializer(post, data=request.data, partial=partial)
    
    if serializer.is_valid():
        post = serializer.save()
        response_serializer = BandPostDetailSerializer(post, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def band_post_delete(request, band_id, post_id):
    """밴드 게시글 삭제 API"""
    band = get_object_or_404(Band, id=band_id)
    post = get_object_or_404(BandPost.objects.filter(band=band), id=post_id)
    
    # 작성자 또는 관리자만 삭제 가능
    member = band.members.filter(user=request.user).first()
    if post.author != request.user and (not member or member.role not in [BandMember.Role.OWNER, BandMember.Role.ADMIN]):
        return Response(
            {'error': '게시글을 삭제할 권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    post.delete()
    
    return Response({'message': '게시글이 삭제되었습니다.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_post_like(request, band_id, post_id):
    """밴드 게시글 좋아요 API"""
    band = get_object_or_404(Band, id=band_id)
    post = get_object_or_404(BandPost.objects.filter(band=band), id=post_id)
    
    like, created = BandPostLike.objects.get_or_create(post=post, user=request.user)
    
    if created:
        post.like_count += 1
        post.save(update_fields=['like_count'])
        return Response({'message': '좋아요가 추가되었습니다.', 'is_liked': True}, status=status.HTTP_200_OK)
    else:
        like.delete()
        post.like_count = max(0, post.like_count - 1)
        post.save(update_fields=['like_count'])
        return Response({'message': '좋아요가 취소되었습니다.', 'is_liked': False}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def band_comment_list(request, band_id, post_id):
    """밴드 댓글 목록 API"""
    band = get_object_or_404(Band, id=band_id)
    post = get_object_or_404(BandPost.objects.filter(band=band), id=post_id)
    
    # 공개된 밴드 또는 본인이 멤버인 밴드만 조회 가능
    if not band.is_public:
        if not request.user.is_authenticated or not band.members.filter(user=request.user, status=BandMember.Status.ACTIVE).exists():
            return Response(
                {'error': '댓글을 조회할 권한이 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    comments = BandComment.objects.filter(post=post, parent__isnull=True).select_related('author').prefetch_related(
        'likes',
        Prefetch('replies', queryset=BandComment.objects.select_related('author').prefetch_related('likes'))
    ).order_by('created_at')
    
    # 각 댓글의 replies_list 속성 설정
    for comment in comments:
        comment.replies_list = comment.replies.all().order_by('created_at')
    
    serializer = BandCommentSerializer(comments, many=True, context={'request': request})
    return Response({
        'count': comments.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_comment_create(request, band_id, post_id):
    """밴드 댓글 생성 API"""
    band = get_object_or_404(Band, id=band_id)
    post = get_object_or_404(BandPost.objects.filter(band=band), id=post_id)
    
    # 멤버만 댓글 작성 가능
    if not band.members.filter(user=request.user, status=BandMember.Status.ACTIVE).exists():
        return Response(
            {'error': '밴드 멤버만 댓글을 작성할 수 있습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = BandCommentCreateSerializer(data=request.data, context={'request': request, 'post': post})
    
    if serializer.is_valid():
        comment = serializer.save()
        # 댓글 수 업데이트
        post.comment_count = post.comments.count()
        post.save(update_fields=['comment_count'])
        
        response_serializer = BandCommentSerializer(comment, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def band_comment_update(request, comment_id):
    """밴드 댓글 수정 API"""
    comment = get_object_or_404(BandComment, id=comment_id)
    
    # 작성자만 수정 가능
    if comment.author != request.user:
        return Response(
            {'error': '댓글을 수정할 권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    partial = request.method == 'PATCH'
    serializer = BandCommentUpdateSerializer(comment, data=request.data, partial=partial)
    
    if serializer.is_valid():
        comment = serializer.save()
        response_serializer = BandCommentSerializer(comment, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def band_comment_delete(request, comment_id):
    """밴드 댓글 삭제 API"""
    comment = get_object_or_404(BandComment, id=comment_id)
    
    # 작성자 또는 관리자만 삭제 가능
    member = comment.post.band.members.filter(user=request.user).first()
    if comment.author != request.user and (not member or member.role not in [BandMember.Role.OWNER, BandMember.Role.ADMIN]):
        return Response(
            {'error': '댓글을 삭제할 권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    post = comment.post
    comment.delete()
    
    # 댓글 수 업데이트
    post.comment_count = post.comments.count()
    post.save(update_fields=['comment_count'])
    
    return Response({'message': '댓글이 삭제되었습니다.'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def band_comment_like(request, comment_id):
    """밴드 댓글 좋아요 API"""
    comment = get_object_or_404(BandComment, id=comment_id)
    
    like, created = BandCommentLike.objects.get_or_create(comment=comment, user=request.user)
    
    if created:
        comment.like_count += 1
        comment.save(update_fields=['like_count'])
        return Response({'message': '좋아요가 추가되었습니다.', 'is_liked': True}, status=status.HTTP_200_OK)
    else:
        like.delete()
        comment.like_count = max(0, comment.like_count - 1)
        comment.save(update_fields=['like_count'])
        return Response({'message': '좋아요가 취소되었습니다.', 'is_liked': False}, status=status.HTTP_200_OK)
