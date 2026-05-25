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
        ETC = "기타", "기타"

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
    slug = models.SlugField("슬러그", unique=True, max_length=100, allow_unicode=True, help_text="URL에서 사용할 고유 값입니다.")
    schedule_start = models.DateField("대회 시작일")
    schedule_end = models.DateField("대회 종료일", blank=True, null=True)
    region = models.CharField("지역", max_length=20, choices=Region.choices, default=Region.SEOUL)
    region_detail = models.CharField("상세 장소", max_length=200, blank=True)
    registration_start = models.DateField("접수 시작일", blank=True, null=True)
    registration_end = models.DateField("접수 종료일", blank=True, null=True)
    entry_fee = models.CharField("접수비", max_length=100, blank=True)
    competition_type = models.CharField("대회구", max_length=100, blank=True)
    shuttlecock = models.CharField("사용구", max_length=100, blank=True, help_text="예: 닉텐 T-Black, 요넥스 AS-50 등")
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
    award_reward_text = models.TextField("입상상품 (텍스트)", blank=True, help_text="기존 입상상품 텍스트. 조별 입상상품이 등록되면 조별 데이터가 우선 표시됩니다.")
    participation_prize = models.CharField("참가상", max_length=200, blank=True, help_text="예: 셔틀콕 1통, 수건 등")
    raffle_prize = models.CharField("경품", max_length=200, blank=True, help_text="예: 라켓 추첨, 가방 추첨 등")
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="liked_contests", blank=True, verbose_name="좋아요")
    view_count = models.PositiveIntegerField("조회수", default=0)
    is_test = models.BooleanField(
        "테스트 데이터",
        default=False,
        help_text="자동 업로더 테스트용 데이터. 관리자 목록에서 일괄 필터·삭제에 사용합니다.",
    )
    created_at = models.DateTimeField("등록일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["schedule_start", "-created_at"]
        verbose_name = "전국 배드민턴 대회"
        verbose_name_plural = "전국 배드민턴 대회"
        indexes = [
            models.Index(fields=["title", "schedule_start"], name="contest_title_start_idx"),
            models.Index(fields=["is_test"], name="contest_is_test_idx"),
        ]

    def __str__(self):
        return self.title

    DAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]

    def get_period_display(self):
        if not self.schedule_start:
            return "-"
        start_day = self.DAY_NAMES[self.schedule_start.weekday()]
        if self.schedule_end and self.schedule_end != self.schedule_start:
            end_day = self.DAY_NAMES[self.schedule_end.weekday()]
            if self.schedule_start.year == self.schedule_end.year:
                return f"{self.schedule_start:%Y.%m.%d}({start_day}) ~ {self.schedule_end:%m.%d}({end_day})"
            return f"{self.schedule_start:%Y.%m.%d}({start_day}) ~ {self.schedule_end:%Y.%m.%d}({end_day})"
        return f"{self.schedule_start:%Y.%m.%d}({start_day})"

    def get_registration_period_display(self):
        if not self.registration_start:
            return "-"
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

    # === SEO 메타·JSON-LD 헬퍼 ===

    def get_entry_fee_int(self):
        """접수비를 정수(원)로 반환. 파싱 불가/애매하면 None.

        OK   : "10000", "10,000원", "10,000 원" → 10000
        None : "무료", "미정", "1팀 5만원", "추후공지", "10000원 (현금)" 등
        """
        import re
        if not self.entry_fee:
            return None
        text = self.entry_fee.strip()
        # 단위/모호 키워드가 들어 있으면 None (offers 통째 생략)
        ambiguous = ['무료', '미정', '추후', '문의', '팀당', '조당', '쌍당',
                     '인당', '인 당', '만원', '천원', '별도']
        for kw in ambiguous:
            if kw in text:
                return None
        # 전체 문자열이 "숫자[+콤마] 원?" 형태일 때만 매칭 (그 외는 None)
        m = re.fullmatch(r'\s*(\d{1,3}(?:,\d{3})*|\d+)\s*원?\s*', text)
        if not m:
            return None
        try:
            return int(m.group(1).replace(',', ''))
        except ValueError:
            return None

    def get_seo_title(self):
        """SEO용 <title>. 대회명에 이미 지역·연도가 포함되므로 중복 제거.

        패턴:
        - 참가비 정수 파싱 가능: "{대회명} 일정·참가비·요강 | 배드민톡"
        - 파싱 불가(무료/미정 등):  "{대회명} 일정·요강 | 배드민톡"
        """
        if self.get_entry_fee_int() is not None:
            suffix = "일정·참가비·요강"
        else:
            suffix = "일정·요강"
        return f"{self.title} {suffix} | 배드민톡"

    def get_seo_description(self):
        """SEO용 meta description. 빈 필드는 문구 자체를 생략.

        형태: "{대회명} {일자}, {지역 [상세장소]}, 참가비 {N}원, 주최 {스폰서}. 접수 {기간}. 종목 {종목}."
        """
        bits = [self.title]
        # 일자
        if self.schedule_start:
            bits.append(self.get_period_display())
        # 장소 (region_detail 있으면 우선)
        region_name = self.get_region_display() or ''
        if region_name:
            if self.region_detail:
                bits.append(f"{region_name} {self.region_detail}")
            else:
                bits.append(region_name)
        # 참가비 (정수 파싱 성공 시만)
        fee = self.get_entry_fee_int()
        if fee:
            bits.append(f"참가비 {fee:,}원")
        # 주최
        if self.sponsor:
            bits.append(f"주최 {self.sponsor.name}")
        head = ", ".join(bits)

        # 마지막 문장 (접수/종목)
        tail_bits = []
        if self.registration_start or self.registration_end:
            tail_bits.append(f"접수 {self.get_registration_period_display()}")
        if self.participant_events:
            tail_bits.append(f"종목 {self.participant_events}")
        tail = ". " + ", ".join(tail_bits) + "." if tail_bits else "."

        return (head + tail).strip()

    @staticmethod
    def _josa(word, with_jongsung, without_jongsung):
        """한국어 조사 자동 처리 (받침 유무 판정).

        예: _josa("대회", "은", "는") → "는", _josa("대회장", "은", "는") → "은"
        """
        if not word:
            return without_jongsung
        last = word[-1]
        if not ('가' <= last <= '힣'):
            return without_jongsung
        code = ord(last) - 0xAC00
        return with_jongsung if code % 28 != 0 else without_jongsung

    def get_seo_body_text(self):
        """본문에 노출할 자동 생성 문장.

        검색의도("OO대회 일정·참가비·장소")에 본문이 직접 답하게.
        빈 필드는 문장 단위로 통째 생략하여 자연스러운 한국어 문단을 만든다.
        모든 핵심 필드가 비어 있으면 빈 문자열 반환 (호출 측에서 표시 안 함).
        """
        sentences = []

        # 1문장: 어디서 언제 열리는지
        region_name = self.get_region_display() or ''
        place = self.region_detail or region_name
        when = self.get_period_display() if self.schedule_start else ''
        if place and when:
            sentences.append(f"{self.title}{self._josa(self.title, '은', '는')} {when} {place}에서 열리는 배드민턴 대회입니다.")
        elif when:
            sentences.append(f"{self.title}{self._josa(self.title, '은', '는')} {when}에 열리는 배드민턴 대회입니다.")
        elif place:
            sentences.append(f"{self.title}{self._josa(self.title, '은', '는')} {place}에서 열리는 배드민턴 대회입니다.")

        # 2문장: 종목 / 연령 / 급수
        target_bits = []
        if self.participant_events:
            target_bits.append(f"종목은 {self.participant_events}")
        if self.participant_ages:
            target_bits.append(f"참가 연령은 {self.participant_ages}")
        if self.participant_grades:
            target_bits.append(f"급수는 {self.participant_grades}")
        if target_bits:
            sentences.append(", ".join(target_bits) + "입니다.")

        # 3문장: 참가비 + 주최
        fee_int = self.get_entry_fee_int()
        fee_part = f"참가비는 {fee_int:,}원" if fee_int is not None else ""
        sponsor_part = f"주최는 {self.sponsor.name}" if self.sponsor else ""
        if fee_part and sponsor_part:
            sentences.append(f"{fee_part}, {sponsor_part}입니다.")
        elif fee_part:
            sentences.append(f"{fee_part}입니다.")
        elif sponsor_part:
            sentences.append(f"{sponsor_part}입니다.")

        # 4문장: 접수기간 + 접수처
        if self.registration_start or self.registration_end:
            reg_period = self.get_registration_period_display()
            if self.registration_name:
                sentences.append(f"접수는 {reg_period} 사이에 {self.registration_name}에서 받습니다.")
            else:
                sentences.append(f"접수는 {reg_period} 사이에 진행됩니다.")

        return " ".join(sentences)

    def get_jsonld(self, request=None):
        """schema.org SportsEvent JSON-LD dict.

        빈 값은 해당 키 자체를 생략 (가짜 데이터 금지).
        request가 주어지면 url/image는 절대 URL로 빌드.
        """
        from django.urls import reverse

        def abs_url(path):
            if not path:
                return None
            if request:
                return request.build_absolute_uri(path)
            return path

        data = {
            "@context": "https://schema.org",
            "@type": "SportsEvent",
            "name": self.title,
            "url": abs_url(reverse('contests:detail', args=[self.slug])),
            "sport": "Badminton",
            "eventStatus": "https://schema.org/EventScheduled",
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        }

        # 일자
        if self.schedule_start:
            data["startDate"] = self.schedule_start.isoformat()
        if self.schedule_end:
            data["endDate"] = self.schedule_end.isoformat()

        # 설명
        desc = self.get_seo_description()
        if desc:
            data["description"] = desc

        # 이미지 (있을 때만)
        first_img = (
            self.images.order_by('order', 'id').first()
            if self.pk else None
        )
        if first_img and first_img.image:
            img_url = abs_url(first_img.image.url)
            if img_url:
                data["image"] = img_url

        # 장소 (region은 항상 있음)
        region_name = self.get_region_display() or ''
        if region_name:
            place_name = self.region_detail if self.region_detail else region_name
            address = {
                "@type": "PostalAddress",
                "addressLocality": region_name,
                "addressCountry": "KR",
            }
            if self.region_detail:
                address["streetAddress"] = self.region_detail
            data["location"] = {
                "@type": "Place",
                "name": place_name,
                "address": address,
            }

        # 주최 (sponsor 있을 때만)
        if self.sponsor:
            data["organizer"] = {
                "@type": "Organization",
                "name": self.sponsor.name,
            }

        # 참가비 (숫자 파싱 성공 시만)
        fee = self.get_entry_fee_int()
        if fee is not None:
            offers = {
                "@type": "Offer",
                "price": str(fee),
                "priceCurrency": "KRW",
                "availability": "https://schema.org/InStock",
            }
            if self.registration_link:
                offers["url"] = self.registration_link
            if self.registration_start:
                offers["validFrom"] = self.registration_start.isoformat()
            data["offers"] = offers

        return data

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
    description = models.CharField("일정 설명", max_length=500, blank=True, help_text="직접 입력 시 체크박스 대신 이 내용이 표시됩니다. 예: 혼복 전 경기, 60대 이상 남·여복 전 경기")
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


class ContestPrize(models.Model):
    """대회 입상상품 (조별)"""
    DIVISION_CHOICES = (
        ("동호인조", "동호인조"),
        ("준자강조", "준자강조"),
        ("자강조", "자강조"),
    )

    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="prizes",
        verbose_name="대회",
    )
    division = models.CharField("조 구분", max_length=100, help_text="동호인조, 준자강조, 자강조 등")
    first_prize = models.CharField("1위 상품", max_length=200, blank=True)
    second_prize = models.CharField("2위 상품", max_length=200, blank=True)
    third_prize = models.CharField("3위 상품", max_length=200, blank=True)
    created_at = models.DateTimeField("등록일", auto_now_add=True)
    updated_at = models.DateTimeField("수정일", auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "입상상품 (조별)"
        verbose_name_plural = "입상상품 (조별)"

    def __str__(self):
        return f"{self.contest.title} - {self.division}"


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
