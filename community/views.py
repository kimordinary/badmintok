from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count, Q, Max, F, Case, When, ExpressionWrapper, FloatField
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
import logging
import os
import uuid

from .models import Category, Post, Comment, PostImage
from badmintok.models import BadmintokBanner, Notice

logger = logging.getLogger(__name__)


class PostListView(ListView):
    """게시판 목록 뷰"""
    model = Post
    template_name = "community/index.html"
    context_object_name = "posts"
    paginate_by = 10
    
    def get_queryset(self):
        from django.db.models import Prefetch
        from django.utils import timezone

        # 임시저장 제외, 예약발행(published_at이 현재 시간 이전인 것만) 필터링
        now = timezone.now()
        queryset = Post.objects.filter(
            is_deleted=False,
            is_draft=False,
            source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS]  # 커뮤니티와 동호인 리뷰 글 표시
        ).filter(
            Q(published_at__lte=now) | Q(published_at__isnull=True)  # published_at이 없거나 현재 시간 이전인 것
        ).select_related("author", "category").prefetch_related(
            Prefetch("images", queryset=PostImage.objects.order_by("order"))
        )
        
        # 탭 필터링 - 동적으로 처리
        active_tab = self.request.GET.get("tab", "")
        category = self.request.GET.get("category", "")

        # Hot 탭인 경우 인기글만 표시
        if active_tab == "hot":
            # Hot 글 - 최근 30일 내 글 + 복합 점수 + 시간 가중치
            recent_30_days = now - timedelta(days=30)
            recent_7_days = now - timedelta(days=7)

            queryset = queryset.annotate(
                # 시간 가중치: 최근 7일 내면 1.5배, 그 외는 1.0배
                time_weight=Case(
                    When(published_at__gte=recent_7_days, then=1.5),
                    When(published_at__isnull=True, created_at__gte=recent_7_days, then=1.5),
                    default=1.0,
                    output_field=FloatField()
                ),
                # 복합 점수: (조회수 * 1 + 좋아요 * 2 + 댓글 * 3) * 시간가중치
                hot_score=ExpressionWrapper(
                    (F('view_count') * 1 + F('like_count') * 2 + F('comment_count') * 3) * F('time_weight'),
                    output_field=FloatField()
                )
            ).filter(
                Q(published_at__gte=recent_30_days) | Q(published_at__isnull=True, created_at__gte=recent_30_days)  # 최근 30일 내 글
            ).order_by('-hot_score')
        elif active_tab:
            # 리뷰 탭인 경우 하드코딩된 카테고리 목록 사용
            if active_tab == 'reviews':
                reviews_category_slugs = ['community-racket', 'community-shoes', 'community-apparel', 'community-shuttlecock', 'community-protective', 'community-accessories']
                queryset = queryset.filter(
                    Q(category__slug__in=reviews_category_slugs) | Q(categories__slug__in=reviews_category_slugs)
                ).distinct()
                
                # 2차 카테고리 필터링 (카테고리 선택 시)
                if category:
                    queryset = queryset.filter(Q(category__slug=category) | Q(categories__slug=category)).distinct()
            # 동적 탭 필터링 (Category 기반)
            else:
                # 상위 카테고리(탭) 찾기
                current_category = Category.objects.filter(
                    slug=active_tab,
                    source=Category.Source.COMMUNITY,
                    parent__isnull=True,
                    is_active=True
                ).first()

                if current_category:
                    # 현재 카테고리와 그 하위 카테고리들을 가져옴
                    category_slugs = [current_category.slug]

                    # 하위 카테고리 추가
                    child_categories = Category.objects.filter(parent=current_category, is_active=True)
                    category_slugs.extend([cat.slug for cat in child_categories])

                    # 카테고리 필터링
                    queryset = queryset.filter(
                        Q(category__slug__in=category_slugs) | Q(categories__slug__in=category_slugs)
                    ).distinct()

                    # 2차 카테고리 필터링 (카테고리 선택 시)
                    if category:
                        queryset = queryset.filter(Q(category__slug=category) | Q(categories__slug=category)).distinct()
        else:
            # 탭이 없는 경우 일반 카테고리 필터링
            if category:
                # slug로 먼저 시도, 없으면 id로 시도
                try:
                    category_obj = Category.objects.get(slug=category, is_active=True)
                    queryset = queryset.filter(category=category_obj)
                except Category.DoesNotExist:
                    try:
                        category_obj = Category.objects.get(id=category, is_active=True)
                        queryset = queryset.filter(category=category_obj)
                    except Category.DoesNotExist:
                        pass
        
        # 검색 기능
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )
        
        # 정렬: 고정글 먼저, 그 다음 최신순
        queryset = queryset.order_by("-is_pinned", "-created_at")
        
        # content 필드는 템플릿에서 직접 사용하지 않고 서버에서 excerpt 추출에만 사용
        # excerpt 추출을 위해 content가 필요하므로 defer를 사용하지 않음
        # 템플릿에서는 서버에서 추출한 excerpt와 image_url만 사용하므로 
        # 템플릿 렌더링 시 content 필드 파싱 오버헤드는 없음
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 활성화된 동호인톡 탭 가져오기 (상위 카테고리 = 탭)
        tabs = Category.objects.filter(
            source=Category.Source.COMMUNITY,
            parent__isnull=True,
            is_active=True
        ).order_by('display_order')
        context["tabs"] = tabs

        # 각 탭의 하위 카테고리를 가져오기 (부모별 독립적인 display_order로 정렬)
        tab_children = {}
        for tab in tabs:
            children = Category.objects.filter(
                parent=tab,
                is_active=True
            ).order_by('display_order')  # 부모 내에서 display_order로 정렬
            tab_children[tab.slug] = children
        context["tab_children"] = tab_children

        context["active_tab"] = self.request.GET.get("tab", "")
        context["current_category"] = self.request.GET.get("category", "")
        context["search_query"] = self.request.GET.get("search", "")
        
        # Hot 글 - 최근 30일 내 글 + 복합 점수 + 시간 가중치
        now = timezone.now()
        # 최근 30일 기준일
        recent_30_days = now - timedelta(days=30)
        # 최근 7일 기준일 (시간 가중치 적용)
        recent_7_days = now - timedelta(days=7)
        
        hot_posts = Post.objects.filter(
            is_deleted=False,
            source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS]
        ).filter(
            Q(published_at__lte=now) | Q(published_at__isnull=True)  # published_at이 없거나 현재 시간 이전인 것
        ).filter(
            Q(published_at__gte=recent_30_days) | Q(published_at__isnull=True, created_at__gte=recent_30_days)  # 최근 30일 내 글
        ).select_related("author", "category").annotate(
            # 시간 가중치: 최근 7일 내면 1.5배, 그 외는 1.0배
            time_weight=Case(
                When(published_at__gte=recent_7_days, then=1.5),
                default=1.0,
                output_field=FloatField()
            ),
            # 복합 점수: (조회수 * 1 + 좋아요 * 2 + 댓글 * 3) * 시간가중치
            hot_score=ExpressionWrapper(
                (F('view_count') * 1 + F('like_count') * 2 + F('comment_count') * 3) * F('time_weight'),
                output_field=FloatField()
            )
        ).order_by('-hot_score')[:10]
        context["hot_posts"] = hot_posts
        
        # admin에서 설정한 배너 이미지 목록
        banners_qs = BadmintokBanner.objects.filter(is_active=True)
        banner_images = []
        for banner in banners_qs:
            if not banner.image:
                continue
            banner_images.append(
                {
                    "url": banner.image.url,
                    "alt": banner.alt_text or banner.title or "",
                    "link_url": banner.link_url,
                }
            )
        context["banner_images"] = banner_images

        # 고정된 공지사항 가져오기 (최신 1개)
        pinned_notice = Notice.objects.filter(is_pinned=True).order_by("-created_at").first()
        context["pinned_notice"] = pinned_notice

        # 페이지네이션 페이지 번호 범위 계산
        if hasattr(context.get('page_obj'), 'paginator'):
            paginator = context['page_obj'].paginator
            current_page = context['page_obj'].number
            total_pages = paginator.num_pages
            
            # 표시할 페이지 번호 범위 계산 (현재 페이지 주변 ±2)
            if total_pages <= 7:
                # 7페이지 이하면 모두 표시
                page_range = list(range(1, total_pages + 1))
            else:
                # 7페이지 초과면 현재 페이지 주변만 표시
                page_range = []
                start_page = max(1, current_page - 2)
                end_page = min(total_pages, current_page + 2)
                
                if start_page > 1:
                    page_range.append(1)
                    if start_page > 2:
                        page_range.append(None)  # ... 표시용
                
                page_range.extend(range(start_page, end_page + 1))
                
                if end_page < total_pages:
                    if end_page < total_pages - 1:
                        page_range.append(None)  # ... 표시용
                    page_range.append(total_pages)
            
            context["pagination_page_range"] = page_range

        # 서버 측 최적화: 게시물 excerpt 및 이미지 URL 추출
        import re
        import html
        from django.utils.html import strip_tags

        # 메인 게시물 리스트 최적화
        posts = context.get('posts', [])
        for post in posts:
            if hasattr(post, 'content') and post.content:
                # HTML 엔티티 디코딩 후 태그 제거 및 excerpt 추출
                unescaped_content = html.unescape(post.content)
                text_content = strip_tags(unescaped_content)
                if len(text_content) > 80:
                    # 80자 초과 시 15단어로 제한
                    words = text_content.split()[:15]
                    post.excerpt = ' '.join(words) + '...'
                else:
                    post.excerpt = text_content

                # 첫 번째 이미지 URL 추출
                pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
                match = re.search(pattern, unescaped_content, re.IGNORECASE)
                if match:
                    post.content_image_url = match.group(1)
                else:
                    post.content_image_url = None
            else:
                post.excerpt = ""
                post.content_image_url = None

        # Hot 게시물 리스트 최적화
        hot_posts = context.get('hot_posts', [])
        for post in hot_posts:
            if hasattr(post, 'content') and post.content:
                # HTML 엔티티 디코딩 후 태그 제거 및 excerpt 추출
                unescaped_content = html.unescape(post.content)
                text_content = strip_tags(unescaped_content)
                if len(text_content) > 80:
                    words = text_content.split()[:15]
                    post.excerpt = ' '.join(words) + '...'
                else:
                    post.excerpt = text_content

                # 첫 번째 이미지 URL 추출
                pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
                match = re.search(pattern, unescaped_content, re.IGNORECASE)
                if match:
                    post.content_image_url = match.group(1)
                else:
                    post.content_image_url = None
            else:
                post.excerpt = ""
                post.content_image_url = None

        return context


