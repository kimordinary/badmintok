from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """알림 모델"""

    class Type(models.TextChoices):
        COMMENT = "comment", _("댓글")
        REPLY = "reply", _("답글")
        NOTICE = "notice", _("공지사항")
        BAND = "band", _("모임")
        SCHEDULE = "schedule", _("일정")
        SCHEDULE_NOTICE = "schedule_notice", _("일정 알림")
        APPLICATION = "application", _("참가신청")
        MEMBERSHIP = "membership", _("가입")
        LIKE = "like", _("좋아요")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("수신자"),
    )
    type = models.CharField(
        _("알림 유형"),
        max_length=20,
        choices=Type.choices,
    )
    title = models.CharField(_("제목"), max_length=200)
    message = models.TextField(_("내용"), blank=True)

    # 연결 대상 (범용)
    related_band_post = models.ForeignKey(
        "band.BandPost",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("관련 밴드 게시글"),
    )
    related_notice = models.ForeignKey(
        "badmintok.Notice",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("관련 공지사항"),
    )
    related_band_schedule = models.ForeignKey(
        "band.BandSchedule",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("관련 밴드 일정"),
    )
    related_band = models.ForeignKey(
        "band.Band",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("관련 밴드"),
    )
    related_community_post = models.ForeignKey(
        "community.Post",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("관련 커뮤니티 게시글"),
    )

    # 알림을 발생시킨 사용자 (댓글/답글 작성자)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
        verbose_name=_("발생자"),
    )

    is_read = models.BooleanField(_("읽음 여부"), default=False)
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)

    class Meta:
        verbose_name = _("알림")
        verbose_name_plural = _("알림")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        return f"[{self.get_type_display()}] {self.title} → {self.user}"


class DeviceToken(models.Model):
    """FCM 디바이스 토큰"""

    class Platform(models.TextChoices):
        ANDROID = "android", _("Android")
        IOS = "ios", _("iOS")
        WEB = "web", _("Web")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
        verbose_name=_("사용자"),
    )
    token = models.CharField(_("FCM 토큰"), max_length=512, unique=True)
    platform = models.CharField(
        _("플랫폼"), max_length=10, choices=Platform.choices, default=Platform.ANDROID
    )
    is_active = models.BooleanField(_("활성"), default=True)
    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("최근 갱신일"), auto_now=True)

    class Meta:
        verbose_name = _("디바이스 토큰")
        verbose_name_plural = _("디바이스 토큰")
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user} / {self.platform} / {self.token[:16]}..."
