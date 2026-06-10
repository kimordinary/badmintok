from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, StackedInline
from unfold.contrib.forms.widgets import WysiwygWidget

from .models import User, UserProfile, Inquiry, Report, UserBlock


class UserProfileInline(StackedInline):
    """User 관리 화면에서 실명·전화번호 등 프로필을 함께 보고 편집."""
    model = UserProfile
    can_delete = False
    extra = 0
    verbose_name_plural = "프로필 (실명·전화번호·배송지 등)"
    fields = (
        "name", "phone_number", "gender", "age_range", "birthday",
        "badminton_level", "shipping_receiver", "shipping_phone_number", "shipping_address",
    )


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    ordering = ("email",)
    inlines = (UserProfileInline,)
    list_display = ("email", "activity_name", "profile_name", "profile_phone", "is_active", "is_staff", "date_joined")
    list_select_related = ("profile",)
    list_filter = ("is_staff", "is_active", "date_joined")
    search_fields = ("email", "activity_name", "profile__name", "profile__phone_number")

    def _get_profile(self, obj):
        try:
            return obj.profile
        except UserProfile.DoesNotExist:
            return None

    @admin.display(description="실명")
    def profile_name(self, obj):
        p = self._get_profile(obj)
        return (p.name if p and p.name else "-")

    @admin.display(description="전화번호")
    def profile_phone(self, obj):
        p = self._get_profile(obj)
        return (p.phone_number if p and p.phone_number else "-")
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
