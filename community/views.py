from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count, Q, Max
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
    paginate_by = 20
    
    def get_queryset(self):
        from django.db.models import Prefetch
        from django.utils import timezone

        # 임시저장 제외, 예약발행(published_at이 현재 시간 이전인 것만) 필터링
        now = timezone.now()
        queryset = Post.objects.filter(
            is_deleted=False,
            is_draft=False,
            published_at__lte=now,
            source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS]  # 커뮤니티와 동호인 리뷰 글 표시
        ).select_related("author", "category").prefetch_related(
            Prefetch("images", queryset=PostImage.objects.order_by("order"))
        )
        
        # 탭 필터링
        active_tab = self.request.GET.get("tab", "")
        category = self.request.GET.get("category", "")
        
        # 리뷰 탭인 경우 리뷰 관련 카테고리만 필터링
        review_categories = ['racket', 'shoes', 'apparel', 'shuttlecock', 'protective', 'accessories']
        if active_tab == "reviews":
            if category and category in review_categories:
                # 특정 리뷰 카테고리 선택
                try:
                    category_obj = Category.objects.get(slug=category, is_active=True)
                    queryset = queryset.filter(category=category_obj)
                except Category.DoesNotExist:
                    pass
            # category가 없거나 'all'이면 리뷰 관련 카테고리 전체 표시
            elif not category or category == 'all':
                queryset = queryset.filter(category__slug__in=review_categories)
        else:
            # 리뷰 탭이 아닌 경우 일반 카테고리 필터링
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
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 동호인톡/동호인 리뷰 게시글에 실제로 사용된 카테고리만 가져오기 (배드민톡 전용 카테고리 제외)
        # 배드민톡 전용 카테고리 슬러그 목록
        badmintok_only_slugs = [
            'tournament', 'player', 'equipment', 'community',
            'yonex', 'lining', 'victor', 'mizuno', 'technist', 
            'strokus', 'redsun', 'trion', 'tricore', 'apacs'
        ]
        # 동호인톡/동호인 리뷰 게시글에 실제로 사용된 카테고리만 필터링
        used_categories = Category.objects.filter(
            is_active=True,
            posts__source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS],
            posts__is_deleted=False
        ).exclude(
            slug__in=badmintok_only_slugs
        ).distinct().order_by("display_order", "name")
        context["category_choices"] = used_categories
        context["active_tab"] = self.request.GET.get("tab", "")
        context["current_category"] = self.request.GET.get("category", "")
        context["search_query"] = self.request.GET.get("search", "")
        
        # Hot 글 (조회수 상위 10개) - 커뮤니티와 동호인 리뷰 글
        hot_posts = Post.objects.filter(
            is_deleted=False,
            source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS]
        ).select_related("author", "category").order_by("-view_count")[:10]
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

        return context


class PostDetailView(DetailView):
    """게시글 상세 뷰"""
    model = Post
    template_name = "community/detail.html"
    context_object_name = "post"
    slug_field = "slug"
    slug_url_kwarg = "slug"

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
        # 활성화된 카테고리만 표시
        form.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("display_order", "name")
        return form
    
    def form_valid(self, form):
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
        # 활성화된 카테고리만 표시
        form.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("display_order", "name")
        return form

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
        category_id = request.POST.get('category')
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
                if category_id:
                    post.category_id = category_id
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

                if is_draft:
                    messages.success(request, '임시저장 되었습니다.')
                else:
                    messages.success(request, '게시글이 수정되었습니다.')
            else:
                # 새 글 작성
                category = None
                if category_id:
                    category = Category.objects.get(id=category_id)

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

                if is_draft:
                    messages.success(request, '임시저장 되었습니다.')
                else:
                    messages.success(request, '게시글이 작성되었습니다.')

            # admin 페이지로 리다이렉트
            return redirect('admin:community_badmintokpost_changelist')

        except Exception as e:
            logger.error(f'게시글 저장 실패: {str(e)}')
            messages.error(request, f'게시글 저장 중 오류가 발생했습니다: {str(e)}')

    # 카테고리 목록 (계층 구조)
    # 상위 카테고리와 하위 카테고리를 모두 가져옴
    badmintok_parent_slugs = ['news', 'reviews', 'brands']
    badmintok_category_slugs = [
        'tournament', 'player', 'equipment', 'community',
        'racket', 'shoes', 'apparel', 'shuttlecock', 'protective', 'accessories',
        'yonex', 'lining', 'victor', 'mizuno', 'technist',
        'strokus', 'redsun', 'trion', 'tricore', 'apacs'
    ]

    all_slugs = badmintok_parent_slugs + badmintok_category_slugs
    all_categories = Category.objects.filter(
        slug__in=all_slugs,
        is_active=True
    ).select_related('parent').order_by('display_order', 'name')

    # 계층 구조로 정리 (상위 -> 하위 순서)
    def build_hierarchy():
        """계층 구조 리스트 생성"""
        hierarchy = []
        parents = [c for c in all_categories if c.parent is None]

        for parent in parents:
            hierarchy.append(parent)
            children = [c for c in all_categories if c.parent_id == parent.id]
            hierarchy.extend(children)

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
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'content': comment.content,
                    'author_name': comment.author.activity_name,
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
        comment = get_object_or_404(Comment, id=comment_id, author=request.user, is_deleted=False)
        post_slug = comment.post.slug

        # 소프트 삭제
        comment.is_deleted = True
        comment.save()

        messages.success(request, "댓글이 삭제되었습니다.")
        # post의 source에 따라 적절한 URL로 리다이렉트
        if comment.post.source == Post.Source.BADMINTOK:
            return redirect("badmintok_detail", slug=post_slug)
        else:
            return redirect("community:detail", slug=post_slug)


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
