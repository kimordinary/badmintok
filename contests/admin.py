from django import forms
from django.contrib import admin

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


class ContestScheduleInline(admin.TabularInline):
    model = ContestSchedule
    form = ContestScheduleInlineForm
    extra = 0
    ordering = ("date",)


class ContestImageInline(admin.TabularInline):
    """대회 이미지 인라인"""
    model = ContestImage
    extra = 1
    fields = ("image", "order")
    ordering = ("order", "id")


@admin.register(ContestCategory)
class ContestCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "description")
    search_fields = ("name",)


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    inlines = [ContestImageInline, ContestScheduleInline]
    list_display = (
        "title",
        "category",
        "is_qualifying",
        "competition_type",
        "schedule_start",
        "schedule_end",
        "region",
        "registration_start",
        "registration_end",
    )
    list_filter = ("category", "is_qualifying", "competition_type", "region", "schedule_start", "registration_start")
    search_fields = ("title", "region_detail", "sponsor__name")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category", "sponsor")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("category", "is_qualifying", "title", "slug", "description", "pdf_file")}),
        # 인라인(경기 일정) 바로 위에 오도록 일정/접수를 가운데로 배치
        ("일정 및 접수", {"fields": ("schedule_start", "schedule_end", "registration_start", "registration_end")}),
        ("참가 대상 (종목 / 연령 / 급수)", {"fields": ("participant_target",)}),
        ("입상상품", {"fields": ("award_reward_text",)}),
        ("세부 정보", {"fields": ("region", "region_detail", "entry_fee", "competition_type", "participant_reward", "sponsor", "registration_name", "registration_link")}),
    )
    actions = ["delete_selected"]
    
    class Media:
        js = ('js/admin-contest-slug.js',)
    
    def has_delete_permission(self, request, obj=None):
        """삭제 권한 확인 - staff 사용자는 삭제 가능"""
        return request.user.is_staff
