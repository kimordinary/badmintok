from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


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


class Contest(models.Model):
    category = models.ForeignKey(
        ContestCategory,
        on_delete=models.SET_NULL,
        related_name="contests",
        blank=True,
        null=True,
        verbose_name="분류",
    )
    title = models.CharField("대회명", max_length=200)
    slug = models.SlugField("슬러그", unique=True, help_text="URL에서 사용할 고유 값입니다.")
    image = models.ImageField("이미지", upload_to="contest_images/", blank=True, null=True)
    schedule_start = models.DateField("대회 시작일")
    schedule_end = models.DateField("대회 종료일", blank=True, null=True)
    location = models.CharField("장소", max_length=200)
    event_division = models.CharField("급수 (종목 / 연령 / 급수)", max_length=255)
    registration_start = models.DateField("접수 시작일")
    registration_end = models.DateField("접수 종료일")
    entry_fee = models.CharField("접수비", max_length=100, blank=True)
    competition_type = models.CharField("대회구", max_length=100, blank=True)
    participant_reward = models.CharField("참가상품", max_length=255, blank=True)
    sponsor = models.CharField("스폰서", max_length=255, blank=True)
    award_reward = models.JSONField("입상상품", blank=True, null=True, help_text="JSON 형식으로 입력하세요.")
    registration_link = models.URLField("접수 링크", blank=True)
    description = models.TextField("상세 설명", blank=True)
    created_at = models.DateTimeField("등록일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["-schedule_start", "-created_at"]
        verbose_name = "배드민턴 대회"
        verbose_name_plural = "배드민턴 대회"

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

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Contest.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.award_reward in (None, "", {}, []):
            self.award_reward = []
            return

        structured = []

        def normalize_prizes(prizes_value):
            prize_list = []
            if isinstance(prizes_value, dict):
                for rank, prize in prizes_value.items():
                    prize_list.append({"rank": str(rank), "prize": str(prize)})
            elif isinstance(prizes_value, list):
                for item in prizes_value:
                    if not isinstance(item, dict) or "rank" not in item or "prize" not in item:
                        raise ValidationError({"award_reward": "입상상품의 prizes 항목은 rank와 prize를 포함해야 합니다."})
                    prize_list.append({"rank": str(item["rank"]), "prize": str(item["prize"])})
            else:
                raise ValidationError({"award_reward": "입상상품의 prizes 형식이 올바르지 않습니다."})
            return prize_list

        if isinstance(self.award_reward, dict):
            ordered = OrderedDict(self.award_reward)
            for division, prizes in ordered.items():
                structured.append({"division": str(division), "prizes": normalize_prizes(prizes)})
        elif isinstance(self.award_reward, list):
            for entry in self.award_reward:
                if not isinstance(entry, dict):
                    raise ValidationError({"award_reward": "입상상품은 JSON 객체 또는 객체 리스트여야 합니다."})
                division = entry.get("division")
                prizes = entry.get("prizes")
                if not division or prizes is None:
                    raise ValidationError({"award_reward": "입상상품 각 항목은 division과 prizes를 포함해야 합니다."})
                structured.append({"division": str(division), "prizes": normalize_prizes(prizes)})
        else:
            raise ValidationError({"award_reward": "입상상품은 JSON 객체 또는 객체 리스트여야 합니다."})

        self.award_reward = structured
