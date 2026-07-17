from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from band.models import BandSchedule


class MatchSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", _("진행중")
        ENDED = "ended", _("종료")

    class DisciplineMode(models.TextChoices):
        MIXED_ONLY = "mixed_only", _("혼복만")
        SINGLES_GENDER = "singles_gender", _("남복·여복만")
        ALL = "all", _("전부 섞기")

    class Preset(models.TextChoices):
        BALANCED = "balanced", _("균형파")
        COMPETITIVE = "competitive", _("박빙파")

    schedule = models.OneToOneField(
        BandSchedule, on_delete=models.CASCADE,
        related_name="match_session", verbose_name=_("번개 일정"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    discipline_mode = models.CharField(
        max_length=20, choices=DisciplineMode.choices, default=DisciplineMode.ALL)
    preset = models.CharField(max_length=12, choices=Preset.choices, default=Preset.BALANCED)
    female_adjust = models.IntegerField(default=1)
    court_count = models.IntegerField(default=4)
    # 자동 배치(경기 종료 시 다음 경기 자동 투입) on/off. False(수동)면 예약만 투입하고 코트는 비워둔다.
    auto = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="match_sessions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("대진 세션")
        verbose_name_plural = _("대진 세션")


class SessionParticipant(models.Model):
    class Attendance(models.TextChoices):
        NOT_PRESENT = "not_present", _("미출석")
        PRESENT = "present", _("참여중")
        LEFT = "left", _("퇴장")

    session = models.ForeignKey(
        MatchSession, on_delete=models.CASCADE, related_name="participants")
    # 임시(현장) 인원은 계정이 없으므로 user=None + guest_name 사용
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    guest_name = models.CharField(max_length=50, blank=True)
    attendance = models.CharField(
        max_length=12, choices=Attendance.choices, default=Attendance.NOT_PRESENT)
    # 세션 시작 시점 스냅샷 (가입 정보가 바뀌어도 세션 내 일관)
    base_level = models.IntegerField()  # 1..7
    gender = models.CharField(max_length=10)  # male | female
    # 회원 급수·성별을 운영자가 세션에서 덮어썼는지. True면 프로필 대신 위 스냅샷 사용
    overridden = models.BooleanField(default=False)
    games_mixed = models.IntegerField(default=0)
    games_mens = models.IntegerField(default=0)
    games_womens = models.IntegerField(default=0)
    last_game_ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["session", "user"]]
        verbose_name = _("대진 참가자")
        verbose_name_plural = _("대진 참가자")

    @property
    def display_name(self):
        # guest_name은 현장 인원 이름 + 세션 내 표시 이름 override 겸용(프로필 원본 불변)
        return self.guest_name or (self.user.activity_name if self.user_id else "임시")

    @property
    def display_real_name(self):
        # 대진 현장 확인용 — 회원은 실명(user.real_name이 실명 없으면 활동명 폴백),
        # 게스트/운영자 편집 이름은 guest_name 그대로.
        return self.guest_name or (self.user.real_name if self.user_id else "임시")

    def live_level_gender(self):
        """매칭·표시용 (base_level, gender).
        회원은 accounts 프로필을 실시간 참조해 프로필 변경을 즉시 반영하고,
        게스트(현장 인원)는 생성 시 입력한 스냅샷 값을 그대로 쓴다.
        단, 운영자가 세션에서 덮어썼으면(overridden) 회원도 스냅샷을 쓴다(프로필 원본 불변).
        """
        if not self.user_id or self.overridden:
            return self.base_level, self.gender
        from band.matchmaking.scoring import level_to_score
        profile = getattr(self.user, "profile", None)
        level = getattr(profile, "badminton_level", "") if profile else ""
        raw = getattr(profile, "gender", None) if profile else None
        gender = raw if raw in ("male", "female") else "unknown"
        return level_to_score(level), gender

    def is_match_eligible(self):
        """매칭 pool 자격. 회원은 프로필(실명·성별·급수) 완성 시에만,
        게스트(현장 인원)는 계정·프로필이 없으므로 항상 자격 있음.
        입구 체크인 게이트와 동일 기준(User.match_profile_ready)으로 일관 유지.
        """
        if not self.user_id:
            return True
        return self.user.match_profile_ready


class Court(models.Model):
    session = models.ForeignKey(MatchSession, on_delete=models.CASCADE, related_name="courts")
    index = models.IntegerField()  # 1..court_count
    name = models.CharField(max_length=50, blank=True)  # 코트 이름(선택). 비우면 'N번 코트'
    # 코치(자강) 고정 코트: 지정 시 매 경기 이 코치가 그 코트에 고정
    coach = models.ForeignKey(
        SessionParticipant, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="coaching_courts")

    class Meta:
        unique_together = [["session", "index"]]
        ordering = ["index"]


class Match(models.Model):
    class Status(models.TextChoices):
        PLAYING = "playing", _("진행중")
        DONE = "done", _("종료")

    class Discipline(models.TextChoices):
        MIXED = "mixed", _("혼복")
        MENS = "mens", _("남복")
        WOMENS = "womens", _("여복")

    session = models.ForeignKey(MatchSession, on_delete=models.CASCADE, related_name="matches")
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name="matches")
    discipline = models.CharField(max_length=10, choices=Discipline.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLAYING)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("경기")
        verbose_name_plural = _("경기")


