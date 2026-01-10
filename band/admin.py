from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.db.models import Q
from .models import (
    Band, BandMember, BandPost, BandPostImage, BandComment,
    BandPostLike, BandCommentLike, BandVote, BandVoteOption, BandVoteChoice,
    BandSchedule, BandScheduleApplication, BandBookmark
)


@admin.register(Band)
class BandAdmin(admin.ModelAdmin):
    list_display = [
        "name", "band_type", "created_by", "is_approved", "is_public", 
        "join_approval_required", "approved_at", "deletion_requested", "created_at", "approval_actions", "deletion_actions", "delete_action"
    ]
    list_filter = ["is_approved", "is_public", "band_type", "join_approval_required", "deletion_requested", "created_at", "approved_at"]
    search_fields = ["name", "description", "created_by__email", "created_by__activity_name"]
    readonly_fields = ["created_at", "updated_at", "approved_at", "approved_by", "deletion_requested_at", "deletion_approved_at", "deletion_approved_by"]
    
    fieldsets = (
        ("기본 정보", {
            "fields": ("name", "description", "band_type", "categories", "region", "flash_region_detail")
        }),
        ("이미지", {
            "fields": ("cover_image", "profile_image")
        }),
        ("설정", {
            "fields": ("is_public", "join_approval_required")
        }),
        ("관리자 승인", {
            "fields": ("is_approved", "rejection_reason", "approved_at", "approved_by"),
            "description": "모임/동호회는 관리자 승인이 필요합니다."
        }),
        ("삭제 신청", {
            "fields": ("deletion_requested", "deletion_reason", "deletion_requested_at", "deletion_approved_at", "deletion_approved_by"),
            "description": "모임 삭제 신청 정보"
        }),
        ("시스템 정보", {
            "fields": ("created_by", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    
    actions = ["approve_selected", "reject_selected", "approve_deletion_selected", "delete_selected"]
    
    def approval_actions(self, obj):
        """승인/거부 버튼"""
        if obj.band_type in ["group", "club"] and not obj.is_approved:
            approve_url = reverse("admin:band_band_approve", args=[obj.pk])
            reject_url = reverse("admin:band_band_reject", args=[obj.pk])
            return format_html(
                '<a class="button" href="{}">승인</a> '
                '<a class="button" href="{}">거부</a>',
                approve_url, reject_url
            )
        return "-"
    approval_actions.short_description = "승인/거부"
    
    def delete_action(self, obj):
        """삭제 버튼"""
        delete_url = reverse("admin:band_band_delete", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="background-color: #dc2626; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none;" onclick="return confirm(\'정말 삭제하시겠습니까?\\n\\n이 모임과 관련된 모든 데이터(멤버, 게시글, 일정 등)가 함께 삭제됩니다.\');">삭제</a>',
            delete_url
        )
    delete_action.short_description = "삭제"
    
    def deletion_actions(self, obj):
        """삭제 승인/거부 버튼"""
        if obj.deletion_requested and not obj.deletion_approved_at:
            approve_url = reverse("admin:band_band_approve_deletion", args=[obj.pk])
            return format_html(
                '<a class="button" href="{}" style="background-color: #dc2626; color: white;">삭제 승인</a>',
                approve_url
            )
        elif obj.deletion_requested and obj.deletion_approved_at:
            return format_html('<span style="color: #64748b;">삭제 완료</span>')
        return "-"
    deletion_actions.short_description = "삭제 신청"
    
    def approve_selected(self, request, queryset):
        """일괄 승인"""
        # 모임/동호회만 필터링
        to_approve = queryset.filter(band_type__in=["group", "club"], is_approved=False)
        count = to_approve.count()
        
        if count == 0:
            self.message_user(request, "승인할 모임/동호회가 없습니다.", messages.WARNING)
            return
        
        updated = to_approve.update(
            is_approved=True,
            is_public=True,
            approved_at=timezone.now(),
            approved_by=request.user
        )
        self.message_user(request, f"{updated}개의 모임/동호회가 승인되었습니다.", messages.SUCCESS)
    approve_selected.short_description = "선택한 모임/동호회 승인"
    
    def reject_selected(self, request, queryset):
        """일괄 거부 (거부 사유 입력 필요)"""
        # 모임/동호회만 필터링
        to_reject = queryset.filter(band_type__in=["group", "club"], is_approved=False)
        count = to_reject.count()
        
        if count == 0:
            self.message_user(request, "거부할 모임/동호회가 없습니다.", messages.WARNING)
            return
        
        # 거부 사유는 개별적으로 입력해야 하므로, 일괄 거부는 기본 메시지로 처리
        # 실제로는 개별 거부 페이지로 리다이렉트하는 것이 좋지만, 
        # 여기서는 간단하게 처리
        self.message_user(
            request,
            "거부 사유 입력이 필요합니다. 개별 거부 기능을 사용해주세요.",
            messages.INFO
        )
    reject_selected.short_description = "선택한 모임/동호회 거부 (개별 거부 권장)"
    
    def approve_deletion_selected(self, request, queryset):
        """일괄 삭제 승인"""
        from datetime import timedelta
        
        to_approve = queryset.filter(deletion_requested=True, deletion_approved_at__isnull=True)
        count = to_approve.count()
        
        if count == 0:
            self.message_user(request, "승인할 삭제 신청이 없습니다.", messages.WARNING)
            return
        
        approved_count = 0
        for band in to_approve:
            # 삭제 승인 처리
            band.deletion_approved_at = timezone.now()
            band.deletion_approved_by = request.user
            band.save()
            
            # 생성자에게 일주일간 모임 생성 제한
            creator = band.created_by
            if creator:
                creator.band_creation_blocked_until = timezone.now() + timedelta(days=7)
                creator.save()
            
            # 모임 삭제 (CASCADE로 관련 데이터도 함께 삭제됨)
            try:
                band_name = band.name
                band.delete()
                approved_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f'"{band.name}" 삭제 중 오류 발생: {str(e)}',
                    messages.ERROR
                )
        
        if approved_count > 0:
            self.message_user(
                request,
                f"{approved_count}개의 모임 삭제가 승인되어 삭제되었습니다. "
                f"해당 계정으로 일주일간 모임을 생성할 수 없습니다.",
                messages.SUCCESS
            )
    approve_deletion_selected.short_description = "선택한 삭제 신청 승인 및 삭제"
    
    def delete_selected(self, request, queryset):
        """선택한 모임 삭제 (관련 데이터 포함)"""
        count = queryset.count()
        
        if count == 0:
            self.message_user(request, "삭제할 모임이 없습니다.", messages.WARNING)
            return
        
        # 삭제 전 정보 수집
        band_info = []
        for band in queryset:
            member_count = band.members.count()
            post_count = band.posts.count()
            schedule_count = band.schedules.count()
            band_info.append(
                f"'{band.name}' (멤버: {member_count}명, 게시글: {post_count}개, 일정: {schedule_count}개)"
            )
        
        # 삭제 실행
        deleted_count = 0
        for band in queryset:
            band_name = band.name
            try:
                band.delete()  # CASCADE로 관련 데이터도 함께 삭제됨
                deleted_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"'{band_name}' 삭제 중 오류 발생: {str(e)}",
                    messages.ERROR
                )
        
        if deleted_count > 0:
            self.message_user(
                request,
                f"{deleted_count}개의 모임이 삭제되었습니다. 관련 멤버, 게시글, 일정도 함께 삭제되었습니다.",
                messages.SUCCESS
            )
    delete_selected.short_description = "선택한 모임 삭제 (관련 데이터 포함)"
    
    def get_queryset(self, request):
        """모든 모임을 표시 (필터로 제어 가능)"""
        qs = super().get_queryset(request)
        # URL 파라미터로 필터링 제어
        approval_status = request.GET.get("approval_status", "all")
        
        if approval_status == "pending":
            # 승인 대기 중인 모임/동호회만
            return qs.filter(is_approved=False, band_type__in=["group", "club"])
        elif approval_status == "approved":
            # 승인된 모임/동호회와 번개
            return qs.filter(
                Q(is_approved=True, band_type__in=["group", "club"]) | Q(band_type="flash")
            )
        else:
            # 기본값: 모든 모임 표시
            return qs
    
    def changelist_view(self, request, extra_context=None):
        """승인 상태 필터 추가"""
        extra_context = extra_context or {}
        approval_status = request.GET.get("approval_status", "all")
        extra_context["approval_status"] = approval_status
        return super().changelist_view(request, extra_context)
    
    def get_urls(self):
        """커스텀 URL 추가"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:band_id>/approve/",
                self.admin_site.admin_view(self.approve_band),
                name="band_band_approve",
            ),
            path(
                "<int:band_id>/reject/",
                self.admin_site.admin_view(self.reject_band),
                name="band_band_reject",
            ),
            path(
                "<int:band_id>/delete/",
                self.admin_site.admin_view(self.delete_band),
                name="band_band_delete",
            ),
            path(
                "<int:band_id>/approve-deletion/",
                self.admin_site.admin_view(self.approve_deletion),
                name="band_band_approve_deletion",
            ),
        ]
        return custom_urls + urls
    
    def approve_band(self, request, band_id):
        """개별 승인"""
        band = Band.objects.get(pk=band_id)
        if band.band_type not in ["group", "club"]:
            messages.error(request, "번개는 승인이 필요하지 않습니다.")
            return HttpResponseRedirect(reverse("admin:band_band_changelist"))
        
        if band.is_approved:
            messages.info(request, "이미 승인된 모임/동호회입니다.")
            return HttpResponseRedirect(reverse("admin:band_band_changelist"))
        
        band.is_approved = True
        band.is_public = True
        band.approved_at = timezone.now()
        band.approved_by = request.user
        band.save()
        
        messages.success(request, f'"{band.name}" 모임/동호회가 승인되었습니다.')
        return HttpResponseRedirect(reverse("admin:band_band_changelist"))
    
    def reject_band(self, request, band_id):
        """개별 거부 (거부 사유 입력)"""
        from django.shortcuts import render
        from django import forms
        
        band = Band.objects.get(pk=band_id)
        if band.band_type not in ["group", "club"]:
            messages.error(request, "번개는 거부할 수 없습니다.")
            return HttpResponseRedirect(reverse("admin:band_band_changelist"))
        
        if band.is_approved:
            messages.info(request, "이미 승인된 모임/동호회입니다.")
            return HttpResponseRedirect(reverse("admin:band_band_changelist"))
        
        class RejectionForm(forms.Form):
            rejection_reason = forms.CharField(
                label="거부 사유",
                widget=forms.Textarea(attrs={"rows": 4, "cols": 50}),
                required=True,
                help_text="거부 사유를 입력해주세요. 이 내용이 사용자에게 전달됩니다."
            )
        
        if request.method == "POST":
            form = RejectionForm(request.POST)
            if form.is_valid():
                rejection_reason = form.cleaned_data["rejection_reason"]
                band.is_approved = False
                band.is_public = False
                band.rejection_reason = rejection_reason
                band.save()
                
                # TODO: 사용자에게 알림 전송 (이메일, 푸시 등)
                # 여기서는 메시지만 표시
                
                messages.success(
                    request,
                    f'"{band.name}" 모임/동호회가 거부되었습니다. '
                    f'거부 사유: {rejection_reason}'
                )
                return HttpResponseRedirect(reverse("admin:band_band_changelist"))
        else:
            form = RejectionForm()
        
        return render(
            request,
            "admin/band/band/reject_band.html",
            {
                "band": band,
                "form": form,
                "opts": self.model._meta,
                "has_view_permission": True,
            }
        )
    
    def delete_band(self, request, band_id):
        """개별 모임 삭제"""
        band = Band.objects.get(pk=band_id)
        band_name = band.name
        
        # 관련 데이터 정보
        member_count = band.members.count()
        post_count = band.posts.count()
        schedule_count = band.schedules.count()
        
        if request.method == "POST":
            try:
                band.delete()  # CASCADE로 관련 데이터도 함께 삭제됨
                messages.success(
                    request,
                    f'"{band_name}" 모임이 삭제되었습니다. '
                    f'관련 멤버 {member_count}명, 게시글 {post_count}개, 일정 {schedule_count}개도 함께 삭제되었습니다.'
                )
            except Exception as e:
                messages.error(request, f'"{band_name}" 삭제 중 오류가 발생했습니다: {str(e)}')
            
            return HttpResponseRedirect(reverse("admin:band_band_changelist"))
        
        # GET 요청 시 확인 페이지 표시
        from django.shortcuts import render
        return render(
            request,
            "admin/band/band/delete_band.html",
            {
                "band": band,
                "member_count": member_count,
                "post_count": post_count,
                "schedule_count": schedule_count,
                "opts": self.model._meta,
                "has_view_permission": True,
            }
        )
    
    def approve_deletion(self, request, band_id):
        """삭제 신청 승인 및 모임 삭제"""
        from datetime import timedelta
        
        band = Band.objects.get(pk=band_id)
        
        if not band.deletion_requested:
            messages.error(request, "삭제 신청이 없는 모임입니다.")
            return HttpResponseRedirect(reverse("admin:band_band_changelist"))
        
        if band.deletion_approved_at:
            messages.info(request, "이미 삭제 승인된 모임입니다.")
            return HttpResponseRedirect(reverse("admin:band_band_changelist"))
        
        # 삭제 승인 처리
        band.deletion_approved_at = timezone.now()
        band.deletion_approved_by = request.user
        band.save()
        
        # 생성자에게 일주일간 모임 생성 제한
        creator = band.created_by
        if creator:
            creator.band_creation_blocked_until = timezone.now() + timedelta(days=7)
            creator.save()
        
        # 모임 삭제 (CASCADE로 관련 데이터도 함께 삭제됨)
        band_name = band.name
        member_count = band.members.count()
        post_count = band.posts.count()
        schedule_count = band.schedules.count()
        
        try:
            band.delete()
            messages.success(
                request,
                f'"{band_name}" 모임 삭제가 승인되어 삭제되었습니다. '
                f'관련 멤버 {member_count}명, 게시글 {post_count}개, 일정 {schedule_count}개도 함께 삭제되었습니다. '
                f'해당 계정으로 일주일간 모임을 생성할 수 없습니다.'
            )
        except Exception as e:
            messages.error(request, f'"{band_name}" 삭제 중 오류가 발생했습니다: {str(e)}')
        
        return HttpResponseRedirect(reverse("admin:band_band_changelist"))


@admin.register(BandMember)
class BandMemberAdmin(admin.ModelAdmin):
    list_display = ["band", "user", "role", "status", "joined_at"]
    list_filter = ["role", "status", "joined_at"]
    search_fields = ["band__name", "user__activity_name", "user__email"]


class BandPostImageInline(admin.TabularInline):
    model = BandPostImage
    extra = 1


@admin.register(BandPost)
class BandPostAdmin(admin.ModelAdmin):
    list_display = ["title", "band", "author", "post_type", "is_pinned", "is_notice", "view_count", "created_at"]
    list_filter = ["post_type", "is_pinned", "is_notice", "created_at"]
    search_fields = ["title", "content", "band__name"]
    readonly_fields = ["view_count", "like_count", "comment_count", "created_at", "updated_at"]
    inlines = [BandPostImageInline]


@admin.register(BandComment)
class BandCommentAdmin(admin.ModelAdmin):
    list_display = ["post", "author", "parent", "like_count", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["content", "post__title", "author__activity_name"]
    readonly_fields = ["like_count", "created_at", "updated_at"]


@admin.register(BandPostLike)
class BandPostLikeAdmin(admin.ModelAdmin):
    list_display = ["post", "user", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["post__title", "user__activity_name"]


@admin.register(BandCommentLike)
class BandCommentLikeAdmin(admin.ModelAdmin):
    list_display = ["comment", "user", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["comment__content", "user__activity_name"]


class BandVoteOptionInline(admin.TabularInline):
    model = BandVoteOption
    extra = 2


@admin.register(BandVote)
class BandVoteAdmin(admin.ModelAdmin):
    list_display = ["title", "post", "is_multiple_choice", "end_datetime", "created_at"]
    list_filter = ["is_multiple_choice", "created_at"]
    search_fields = ["title", "post__title"]
    inlines = [BandVoteOptionInline]


@admin.register(BandSchedule)
class BandScheduleAdmin(admin.ModelAdmin):
    list_display = ["title", "band", "start_datetime", "location", "max_participants", "current_participants", "created_at"]
    list_filter = ["requires_approval", "start_datetime", "created_at"]
    search_fields = ["title", "band__name", "location"]
    readonly_fields = ["current_participants", "created_at", "updated_at"]


@admin.register(BandScheduleApplication)
class BandScheduleApplicationAdmin(admin.ModelAdmin):
    list_display = ["schedule", "user", "status", "applied_at", "reviewed_at", "reviewed_by"]
    list_filter = ["status", "applied_at", "reviewed_at"]
    search_fields = ["schedule__title", "user__activity_name", "user__email"]
    readonly_fields = ["applied_at", "reviewed_at"]


@admin.register(BandBookmark)
class BandBookmarkAdmin(admin.ModelAdmin):
    list_display = ["band", "user", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["band__name", "user__activity_name", "user__email"]
    readonly_fields = ["created_at"]

