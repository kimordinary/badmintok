from django.shortcuts import render, redirect
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.urls import reverse
from band.models import Band
from community.models import Post, Category, PostImage
from .models import BadmintokBanner, Notice


def home(request):
    """홈페이지 뷰"""
    # 인기 모임 (멤버 수가 많은 순서대로)
    popular_bands = Band.objects.filter(is_public=True).annotate(
        total_members=Count("members", filter=Q(members__status="active"))
    ).order_by("-total_members", "-created_at")[:5]
    
    # 최신 모임
    recent_bands = Band.objects.filter(is_public=True).annotate(
        total_members=Count("members", filter=Q(members__status="active"))
    ).order_by("-created_at")[:5]
    
    return render(request, "home.html", {
        "popular_bands": popular_bands,
        "recent_bands": recent_bands,
    })


def badmintok_detail(request, slug):
    """배드민톡 게시글 상세 뷰"""
    from django.shortcuts import get_object_or_404
    from datetime import datetime
    from django.utils import timezone

    # 배드민톡 글만 가져오기 (임시저장 및 예약발행 글은 작성자만 볼 수 있음)
    now = timezone.now()

    # 기본 필터: 삭제되지 않은 배드민톡 글
    base_filter = Q(is_deleted=False, source=Post.Source.BADMINTOK)

    # 로그인 사용자가 작성자가 아니면 공개된 글만
    if not request.user.is_authenticated or not request.user.is_staff:
        base_filter &= Q(is_draft=False, published_at__lte=now)

    post = get_object_or_404(
        Post.objects.filter(base_filter)
        .select_related("author", "category")
        .prefetch_related("images", "likes"),
        slug=slug
    )

    # 세션 기반 조회수 중복 방지 (3시간 제한)
    session_key = 'viewed_posts'
    viewed_posts = request.session.get(session_key, {})
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
        request.session[session_key] = viewed_posts
        request.session.modified = True

    # 댓글 목록 가져오기
    from community.models import Comment
    comments = Comment.objects.filter(
        post=post,
        is_deleted=False,
        parent__isnull=True
    ).select_related("author").prefetch_related("replies__author", "likes").order_by("created_at")

    # 추천 콘텐츠 가져오기
    recommended_posts = []
    # 뉴스 탭 카테고리 slug 목록
    news_category_slugs = ['tournament', 'player', 'equipment', 'community']
    
    # 현재 글의 카테고리가 뉴스 탭에 속하는지 확인
    is_news_tab = False
    if post.category:
        # 카테고리 slug가 뉴스 탭 목록에 있는지 확인
        if post.category.slug in news_category_slugs:
            is_news_tab = True
        # 카테고리의 parent가 "뉴스"인 경우도 확인
        elif post.category.parent:
            # parent 카테고리의 slug가 "news"이거나 이름이 "뉴스"인 경우
            if post.category.parent.slug == 'news' or '뉴스' in post.category.parent.name:
                is_news_tab = True
    
    # 뉴스 탭 글인 경우에만 추천 콘텐츠 표시
    if is_news_tab:
        # 뉴스 탭의 모든 카테고리에서 추천 글 가져오기
        news_posts = Post.objects.filter(
            is_deleted=False,
            is_draft=False,
            source=Post.Source.BADMINTOK,
            published_at__lte=now
        ).exclude(id=post.id).select_related("author", "category").prefetch_related("images")
        
        # 뉴스 탭 카테고리 필터링
        news_filter = Q(category__slug__in=news_category_slugs)
        # parent가 뉴스인 경우도 포함
        news_filter |= Q(category__parent__slug='news')
        news_filter |= Q(category__parent__name__icontains='뉴스')
        news_posts = news_posts.filter(news_filter)
        
        # 결과가 없으면 모든 배드민톡 글에서 추천 (임시)
        if not news_posts.exists():
            news_posts = Post.objects.filter(
                is_deleted=False,
                is_draft=False,
                source=Post.Source.BADMINTOK,
                published_at__lte=now
            ).exclude(id=post.id).select_related("author", "category").prefetch_related("images")
        
        # 인기글 (조회수 기준) - 상위 2개
        popular_posts = list(news_posts.order_by("-view_count")[:2])
        
        # 최신글 - 상위 2개
        recent_posts = list(news_posts.order_by("-created_at")[:2])
        
        # 중복 제거 후 반반 섞기
        import random
        # 중복 제거를 위해 set 사용 (id 기준)
        seen_ids = set()
        unique_posts = []
        for p in popular_posts + recent_posts:
            if p.id not in seen_ids:
                seen_ids.add(p.id)
                unique_posts.append(p)
        random.shuffle(unique_posts)
        recommended_posts = unique_posts[:4]  # 최대 4개
    else:
        # 뉴스 탭이 아니어도 모든 배드민톡 글에서 추천 (임시 - 테스트용)
        all_posts = Post.objects.filter(
            is_deleted=False,
            is_draft=False,
            source=Post.Source.BADMINTOK,
            published_at__lte=now
        ).exclude(id=post.id).select_related("author", "category").prefetch_related("images")
        
        # 인기글 (조회수 기준) - 상위 2개
        popular_posts = list(all_posts.order_by("-view_count")[:2])
        
        # 최신글 - 상위 2개
        recent_posts = list(all_posts.order_by("-created_at")[:2])
        
        # 중복 제거 후 반반 섞기
        import random
        # 중복 제거를 위해 set 사용 (id 기준)
        seen_ids = set()
        unique_posts = []
        for p in popular_posts + recent_posts:
            if p.id not in seen_ids:
                seen_ids.add(p.id)
                unique_posts.append(p)
        random.shuffle(unique_posts)
        recommended_posts = unique_posts[:4]  # 최대 4개

    return render(request, "badmintok/detail.html", {
        "post": post,
        "comments": comments,
        "recommended_posts": recommended_posts,
    })


