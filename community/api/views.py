from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django.db.models import Q, F, Case, When, ExpressionWrapper, FloatField, Prefetch
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
import os
import uuid

from community.models import Post, Comment, Category, PostImage
from .serializers import (
    CommunityPostListSerializer, CommunityPostDetailSerializer,
    CommunityPostCreateSerializer, CommunityPostUpdateSerializer,
    CommentSerializer, CommentCreateSerializer, CommentUpdateSerializer,
    CategorySerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])
def post_list(request):
    """동호인톡 게시글 목록 API"""
    now = timezone.now()
    
    # 기본 필터: 동호인톡/동호인 리뷰 글, 삭제되지 않음, 임시저장 아님
    posts = Post.objects.filter(
        is_deleted=False,
        is_draft=False,
        source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS]
    ).filter(
        Q(published_at__lte=now) | Q(published_at__isnull=True)
    ).select_related("author", "category").prefetch_related(
        Prefetch("images", queryset=PostImage.objects.order_by("order")),
        "categories", "likes"
    )
    
    # 탭 필터링
    tab = request.GET.get('tab', '')
    category = request.GET.get('category', '')

    if tab:
        # Hot 탭
        if tab == 'hot':
            recent_30_days = now - timedelta(days=30)
            recent_7_days = now - timedelta(days=7)
            
            posts = posts.annotate(
                time_weight=Case(
                    When(published_at__gte=recent_7_days, then=1.5),
                    When(published_at__isnull=True, created_at__gte=recent_7_days, then=1.5),
                    default=1.0,
                    output_field=FloatField()
                ),
                hot_score=ExpressionWrapper(
                    (F('view_count') * 1 + F('like_count') * 2 + F('comment_count') * 3) * F('time_weight'),
                    output_field=FloatField()
                )
            ).filter(
                Q(published_at__gte=recent_30_days) | Q(published_at__isnull=True, created_at__gte=recent_30_days)
            ).order_by('-hot_score')
        # 리뷰 탭
        elif tab == 'reviews':
            reviews_category_slugs = ['community-racket', 'community-shoes', 'community-apparel', 
                                     'community-shuttlecock', 'community-protective', 'community-accessories']
            posts = posts.filter(
                Q(category__slug__in=reviews_category_slugs) | Q(categories__slug__in=reviews_category_slugs)
            ).distinct()
            
            if category:
                posts = posts.filter(Q(category__slug=category) | Q(categories__slug=category)).distinct()
        # 동적 탭 필터링
        else:
            current_category = Category.objects.filter(
                slug=tab,
                source=Category.Source.COMMUNITY,
                parent__isnull=True,
                is_active=True
            ).first()
            
            if current_category:
                category_slugs = [current_category.slug]
                child_categories = Category.objects.filter(parent=current_category, is_active=True)
                category_slugs.extend([cat.slug for cat in child_categories])
                
                posts = posts.filter(
                    Q(category__slug__in=category_slugs) | Q(categories__slug__in=category_slugs)
                ).distinct()
                
                if category:
                    posts = posts.filter(Q(category__slug=category) | Q(categories__slug=category)).distinct()
    
    # 카테고리 필터링 (탭이 없을 때)
    elif category:
        try:
            category_obj = Category.objects.get(slug=category, source=Category.Source.COMMUNITY, is_active=True)
            posts = posts.filter(Q(category=category_obj) | Q(categories=category_obj)).distinct()
        except Category.DoesNotExist:
            pass
    
    # 검색
    search = request.GET.get('search', '')
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | Q(content__icontains=search)
        )
    
    # 정렬 (Hot 탭이 아닐 때만)
    if tab != 'hot':
        posts = posts.order_by("-is_pinned", "-created_at")
    
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
    
    serializer = CommunityPostListSerializer(page_obj, many=True, context={'request': request})
    
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
def post_detail(request, slug):
    """동호인톡 게시글 상세 API"""
    now = timezone.now()
    
    # 기본 필터
    base_filter = Q(
        is_deleted=False,
        source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS],
        slug=slug
    )
    
    # 로그인 사용자가 작성자가 아니면 공개된 글만
    if not request.user.is_authenticated or not request.user.is_staff:
        base_filter &= Q(is_draft=False) & (Q(published_at__lte=now) | Q(published_at__isnull=True))
    
    post = get_object_or_404(
        Post.objects.filter(base_filter)
        .select_related("author", "category")
        .prefetch_related(
            Prefetch("images", queryset=PostImage.objects.order_by("order")),
            "categories", "likes"
        )
    )
    
    # 조회수 증가
    post.increase_view_count()
    
    serializer = CommunityPostDetailSerializer(post, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_create(request):
    """동호인톡 게시글 생성 API"""
    serializer = CommunityPostCreateSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        post = serializer.save()

        # request.FILES에서 직접 이미지 처리 (DRF ListField 병합 이슈 대응)
        if not post.images.exists():
            images = request.FILES.getlist('images')
            for idx, image in enumerate(images):
                PostImage.objects.create(post=post, image=image, order=idx)

        response_serializer = CommunityPostDetailSerializer(post, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def post_update(request, slug):
    """동호인톡 게시글 수정 API"""
    now = timezone.now()
    
    post = get_object_or_404(
        Post.objects.filter(
            slug=slug,
            source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS],
            is_deleted=False
        )
    )
    
    # 작성자만 수정 가능
    if post.author != request.user and not request.user.is_staff:
        return Response(
            {'error': '게시글을 수정할 권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    partial = request.method == 'PATCH'
    serializer = CommunityPostUpdateSerializer(
        post, data=request.data, partial=partial, context={'request': request}
    )
    
    if serializer.is_valid():
        post = serializer.save()

        # request.FILES에서 직접 이미지 처리 (DRF ListField 병합 이슈 대응)
        images = request.FILES.getlist('images')
        if images:
            post.images.all().delete()
            for idx, image in enumerate(images):
                PostImage.objects.create(post=post, image=image, order=idx)

        response_serializer = CommunityPostDetailSerializer(post, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def post_delete(request, slug):
    """동호인톡 게시글 삭제 API"""
    post = get_object_or_404(
        Post.objects.filter(
            slug=slug,
            source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS],
            is_deleted=False
        )
    )
    
    # 작성자만 삭제 가능
    if post.author != request.user and not request.user.is_staff:
        return Response(
            {'error': '게시글을 삭제할 권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    post.is_deleted = True
    post.save(update_fields=['is_deleted'])
    
    return Response({'message': '게시글이 삭제되었습니다.'}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_like(request, slug):
    """동호인톡 게시글 좋아요 API"""
    post = get_object_or_404(
        Post.objects.filter(
            slug=slug,
            source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS],
            is_deleted=False
        )
    )
    
    if post.likes.filter(id=request.user.id).exists():
        # 좋아요 취소
        post.likes.remove(request.user)
        post.update_like_count()
        return Response({'message': '좋아요가 취소되었습니다.', 'is_liked': False}, status=status.HTTP_200_OK)
    else:
        # 좋아요 추가
        post.likes.add(request.user)
        post.update_like_count()
        return Response({'message': '좋아요가 추가되었습니다.', 'is_liked': True}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def comment_list(request, slug):
    """댓글 목록 API"""
    post = get_object_or_404(
        Post.objects.filter(
            slug=slug,
            source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS],
            is_deleted=False
        )
    )
    
    # 삭제되지 않은 댓글만, 부모 댓글만 (대댓글 제외)
    comments = Comment.objects.filter(
        post=post,
        is_deleted=False,
        parent__isnull=True
    ).select_related('author').prefetch_related(
        'likes',
        Prefetch('replies', queryset=Comment.objects.filter(is_deleted=False).select_related('author').prefetch_related('likes'))
    ).order_by('created_at')
    
    # 각 댓글의 replies_list 속성 설정
    for comment in comments:
        comment.replies_list = comment.replies.filter(is_deleted=False).order_by('created_at')
    
    serializer = CommentSerializer(comments, many=True, context={'request': request})
    return Response({
        'count': comments.count(),
        'results': serializer.data
    }, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_create(request, slug):
    """댓글 생성 API"""
    post = get_object_or_404(
        Post.objects.filter(
            slug=slug,
            source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS],
            is_deleted=False
        )
    )
    
    serializer = CommentCreateSerializer(data=request.data, context={'request': request, 'post': post})
    
    if serializer.is_valid():
        comment = serializer.save()
        response_serializer = CommentSerializer(comment, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def comment_update(request, comment_id):
    """댓글 수정 API"""
    comment = get_object_or_404(
        Comment.objects.filter(is_deleted=False),
        id=comment_id
    )
    
    # 작성자만 수정 가능
    if comment.author != request.user and not request.user.is_staff:
        return Response(
            {'error': '댓글을 수정할 권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    partial = request.method == 'PATCH'
    serializer = CommentUpdateSerializer(comment, data=request.data, partial=partial)
    
    if serializer.is_valid():
        comment = serializer.save()
        response_serializer = CommentSerializer(comment, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def comment_delete(request, comment_id):
    """댓글 삭제 API"""
    comment = get_object_or_404(
        Comment.objects.filter(is_deleted=False),
        id=comment_id
    )
    
    # 작성자만 삭제 가능
    if comment.author != request.user and not request.user.is_staff:
        return Response(
            {'error': '댓글을 삭제할 권한이 없습니다.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    comment.is_deleted = True
    comment.save(update_fields=['is_deleted'])
    
    # 게시글 댓글 수 업데이트
    comment.post.update_comment_count()
    
    return Response({'message': '댓글이 삭제되었습니다.'}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def comment_like(request, comment_id):
    """댓글 좋아요 API"""
    comment = get_object_or_404(
        Comment.objects.filter(is_deleted=False),
        id=comment_id
    )
    
    if comment.likes.filter(id=request.user.id).exists():
        # 좋아요 취소
        comment.likes.remove(request.user)
        comment.update_like_count()
        return Response({'message': '좋아요가 취소되었습니다.', 'is_liked': False}, status=status.HTTP_200_OK)
    else:
        # 좋아요 추가
        comment.likes.add(request.user)
        comment.update_like_count()
        return Response({'message': '좋아요가 추가되었습니다.', 'is_liked': True}, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def image_upload(request):
    """이미지 업로드 API"""
    if 'image' not in request.FILES:
        return Response(
            {'error': '이미지 파일이 필요합니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    image_file = request.FILES['image']
    
    # 파일 크기 제한 (10MB)
    if image_file.size > 10 * 1024 * 1024:
        return Response(
            {'error': '이미지 크기는 10MB 이하여야 합니다.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 파일 확장자 검증
    allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp']
    file_extension = os.path.splitext(image_file.name)[1][1:].lower()
    if file_extension not in allowed_extensions:
        return Response(
            {'error': f'허용되지 않는 파일 형식입니다. ({", ".join(allowed_extensions)}만 가능)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # 파일 저장
    file_name = f"{uuid.uuid4().hex}.{file_extension}"
    file_path = f"community/post_images/{timezone.now().strftime('%Y/%m/%d')}/{file_name}"
    
    from django.core.files.storage import default_storage
    saved_path = default_storage.save(file_path, image_file)
    
    # URL 생성
    request_url = request.build_absolute_uri(default_storage.url(saved_path))
    
    return Response({
        'url': request_url,
        'message': '이미지가 업로드되었습니다.'
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def category_list(request):
    """카테고리 목록 API"""
    categories = Category.objects.filter(
        source=Category.Source.COMMUNITY,
        is_active=True
    ).order_by('display_order', 'name')
    
    serializer = CategorySerializer(categories, many=True)
    return Response({
        'categories': serializer.data
    }, status=status.HTTP_200_OK)
