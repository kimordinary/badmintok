from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from centers.models import Center, CenterBookmark, CenterManager


class CenterManagerInline(TabularInline):
    """센터 편집 화면에서 관리자(회원)를 인라인으로 추가/제거."""
    model = CenterManager
    extra = 1
    autocomplete_fields = ("user",)
    fields = ("user", "role", "created_at")
    readonly_fields = ("created_at",)
    verbose_name = "센터 관리자"
    verbose_name_plural = "센터 관리자"


@admin.register(Center)
class CenterAdmin(ModelAdmin):
    list_display = (
        "name", "region", "court_count", "address",
        "is_published", "created_at",
    )
    list_filter = ("region", "is_published", "created_at")
    search_fields = ("name", "address", "description")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("created_by",)
    inlines = (CenterManagerInline,)
    fieldsets = (
        ("기본 정보", {
            "fields": ("name", "region", "address", "phone", "description"),
        }),
        ("운영 정보", {
            "fields": ("operating_hours", "pricing", "court_count", "amenities"),
        }),
        ("이미지·지도", {
            "fields": ("cover_image", "latitude", "longitude"),
        }),
        ("공개 설정", {
            "fields": ("is_published",),
        }),
        ("등록자", {
            "fields": ("created_by",),
        }),
        ("시스템", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(CenterManager)
class CenterManagerAdmin(ModelAdmin):
    list_display = ("center", "user", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("center__name", "user__activity_name", "user__email")
    autocomplete_fields = ("center", "user")
    readonly_fields = ("created_at",)


@admin.register(CenterBookmark)
class CenterBookmarkAdmin(ModelAdmin):
    list_display = ("user", "center", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "user__activity_name", "center__name")
    readonly_fields = ("user", "center", "created_at")

    def has_add_permission(self, request):
        return False
