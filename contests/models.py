from datetime import date
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from badmintok.fields import WebPImageField


class ContestCategory(models.Model):
    name = models.CharField("분류명", max_length=100)
    color = models.CharField("색상", max_length=7, help_text="예: #31AA60")
    description = models.CharField("설명", max_length=255, blank=True)

    class Meta:
        verbose_name = "대회 분류"
        verbose_name_plural = "대회 분류"
        ordering = ["name"]

    def __str__(self):
        return self.name


def contest_image_upload_to(instance, filename):
    """대회 이미지 파일명 생성 함수 - 파일명을 안전하게 처리"""
    # 파일 확장자 추출
    ext = os.path.splitext(filename)[1].lower()
    # UUID를 사용하여 고유 파일명 생성 (한글/특수문자 문제 해결)
    unique_filename = f"{uuid.uuid4().hex[:12]}{ext}"
    return f"contest_images/{unique_filename}"


def contest_pdf_upload_to(instance, filename):
    """대회 요강 PDF 파일명 생성 함수 - 파일명을 안전하게 처리"""
    # 파일 확장자 추출
    ext = os.path.splitext(filename)[1].lower()
    # UUID를 사용하여 고유 파일명 생성 (한글/특수문자 문제 해결)
    unique_filename = f"{uuid.uuid4().hex[:12]}{ext}"
    return f"contest_pdfs/{unique_filename}"


class Sponsor(models.Model):
    name = models.CharField("스폰서명", max_length=100, unique=True)

    class Meta:
        verbose_name = "스폰서"
        verbose_name_plural = "스폰서"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Contest(models.Model):
    class Region(models.TextChoices):
        SEOUL = "서울", "서울"
        GYEONGGI = "경기", "경기"
        INCHEON = "인천", "인천"
        BUSAN = "부산", "부산"
        DAEGU = "대구", "대구"
        GWANGJU = "광주", "광주"
        DAEJEON = "대전", "대전"
        ULSAN = "울산", "울산"
        GANGWON = "강원", "강원"
        SEJONG = "세종", "세종"
        CHUNGBUK = "충북", "충북"
        CHUNGNAM = "충남", "충남"
        JEONBUK = "전북", "전북"
        JEONNAM = "전남", "전남"
        GYEONGBUK = "경북", "경북"
        GYEONGNAM = "경남", "경남"
        JEJU = "제주", "제주"

    category = models.ForeignKey(
        ContestCategory,
        on_delete=models.SET_NULL,
        related_name="contests",
        blank=True,
        null=True,
        verbose_name="분류",
    )
    is_qualifying = models.BooleanField(
        "승급 대회",
        default=False,
        help_text="승급 대회인 경우 체크하세요. 비승급 대회는 체크하지 않습니다.",
    )
    title = models.CharField("대회명", max_length=200)
    slug = models.SlugField("슬러그", unique=True, max_length=37, allow_unicode=True, help_text="URL에서 사용할 고유 값입니다.")
    schedule_start = models.DateField("대회 시작일")
    schedule_end = models.DateField("대회 종료일", blank=True, null=True)
    region = models.CharField("지역", max_length=20, choices=Region.choices, default=Region.SEOUL)
    region_detail = models.CharField("상세 장소", max_length=200, blank=True)
    registration_start = models.DateField("접수 시작일", blank=True, null=True)
    registration_end = models.DateField("접수 종료일", blank=True, null=True)
    entry_fee = models.CharField("접수비", max_length=100, blank=True)
    competition_type = models.CharField("대회구", max_length=100, blank=True)
    sponsor = models.ForeignKey(
        "Sponsor",
        on_delete=models.SET_NULL,
        related_name="contests",
        blank=True,
        null=True,
        verbose_name="스폰서",
    )
    registration_name = models.CharField("접수처 이름", max_length=200, blank=True, help_text="접수처 이름을 입력하세요. 예: 배드민톡, 네이버 등")
    registration_link = models.URLField("접수 링크", blank=True)
    description = models.TextField("대회 요강 AI 요약", blank=True)
    pdf_file = models.FileField("대회 요강 PDF", upload_to=contest_pdf_upload_to, blank=True, null=True, help_text="대회 요강 원본 PDF 파일을 업로드하세요.")
    participant_target = models.TextField("참가 대상 (종목 / 연령 / 급수)", blank=True, help_text="참가 대상, 종목, 연령, 급수 정보를 입력하세요.")
    participant_events = models.CharField("종목", max_length=200, blank=True, help_text="예: 남복, 여복, 혼복, 단식")
    participant_ages = models.CharField("연령", max_length=200, blank=True, help_text="예: 20대 ~ 60대, 전연령")
    participant_grades = models.CharField("급수", max_length=200, blank=True, help_text="예: A, B, C, D, 초심, 입문")
    award_reward_text = models.TextField("입상상품", blank=True, help_text="입상상품에 대한 상세 정보를 입력하세요.")
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="liked_contests", blank=True, verbose_name="좋아요")
    view_count = models.PositiveIntegerField("조회수", default=0)
    created_at = models.DateTimeField("등록일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["schedule_start", "-created_at"]
        verbose_name = "전국 배드민턴 대회"
        verbose_name_plural = "전국 배드민턴 대회"

    def __str__(self):
        return self.title

    def get_period_display(self):
        if self.schedule_end and self.schedule_end != self.schedule_start:
            return f"{self.schedule_start:%Y.%m.%d} ~ {self.schedule_end:%Y.%m.%d}"
        return f"{self.schedule_start:%Y.%m.%d}"

    def get_registration_period_display(self):
        if self.registration_end and self.registration_end != self.registration_start:
            return f"{self.registration_start:%Y.%m.%d} ~ {self.registration_end:%Y.%m.%d}"
        return f"{self.registration_start:%Y.%m.%d}"

    def get_d_day(self):
        """대회 시작일 기준 D-day를 계산합니다."""
        if not self.schedule_start:
            return None
        today = date.today()
        delta = (self.schedule_start - today).days
        return delta

    def get_d_day_display(self):
        """대회 시작일 기준 D-day를 표시용 문자열로 반환합니다."""
        d_day = self.get_d_day()
        if d_day is None:
            return None
        if d_day < 0:
            return "종료"
        elif d_day == 0:
            return "D-Day"
        else:
            return f"D-{d_day}"

    def get_location_display(self):
        """장소를 '[지역] 상세주소' 형식으로 반환합니다."""
        region_name = self.get_region_display()
        if self.region_detail:
            return f"[{region_name}] {self.region_detail}"
        return f"[{region_name}]"

    @property
    def like_count(self):
        """좋아요 개수를 반환합니다."""
        return self.likes.count()

    def increase_view_count(self):
        """조회수 증가"""
        self.view_count += 1
        self.save(update_fields=["view_count"])

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title, allow_unicode=True)
            slug = base_slug
            counter = 1
            while Contest.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        # 대회 일정 검증: 종료일이 시작일보다 이전이면 오류
        if self.schedule_end and self.schedule_start and self.schedule_end < self.schedule_start:
            raise ValidationError({"schedule_end": "대회 종료일은 시작일보다 이후여야 합니다."})
        # 접수 일정 검증: 종료일이 시작일보다 이전이면 오류
        if self.registration_end and self.registration_start and self.registration_end < self.registration_start:
            raise ValidationError({"registration_end": "접수 종료일은 시작일보다 이후여야 합니다."})



