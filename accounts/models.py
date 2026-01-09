from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("이메일은 필수 값입니다.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser는 is_staff=True 여야 합니다.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser는 is_superuser=True 여야 합니다.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(_("이메일"), unique=True)
    activity_name = models.CharField(_("활동명"), max_length=150)
    auth_provider = models.CharField(
        _("인증 제공자"),
        max_length=20,
        blank=True,
        null=True,
        help_text="소셜 로그인 제공자 (kakao, google 등). 일반 회원가입은 비어있음."
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["activity_name"]
    
    # 모임 생성 제한 필드
    band_creation_blocked_until = models.DateTimeField(
        _("모임 생성 제한 일시"),
        blank=True,
        null=True,
        help_text="이 일시까지 모임을 생성할 수 없습니다."
    )

    objects = UserManager()

    def __str__(self):
        return self.activity_name or self.email
    
    @property
    def is_social_auth(self):
        """소셜 로그인으로 가입한 사용자인지 확인"""
        return bool(self.auth_provider)

    @property
    def real_name(self):
        """실명 반환 (웹민턴용)"""
        profile = getattr(self, "profile", None)
        if profile and profile.name:
            return profile.name
        return self.activity_name  # 실명이 없으면 활동명 반환

    @property
    def profile_image_url(self):
        default_url = static("images/userprofile/user.png")
        profile = getattr(self, "profile", None)
        if not profile:
            return default_url
        image = profile.profile_image
        if not image:
            return default_url
        if image.name == "images/userprofile/user.png":
            return default_url
        return image.url


profile_storage = FileSystemStorage(
    location=settings.MEDIA_ROOT,
    base_url=settings.MEDIA_URL,
)


class UserProfile(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", _("남성")
        FEMALE = "female", _("여성")
        OTHER = "other", _("기타")
        UNKNOWN = "unknown", _("선택 안 함")

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_image = models.ImageField(
        _("프로필 사진"),
        storage=profile_storage,
        upload_to="images/userprofile/",
        blank=True,
        null=True,
        default="images/userprofile/user.png",
    )
    name = models.CharField(_("이름"), max_length=100, blank=True)
    
    class BadmintonLevel(models.TextChoices):
        BEGINNER = "beginner", _("왕초심")
        D = "d", _("D")
        C = "c", _("C")
        B = "b", _("B")
        A = "a", _("A")
        S = "s", _("S")
        MASTER = "master", _("자강")
        NONE = "", _("미입력")
    
    badminton_level = models.CharField(
        _("배드민턴 급수"),
        max_length=20,
        choices=BadmintonLevel.choices,
        blank=True,
        default="",
        help_text="배드민턴 실력 급수"
    )
    gender = models.CharField(_("성별"), max_length=10, choices=Gender.choices, default=Gender.UNKNOWN)
    age_range = models.CharField(_("연령대"), max_length=50, blank=True)
    birthday = models.DateField(_("생일"), blank=True, null=True)
    birth_year = models.PositiveIntegerField(_("출생연도"), blank=True, null=True)
    phone_number = models.CharField(_("전화번호"), max_length=20, blank=True)
    shipping_receiver = models.CharField(_("수령인명"), max_length=100, blank=True)
    shipping_phone_number = models.CharField(_("배송지 전화번호"), max_length=20, blank=True)
    shipping_address = models.TextField(_("배송지 주소"), blank=True)

    created_at = models.DateTimeField(_("생성일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)

    def __str__(self):
        return f"{self.user}의 프로필"


class UserBlock(models.Model):
    """사용자 차단 모델"""
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocked_users",
        verbose_name=_("차단한 사용자")
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocked_by_users",
        verbose_name=_("차단당한 사용자")
    )
    created_at = models.DateTimeField(_("차단일"), auto_now_add=True)

    class Meta:
        verbose_name = _("사용자 차단")
        verbose_name_plural = _("사용자 차단")
        unique_together = [["blocker", "blocked"]]
        indexes = [
            models.Index(fields=["blocker"]),
            models.Index(fields=["blocked"]),
        ]

    def __str__(self):
        return f"{self.blocker.activity_name}이(가) {self.blocked.activity_name}을(를) 차단"


class Report(models.Model):
    """신고 모델"""
    class ReportType(models.TextChoices):
        USER = "user", _("사용자")
        POST = "post", _("게시글")
        COMMENT = "comment", _("댓글")
        BAND = "band", _("모임")
        OTHER = "other", _("기타")

    class Status(models.TextChoices):
        PENDING = "pending", _("대기중")
        REVIEWING = "reviewing", _("검토중")
        RESOLVED = "resolved", _("처리완료")
        REJECTED = "rejected", _("기각")

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
        verbose_name=_("신고자")
    )
    report_type = models.CharField(_("신고 유형"), max_length=20, choices=ReportType.choices)
    target_id = models.PositiveIntegerField(_("대상 ID"), help_text="신고 대상의 ID")
    reason = models.TextField(_("신고 사유"))
    status = models.CharField(_("처리 상태"), max_length=20, choices=Status.choices, default=Status.PENDING)
    admin_note = models.TextField(_("관리자 메모"), blank=True)
    created_at = models.DateTimeField(_("신고일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)
    processed_at = models.DateTimeField(_("처리일"), blank=True, null=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="processed_reports",
        null=True,
        blank=True,
        verbose_name=_("처리자")
    )

    class Meta:
        verbose_name = _("신고")
        verbose_name_plural = _("신고")
        indexes = [
            models.Index(fields=["reporter"]),
            models.Index(fields=["report_type", "target_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.reporter.activity_name}의 {self.get_report_type_display()} 신고"


class Inquiry(models.Model):
    """문의하기 모델"""
    class Category(models.TextChoices):
        GENERAL = "general", _("일반 문의")
        TECHNICAL = "technical", _("기술 문의")
        BUG = "bug", _("버그 신고")
        SUGGESTION = "suggestion", _("건의사항")
        OTHER = "other", _("기타")

    class Status(models.TextChoices):
        PENDING = "pending", _("대기중")
        ANSWERED = "answered", _("답변완료")
        CLOSED = "closed", _("종료")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inquiries",
        verbose_name=_("문의자")
    )
    category = models.CharField(_("문의 유형"), max_length=20, choices=Category.choices, default=Category.GENERAL)
    title = models.CharField(_("제목"), max_length=200)
    content = models.TextField(_("내용"))
    status = models.CharField(_("상태"), max_length=20, choices=Status.choices, default=Status.PENDING)
    admin_response = models.TextField(_("관리자 답변"), blank=True)
    created_at = models.DateTimeField(_("문의일"), auto_now_add=True)
    updated_at = models.DateTimeField(_("수정일"), auto_now=True)
    answered_at = models.DateTimeField(_("답변일"), blank=True, null=True)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="answered_inquiries",
        null=True,
        blank=True,
        verbose_name=_("답변자")
    )

    class Meta:
        verbose_name = _("문의")
        verbose_name_plural = _("문의")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.activity_name}의 문의: {self.title}"
