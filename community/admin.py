from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Category, Post, PostImage, Comment, PostShare, BadmintokPost, CommunityPost
from .widgets import EditorJSWidget


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "slug", "display_order", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "slug"]
    list_editable = ["display_order", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["display_order", "name"]


class PostAdminForm(forms.ModelForm):
    """Admin에서 Post.content에 Editor.js 블록 에디터 사용"""

    class Meta:
        model = Post
        fields = "__all__"
        widgets = {
            "content": EditorJSWidget(),  # 항상 Editor.js 사용
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 배드민톡 글 작성 시에만 탭 기반 카테고리 필터링 적용
        # 이 Form은 BadmintokPostAdmin에서만 사용되므로 여기서 처리
        pass


class BasePostAdmin(admin.ModelAdmin):
    """공통 Post Admin 기능"""
    form = PostAdminForm
    list_display = ["id", "title", "category", "author", "status_badge", "view_count", "like_count", "comment_count", "is_pinned", "created_at", "actions_column"]
    list_filter = ["category", "is_draft", "is_pinned", "is_deleted", "created_at"]
    search_fields = ["title", "content", "author__activity_name", "author__email"]
    readonly_fields = ["view_count", "like_count", "comment_count", "created_at", "updated_at"]
    list_editable = ["is_pinned"]

    def status_badge(self, obj):
        """게시 상태 배지 표시"""
        from django.utils import timezone

        if obj.is_draft:
            return format_html(
                '<span style="display: inline-block; padding: 4px 10px; background: #f59e0b; color: white; border-radius: 12px; font-size: 11px; font-weight: 600;">📝 임시저장</span>'
            )
        elif obj.is_deleted:
            return format_html(
                '<span style="display: inline-block; padding: 4px 10px; background: #dc2626; color: white; border-radius: 12px; font-size: 11px; font-weight: 600;">🗑️ 삭제됨</span>'
            )
        elif obj.published_at and obj.published_at > timezone.now():
            return format_html(
                '<span style="display: inline-block; padding: 4px 10px; background: #8b5cf6; color: white; border-radius: 12px; font-size: 11px; font-weight: 600;">⏰ 예약발행</span>'
            )
        else:
            return format_html(
                '<span style="display: inline-block; padding: 4px 10px; background: #10b981; color: white; border-radius: 12px; font-size: 11px; font-weight: 600;">✅ 게시됨</span>'
            )
    status_badge.short_description = "상태"

    def get_list_display_links(self, request, list_display):
        """제목을 클릭 가능하게 만들기"""
        return ['title']

    def actions_column(self, obj):
        """수정/삭제 버튼 컬럼"""
        if obj.pk:
            change_url = reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk])
            delete_url = reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_delete', args=[obj.pk])
            return format_html(
                '<div style="display: flex; gap: 8px;">'
                '<a href="{}" class="button" style="padding: 6px 12px; background: #417690; color: white; text-decoration: none; border-radius: 4px; font-size: 12px;">수정</a>'
                '<a href="{}" class="button" style="padding: 6px 12px; background: #ba2121; color: white; text-decoration: none; border-radius: 4px; font-size: 12px;">삭제</a>'
                '</div>',
                change_url,
                delete_url
            )
        return "-"
    actions_column.short_description = "작업"
    
    fieldsets = (
        ("기본 정보", {
            "fields": ("title", "author", "source")
        }),
        ("카테고리", {
            "fields": ("category",),
            "description": "배드민톡 글의 경우 탭과 카테고리를 선택하세요."
        }),
        ("내용", {
            "fields": ("content",)
        }),
        ("발행 설정", {
            "fields": ("published_at", "is_draft", "slug"),
            "description": "예약 발행: 미래 시간 설정 시 해당 시간에 자동 공개됩니다. 임시저장: 체크 시 공개되지 않습니다."
        }),
        ("SEO 설정", {
            "fields": ("thumbnail", "thumbnail_alt", "focus_keyword", "meta_description"),
            "classes": ("collapse",),
        }),
        ("통계", {
            "fields": ("view_count", "like_count", "comment_count")
        }),
        ("설정", {
            "fields": ("is_pinned", "is_deleted")
        }),
        ("날짜", {
            "fields": ("created_at", "updated_at")
        }),
    )

    class Media:
        # Editor.js 및 플러그인 로드 (UMD 번들 사용)
        css = {
            "all": (
                "https://cdn.jsdelivr.net/npm/@editorjs/editorjs@latest/dist/editor.css",
            )
        }
        js = (
            "https://cdn.jsdelivr.net/npm/@editorjs/editorjs@latest",
            "https://cdn.jsdelivr.net/npm/@editorjs/paragraph@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/header@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/list@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/image@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/quote@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/code@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/delimiter@latest/dist/bundle.js",
            "js/admin-editorjs.js",
        )