class MatchPlayer(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="players")
    participant = models.ForeignKey(SessionParticipant, on_delete=models.CASCADE)
    team = models.IntegerField()  # 1 | 2

    class Meta:
        unique_together = [["match", "participant"]]


class Pair(models.Model):
    """고정 2인 팀 ('둘이 같이 쳐주세요'). 종목은 두 사람 성별로 자동 결정."""
    session = models.ForeignKey(MatchSession, on_delete=models.CASCADE, related_name="pairs")
    p1 = models.ForeignKey(SessionParticipant, on_delete=models.CASCADE, related_name="pair_as_p1")
    p2 = models.ForeignKey(SessionParticipant, on_delete=models.CASCADE, related_name="pair_as_p2")
    strict = models.BooleanField(default=False)  # True=같이만 / False=따로도 OK(best-effort)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("파트너 쌍")
        verbose_name_plural = _("파트너 쌍")


class PartnerRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("대기")
        APPROVED = "approved", _("승인")
        REJECTED = "rejected", _("거절")

    session = models.ForeignKey(
        MatchSession, on_delete=models.CASCADE, related_name="partner_requests")
    from_participant = models.ForeignKey(
        SessionParticipant, on_delete=models.CASCADE, related_name="partner_requests_sent")
    to_participant = models.ForeignKey(
        SessionParticipant, on_delete=models.CASCADE, related_name="partner_requests_received")
    strict = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("파트너 신청")
        verbose_name_plural = _("파트너 신청")


class ReservedMatch(models.Model):
    """운영자가 대기열에서 4명을 골라 예약한 '이후 예정' 경기.
    코트가 비면 자동 추천보다 우선 투입된다. 예약된 4명은 그동안 일반 풀에서 제외(확보)."""

    session = models.ForeignKey(
        MatchSession, on_delete=models.CASCADE, related_name="reservations")
    # 비우면 4명 성별로 자동 결정 (mens/womens/mixed)
    discipline = models.CharField(
        max_length=10, choices=Match.Discipline.choices, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("예약 경기")
        verbose_name_plural = _("예약 경기")
        ordering = ["created_at"]


class ReservedMatchPlayer(models.Model):
    reservation = models.ForeignKey(
        ReservedMatch, on_delete=models.CASCADE, related_name="players")
    participant = models.ForeignKey(SessionParticipant, on_delete=models.CASCADE)

    class Meta:
        unique_together = [["reservation", "participant"]]
