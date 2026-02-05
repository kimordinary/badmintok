from datetime import date

from django import forms
from django.contrib import admin
from django.db.models import Exists, OuterRef, Q
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RelatedDropdownFilter

from .models import Contest, ContestCategory, ContestImage, ContestSchedule, Sponsor


class CompletionFilter(admin.SimpleListFilter):
    """완성도 필터 (이미지/PDF/접수링크)"""
    title = _("완성도")
    parameter_name = "completion"

    def lookups(self, request, model_admin):
        return (
            ("complete", "완성 (모두 있음)"),
            ("incomplete", "미완성 (하나라도 없음)"),
            ("no_image", "이미지 없음"),
            ("no_pdf", "PDF 없음"),
            ("no_link", "접수링크 없음"),
        )

    def queryset(self, request, queryset):
        if self.value() == "complete":
            # 이미지, PDF, 접수링크 모두 있는 대회
            return queryset.annotate(
                has_image=Exists(ContestImage.objects.filter(contest=OuterRef("pk")))
            ).filter(
                has_image=True,
                pdf_file__isnull=False,
                registration_link__isnull=False,
            ).exclude(pdf_file="").exclude(registration_link="")
        elif self.value() == "incomplete":
            # 하나라도 없는 대회
            return queryset.annotate(
                has_image=Exists(ContestImage.objects.filter(contest=OuterRef("pk")))
            ).filter(
                Q(has_image=False) |
                Q(pdf_file__isnull=True) | Q(pdf_file="") |
                Q(registration_link__isnull=True) | Q(registration_link="")
            )
        elif self.value() == "no_image":
            return queryset.annotate(
                has_image=Exists(ContestImage.objects.filter(contest=OuterRef("pk")))
            ).filter(has_image=False)
        elif self.value() == "no_pdf":
            return queryset.filter(Q(pdf_file__isnull=True) | Q(pdf_file=""))
        elif self.value() == "no_link":
            return queryset.filter(Q(registration_link__isnull=True) | Q(registration_link=""))
        return queryset


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
    fields = ("image", "order")
    ordering = ("order", "id")


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
    list_filter = (
        ("category", RelatedDropdownFilter),
        ("region", ChoicesDropdownFilter),
        CompletionFilter,
    )
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
        js = ("js/admin-contest-slug.js",)

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