@admin.register(BadmintokPost)
class BadmintokPostAdmin(BasePostAdmin):
    """배드민톡 게시글 Admin"""

    # 배드민톡 카테고리 매핑
    BADMINTOK_CATEGORIES = {
        'news': ['tournament', 'player', 'equipment', 'community'],
        'reviews': ['racket', 'shoes', 'apparel', 'shuttlecock', 'protective', 'accessories'],
        'brand': ['yonex', 'lining', 'victor', 'mizuno', 'technist', 'strokus', 'redsun', 'trion', 'tricore', 'apacs'],
        'feed': []
    }

    # 임시저장 글이 먼저 표시되도록 정렬
    ordering = ['-is_draft', '-created_at']

    def get_queryset(self, request):
        """배드민톡 글만 표시"""
        qs = super().get_queryset(request)
        return qs.filter(source=Post.Source.BADMINTOK)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # 새 글 작성 시 기본값을 배드민톡으로 설정
        if obj is None:
            form.base_fields['source'].initial = Post.Source.BADMINTOK
            form.base_fields['source'].widget = forms.HiddenInput()  # source는 숨김

        return form

    def add_view(self, request, form_url='', extra_context=None):
        """추가 버튼 클릭 시 워드프레스 스타일 에디터로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('community:badmintok_editor')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """수정 버튼 클릭 시 워드프레스 스타일 에디터로 리다이렉트"""
        from django.shortcuts import redirect
        return redirect('community:badmintok_editor_update', post_id=object_id)
    
    def changelist_view(self, request, extra_context=None):
        """목록 페이지에 카테고리 정보 전달"""
        extra_context = extra_context or {}
        # 카테고리 slug 정보를 JavaScript에 전달
        from .models import Category
        categories = Category.objects.filter(is_active=True).values('id', 'name', 'slug')
        extra_context['category_data'] = list(categories)
        return super().changelist_view(request, extra_context)
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """작성/수정 페이지에 카테고리 정보 전달"""
        extra_context = extra_context or {}
        # 카테고리 slug 정보를 JavaScript에 전달
        from .models import Category
        import json
        categories = list(Category.objects.filter(is_active=True).values('id', 'name', 'slug'))
        # id를 문자열로 변환 (JSON 직렬화를 위해)
        for cat in categories:
            cat['id'] = str(cat['id'])
        extra_context['category_data'] = json.dumps(categories, ensure_ascii=False)
        return super().changeform_view(request, object_id, form_url, extra_context)
    
    class Media:
        css = {
            "all": (
                "https://cdn.jsdelivr.net/npm/@editorjs/editorjs@latest/dist/editor.css",
            )
        }
        js = (
            "https://cdn.jsdelivr.net/npm/@editorjs/editorjs@latest",
            "https://cdn.jsdelivr.net/npm/@editorjs/paragraph@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/header@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/list@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/image@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/quote@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/code@latest/dist/bundle.js",
            "https://cdn.jsdelivr.net/npm/@editorjs/delimiter@latest/dist/bundle.js",
            "js/admin-editorjs.js",
            "js/admin-badmintok-category.js",
        )
    
    def actions_column(self, obj):
        """수정/삭제 버튼 컬럼"""
        if obj.pk:
            change_url = reverse('admin:community_badmintokpost_change', args=[obj.pk])
            delete_url = reverse('admin:community_badmintokpost_delete', args=[obj.pk])
            return format_html(
                '<div style="display: flex; gap: 8px;">'
                '<a href="{}" class="button" style="padding: 6px 12px; background: #417690; color: white; text-decoration: none; border-radius: 4px; font-size: 12px;">수정</a>'
                '<a href="{}" class="button" style="padding: 6px 12px; background: #ba2121; color: white; text-decoration: none; border-radius: 4px; font-size: 12px;">삭제</a>'
                '</div>',
                change_url,
                delete_url
            )
        return "-"
    actions_column.short_description = "작업"


@admin.register(CommunityPost)
class CommunityPostAdmin(BasePostAdmin):
    """동호인톡 게시글 Admin (커뮤니티 + 동호인 리뷰)"""
    
    def get_queryset(self, request):
        """동호인톡과 동호인 리뷰 글만 표시"""
        qs = super().get_queryset(request)
        return qs.filter(source__in=[Post.Source.COMMUNITY, Post.Source.MEMBER_REVIEWS])
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # 새 글 작성 시 기본값을 커뮤니티로 설정
        if obj is None:
            form.base_fields['source'].initial = Post.Source.COMMUNITY
        return form
    
    def actions_column(self, obj):
        """수정/삭제 버튼 컬럼"""
        if obj.pk:
            change_url = reverse('admin:community_communitypost_change', args=[obj.pk])
            delete_url = reverse('admin:community_communitypost_delete', args=[obj.pk])
            return format_html(
                '<div style="display: flex; gap: 8px;">'
                '<a href="{}" class="button" style="padding: 6px 12px; background: #417690; color: white; text-decoration: none; border-radius: 4px; font-size: 12px;">수정</a>'
                '<a href="{}" class="button" style="padding: 6px 12px; background: #ba2121; color: white; text-decoration: none; border-radius: 4px; font-size: 12px;">삭제</a>'
                '</div>',
                change_url,
                delete_url
            )
        return "-"
    actions_column.short_description = "작업"


@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ["id", "post", "order", "image", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["post__title"]
    ordering = ["post", "order", "created_at"]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["id", "post", "author", "parent", "like_count", "is_deleted", "created_at"]
    list_filter = ["is_deleted", "created_at"]
    search_fields = ["content", "author__activity_name", "post__title"]
    readonly_fields = ["like_count", "created_at", "updated_at"]
    
    fieldsets = (
        ("기본 정보", {
            "fields": ("post", "author", "parent")
        }),
        ("내용", {
            "fields": ("content",)
        }),
        ("통계", {
            "fields": ("like_count",)
        }),
        ("설정", {
            "fields": ("is_deleted",)
        }),
        ("날짜", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(PostShare)
class PostShareAdmin(admin.ModelAdmin):
    list_display = ["id", "post", "user", "shared_at"]
    list_filter = ["shared_at"]
    search_fields = ["post__title", "user__activity_name"]
    readonly_fields = ["shared_at"]
