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
        return self.user.activity_name if self.user_id else (self.guest_name or "임시")


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