class PostDetailView(DetailView):
    """게시글 상세 뷰"""
    model = Post
    template_name = "community/detail.html"
    context_object_name = "post"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get(self, request, *args, **kwargs):
        """배드민톡 게시물은 배드민톡 URL로 리다이렉트"""
        try:
            self.object = self.get_object()
            # 배드민톡 게시물인 경우 배드민톡 URL로 리다이렉트
            if self.object.source == Post.Source.BADMINTOK:
                from django.shortcuts import redirect
                return redirect('badmintok_detail', slug=self.object.slug)
            context = self.get_context_data(object=self.object)
            return self.render_to_response(context)
        except:
            return super().get(request, *args, **kwargs)

    def get_queryset(self):
        from django.utils import timezone

        # 임시저장 및 예약발행 글은 작성자 또는 관리자만 볼 수 있음
        now = timezone.now()
        queryset = Post.objects.filter(is_deleted=False)

        # 로그인 사용자가 작성자 또는 관리자가 아니면 공개된 글만
        if not self.request.user.is_authenticated or not self.request.user.is_staff:
            queryset = queryset.filter(is_draft=False, published_at__lte=now)

        return queryset.select_related("author", "category").prefetch_related("images", "likes")
    
    def get_object(self, queryset=None):
        # queryset이 없으면 get_queryset()에서 가져옴
        if queryset is None:
            queryset = self.get_queryset()

        # slug로 조회 (중복된 경우 가장 최신 것 선택)
        slug = self.kwargs.get(self.slug_url_kwarg)
        if slug is None:
            raise AttributeError(
                "Generic detail view %s must be called with either an object "
                "pk or a slug." % self.__class__.__name__
            )

        # slug로 필터링하고, 중복된 경우 최신 것 선택
        post = queryset.filter(slug=slug).order_by('-created_at').first()

        if post is None:
            from django.http import Http404
            raise Http404("No %s found matching the query" % (queryset.model._meta.verbose_name))
        
        # 세션 기반 조회수 중복 방지 (3시간 제한)
        session_key = 'viewed_posts'
        viewed_posts = self.request.session.get(session_key, {})
        post_id_str = str(post.id)
        current_time = datetime.now()
        
        # 세션에 조회 기록이 있는지 확인
        should_increase = True
        if post_id_str in viewed_posts:
            last_viewed_time = datetime.fromisoformat(viewed_posts[post_id_str])
            time_diff = current_time - last_viewed_time
            
            # 3시간(10800초) 이내면 조회수 증가하지 않음
            if time_diff.total_seconds() < 10800:
                should_increase = False
        
        # 조회수 증가 및 세션 업데이트
        if should_increase:
            post.increase_view_count()
            viewed_posts[post_id_str] = current_time.isoformat()
            self.request.session[session_key] = viewed_posts
            self.request.session.modified = True
        
        return post
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        
        # 댓글 목록 (대댓글 제외)
        context["comments"] = Comment.objects.filter(
            post=post,
            is_deleted=False,
            parent__isnull=True
        ).select_related("author").prefetch_related("replies__author", "likes").order_by("created_at")
        
        # 좋아요 여부
        if self.request.user.is_authenticated:
            context["is_liked"] = post.likes.filter(id=self.request.user.id).exists()
        else:
            context["is_liked"] = False
        
        return context


