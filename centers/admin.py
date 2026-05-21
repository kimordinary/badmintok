from django.contrib import admin
from unfold.admin import ModelAdmin

from centers.models import Center, CenterBookmark


@admin.register(Center)
class CenterAdmin(ModelAdmin):
    list_display = (
        "name", "region", "court_count", "address",
        "is_published", "created_at",
    )
    list_filter = ("region", "is_published", "created_at")
    search_fields = ("name", "address", "description")
    readonly_fields = ("created_at", "updated_at")
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
        ("시스템", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(CenterBookmark)
class CenterBookmarkAdmin(ModelAdmin):
    list_display = ("user", "center", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "user__activity_name", "center__name")
    readonly_fields = ("user", "center", "created_at")

    def has_add_permission(self, request):
        return False
