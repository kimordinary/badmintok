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

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["activity_name"]

    objects = UserManager()

    def __str__(self):
        return self.activity_name or self.email

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
    location=settings.BASE_DIR / "static",
    base_url=settings.STATIC_URL,
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
