from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget

from .models import User, UserProfile, Inquiry, Report, UserBlock


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    ordering = ("email",)
    list_display = ("email", "activity_name", "is_staff", "is_active")
    search_fields = ("email", "activity_name")
    fieldsets = (
        (None, {"fields": ("email", "password", "activity_name")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "activity_name", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")
    readonly_fields = ("last_login", "date_joined")


@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ("user", "name", "gender", "phone_number", "shipping_receiver")
    search_fields = ("user__email", "name", "phone_number", "shipping_receiver")
    list_filter = ("gender", "age_range", "created_at")
    autocomplete_fields = ("user",)


@admin.register(Inquiry)
class InquiryAdmin(ModelAdmin):
    list_display = ("user", "title", "category", "status", "created_at", "answered_at")
    list_filter = ("status", "category", "created_at")
    search_fields = ("user__email", "user__activity_name", "title", "content")
    readonly_fields = ("created_at", "updated_at", "answered_at")
    fieldsets = (
        ("문의 정보", {
            "fields": ("user", "category", "title", "content", "status")
        }),
        ("답변 정보", {
            "fields": ("admin_response", "answered_by", "answered_at")
        }),
        ("날짜 정보", {
            "fields": ("created_at", "updated_at")
        }),
    )

    def save_model(self, request, obj, form, change):
        # 답변을 작성하면 상태를 answered로 변경하고 답변일시 기록
        if obj.admin_response and not obj.answered_at:
            obj.status = Inquiry.Status.ANSWERED
            from django.utils import timezone
            obj.answered_at = timezone.now()
            obj.answered_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Report)
class ReportAdmin(ModelAdmin):
    list_display = ("reporter", "report_type", "target_id", "status", "created_at", "processed_at")
    list_filter = ("status", "report_type", "created_at")
    search_fields = ("reporter__email", "reporter__activity_name", "reason")
    readonly_fields = ("created_at", "updated_at", "processed_at")
    fieldsets = (
        ("신고 정보", {
            "fields": ("reporter", "report_type", "target_id", "reason", "status")
        }),
        ("처리 정보", {
            "fields": ("admin_note", "processed_by", "processed_at")
        }),
        ("날짜 정보", {
            "fields": ("created_at", "updated_at")
        }),
    )

    def save_model(self, request, obj, form, change):
        # 처리 상태가 변경되면 처리일시 기록
        if obj.status in [Report.Status.RESOLVED, Report.Status.REJECTED] and not obj.processed_at:
            from django.utils import timezone
            obj.processed_at = timezone.now()
            obj.processed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(UserBlock)
class UserBlockAdmin(ModelAdmin):
    list_display = ("blocker", "blocked", "created_at")
    list_filter = ("created_at",)
    search_fields = ("blocker__email", "blocker__activity_name", "blocked__email", "blocked__activity_name")
    readonly_fields = ("created_at",)
