from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import os
import uuid

from badmintok.fields import WebPImageField


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
    image = WebPImageField("배너 이미지", upload_to=badmintok_banner_upload_to)
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


class VisitorLog(models.Model):
    """사이트 방문 로그 - 젯팩 스타일 통계를 위한 모델"""

    # 방문자 정보
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visitor_logs",
        verbose_name=_("사용자")
    )
    session_key = models.CharField(_("세션 키"), max_length=40, db_index=True)
    ip_address = models.GenericIPAddressField(_("IP 주소"), null=True, blank=True)

    # 페이지 정보
    url_path = models.CharField(_("URL 경로"), max_length=500, db_index=True)
    page_title = models.CharField(_("페이지 제목"), max_length=200, blank=True)

    # 접속 경로 정보
    referer = models.CharField(_("리퍼러"), max_length=500, blank=True, help_text="유입 경로")
    referer_domain = models.CharField(_("리퍼러 도메인"), max_length=200, blank=True, db_index=True)

    # 브라우저/디바이스 정보
    user_agent = models.CharField(_("User Agent"), max_length=500, blank=True)
    device_type = models.CharField(
        _("디바이스 유형"),
        max_length=20,
        choices=[
            ("desktop", "데스크톱"),
            ("mobile", "모바일"),
            ("tablet", "태블릿"),
            ("bot", "봇"),
        ],
        default="desktop"
    )

    # 시간 정보
    visited_at = models.DateTimeField(_("방문 시각"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("방문 로그")
        verbose_name_plural = _("방문 로그")
        ordering = ["-visited_at"]
        indexes = [
            models.Index(fields=["-visited_at"]),
            models.Index(fields=["session_key", "-visited_at"]),
            models.Index(fields=["url_path", "-visited_at"]),
            models.Index(fields=["referer_domain", "-visited_at"]),
            # 통계 쿼리 최적화를 위한 복합 인덱스
            models.Index(fields=["device_type", "-visited_at"]),
            models.Index(fields=["-visited_at", "device_type"]),
        ]

    def __str__(self):
        return f"{self.url_path} - {self.visited_at.strftime('%Y-%m-%d %H:%M')}"


class OutboundClick(models.Model):
    """외부 링크 클릭 추적 - 광고 배너, 외부 링크 등"""

    # 클릭자 정보
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outbound_clicks",
        verbose_name=_("사용자")
    )
    session_key = models.CharField(_("세션 키"), max_length=40, db_index=True)
    ip_address = models.GenericIPAddressField(_("IP 주소"), null=True, blank=True)

    # 클릭된 링크 정보
    destination_url = models.URLField(_("목적지 URL"), max_length=1000)
    destination_domain = models.CharField(_("목적지 도메인"), max_length=200, db_index=True)
    link_text = models.CharField(_("링크 텍스트"), max_length=200, blank=True, help_text="링크에 표시된 텍스트")
    link_type = models.CharField(
        _("링크 유형"),
        max_length=50,
        choices=[
            ("banner", "배너"),
            ("text_link", "텍스트 링크"),
            ("button", "버튼"),
            ("other", "기타"),
        ],
        default="text_link"
    )

    # 페이지 정보 (어느 페이지에서 클릭했는지)
    source_url = models.CharField(_("소스 URL"), max_length=500, help_text="클릭이 발생한 페이지")

    # 브라우저/디바이스 정보
    user_agent = models.CharField(_("User Agent"), max_length=500, blank=True)
    device_type = models.CharField(
        _("디바이스 유형"),
        max_length=20,
        choices=[
            ("desktop", "데스크톱"),
            ("mobile", "모바일"),
            ("tablet", "태블릿"),
        ],
        default="desktop"
    )

    # 시간 정보
    clicked_at = models.DateTimeField(_("클릭 시각"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("외부 링크 클릭")
        verbose_name_plural = _("외부 링크 클릭")
        ordering = ["-clicked_at"]
        indexes = [
            models.Index(fields=["-clicked_at"]),
            models.Index(fields=["destination_domain", "-clicked_at"]),
            models.Index(fields=["link_type", "-clicked_at"]),
            # 통계 쿼리 최적화를 위한 복합 인덱스
            models.Index(fields=["device_type", "-clicked_at"]),
        ]

    def __str__(self):
        return f"{self.destination_domain} - {self.clicked_at.strftime('%Y-%m-%d %H:%M')}"