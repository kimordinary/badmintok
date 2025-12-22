from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import BadmintokBanner, Notice


@admin.register(BadmintokBanner)
class BadmintokBannerAdmin(admin.ModelAdmin):
    list_display = ("id", "image_preview", "title", "link_url", "is_active", "display_order", "created_at", "edit_button", "delete_button")
    list_editable = ("is_active", "display_order")
    search_fields = ("title", "alt_text", "link_url")
    list_filter = ("is_active",)
    ordering = ("display_order", "id")

    def image_preview(self, obj):
        """배너 이미지 미리보기"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 100px; object-fit: contain;" />',
                obj.image.url
            )
        return "-"
    image_preview.short_description = "이미지 미리보기"

    def edit_button(self, obj):
        """수정 버튼"""
        url = reverse('admin:badmintok_badmintokbanner_change', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="padding: 5px 10px; background-color: #417690; color: white; text-decoration: none; border-radius: 4px;">수정</a>',
            url
        )
    edit_button.short_description = "수정"

    def delete_button(self, obj):
        """삭제 버튼"""
        url = reverse('admin:badmintok_badmintokbanner_delete', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="padding: 5px 10px; background-color: #ba2121; color: white; text-decoration: none; border-radius: 4px;">삭제</a>',
            url
        )
    delete_button.short_description = "삭제"

    fieldsets = (
        ("배너 정보", {
            "fields": ("title", "image", "alt_text", "link_url")
        }),
        ("설정", {
            "fields": ("is_active", "display_order")
        }),
        ("날짜 정보", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    readonly_fields = ("created_at", "updated_at")


@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "is_pinned", "view_count", "created_at")
    list_editable = ("is_pinned",)
    search_fields = ("title", "content")
    list_filter = ("is_pinned", "created_at")
    ordering = ("-is_pinned", "-created_at")
    readonly_fields = ("view_count", "created_at", "updated_at")
    
    fieldsets = (
        ("기본 정보", {
            "fields": ("title", "content", "author")
        }),
        ("설정", {
            "fields": ("is_pinned",)
        }),
        ("통계", {
            "fields": ("view_count",)
        }),
        ("날짜 정보", {
            "fields": ("created_at", "updated_at")
        }),
    )