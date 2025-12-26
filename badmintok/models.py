from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import os
import uuid


def badmintok_banner_upload_to(instance, filename):
    """배너 이미지 파일명 생성 함수 - 파일명을 안전하게 처리"""
    # 파일 확장자 추출
    ext = os.path.splitext(filename)[1].lower()
    # UUID를 사용하여 고유 파일명 생성 (한글/특수문자 문제 해결)
    unique_filename = f"{uuid.uuid4().hex[:12]}{ext}"
    return f"badmintok_banners/{unique_filename}"


class BadmintokBanner(models.Model):
    """배드민톡 페이지 배너 이미지 (뉴스/리뷰/피드 공통으로 사용)."""

    title = models.CharField("배너 제목", max_length=100, blank=True)
    image = models.ImageField("배너 이미지", upload_to=badmintok_banner_upload_to)
    link_url = models.URLField("링크 URL", blank=True)
    alt_text = models.CharField("대체 텍스트", max_length=255, blank=True)
    is_active = models.BooleanField("노출 여부", default=True)
    display_order = models.PositiveIntegerField(
        "정렬 순서",
        default=0,
        help_text="숫자가 낮을수록 먼저 노출됩니다.",
    )

    created_at = models.DateTimeField("등록일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        verbose_name = "배드민톡 배너"
        verbose_name_plural = "배드민톡 배너"
        ordering = ["display_order", "id"]

    def __str__(self) -> str:
        return self.title or f"배너 #{self.pk}"


class Notice(models.Model):
    """공지사항 모델"""
    title = models.CharField(_("제목"), max_length=200)
    content = models.TextField(_("내용"))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notices",
        verbose_name=_("작성자")
    )
    is_pinned = models.BooleanField(_("고정"), default=False, help_text="고정된 공지사항은 상단에 표시됩니다.")
    view_count = models.PositiveIntegerField(_("조회수"), default=0)
    created_at = models.DateTimeField(_("작성일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)

    class Meta:
        verbose_name = _("공지사항")
        verbose_name_plural = _("공지사항")
        ordering = ["-is_pinned", "-created_at"]
        indexes = [
            models.Index(fields=["-is_pinned", "-created_at"]),
            models.Index(fields=["author"]),
        ]

    def __str__(self):
        return self.title

    def increase_view_count(self):
        """조회수 증가"""
        self.view_count += 1
        self.save(update_fields=["view_count"])