class PostCreateView(LoginRequiredMixin, CreateView):
    """게시글 작성 뷰"""
    model = Post
    template_name = "community/post_form.html"
    fields = ["title", "category", "content"]
    success_url = reverse_lazy("community:list")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # 동호인톡 활성 카테고리만 포함 (상위 카테고리 = 탭)
        community_categories = Category.objects.filter(
            source=Category.Source.COMMUNITY,
            parent__isnull=True,
            is_active=True
        )

        # 상위 카테고리(탭)와 하위 카테고리 slug 목록 생성
        allowed_category_slugs = set()
        for category in community_categories:
            allowed_category_slugs.add(category.slug)
            # 하위 카테고리도 포함
            child_categories = Category.objects.filter(parent=category, is_active=True)
            allowed_category_slugs.update(child_categories.values_list('slug', flat=True))

        # hot 카테고리는 제외하고, allowed_category_slugs가 비어있으면 모든 카테고리 허용
        if allowed_category_slugs:
            form.fields["category"].queryset = Category.objects.filter(
                slug__in=allowed_category_slugs,
                is_active=True
            ).exclude(
                slug='hot'
            ).order_by("display_order", "name")
        else:
            # 카테고리가 없는 경우 모든 활성 카테고리 허용
            form.fields["category"].queryset = Category.objects.filter(
                is_active=True
            ).exclude(
                slug='hot'
            ).order_by("display_order", "name")
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 중복 제출 방지를 위한 토큰 생성
        import secrets
        submit_token = secrets.token_urlsafe(32)
        session_key = 'post_submit_token'
        self.request.session[session_key] = submit_token
        self.request.session.modified = True
        context['submit_token'] = submit_token
        
        # 계층 구조로 카테고리 정리
        # 동호인톡 활성 카테고리만 포함 (상위 카테고리 = 탭)
        community_categories = Category.objects.filter(
            source=Category.Source.COMMUNITY,
            parent__isnull=True,
            is_active=True
        )

        # 상위 카테고리(탭)와 하위 카테고리 slug 목록 생성
        allowed_category_slugs = set()
        for category in community_categories:
            allowed_category_slugs.add(category.slug)
            # 하위 카테고리도 포함
            child_categories = Category.objects.filter(parent=category, is_active=True)
            allowed_category_slugs.update(child_categories.values_list('slug', flat=True))

        # allowed_category_slugs가 비어있으면 모든 카테고리 허용
        if allowed_category_slugs:
            all_categories = list(Category.objects.filter(
                slug__in=allowed_category_slugs,
                is_active=True
            ).exclude(
                slug='hot'
            ).select_related('parent').order_by("display_order", "name"))
        else:
            all_categories = list(Category.objects.filter(
                is_active=True
            ).exclude(
                slug='hot'
            ).select_related('parent').order_by("display_order", "name"))

        def build_hierarchy():
            """계층 구조 리스트 생성"""
            hierarchy = []
            parents = [c for c in all_categories if c.parent is None]

            for parent in parents:
                # 해당 parent의 children 찾기
                children = [c for c in all_categories if c.parent_id == parent.id]

                if children:
                    # children이 있으면 parent를 상위 카테고리로 표시
                    parent.has_children = True
                    hierarchy.append(parent)
                    for child in children:
                        child.has_children = False
                    hierarchy.extend(children)
                else:
                    # children이 없으면 선택 가능한 일반 카테고리로 표시
                    parent.has_children = False
                    hierarchy.append(parent)

            return hierarchy

        context['categories_hierarchical'] = build_hierarchy()
        return context

    def form_valid(self, form):
        # 중복 제출 방지: 세션 기반 토큰 사용
        session_key = 'post_submit_token'
        submitted_token = self.request.POST.get('submit_token')
        stored_token = self.request.session.get(session_key)
        
        # 토큰 검증: 세션에 토큰이 있고 POST의 토큰과 일치하는 경우에만 정상 처리
        if stored_token and submitted_token and stored_token == submitted_token:
            # 토큰 사용 후 제거 (중복 제출 방지)
            del self.request.session[session_key]
            self.request.session.modified = True
        else:
            # 토큰이 없거나 일치하지 않으면 중복 제출로 간주
            # (이미 사용된 토큰이거나 유효하지 않은 요청)
            messages.warning(self.request, "중복 제출이 감지되었습니다. 이미 게시글이 작성되었을 수 있습니다.")
            logger.warning(f"Duplicate post submission detected for user {self.request.user.id} - stored_token: {bool(stored_token)}, submitted_token: {bool(submitted_token)}")
            return redirect("community:list")
        
        form.instance.author = self.request.user
        
        # 동호인 리뷰 카테고리인 경우 source를 MEMBER_REVIEWS로 설정
        member_review_categories = ['match', 'tournament', 'court', 'lesson']
        if form.cleaned_data.get('category') and form.cleaned_data.get('category').slug in member_review_categories:
            form.instance.source = Post.Source.MEMBER_REVIEWS
        else:
            form.instance.source = Post.Source.COMMUNITY  # 커뮤니티 글로 설정
        
        # 디버깅: 폼 데이터 확인
        logger.debug(f"Form data - title: {form.cleaned_data.get('title')}, category: {form.cleaned_data.get('category')}")
        logger.debug(f"Content length: {len(form.cleaned_data.get('content', ''))}")
        
        # 폼 검증 및 저장
        try:
            response = super().form_valid(form)
            logger.debug(f"Post created successfully - ID: {self.object.id}")
        except Exception as e:
            logger.error(f"Error creating post: {str(e)}", exc_info=True)
            messages.error(self.request, f"게시글 저장 중 오류가 발생했습니다: {str(e)}")
            return self.form_invalid(form)
        
        messages.success(self.request, "게시글이 작성되었습니다.")
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 중복 제출 방지를 위한 토큰 생성
        import secrets
        submit_token = secrets.token_urlsafe(32)
        session_key = 'post_submit_token'
        self.request.session[session_key] = submit_token
        self.request.session.modified = True
        context['submit_token'] = submit_token
        
        # 계층 구조로 카테고리 정리
        # 동호인톡 활성 카테고리만 포함 (상위 카테고리 = 탭)
        community_categories = Category.objects.filter(
            source=Category.Source.COMMUNITY,
            parent__isnull=True,
            is_active=True
        )

        # 상위 카테고리(탭)와 하위 카테고리 slug 목록 생성
        allowed_category_slugs = set()
        for category in community_categories:
            allowed_category_slugs.add(category.slug)
            # 하위 카테고리도 포함
            child_categories = Category.objects.filter(parent=category, is_active=True)
            allowed_category_slugs.update(child_categories.values_list('slug', flat=True))

        # allowed_category_slugs가 비어있으면 모든 카테고리 허용
        if allowed_category_slugs:
            all_categories = list(Category.objects.filter(
                slug__in=allowed_category_slugs,
                is_active=True
            ).exclude(
                slug='hot'
            ).select_related('parent').order_by("display_order", "name"))
        else:
            all_categories = list(Category.objects.filter(
                is_active=True
            ).exclude(
                slug='hot'
            ).select_related('parent').order_by("display_order", "name"))

        def build_hierarchy():
            """계층 구조 리스트 생성"""
            hierarchy = []
            parents = [c for c in all_categories if c.parent is None]

            for parent in parents:
                # 해당 parent의 children 찾기
                children = [c for c in all_categories if c.parent_id == parent.id]

                if children:
                    # children이 있으면 parent를 상위 카테고리로 표시
                    parent.has_children = True
                    hierarchy.append(parent)
                    for child in children:
                        child.has_children = False
                    hierarchy.extend(children)
                else:
                    # children이 없으면 선택 가능한 일반 카테고리로 표시
                    parent.has_children = False
                    hierarchy.append(parent)

            return hierarchy

        context['categories_hierarchical'] = build_hierarchy()
        return context


