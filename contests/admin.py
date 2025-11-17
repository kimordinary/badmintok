from django.contrib import admin

from .models import Contest, ContestCategory


@admin.register(ContestCategory)
class ContestCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "description")
    search_fields = ("name",)


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "competition_type",
        "schedule_start",
        "schedule_end",
        "location",
        "registration_start",
        "registration_end",
    )
    list_filter = ("category", "competition_type", "schedule_start", "registration_start")
    search_fields = ("title", "location", "sponsor")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category",)
    fieldsets = (
        (None, {"fields": ("category", "title", "slug", "image", "description")}),
        ("일정 및 접수", {"fields": ("schedule_start", "schedule_end", "registration_start", "registration_end")}),
        ("세부 정보", {"fields": ("location", "event_division", "entry_fee", "competition_type", "participant_reward", "sponsor", "award_reward", "registration_link")}),
    )
