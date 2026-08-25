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
            discipline_mode=mode, preset=preset, created_by=created_by,
            status=MatchSession.Status.PREPARING)  # 진입 시 '준비' 상태 → [운영 시작] 눌러야 진행
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


def sync_session_with_approvals(session):
    """세션 참가자 풀 ↔ 스케줄 승인 상태 **양방향** 동기화. 반환: (added, restored, removed).
    - 승인인데 세션에 없음 → 추가
    - 승인인데 세션에서 left(강등 후 재승인) → 출석 상태 복구 (급수·성별 override 값은 유지)
    - 세션에 있으나 더 이상 승인 아닌 **회원** → attendance=left (큐·추천에서 제외). 진행 중 경기는 Match 그대로 보존.
    - 게스트(user=None, 현장 인원)는 대상 아님.
    신청 상태 변경(approve/demote/kick/reject/취소 등) 시 호출 → 명단 누락·잔존 방지.
    """
    approved = {app.user_id: app for app in BandScheduleApplication.objects.filter(
        schedule=session.schedule, status="approved").select_related("user")}
    approved_uids = set(approved)
    added = restored = removed = 0
    with transaction.atomic():
        # 1) 승인 취소된 회원 → 큐/추천에서 제외(left). 경기 중이면 진행 경기는 보존(자연 종료 후 빠짐).
        for sp in session.participants.exclude(user__isnull=True):
            if sp.user_id not in approved_uids and sp.attendance != SessionParticipant.Attendance.LEFT:
                sp.attendance = SessionParticipant.Attendance.LEFT
                sp.save(update_fields=["attendance"])
                removed += 1
        # 2) 승인자 → 없으면 추가, left(강등 후 재승인)면 출석만 복구(override 유지)
        for uid, app in approved.items():
            att = (SessionParticipant.Attendance.PRESENT if app.checked_in_at
                   else SessionParticipant.Attendance.NOT_PRESENT)
            sp = session.participants.filter(user_id=uid).first()
            if sp is None:
                score, gender = _level_gender(app.user)
                SessionParticipant.objects.create(
                    session=session, user=app.user, base_level=score, gender=gender, attendance=att)
                added += 1
            elif sp.attendance == SessionParticipant.Attendance.LEFT:
                sp.attendance = att
                sp.save(update_fields=["attendance"])
                restored += 1
    return added, restored, removed


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