def badmintok(request):
    """배드민톡 통합 페이지 (뉴스 & 리뷰 & 피드)"""
    from django.utils import timezone

    active_tab = request.GET.get("tab", "news")  # 기본값은 뉴스
    category = request.GET.get("category", "")

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

    # 배드민톡 게시물 목록 가져오기 (배드민톡 source만)
    # 임시저장 제외, 예약발행(published_at이 현재 시간 이전인 것만) 필터링
    now = timezone.now()
    posts = Post.objects.filter(
        is_deleted=False,
        is_draft=False,
        source=Post.Source.BADMINTOK,
        published_at__lte=now
    ).select_related("author", "category").prefetch_related("images")
    
    # 탭별 필터링
    if active_tab == "news":
        # 뉴스: 카테고리 필터링
        if category:
            posts = posts.filter(category__slug=category)
    elif active_tab == "reviews":
        # 리뷰: 카테고리 필터링
        if category:
            posts = posts.filter(category__slug=category)
    elif active_tab == "feed":
        # 피드: 전체 게시물
        pass
    
    # 검색 기능
    search = request.GET.get("search")
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | Q(content__icontains=search)
        )
    
    # 정렬
    posts = posts.order_by("-is_pinned", "-created_at")
    
    # 페이지네이션
    paginator = Paginator(posts, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    
    # Hot 글 (조회수 상위 10개) - 배드민톡 글만 (임시저장 및 예약발행 제외)
    hot_posts = Post.objects.filter(
        is_deleted=False,
        is_draft=False,
        source=Post.Source.BADMINTOK,
        published_at__lte=now
    ).select_related("author", "category").order_by("-view_count")[:10]

    # 고정된 공지사항 가져오기 (최신 1개)
    pinned_notice = Notice.objects.filter(is_pinned=True).order_by("-created_at").first()

    return render(request, "badmintok/index.html", {
        "active_tab": active_tab,
        "category": category,
        "banner_images": banner_images,
        "posts": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "hot_posts": hot_posts,
        "search_query": search or "",
        "pinned_notice": pinned_notice,
    })


def badmintok_create(request):
    """배드민톡 게시글 작성 뷰 (관리자 전용)"""
    from django.contrib.auth.decorators import login_required, staff_member_required
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.forms import ModelForm
    from django.http import HttpResponseForbidden
    
    # 관리자만 접근 가능
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    
    if not request.user.is_staff:
        messages.error(request, "배드민톡 글은 관리자만 작성할 수 있습니다.")
        return redirect("badmintok")
    
    class BadmintokPostForm(ModelForm):
        class Meta:
            model = Post
            fields = ["title", "category", "content"]
    
    if request.method == "POST":
        form = BadmintokPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.source = Post.Source.BADMINTOK  # 배드민톡 글로 설정
            post.save()
            
            # 이미지 저장
            images = request.FILES.getlist("images")
            for idx, image in enumerate(images):
                PostImage.objects.create(post=post, image=image, order=idx)
            
            messages.success(request, "게시글이 작성되었습니다.")
            # 탭 정보 유지하면서 리다이렉트
            tab = request.GET.get("tab", "news")
            return redirect(f"{reverse('badmintok')}?tab={tab}")
    else:
        form = BadmintokPostForm()
        form.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("display_order", "name")
    
    return render(request, "community/post_form.html", {
        "form": form,
        "is_badmintok": True,
    })


def member_reviews_create(request):
    """동호인 리뷰 게시글 작성 뷰"""
    from django.contrib.auth.decorators import login_required
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.forms import ModelForm
    
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    
    class MemberReviewsPostForm(ModelForm):
        class Meta:
            model = Post
            fields = ["title", "category", "content"]
    
    if request.method == "POST":
        form = MemberReviewsPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.source = Post.Source.MEMBER_REVIEWS  # 동호인 리뷰 글로 설정
            post.save()
            
            # 이미지 저장
            images = request.FILES.getlist("images")
            for idx, image in enumerate(images):
                PostImage.objects.create(post=post, image=image, order=idx)
            
            messages.success(request, "게시글이 작성되었습니다.")
            return redirect("member_reviews")
    else:
        form = MemberReviewsPostForm()
        form.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("display_order", "name")
    
    return render(request, "community/post_form.html", {
        "form": form,
        "is_member_reviews": True,
    })


def news_redirect(request):
    """기존 뉴스 URL을 통합 페이지로 리다이렉트"""
    return redirect("badmintok" + "?tab=news")


def reviews_redirect(request):
    """기존 리뷰 URL을 통합 페이지로 리다이렉트"""
    return redirect("badmintok" + "?tab=reviews")


def member_reviews(request):
    """동호인 리뷰 페이지"""
    from django.utils import timezone

    category = request.GET.get("category", "")

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

    # 동호인 리뷰 게시물 목록 가져오기 (동호인 리뷰 source만)
    # 임시저장 제외, 예약발행(published_at이 현재 시간 이전인 것만) 필터링
    now = timezone.now()
    posts = Post.objects.filter(
        is_deleted=False,
        is_draft=False,
        source=Post.Source.MEMBER_REVIEWS,
        published_at__lte=now
    ).select_related("author", "category").prefetch_related("images")
    
    # 카테고리 필터링
    if category:
        posts = posts.filter(category__slug=category)
    
    # 검색 기능
    search = request.GET.get("search")
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | Q(content__icontains=search)
        )
    
    # 정렬
    posts = posts.order_by("-is_pinned", "-created_at")
    
    # 페이지네이션
    paginator = Paginator(posts, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)
    
    # Hot 글 (조회수 상위 10개) - 동호인 리뷰 글만 (임시저장 및 예약발행 제외)
    hot_posts = Post.objects.filter(
        is_deleted=False,
        is_draft=False,
        source=Post.Source.MEMBER_REVIEWS,
        published_at__lte=now
    ).select_related("author", "category").order_by("-view_count")[:10]
    
    return render(request, "member_reviews/index.html", {
        "category": category,
        "banner_images": banner_images,
        "posts": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "hot_posts": hot_posts,
        "search_query": search or "",
    })


def notice_list(request):
    """공지사항 목록"""
    per_page = 20
    page = request.GET.get('page', 1)
    
    notices = Notice.objects.all().select_related('author').order_by("-is_pinned", "-created_at")
    paginator = Paginator(notices, per_page)
    notices_page = paginator.get_page(page)
    
    return render(request, "notices/list.html", {
        "notices_page": notices_page,
    })


def notice_detail(request, notice_id):
    """공지사항 상세"""
    from django.shortcuts import get_object_or_404
    
    notice = get_object_or_404(Notice.objects.select_related('author'), id=notice_id)
    notice.increase_view_count()
    
    return render(request, "notices/detail.html", {
        "notice": notice,
    })
