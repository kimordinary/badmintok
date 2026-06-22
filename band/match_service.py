"""대진 세션 생성 로직 (서버 API·웹 콘솔 공용).

웹 '번개 시작'(schedule_console)과 앱 start API가 동일한 방식으로 MatchSession을
만들도록 하여, 어느 경로로 시작하든 참가자 앱이 세션에 연결되게 한다.
"""
from django.db import transaction, IntegrityError

from band.models import BandScheduleApplication
from band.match_models import MatchSession, Court, SessionParticipant
from band.matchmaking.scoring import level_to_score


def _level_gender(user):
    profile = getattr(user, "profile", None)
    level = getattr(profile, "badminton_level", "") if profile else ""
    gender = getattr(profile, "gender", "unknown") if profile else "unknown"
    return level_to_score(level), gender


def create_session_snapshot(schedule, created_by, court_count=4, mode=None, preset=None):
    """MatchSession + 코트 + 승인 신청자 스냅샷 생성. 호출 전 중복 여부는 확인할 것."""
    mode = mode or MatchSession.DisciplineMode.ALL
    preset = preset or MatchSession.Preset.BALANCED
    with transaction.atomic():
        session = MatchSession.objects.create(
            schedule=schedule, court_count=court_count,
            discipline_mode=mode, preset=preset, created_by=created_by)
        for i in range(1, court_count + 1):
            Court.objects.create(session=session, index=i)
        apps = BandScheduleApplication.objects.filter(
            schedule=schedule, status="approved").select_related("user")
        for app in apps:
            score, gender = _level_gender(app.user)
            # 자가 체크인(checked_in_at)한 사람은 바로 참여중, 아니면 미출석
            attendance = (SessionParticipant.Attendance.PRESENT if app.checked_in_at
                          else SessionParticipant.Attendance.NOT_PRESENT)
            SessionParticipant.objects.create(
                session=session, user=app.user, base_level=score, gender=gender,
                attendance=attendance)
    return session


def ensure_session(schedule, created_by, court_count=4):
    """순수 get-or-create. 이미 있으면 그대로 반환(재생성·덮어쓰기 절대 안 함).

    세션이 있으면 손대지 않는다. 없을 때만 생성하며, 동시 진입(레이스)으로
    다른 요청이 먼저 만든 경우엔 unique 제약 → 그 세션을 그대로 반환한다.
    """
    existing = getattr(schedule, "match_session", None)
    if existing is not None:
        return existing
    try:
        return create_session_snapshot(schedule, created_by, court_count=court_count)
    except IntegrityError:
        # 동시 진입: 먼저 만들어진 세션을 반환 (덮어쓰지 않음)
        return MatchSession.objects.get(schedule=schedule)