class ContestSchedule(models.Model):
    EVENT_CHOICES = (
        ("혼복", "혼복"),
        ("여복", "여복"),
        ("남복", "남복"),
        ("단식", "단식"),
        ("준자강", "준자강"),
        ("자강", "자강"),
    )
    AGE_CHOICES = (
        ("10대", "10대"),
        ("20대", "20대"),
        ("30대", "30대"),
        ("40대", "40대"),
        ("50대", "50대"),
        ("60대", "60대"),
        ("70대", "70대"),
        ("전연령", "전연령"),
    )
    
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="schedules",
        verbose_name="대회",
    )
    date = models.DateField("경기일")
    events = models.JSONField("경기 종목", blank=True, null=True, help_text="혼복/여복/남복 복수 선택")
    ages = models.JSONField("연령대", blank=True, null=True, help_text="10대~70대 또는 전연령 복수 선택")
    created_at = models.DateTimeField("등록일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["date", "id"]
        verbose_name = "경기 일정"
        verbose_name_plural = "경기 일정"

    def __str__(self):
        return f"{self.contest.title} - {self.date}"

    def get_events_display(self):
        if not self.events:
            return []
        if isinstance(self.events, list):
            # 중복 제거하고 순서 유지
            seen = set()
            result = []
            for event in self.events:
                if event not in seen:
                    seen.add(event)
                    result.append(event)
            return result
        return []

    def get_age_display(self):
        if not self.ages:
            return ""
        if not isinstance(self.ages, list):
            return ""

        ages = [a for a in self.ages if isinstance(a, str)]
        if "전연령" in ages:
            return "전연령"

        order = ["10대", "20대", "30대", "40대", "50대", "60대", "70대"]
        idx = {v: i for i, v in enumerate(order)}
        ages_sorted = sorted([a for a in ages if a in idx], key=lambda x: idx[x])

        # 연속 구간 압축
        ranges = []
        start = None
        prev = None
        for age in ages_sorted:
            if start is None:
                start = age
                prev = age
                continue
            if idx[age] == idx[prev] + 1:
                prev = age
            else:
                ranges.append((start, prev))
                start = age
                prev = age
        if start:
            ranges.append((start, prev))

        parts = []
        for s, e in ranges:
            parts.append(f"{s}~{e}" if s != e else s)
        return ", ".join(parts)

    # ContestSchedule does not override save/clean; no extra logic needed.


class ContestImage(models.Model):
    """대회 이미지 (여러 장 업로드 가능)"""
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="대회",
    )
    image = WebPImageField("이미지", upload_to=contest_image_upload_to)
    order = models.PositiveIntegerField("순서", default=0, help_text="이미지 표시 순서 (작은 숫자가 먼저 표시됨)")
    created_at = models.DateTimeField("등록일", auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "대회 이미지"
        verbose_name_plural = "대회 이미지"

    def __str__(self):
        return f"{self.contest.title} - 이미지 {self.order}"
