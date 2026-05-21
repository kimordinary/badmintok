from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from badmintok.fields import WebPImageField


class Center(models.Model):
    """전국 배드민턴 센터(체육관/클럽 시설)."""

    # band 앱과 일관된 지역 코드 사용
    class Region(models.TextChoices):
        ALL = "all", _("전체")
        CAPITAL = "capital", _("수도권")
        BUSAN = "busan", _("영남권")
        DAEGU = "daegu", _("대구권")
        GWANGJU = "gwangju", _("호남권")
        DAEJEON = "daejeon", _("충청권")
        ULSAN = "ulsan", _("울산권")
        GANGWON = "gangwon", _("강원권")
        JEJU = "jeju", _("제주권")

    name = models.CharField(_("센터명"), max_length=200, db_index=True)
    region = models.CharField(
        _("지역"), max_length=20, choices=Region.choices, default=Region.ALL,
        db_index=True,
    )
    address = models.CharField(_("주소"), max_length=300, blank=True)
    phone = models.CharField(_("전화번호"), max_length=30, blank=True)
    description = models.TextField(_("센터 소개"), blank=True)
    operating_hours = models.CharField(
        _("운영 시간"), max_length=200, blank=True,
        help_text="예: 평일 06:00-23:00 / 주말 08:00-22:00",
    )
    pricing = models.CharField(
        _("요금 정보"), max_length=300, blank=True,
        help_text="예: 1시간 ₩10,000",
    )
    court_count = models.PositiveIntegerField(_("코트 수"), default=0)
    amenities = models.CharField(
        _("편의 시설"), max_length=300, blank=True,
        help_text="쉼표 구분: 샤워실, 락커, 주차장",
    )
    cover_image = WebPImageField(_("커버 이미지"), upload_to="centers/", blank=True, null=True)
    latitude = models.FloatField(_("위도"), null=True, blank=True)
    longitude = models.FloatField(_("경도"), null=True, blank=True)

    is_published = models.BooleanField(
        _("공개"), default=True, db_index=True,
        help_text="해제하면 목록/상세 모두 비공개",
    )

    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)

    class Meta:
        verbose_name = _("배드민턴 센터")
        verbose_name_plural = _("배드민턴 센터")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["region", "is_published", "-created_at"]),
        ]

    def __str__(self):
        return self.name


class CenterBookmark(models.Model):
    """센터 관심 등록."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="center_bookmarks",
        verbose_name=_("사용자"),
    )
    center = models.ForeignKey(
        Center,
        on_delete=models.CASCADE,
        related_name="bookmarks",
        verbose_name=_("센터"),
    )
    created_at = models.DateTimeField(_("등록일"), auto_now_add=True)

    class Meta:
        verbose_name = _("센터 북마크")
        verbose_name_plural = _("센터 북마크")
        unique_together = [("user", "center")]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["center", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user} ★ {self.center}"