class PostUpdateView(LoginRequiredMixin, UpdateView):
    """게시글 수정 뷰"""
    model = Post
    template_name = "community/post_form.html"
    fields = ["title", "category", "content"]
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Post.objects.filter(is_deleted=False, author=self.request.user).select_related("category")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # 동호인톡 활성 카테고리만 포함 (상위 카테고리 = 탭)
        community_categories = Category.objects.filter(
            source=Category.Source.COMMUNITY,
            parent__isnull=True,
            is_active=True
        )

        # 상위 카테고리(탭)와 하위 카테고리 slug 목록 생성
        allowed_category_slugs = set()
        for category in community_categories:
            allowed_category_slugs.add(category.slug)
            # 하위 카테고리도 포함
            child_categories = Category.objects.filter(parent=category, is_active=True)
            allowed_category_slugs.update(child_categories.values_list('slug', flat=True))

        # hot 카테고리는 제외하고, allowed_category_slugs가 비어있으면 모든 카테고리 허용
        if allowed_category_slugs:
            form.fields["category"].queryset = Category.objects.filter(
                slug__in=allowed_category_slugs,
                is_active=True
            ).exclude(
                slug='hot'
            ).order_by("display_order", "name")
        else:
            # 카테고리가 없는 경우 모든 활성 카테고리 허용
            form.fields["category"].queryset = Category.objects.filter(
                is_active=True
            ).exclude(
                slug='hot'
            ).order_by("display_order", "name")
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 계층 구조로 카테고리 정리
        # 동호인톡 활성 카테고리만 포함 (상위 카테고리 = 탭)
        community_categories = Category.objects.filter(
            source=Category.Source.COMMUNITY,
            parent__isnull=True,
            is_active=True
        )

        # 상위 카테고리(탭)와 하위 카테고리 slug 목록 생성
        allowed_category_slugs = set()
        for category in community_categories:
            allowed_category_slugs.add(category.slug)
            # 하위 카테고리도 포함
            child_categories = Category.objects.filter(parent=category, is_active=True)
            allowed_category_slugs.update(child_categories.values_list('slug', flat=True))

        # allowed_category_slugs가 비어있으면 모든 카테고리 허용
        if allowed_category_slugs:
            all_categories = list(Category.objects.filter(
                slug__in=allowed_category_slugs,
                is_active=True
            ).exclude(
                slug='hot'
            ).select_related('parent').order_by("display_order", "name"))
        else:
            all_categories = list(Category.objects.filter(
                is_active=True
            ).exclude(
                slug='hot'
            ).select_related('parent').order_by("display_order", "name"))

        def build_hierarchy():
            """계층 구조 리스트 생성"""
            hierarchy = []
            parents = [c for c in all_categories if c.parent is None]

            for parent in parents:
                # 해당 parent의 children 찾기
                children = [c for c in all_categories if c.parent_id == parent.id]

                if children:
                    # children이 있으면 parent를 상위 카테고리로 표시
                    parent.has_children = True
                    hierarchy.append(parent)
                    for child in children:
                        child.has_children = False
                    hierarchy.extend(children)
                else:
                    # children이 없으면 선택 가능한 일반 카테고리로 표시
                    parent.has_children = False
                    hierarchy.append(parent)

            return hierarchy

        context['categories_hierarchical'] = build_hierarchy()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        return response

    def get_success_url(self):
        return reverse_lazy("community:detail", kwargs={"slug": self.object.slug})


