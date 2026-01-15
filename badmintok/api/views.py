from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Q, F, Case, When, ExpressionWrapper, FloatField, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import timedelta
from django.core.paginator import Paginator

from badmintok.models import BadmintokBanner, Notice
from community.models import Post, Category
from badmintok.api.serializers import (
    BannerSerializer, NoticeListSerializer, NoticeSerializer,
    PostListSerializer, PostDetailSerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])
def home(request):
    """홈 페이지 API (최신 게시물 5개)"""
    now = timezone.now()
    latest_posts = Post.objects.filter(
        source=Post.Source.BADMINTOK,
        is_deleted=False,
        is_draft=False,
        published_at__lte=now
    ).select_related('author', 'category').prefetch_related('images').order_by('-created_at')[:5]
    
    serializer = PostListSerializer(latest_posts, many=True, context={'request': request})
    return Response({
        'latest_posts': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def post_list(request):
    """배드민톡 게시글 목록 API"""
    now = timezone.now()
    
    # 기본 필터: 배드민톡 글, 삭제되지 않음, 임시저장 아님
    posts = Post.objects.filter(
        is_deleted=False,
        is_draft=False,
        source=Post.Source.BADMINTOK
    ).filter(
        Q(published_at__lte=now) | Q(published_at__isnull=True)
    ).select_related("author", "category").prefetch_related("images", "categories")
    
    # 탭 필터링
    tab = request.GET.get('tab', '')
    category = request.GET.get('category', '')

    if tab:
        # NEW 탭
        if tab == 'new':
            # 모든 배드민톡 글 표시 (카테고리 필터링 없음)
            pass
        # 뉴스 탭
        elif tab == 'news':
            news_category_slugs = ['tournament', 'player', 'equipment', 'community']
            posts = posts.filter(
                Q(category__slug__in=news_category_slugs) | Q(categories__slug__in=news_category_slugs)
            ).distinct()
            
            if category:
                posts = posts.filter(Q(category__slug=category) | Q(categories__slug=category)).distinct()
        # 리뷰 탭
        elif tab == 'reviews':
            reviews_category_slugs = ['racket', 'shoes', 'apparel', 'shuttlecock', 'protective', 'accessories']
            posts = posts.filter(
                Q(category__slug__in=reviews_category_slugs) | Q(categories__slug__in=reviews_category_slugs)
            ).distinct()
            
            if category:
                posts = posts.filter(Q(category__slug=category) | Q(categories__slug=category)).distinct()
        # 브랜드관 탭
        elif tab == 'brand':
            brand_category_slugs = ['yonex', 'lining', 'victor', 'mizuno', 'technist', 'strokus', 'redsun', 'trion', 'tricore', 'apacs']
            posts = posts.filter(
                Q(category__slug__in=brand_category_slugs) | Q(categories__slug__in=brand_category_slugs)
            ).distinct()
            
            if category:
                posts = posts.filter(Q(category__slug=category) | Q(categories__slug=category)).distinct()
        # 기타 탭
        else:
            current_tab = Category.objects.filter(
                slug=tab,
                source=Category.Source.BADMINTOK,
                parent__isnull=True,
                is_active=True
            ).first()
            
            if current_tab:
                category_slugs = [current_tab.slug]
                child_categories = Category.objects.filter(parent=current_tab, is_active=True)
                category_slugs.extend([cat.slug for cat in child_categories])
                
                posts = posts.filter(
                    Q(category__slug__in=category_slugs) | Q(categories__slug__in=category_slugs)
                ).distinct()
                
                if category:
                    posts = posts.filter(Q(category__slug=category) | Q(categories__slug=category)).distinct()
    
    # 검색
    search = request.GET.get('search', '')
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | Q(content__icontains=search)
        )
    
    # 정렬
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
    
    serializer = PostListSerializer(page_obj, many=True, context={'request': request})
    
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
    """배드민톡 게시글 상세 API"""
    now = timezone.now()
    
    # 기본 필터: 삭제되지 않은 배드민톡 글
    base_filter = Q(is_deleted=False, source=Post.Source.BADMINTOK)
    
    # 로그인 사용자가 작성자가 아니면 공개된 글만
    if not request.user.is_authenticated or not request.user.is_staff:
        base_filter &= Q(is_draft=False, published_at__lte=now)
    
    post = get_object_or_404(
        Post.objects.filter(base_filter)
        .select_related("author", "category")
        .prefetch_related("images", "likes", "categories"),
        slug=slug
    )
    
    # 조회수 증가 (API에서는 단순 증가, 세션 체크 없음)
    post.increase_view_count()
    
    serializer = PostDetailSerializer(post, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def hot_posts(request):
    """인기 게시글 API (Hot 글 - 최근 30일 내)"""
    now = timezone.now()
    recent_30_days = now - timedelta(days=30)
    recent_7_days = now - timedelta(days=7)
    
    hot_posts_qs = Post.objects.filter(
        is_deleted=False,
        is_draft=False,
        source=Post.Source.BADMINTOK
    ).filter(
        Q(published_at__lte=now) | Q(published_at__isnull=True)
    ).filter(
        Q(published_at__gte=recent_30_days) | Q(published_at__isnull=True, created_at__gte=recent_30_days)
    ).select_related("author", "category").prefetch_related("categories").annotate(
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
    ).order_by('-hot_score')[:10]
    
    serializer = PostListSerializer(hot_posts_qs, many=True, context={'request': request})
    return Response({
        'hot_posts': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def banner_list(request):
    """배너 목록 API"""
    banners = BadmintokBanner.objects.filter(is_active=True).order_by('display_order', 'id')
    serializer = BannerSerializer(banners, many=True, context={'request': request})
    return Response({
        'banners': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def notice_list(request):
    """공지사항 목록 API"""
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
    
    notices = Notice.objects.all().select_related('author').order_by("-is_pinned", "-created_at")
    paginator = Paginator(notices, page_size)
    page_obj = paginator.get_page(page_number)
    
    serializer = NoticeListSerializer(page_obj, many=True, context={'request': request})
    
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
def notice_detail(request, notice_id):
    """공지사항 상세 API"""
    notice = get_object_or_404(Notice.objects.select_related('author'), id=notice_id)
    notice.increase_view_count()
    
    serializer = NoticeSerializer(notice, context={'request': request})
    return Response(serializer.data, status=status.HTTP_200_OK)

