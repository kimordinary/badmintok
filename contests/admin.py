from datetime import date

from django import forms
from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline

from .models import Contest, ContestCategory, ContestImage, ContestSchedule, Sponsor


class ContestScheduleInlineForm(forms.ModelForm):
    event_choices = ContestSchedule.EVENT_CHOICES
    age_choices = ContestSchedule.AGE_CHOICES

    events = forms.MultipleChoiceField(
        label="경기 종목",
        required=False,
        choices=event_choices,
        widget=forms.CheckboxSelectMultiple,
    )
    ages = forms.MultipleChoiceField(
        label="연령대 (10~70대 / 전연령)",
        required=False,
        choices=age_choices,
        widget=forms.CheckboxSelectMultiple,
        help_text="여러 연령대를 선택할 수 있습니다.",
    )

    class Meta:
        model = ContestSchedule
        fields = ("date", "events", "ages")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.events:
            self.initial["events"] = self.instance.get_events_display()
        if self.instance and self.instance.ages:
            if isinstance(self.instance.ages, list):
                self.initial["ages"] = self.instance.ages

    def clean_events(self):
        data = self.cleaned_data.get("events", [])
        return data or []

    def clean_ages(self):
        data = self.cleaned_data.get("ages", [])
        return data or []


class ContestScheduleInline(TabularInline):
    model = ContestSchedule
    form = ContestScheduleInlineForm
    extra = 0
    ordering = ("date",)


class ContestImageInline(TabularInline):
    """대회 이미지 인라인"""
    model = ContestImage
    extra = 1
    fields = ("image_preview", "image", "order")
    readonly_fields = ("image_preview",)
    ordering = ("order", "id")

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 80px; max-width: 120px; object-fit: contain;" />', obj.image.url)
        return "-"
    image_preview.short_description = "미리보기"


@admin.register(ContestCategory)
class ContestCategoryAdmin(ModelAdmin):
    list_display = ("name", "color", "description")
    search_fields = ("name",)


@admin.register(Sponsor)
class SponsorAdmin(ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Contest)
class ContestAdmin(ModelAdmin):
    inlines = [ContestImageInline, ContestScheduleInline]
    list_display = (
        "title",
        "display_status",
        "display_d_day",
        "display_completion",
        "created_at",
    )
    list_filter = ("category", "is_qualifying", "competition_type", "region", "schedule_start", "registration_start")
    search_fields = ("title", "region_detail", "sponsor__name")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category", "sponsor")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("category", "is_qualifying", "title", "slug", "pdf_file", "description")}),
        ("대회 일정", {"fields": (("schedule_start", "schedule_end"),)}),
        ("접수 정보", {"fields": (("registration_start", "registration_end"), "registration_name", "registration_link", "entry_fee")}),
        ("참가 대상", {"fields": ("participant_events", "participant_ages", "participant_grades")}),
        ("입상상품", {"fields": ("award_reward_text",)}),
        ("장소 및 기타", {"fields": ("region", "region_detail", "competition_type", "sponsor")}),
    )
    actions = ["delete_selected"]

    class Media:
        css = {"all": ("css/admin-contest.css",)}
        js = ("js/admin-contest-slug.js", "js/admin-image-preview.js")

    def has_delete_permission(self, request, obj=None):
        """삭제 권한 확인 - staff 사용자는 삭제 가능"""
        return request.user.is_staff

    def display_status(self, obj):
        """대회 상태 표시 (접수중/접수마감/종료)"""
        today = date.today()
        if obj.schedule_start and today > obj.schedule_start:
            return format_html('<span style="color: #9ca3af;">종료</span>')
        if obj.registration_end and today > obj.registration_end:
            return format_html('<span style="color: #f59e0b;">접수마감</span>')
        if obj.registration_start and today >= obj.registration_start:
            return format_html('<span style="color: #10b981;">접수중</span>')
        if obj.registration_start and today < obj.registration_start:
            return format_html('<span style="color: #3b82f6;">접수예정</span>')
        return "-"
    display_status.short_description = "상태"

    def display_d_day(self, obj):
        """대회 시작일 D-day 표시"""
        if not obj.schedule_start:
            return "-"
        today = date.today()
        delta = (obj.schedule_start - today).days
        if delta < 0:
            return format_html('<span style="color: #9ca3af;">{}</span>', obj.schedule_start.strftime("%Y.%m.%d"))
        elif delta == 0:
            return format_html('<span style="color: #ef4444; font-weight: bold;">D-Day</span>')
        else:
            return format_html('{} <span style="color: #3b82f6;">(D-{})</span>', obj.schedule_start.strftime("%Y.%m.%d"), delta)
    display_d_day.short_description = "대회일"

    def display_completion(self, obj):
        """필수 항목 완성 여부 체크"""
        checks = []
        # 이미지 체크
        has_image = obj.images.exists()
        checks.append(("이미지", has_image))
        # PDF 체크
        has_pdf = bool(obj.pdf_file)
        checks.append(("PDF", has_pdf))
        # 접수링크 체크
        has_link = bool(obj.registration_link)
        checks.append(("접수링크", has_link))

        result = []
        for label, status in checks:
            if status:
                result.append(f'<span style="color: #10b981;" title="{label}">●</span>')
            else:
                result.append(f'<span style="color: #ef4444;" title="{label}">○</span>')
        return format_html(" ".join(result))
    display_completion.short_description = "완성도"