class PostDeleteView(LoginRequiredMixin, DeleteView):
    """게시글 삭제 뷰 (소프트 삭제)"""
    model = Post
    success_url = reverse_lazy("community:list")
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Post.objects.filter(is_deleted=False, author=self.request.user).select_related("category")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_deleted = True
        self.object.save()
        messages.success(request, "게시글이 삭제되었습니다.")
        return redirect(self.success_url)


class PostLikeView(LoginRequiredMixin, View):
    """게시글 좋아요 토글 뷰"""

    def post(self, request, slug):
        post = get_object_or_404(Post, slug=slug, is_deleted=False)

        if post.likes.filter(id=request.user.id).exists():
            post.likes.remove(request.user)
            liked = False
        else:
            post.likes.add(request.user)
            liked = True

        post.update_like_count()
        post.refresh_from_db()

        # AJAX 요청인 경우 JSON 응답
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'liked': liked,
                'like_count': post.like_count
            })

        return redirect("community:detail", slug=post.slug)


@staff_member_required
@require_POST
def upload_image_for_editorjs(request):
    """Editor.js에서 이미지 업로드 처리"""
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'success': 0, 'message': '이미지 파일이 없습니다.'}, status=400)

        image_file = request.FILES['image']

        # 파일 크기 검증 (3MB)
        if image_file.size > 3 * 1024 * 1024:
            return JsonResponse({'success': 0, 'message': '이미지 크기는 3MB 이하여야 합니다.'}, status=400)

        # 파일 확장자 검증
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        file_ext = os.path.splitext(image_file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return JsonResponse({'success': 0, 'message': '지원하지 않는 이미지 형식입니다.'}, status=400)

        # 고유 파일명 생성
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join('community', 'editor', unique_filename)

        # 파일 저장
        saved_path = default_storage.save(file_path, image_file)
        file_url = default_storage.url(saved_path)

        return JsonResponse({
            'success': 1,
            'url': file_url
        })

    except Exception as e:
        logger.error(f'이미지 업로드 실패: {str(e)}')
        return JsonResponse({'success': 0, 'message': '이미지 업로드 중 오류가 발생했습니다.'}, status=500)


@staff_member_required
def badmintok_post_editor(request, post_id=None):
    """워드프레스 스타일 배드민톡 포스트 에디터"""
    from .models import BadmintokPost
    from django.shortcuts import render

    post = None
    is_update = False

    if post_id:
        post = get_object_or_404(BadmintokPost, pk=post_id)
        is_update = True

    if request.method == 'POST':
        title = request.POST.get('title', '')
        content = request.POST.get('content', '')
        category_ids = request.POST.getlist('categories')  # 복수 카테고리 선택
        is_pinned = request.POST.get('is_pinned') == 'on'
        is_draft = request.POST.get('is_draft') == 'true'  # 임시저장 여부
        slug = request.POST.get('slug', '').strip()
        published_at = request.POST.get('published_at', '').strip()
        thumbnail = request.FILES.get('thumbnail')
        thumbnail_alt = request.POST.get('thumbnail_alt', '').strip()
        remove_thumbnail = request.POST.get('remove_thumbnail') == 'true'
        focus_keyword = request.POST.get('focus_keyword', '').strip()
        meta_description = request.POST.get('meta_description', '').strip()

        try:
            if is_update:
                # 수정
                post.title = title
                post.content = content
                # 첫 번째 카테고리를 메인 카테고리로 설정
                if category_ids:
                    post.category_id = category_ids[0]
                else:
                    post.category = None
                post.is_pinned = is_pinned
                post.is_draft = is_draft

                # 슬러그 설정
                if slug:
                    post.slug = slug
                elif not post.slug:
                    # 슬러그가 없고 입력도 없으면 자동 생성
                    post.slug = post.generate_slug()

                # 발행 일시 설정
                if published_at:
                    from django.utils.dateparse import parse_datetime
                    parsed_datetime = parse_datetime(published_at)
                    if parsed_datetime:
                        post.published_at = parsed_datetime

                # 썸네일 처리
                if remove_thumbnail:
                    if post.thumbnail:
                        post.thumbnail.delete(save=False)
                        post.thumbnail = None
                elif thumbnail:
                    # 기존 썸네일 제거
                    if post.thumbnail:
                        post.thumbnail.delete(save=False)
                    post.thumbnail = thumbnail

                # SEO 필드 설정
                post.focus_keyword = focus_keyword
                post.meta_description = meta_description
                post.thumbnail_alt = thumbnail_alt

                post.save()

                # 카테고리 설정 (ManyToMany)
                if category_ids:
                    post.categories.set(category_ids)
                else:
                    post.categories.clear()

                if is_draft:
                    messages.success(request, '임시저장 되었습니다.')
                else:
                    messages.success(request, '게시글이 수정되었습니다.')
            else:
                # 새 글 작성
                category = None
                if category_ids:
                    category = Category.objects.get(id=category_ids[0])

                # 발행 일시 파싱
                parsed_published_at = None
                if published_at:
                    from django.utils.dateparse import parse_datetime
                    parsed_published_at = parse_datetime(published_at)

                post = BadmintokPost(
                    title=title,
                    content=content,
                    category=category,
                    author=request.user,
                    source=Post.Source.BADMINTOK,
                    is_pinned=is_pinned,
                    is_draft=is_draft,
                    slug=slug if slug else '',
                    published_at=parsed_published_at,
                    thumbnail=thumbnail,
                    thumbnail_alt=thumbnail_alt,
                    focus_keyword=focus_keyword,
                    meta_description=meta_description
                )
                post.save()

                # 카테고리 설정 (ManyToMany)
                if category_ids:
                    post.categories.set(category_ids)

                if is_draft:
                    messages.success(request, '임시저장 되었습니다.')
                else:
                    messages.success(request, '게시글이 작성되었습니다.')

            # admin 페이지로 리다이렉트
            # Django admin URL 이름은 Proxy 모델의 app_label을 사용
            # BadmintokPost의 app_label이 'badmintok'이므로 badmintok_badmintokpost
            return redirect('admin:badmintok_badmintokpost_changelist')

        except Exception as e:
            logger.error(f'게시글 저장 실패: {str(e)}')
            messages.error(request, f'게시글 저장 중 오류가 발생했습니다: {str(e)}')

    # 카테고리 목록 (계층 구조)
    # Category 기반으로 동적으로 카테고리 가져오기 (상위 카테고리 = 탭)
    badmintok_categories = Category.objects.filter(
        source=Category.Source.BADMINTOK,
        parent__isnull=True,
        is_active=True
    )

    # 상위 카테고리(탭)와 그 하위 카테고리들을 모두 수집
    category_ids = set()
    for category in badmintok_categories:
        # 상위 카테고리 추가
        category_ids.add(category.id)
        # 하위 카테고리들 추가
        child_categories = Category.objects.filter(parent=category, is_active=True)
        category_ids.update(child_categories.values_list('id', flat=True))

    # 수집한 카테고리들을 가져옴
    all_categories = Category.objects.filter(
        id__in=category_ids,
        is_active=True
    ).select_related('parent').order_by('display_order', 'name')

    # 계층 구조로 정리 (상위 -> 하위 순서)
    def build_hierarchy():
        """계층 구조 리스트 생성 - children이 있는 parent만 구분"""
        hierarchy = []
        parents = [c for c in all_categories if c.parent is None]

        for parent in parents:
            # 해당 parent의 children 찾기
            children = [c for c in all_categories if c.parent_id == parent.id]

            # children이 있는 경우만 parent를 먼저 추가하고 children 추가
            if children:
                # children이 있으면 parent를 상위 카테고리로 표시
                parent.has_children = True
                hierarchy.append(parent)
                # 각 하위 카테고리에도 has_children = False 설정
                for child in children:
                    child.has_children = False
                hierarchy.extend(children)
            else:
                # children이 없으면 선택 가능한 일반 카테고리로 표시
                parent.has_children = False
                hierarchy.append(parent)

        return hierarchy

    categories_hierarchical = build_hierarchy()

    context = {
        'post': post,
        'is_update': is_update,
        'categories': categories_hierarchical,
        'user': request.user,
    }

    return render(request, 'community/badmintok_post_editor.html', context)


@staff_member_required
@require_POST
def badmintok_post_image_upload(request):
    """워드프레스 스타일 에디터에서 이미지 업로드"""
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'success': False, 'error': '이미지 파일이 없습니다.'})

        image_file = request.FILES['image']

        # 파일 크기 검증 (10MB)
        if image_file.size > 10 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': '이미지 크기는 10MB 이하여야 합니다.'})

        # 파일 확장자 검증
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        file_ext = os.path.splitext(image_file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return JsonResponse({'success': False, 'error': '지원하지 않는 이미지 형식입니다.'})

        # 고유 파일명 생성
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join('community', 'badmintok', 'posts', unique_filename)

        # 파일 저장
        saved_path = default_storage.save(file_path, image_file)
        file_url = default_storage.url(saved_path)

        return JsonResponse({
            'success': True,
            'url': file_url
        })

    except Exception as e:
        logger.error(f'이미지 업로드 실패: {str(e)}')
        return JsonResponse({'success': False, 'error': '이미지 업로드 중 오류가 발생했습니다.'})


class CommentCreateView(LoginRequiredMixin, View):
    """댓글 작성 뷰"""

    def post(self, request, slug):
        post = get_object_or_404(Post, slug=slug, is_deleted=False)
        content = request.POST.get("content", "").strip()
        parent_id = request.POST.get("parent_id")

        if not content:
            # AJAX 요청인 경우 JSON 응답
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': '댓글 내용을 입력해주세요.'
                }, status=400)
            
            messages.error(request, "댓글 내용을 입력해주세요.")
            # post의 source에 따라 적절한 URL로 리다이렉트
            if post.source == Post.Source.BADMINTOK:
                return redirect("badmintok_detail", slug=post.slug)
            else:
                return redirect("community:detail", slug=post.slug)

        # 대댓글인 경우 부모 댓글 확인
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, id=parent_id, post=post, is_deleted=False)

        # 댓글 생성
        comment = Comment.objects.create(
            post=post,
            author=request.user,
            parent=parent,
            content=content
        )

        # AJAX 요청인 경우 JSON 응답
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # 프로필 이미지 URL을 절대 URL로 변환
            profile_image_url = comment.author.profile_image_url
            if profile_image_url and not profile_image_url.startswith('http'):
                # 상대 경로인 경우 절대 URL로 변환
                profile_image_url = request.build_absolute_uri(profile_image_url)
            
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'content': comment.content,
                    'author_name': comment.author.activity_name,
                    'author_profile_image': profile_image_url,
                    'author_initial': comment.author.activity_name[0] if comment.author.activity_name else '',
                    'created_at': comment.created_at.strftime('%Y.%m.%d %H:%M'),
                    'like_count': comment.like_count,
                    'parent_id': comment.parent.id if comment.parent else None,
                    'is_author': True  # 작성자 본인
                }
            })

        messages.success(request, "댓글이 작성되었습니다.")
        # post의 source에 따라 적절한 URL로 리다이렉트
        if post.source == Post.Source.BADMINTOK:
            return redirect("badmintok_detail", slug=post.slug)
        else:
            return redirect("community:detail", slug=post.slug)


