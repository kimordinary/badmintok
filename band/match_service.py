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
    raw = getattr(profile, "gender", None) if profile else None
    # 성별 null·빈값·미정이면 'unknown'(무관)으로 폴백 → 성별 없어도 start 실패 안 함
    gender = raw if raw in ("male", "female") else "unknown"
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


def sync_approved_participants(session):
    """세션 시작 후 새로 승인된 신청자를 세션에 추가(빠진 사람만). 반환: 추가 수.
    이미 들어온 사람은 건드리지 않으므로 출석·경기·카운트에 영향 없음.
    스냅샷 1회 한계 보정 — 세션을 먼저 열고 나중에 승인받는 모임에서 명단이 비는 문제 방지."""
    existing = set(session.participants.exclude(user__isnull=True)
                   .values_list("user_id", flat=True))
    apps = BandScheduleApplication.objects.filter(
        schedule=session.schedule, status="approved").select_related("user")
    added = 0
    with transaction.atomic():
        for app in apps:
            if app.user_id in existing:
                continue
            score, gender = _level_gender(app.user)
            attendance = (SessionParticipant.Attendance.PRESENT if app.checked_in_at
                          else SessionParticipant.Attendance.NOT_PRESENT)
            SessionParticipant.objects.create(
                session=session, user=app.user, base_level=score, gender=gender,
                attendance=attendance)
            added += 1
    return added


def ensure_session(schedule, created_by, court_count=4):
    """get-or-create + 승인자 동기화. 이미 있으면 재생성하지 않되, 빠진 승인자는 추가한다.

    세션 자체는 덮어쓰지 않는다(출석·경기·설정 보존). 진입할 때마다 새로 승인된
    신청자만 세션에 반영해 '나중에 승인된 사람 명단 누락'을 방지한다.
    """
    existing = getattr(schedule, "match_session", None)
    if existing is not None:
        sync_approved_participants(existing)  # 콘솔 진입마다 빠진 승인자 동기화
        return existing
    try:
        return create_session_snapshot(schedule, created_by, court_count=court_count)
    except IntegrityError:
        # 동시 진입: 먼저 만들어진 세션을 반환 (덮어쓰지 않음) + 동기화
        session = MatchSession.objects.get(schedule=schedule)
        sync_approved_participants(session)
        return session