class CommentDeleteView(LoginRequiredMixin, View):
    """댓글 삭제 뷰"""

    def post(self, request, comment_id):
        try:
            comment = get_object_or_404(Comment, id=comment_id, author=request.user, is_deleted=False)
            post_slug = comment.post.slug
            post_source = comment.post.source

            # 소프트 삭제
            comment.is_deleted = True
            comment.save()

            logger.info(f"Comment {comment_id} deleted by user {request.user.id}")

            # AJAX 요청인 경우 JSON 응답
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': '댓글이 삭제되었습니다.'
                })

            messages.success(request, "댓글이 삭제되었습니다.")
            # post의 source에 따라 적절한 URL로 리다이렉트
            if post_source == Post.Source.BADMINTOK:
                return redirect("badmintok_detail", slug=post_slug)
            else:
                return redirect("community:detail", slug=post_slug)

        except Exception as e:
            logger.error(f"Error deleting comment {comment_id}: {str(e)}", exc_info=True)

            # AJAX 요청인 경우 JSON 응답
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': '댓글 삭제 중 오류가 발생했습니다.'
                }, status=500)

            messages.error(request, "댓글 삭제 중 오류가 발생했습니다.")
            return redirect("community:list")


class CommentLikeView(LoginRequiredMixin, View):
    """댓글 좋아요 토글 뷰"""

    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, id=comment_id, is_deleted=False)

        if comment.likes.filter(id=request.user.id).exists():
            comment.likes.remove(request.user)
            liked = False
        else:
            comment.likes.add(request.user)
            liked = True

        comment.update_like_count()
        comment.refresh_from_db()

        # AJAX 요청인 경우 JSON 응답
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'liked': liked,
                'like_count': comment.like_count
            })

        # post의 source에 따라 적절한 URL로 리다이렉트
        if comment.post.source == Post.Source.BADMINTOK:
            return redirect("badmintok_detail", slug=comment.post.slug)
        else:
            return redirect("community:detail", slug=comment.post.slug)
