import logging
from itertools import combinations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, F, Max
from django.utils import timezone

from band.models import BandMember, BandSchedule, BandScheduleApplication

logger = logging.getLogger(__name__)
from band.match_models import (
    MatchSession, SessionParticipant, Court, Match, MatchPlayer, Pair, PartnerRequest,
    ReservedMatch, ReservedMatchPlayer)
from band.matchmaking.scoring import level_to_score
from band.match_state import (
    build_pool, build_pairstats, build_pairs, build_player, build_met_count, build_coach_met,
    reserved_participant_ids)
from band.matchmaking.engine import (
    recommend_next_game, recommend_with_pairs, _discipline_feasible,
    pick_ace_three, build_ace_match)
from band.matchmaking.types import Mode, Preset, Discipline, NeedOperatorChoice, GamePlan, PRESETS
from band.matchmaking.cost import best_split
from band.matchmaking.selection import queue_order
from band.api.match_serializers import (
    serialize_session, serialize_match, serialize_participant, serialize_my_status,
    serialize_pair, serialize_partner_request, serialize_reservation,
    serialize_match_history)
from band.match_service import create_session_snapshot


def _is_operator(user, band) -> bool:
    # 조회 can_manage 산정과 동일 기준: 사이트 관리자(슈퍼유저)는 모든 번개 운영 가능
    from accounts.permissions import is_site_admin
    if is_site_admin(user):
        return True
    return BandMember.objects.filter(
        band=band, user=user, status="active",
        role__in=["owner", "admin"]).exists()


def _my_participant(session, user):
    return SessionParticipant.objects.filter(
        session=session, user=user).select_related("user").first()


def _profile_level_gender(user):
    profile = getattr(user, "profile", None)
    level = getattr(profile, "badminton_level", "") if profile else ""
    gender = getattr(profile, "gender", "unknown") if profile else "unknown"
    return level_to_score(level), gender


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_session(request, schedule_id):
    schedule = get_object_or_404(BandSchedule, id=schedule_id)
    if not _is_operator(request.user, schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if hasattr(schedule, "match_session"):
        return Response({"detail": "이미 대진 세션이 있습니다.", "id": schedule.match_session.id},
                        status=status.HTTP_409_CONFLICT)

    court_count = int(request.data.get("court_count", 4))
    mode = request.data.get("discipline_mode", MatchSession.DisciplineMode.ALL)
    preset = request.data.get("preset", MatchSession.Preset.BALANCED)
    session = create_session_snapshot(
        schedule, request.user, court_count=court_count, mode=mode, preset=preset)
    return Response(serialize_session(session), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def session_state(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    ensure_next_lineup(session)
    return Response(serialize_session(session))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def match_history(request, session_id):
    """게임 보드 — 세션의 경기(진행+완료)를 최신순으로. 운영자 또는 세션 참가자."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not (_is_operator(request.user, session.schedule.band)
            or _my_participant(session, request.user) is not None):
        return Response({"detail": "권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    # 진행중(ended_at 없음) 맨 위 → 완료는 끝난 순(최근에 끝난 경기가 위)
    matches = (Match.objects.filter(session=session)
               .select_related("court")
               .prefetch_related("players__participant__user__profile")
               .order_by(F("ended_at").desc(nulls_first=True), "-started_at"))
    return Response([serialize_match_history(m) for m in matches])


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_mode(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    mode = request.data.get("discipline_mode")
    if mode not in MatchSession.DisciplineMode.values:
        return Response({"detail": "잘못된 모드"}, status=status.HTTP_400_BAD_REQUEST)
    session.discipline_mode = mode
    session.next_lineup = None  # 종목 바뀌면 확정 다음경기 무효화 → 새 종목으로 재계산
    session.save(update_fields=["discipline_mode", "next_lineup", "updated_at"])
    ensure_next_lineup(session)
    return Response(serialize_session(session))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_preset(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    preset = request.data.get("preset")
    if preset not in MatchSession.Preset.values:
        return Response({"detail": "잘못된 성향"}, status=status.HTTP_400_BAD_REQUEST)
    session.preset = preset
    session.next_lineup = None  # 성향 바뀌면 확정 다음경기 무효화 → 재계산
    session.save(update_fields=["preset", "next_lineup", "updated_at"])
    ensure_next_lineup(session)
    return Response(serialize_session(session))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_auto(request, session_id):
    """자동 배치 on/off. False(수동)면 경기 종료 시 자동 투입 안 함(예약만)."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    session.auto = bool(request.data.get("auto", True))
    session.next_lineup = None  # 자동↔수동 전환 시 확정 무효화(수동에서 예약이 옛 확정에 가려지는 문제 방지)
    session.save(update_fields=["auto", "next_lineup", "updated_at"])
    ensure_next_lineup(session)
    return Response(serialize_session(session))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_attendance(request, session_id, pid):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    sp = get_object_or_404(SessionParticipant, id=pid, session=session)
    value = request.data.get("attendance")
    if value not in SessionParticipant.Attendance.values:
        return Response({"detail": "잘못된 출석 상태"}, status=status.HTTP_400_BAD_REQUEST)
    sp.attendance = value
    sp.save(update_fields=["attendance"])
    return Response(serialize_participant(sp))


_MODE_MAP = {
    "mixed_only": Mode.MIXED_ONLY,
    "singles_gender": Mode.SINGLES_GENDER,
    "all": Mode.ALL,
}
_PRESET_MAP = {"balanced": Preset.BALANCED, "competitive": Preset.COMPETITIVE}
_DISC_MAP = {"mixed": Discipline.MIXED, "mens": Discipline.MENS, "womens": Discipline.WOMENS}

# 경기 시작 직후 종료 금지 구간(초) — 더블클릭으로 코트가 연속 두 번 넘어가는 것 방지. 콘솔 버튼 쿨다운과 동일 값
END_COOLDOWN_SEC = 1.5


def _on_court_ids(session):
    ids = set()
    for m in Match.objects.filter(session=session, status="playing").prefetch_related("players"):
        ids.update(mp.participant_id for mp in m.players.all())
    return ids


def _notify_next_game(match):
    """경기 선수들에게 '다음 경기' 알림(=FCM 푸시). 코트 고정 코치는 매 경기 들어가므로 제외."""
    from notifications.models import Notification
    schedule = match.session.schedule
    band = schedule.band
    coach_id = match.court.coach_id
    disc = match.get_discipline_display()
    for mp in match.players.select_related("participant").all():
        if coach_id and mp.participant_id == coach_id:
            continue
        if not mp.participant.user_id:
            continue  # 임시(현장) 인원은 계정이 없어 푸시 대상 아님
        Notification.objects.create(
            user_id=mp.participant.user_id,
            type=Notification.Type.MATCH_NEXT_GAME,
            title="다음 경기예요! 코트로 들어가 주세요",
            message=f"[{band.name}] 코트 {match.court.index} · {disc}",
            related_band_schedule=schedule,
            related_band=band,
        )


def _create_match(session, court, plan: GamePlan):
    match = Match.objects.create(
        session=session, court=court, discipline=plan.discipline.value,
        court_index=court.index, court_name=court.name or "")   # 코트 제거돼도 기록 유지
    for pid in plan.team1:
        MatchPlayer.objects.create(match=match, participant_id=pid, team=1)
    for pid in plan.team2:
        MatchPlayer.objects.create(match=match, participant_id=pid, team=2)
    _notify_next_game(match)
    return match


def _coach_ids(session):
    return set(Court.objects.filter(session=session, coach__isnull=False)
               .values_list("coach_id", flat=True))


def _reservation_discipline(players, explicit):
    if explicit:
        return Discipline(explicit)
    males = sum(1 for p in players if p.gender == "male")
    if males == 4:
        return Discipline.MENS
    if males == 0:
        return Discipline.WOMENS
    return Discipline.MIXED


def _disc_allowed_in_mode(disc, mode):
    """예약 종목(disc)이 현재 세션 종목 모드에 맞는지."""
    if mode == MatchSession.DisciplineMode.ALL:
        return True
    if mode == MatchSession.DisciplineMode.MIXED_ONLY:
        return disc == Discipline.MIXED
    return disc in (Discipline.MENS, Discipline.WOMENS)  # singles_gender


def _mode_mismatch_msg(mode):
    if mode == MatchSession.DisciplineMode.MIXED_ONLY:
        return "혼복 모드예요. 남녀가 섞인 4명으로 구성해 주세요."
    return "남복·여복 모드예요. 남자 4명 또는 여자 4명으로 구성해 주세요."


def _consume_reservation(session, court, stats):
    """투입 가능한(4명 전원 출석·코트 밖) 가장 오래된 예약을 경기로 만든다."""
    on_court = _on_court_ids(session)
    weights = PRESETS[_PRESET_MAP[session.preset]]
    reservations = session.reservations.prefetch_related(
        "players__participant__user").all()  # created_at 순
    for r in reservations:
        sps = [rp.participant for rp in r.players.all()]
        if len(sps) != 4:
            continue
        if any(sp.attendance != SessionParticipant.Attendance.PRESENT or sp.id in on_court
               for sp in sps):
            continue
        players = [build_player(sp) for sp in sps]
        disc = _reservation_discipline(players, r.discipline)
        split = best_split(players, disc, weights, stats, session.female_adjust)
        if split is None:
            continue
        match = _create_match(session, court, split)
        r.delete()
        return match
    return None


def _manual_fill(session, court, participant_ids, forced=None):
    """직접 채우기: 지정 4명을 빈 코트에 즉시 투입. 반환: (match|None, error_str|None)."""
    if not isinstance(participant_ids, (list, tuple)) or len({*participant_ids}) != 4:
        return None, "서로 다른 4명을 지정해야 합니다."
    sps = list(SessionParticipant.objects.filter(
        id__in=participant_ids, session=session).select_related("user"))
    if len(sps) != 4:
        return None, "참가자를 찾을 수 없습니다."
    on_court = _on_court_ids(session)
    coach_ids = _coach_ids(session)
    reserved = reserved_participant_ids(session)
    for sp in sps:
        if sp.attendance != SessionParticipant.Attendance.PRESENT:
            return None, "참여중인 사람만 넣을 수 있어요."
        if sp.id in on_court:
            return None, "경기 중인 사람은 넣을 수 없어요."
        if sp.id in coach_ids:
            return None, "코치는 직접 채우기에 넣을 수 없어요."
        if sp.id in reserved:
            return None, "예약에 들어간 사람이 있어요."
    players = [build_player(sp) for sp in sps]
    disc = _reservation_discipline(
        players, forced if forced in Match.Discipline.values else None)
    weights = PRESETS[_PRESET_MAP[session.preset]]
    split = best_split(players, disc, weights, build_pairstats(session), session.female_adjust)
    if split is None:
        return None, "이 4명으로는 그 종목을 구성할 수 없어요."
    return _create_match(session, court, split), None


def _dict_to_plan(lineup):
    return GamePlan(
        discipline=Discipline(lineup["discipline"]),
        team1=tuple(lineup["team1"]),
        team2=tuple(lineup["team2"]))


def _lineup_valid(session, lineup):
    """확정 다음경기 4명이 여전히 투입 가능한지(출석·비경기중·예약/코치 미포함)."""
    if not lineup:
        return False
    ids = list(lineup.get("team1", [])) + list(lineup.get("team2", []))
    if len(set(ids)) != 4:
        return False
    sps = list(SessionParticipant.objects.filter(id__in=ids, session=session))
    if len(sps) != 4:
        return False
    blocked = _on_court_ids(session) | _coach_ids(session) | reserved_participant_ids(session)
    for sp in sps:
        if sp.attendance != SessionParticipant.Attendance.PRESENT:
            return False
        if sp.id in blocked:
            return False
    return True


def _compute_next_lineup(session):
    """다음 1경기 GamePlan을 계산해 dict로. 불가하면 None. (예약·코치·경기중 제외 풀에서 추천)"""
    coach_ids = _coach_ids(session)
    reserved_ids = reserved_participant_ids(session)
    pool = build_pool(
        session,
        on_court_participant_ids=_on_court_ids(session) | coach_ids | reserved_ids)
    stats = build_pairstats(session)
    result = recommend_with_pairs(
        pool, build_pairs(session), _MODE_MAP[session.discipline_mode],
        _PRESET_MAP[session.preset], stats, female_adjust=session.female_adjust)
    if isinstance(result, GamePlan):
        return {"discipline": result.discipline.value,
                "team1": list(result.team1), "team2": list(result.team2)}
    return None


def _has_ready_reservation(session):
    """투입 가능한(4명 전원 출석·코트 밖) 예약이 하나라도 있는지."""
    on_court = _on_court_ids(session)
    for r in session.reservations.prefetch_related("players__participant").all():
        sps = [rp.participant for rp in r.players.all()]
        if len(sps) == 4 and all(
                sp.attendance == SessionParticipant.Attendance.PRESENT
                and sp.id not in on_court for sp in sps):
            return True
    return False


def ensure_next_lineup(session):
    """자동 모드 + 빈 코트 없음일 때 '다음 1경기'를 확정 유지. 반환: dict|None.
    - 수동이거나 빈 코트가 있으면 확정 없음(None): 빈 코트는 바로 투입되므로.
    - 이미 예고된 확정이 유효하면 그대로 유지(예고 신뢰).
    - 새로 만들 차례에 투입 가능한 예약이 대기 중이면 확정을 만들지 않음(예약 먼저 소진 → 예약 영구 밀림 방지)."""
    if session.status != MatchSession.Status.ACTIVE:  # 준비/종료 상태에선 자동 투입 안 함
        if session.next_lineup is not None:
            session.next_lineup = None
            session.save(update_fields=["next_lineup", "updated_at"])
        return None
    empty = session.courts.count() - Match.objects.filter(
        session=session, status="playing").count()
    if not session.auto or empty > 0:
        if session.next_lineup is not None:
            session.next_lineup = None
            session.save(update_fields=["next_lineup", "updated_at"])
        return None
    if _lineup_valid(session, session.next_lineup):
        return session.next_lineup  # 이미 예고된 확정은 유지(예고 신뢰)
    if _has_ready_reservation(session):
        # 대기 예약이 있으면 확정을 새로 만들지 않고 예약부터 소진 → 소진 후 확정 재개
        if session.next_lineup is not None:
            session.next_lineup = None
            session.save(update_fields=["next_lineup", "updated_at"])
        return None
    session.next_lineup = _compute_next_lineup(session)
    session.save(update_fields=["next_lineup", "updated_at"])
    return session.next_lineup


def _fill_court(session, court, forced_discipline=None, allow_auto=True):
    """반환: (match | None, need: NeedOperatorChoice | None).
    allow_auto=False(수동 모드)면 예약만 투입하고 자동 추천은 건너뛴다(코트 비움)."""
    coach_ids = _coach_ids(session)
    reserved_ids = reserved_participant_ids(session)
    # 코치는 본인 코트 고정, 예약 멤버는 확보 → 일반 풀(큐·공정성)에서 제외
    pool = build_pool(
        session,
        on_court_participant_ids=_on_court_ids(session) | coach_ids | reserved_ids)
    stats = build_pairstats(session)

    # 코치 고정 코트: 코치(출석 시) + '못 만난 사람 우선' 3명
    if court.coach_id is not None and forced_discipline is None:
        if court.coach_resting:
            # '이번 판 코치 쉼' — 코치 로직 건너뛰고 일반 경기로(아래), 1회성 플래그 소비 → 다음 판 코치 복귀
            court.coach_resting = False
            court.save(update_fields=["coach_resting"])
        else:
            coach_sp = SessionParticipant.objects.filter(
                id=court.coach_id, session=session,
                attendance=SessionParticipant.Attendance.PRESENT).select_related("user").first()
            if coach_sp is not None:
                met = build_met_count(session, coach_ids, stats)
                mode_enum = _MODE_MAP.get(session.discipline_mode, Mode.ALL)
                coach_player = build_player(coach_sp)
                with_coach = build_coach_met(session, court.coach_id, stats)
                three = pick_ace_three(pool, met, mode_enum, coach_player, with_coach)
                plan = build_ace_match(coach_player, three, mode_enum) if three else None
                if plan is None and mode_enum == Mode.MIXED_ONLY:
                    # 혼복 2남2여를 못 만들면 코트를 비우지 않고 동성(남복/여복)으로 채운다.
                    # 이 상황은 모드 전환 시 성비 경고로 대부분 걸러지지만, 운영 중 인원 변동에 대비한 안전망.
                    three = pick_ace_three(pool, met, Mode.SINGLES_GENDER, coach_player, with_coach)
                    plan = build_ace_match(coach_player, three, Mode.SINGLES_GENDER) if three else None
                if plan is not None:
                    return _create_match(session, court, plan), None
                return None, None  # 코치 코트에 채울 3명 부족

    if forced_discipline is not None:
        # 운영자가 종목을 강제 → 그 종목으로 best_split (윈도우 앞 4명 중 가능한 조합)
        weights = PRESETS[_PRESET_MAP[session.preset]]
        order = queue_order(pool)
        for combo in combinations(order[:8], 4):
            if not _discipline_feasible(combo, forced_discipline):
                continue
            split = best_split(list(combo), forced_discipline, weights, stats, session.female_adjust)
            if split:
                return _create_match(session, court, split), None
        return None, NeedOperatorChoice(reason="강제 종목 구성 불가", options=())

    # 자동: 확정된 다음 1경기를 최우선 투입(참가자 '곧 경기에요' 예고 신뢰) → 예약 → 자동추천
    if allow_auto and _lineup_valid(session, session.next_lineup):
        plan = _dict_to_plan(session.next_lineup)
        session.next_lineup = None
        session.save(update_fields=["next_lineup", "updated_at"])
        return _create_match(session, court, plan), None
    # 예약(이후 예정) 경기가 준비됐으면 자동 추천보다 우선 투입
    reserved = _consume_reservation(session, court, stats)
    if reserved is not None:
        return reserved, None
    if not allow_auto:
        return None, None  # 수동 모드: 자동 추천 스킵, 코트 비워둠

    result = recommend_with_pairs(
        pool, build_pairs(session), _MODE_MAP[session.discipline_mode],
        _PRESET_MAP[session.preset], stats, female_adjust=session.female_adjust)
    if isinstance(result, GamePlan):
        return _create_match(session, court, result), None
    if isinstance(result, NeedOperatorChoice):
        return None, result
    return None, None  # 인원 부족(None)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def fill_court(request, session_id, index):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)
    if session.status == MatchSession.Status.PREPARING:
        return Response({"detail": "먼저 [운영 시작]을 눌러 대진을 시작하세요."}, status=status.HTTP_409_CONFLICT)
    if session.paused:
        return Response({"detail": "일시 중단 중이에요. [재개]를 누르면 경기를 넣을 수 있어요.",
                         "code": "paused"}, status=status.HTTP_409_CONFLICT)
    court = get_object_or_404(Court, session=session, index=index)
    forced = request.data.get("discipline")
    pids = request.data.get("participant_ids")
    forced_disc = _DISC_MAP.get(forced) if forced else None

    # 더블클릭·동시요청 방어 — 코트 행을 잠그고 '이미 찬 코트' 판정과 투입을 한 트랜잭션에서 처리한다.
    # 잠금 밖에서 판정하면 두 요청이 모두 '빈 코트'로 보고 같은 코트에 playing 경기를 2개 만든다.
    with transaction.atomic():
        Court.objects.select_for_update().get(pk=court.pk)
        playing = court.matches.filter(status="playing").prefetch_related("players").first()
        if playing is None:
            if pids:
                match, err = _manual_fill(session, court, pids, forced)
                need = None
            else:
                # 수동 모드 '경기 시작'은 1순위 예약만 투입(자동추천 안 함). 자동은 확정/예약/추천 전부.
                match, need = _fill_court(session, court, forced_disc, allow_auto=session.auto)
                err = None

    if playing is not None:
        # 화면-서버 동기화 어긋남으로 '이미 찬 코트'에 경기 시작/채우기가 호출된 상황.
        # 오류 대신 현재 상태를 그대로 반환(멱등)해 운영자에게 오류가 안 뜨게 하고, 원인 추적용 진단 로그만 남긴다.
        logger.warning(
            "fill_court on busy court — session=%s court=%s auto=%s match=%s players=%s pids=%s",
            session.id, index, session.auto, playing.id,
            [mp.participant_id for mp in playing.players.all()],
            request.data.get("participant_ids"),
        )
        return Response(serialize_session(session))

    # 직접 채우기(participant_ids 지정)는 그 4명으로 즉시 투입 → 자동추천 경로와 응답 형식이 다르다
    if pids:
        if err is not None:
            return Response({"match": None, "needs_choice": False, "detail": err},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"match": serialize_match(match), "needs_choice": False})

    if need is not None:
        return Response({"match": None, "needs_choice": True,
                         "reason": need.reason,
                         "options": [d.value for d in need.options]})
    if match is None:
        return Response({"match": None, "needs_choice": False,
                         "detail": "대기 인원이 부족합니다."})
    return Response({"match": serialize_match(match), "needs_choice": False})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_coach(request, session_id, index):
    """코트에 코치(자강) 고정/해제. participant_id 없으면 해제. 같은 코치는 한 코트만."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    court = get_object_or_404(Court, session=session, index=index)
    pid = request.data.get("participant_id")
    if not pid:
        court.coach = None
        court.save(update_fields=["coach"])
        return Response(serialize_session(session))
    sp = get_object_or_404(SessionParticipant, id=pid, session=session)
    with transaction.atomic():
        Court.objects.filter(session=session, coach=sp).exclude(id=court.id).update(coach=None)
        court.coach = sp
        court.save(update_fields=["coach"])
    return Response(serialize_session(session))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_coach_rest(request, session_id, index):
    """코치 '이번 판 쉼' 토글. 다음 채우기 때 코치 제외 일반 경기로 1회 진행 후 코치 복귀."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    court = get_object_or_404(Court, session=session, index=index)
    if court.coach_id is None:
        return Response({"detail": "코치 코트가 아닙니다."}, status=status.HTTP_400_BAD_REQUEST)
    court.coach_resting = bool(request.data.get("resting", True))
    court.save(update_fields=["coach_resting"])
    return Response(serialize_session(session))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_court(request, session_id, index):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)
    if session.status == MatchSession.Status.PREPARING:
        return Response({"detail": "먼저 [운영 시작]을 눌러 대진을 시작하세요."}, status=status.HTTP_409_CONFLICT)
    court = get_object_or_404(Court, session=session, index=index)

    now = timezone.now()
    with transaction.atomic():
        # 더블클릭·동시요청 방어 — 코트 행을 잠근 뒤 진행 중 경기를 조회한다. 잠금 없이 밖에서 읽으면
        # 두 요청이 같은 경기를 playing으로 보고 게임수를 이중 카운트하고, _fill_court가 두 번 돌아
        # 같은 코트에 playing 경기가 2개 생긴다(콘솔은 하나만 표시 → 나머지 4명이 유령으로 묶임).
        Court.objects.select_for_update().get(pk=court.pk)
        match = court.matches.filter(status="playing").prefetch_related("players__participant").first()
        if match is None:
            return Response({"detail": "이미 종료된 경기예요.", "code": "stale_match"},
                            status=status.HTTP_409_CONFLICT)
        # 더블클릭·오래된 화면 방어 — 콘솔이 보고 있던 경기와 다르면 거부한다. 서버가 빨라서 1번째 클릭으로
        # 이미 다음 경기가 투입된 뒤 2번째 클릭이 도착하면, 잠금만으로는 '새로 들어간 경기'가 종료돼 버린다.
        expected_id = request.data.get("match_id")
        if expected_id is not None and str(expected_id) != str(match.id):
            return Response({"detail": "이미 종료된 경기예요.", "code": "stale_match"},
                            status=status.HTTP_409_CONFLICT)
        # 쿨다운 — 서버가 빠르면(45ms) 1번째 클릭으로 다음 경기가 이미 투입되고 화면도 갱신돼서,
        # 0.2초 뒤 2번째 클릭은 '새 경기를 종료하라'는 정당한 요청이 된다(토큰·잠금으로 못 막음).
        # 방금 시작한 경기는 종료를 거부해 코트가 연속으로 두 번 넘어가는 것을 막는다.
        if match.started_at is not None and (now - match.started_at).total_seconds() < END_COOLDOWN_SEC:
            return Response({"detail": "방금 시작한 경기예요. 잠시 후 종료할 수 있어요.",
                             "code": "just_started"}, status=status.HTTP_409_CONFLICT)
        match.status = "done"
        match.ended_at = now
        match.save(update_fields=["status", "ended_at"])
        # 시작 2분 내 종료면 카운트·대기시간 갱신 안 함(오조작·연습·즉시종료 방지)
        too_short = match.started_at is not None and (now - match.started_at).total_seconds() < 120
        if not too_short:
            disc_field = {"mixed": "games_mixed", "mens": "games_mens", "womens": "games_womens"}[match.discipline]
            for mp in match.players.all():
                sp = mp.participant
                setattr(sp, disc_field, getattr(sp, disc_field) + 1)
                sp.last_game_ended_at = now
                sp.save(update_fields=[disc_field, "last_game_ended_at"])
        if session.auto and not session.paused:
            new_match, need = _fill_court(session, court, allow_auto=True)
            ensure_next_lineup(session)   # 빈 코트 채워진 뒤 다음 1경기 재확정
        elif session.paused:
            # 일시 중단 — 치던 경기는 끝내되 다음 경기는 넣지 않는다. 재개하면 그때 투입.
            new_match, need = None, None
        else:
            # 수동: 종료 후 빈 코트 유지 → 운영자가 '경기 시작'을 눌러야 1순위 예약 투입
            new_match, need = None, None

    if need is not None:
        return Response({"ended": match.id, "match": None, "needs_choice": True,
                         "reason": need.reason, "options": [d.value for d in need.options]})
    # 전체 상태를 바로 응답 → 콘솔이 재조회(refetch) 없이 새 경기까지 한 번에 반영(자동 종료 깜빡임 제거)
    return Response(serialize_session(session))


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def edit_match(request, session_id, match_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)
    if session.status == MatchSession.Status.PREPARING:
        return Response({"detail": "먼저 [운영 시작]을 눌러 대진을 시작하세요."}, status=status.HTTP_409_CONFLICT)
    match = get_object_or_404(Match, id=match_id, session=session, status="playing")

    swap = request.data.get("swap")          # [out_participant_id, in_participant_id] (1명 교체)
    new_ids = request.data.get("participant_ids")  # [id×4] 새 라인업 (여러 명 동시 교체)
    discipline = request.data.get("discipline")

    if swap is not None:
        if not isinstance(swap, (list, tuple)) or len(swap) != 2:
            return Response({"detail": "swap은 [out_id, in_id] 형식이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST)
    if new_ids is not None:
        if not isinstance(new_ids, (list, tuple)) or len({*new_ids}) != 4:
            return Response({"detail": "participant_ids는 서로 다른 4명이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        if swap:
            out_id, in_id = swap
            mp = get_object_or_404(MatchPlayer, match=match, participant_id=out_id)
            # 들어올 사람은 present 이고 다른 코트에 없어야
            if in_id in _on_court_ids(session):
                return Response({"detail": "교체 대상이 이미 경기 중입니다."},
                                status=status.HTTP_400_BAD_REQUEST)
            in_sp = get_object_or_404(SessionParticipant, id=in_id, session=session,
                                      attendance="present")
            mp.participant = in_sp
            mp.save(update_fields=["participant"])
        elif new_ids:
            # 새 4명으로 교체 — 바뀐 사람만 실제 교체(나간 사람은 MatchPlayer에서 빠져 카운트 안 됨)
            cur = {mp.participant_id: mp for mp in match.players.all()}
            keep = {*new_ids} & set(cur)
            outs = [pid for pid in cur if pid not in keep]
            ins = [nid for nid in new_ids if nid not in cur]
            on_court_other = _on_court_ids(session) - set(cur)
            for nid in ins:
                if nid in on_court_other:
                    return Response({"detail": "교체 대상이 다른 코트에서 경기 중입니다."},
                                    status=status.HTTP_400_BAD_REQUEST)
                if not SessionParticipant.objects.filter(
                        id=nid, session=session, attendance="present").exists():
                    return Response({"detail": "교체 대상은 참여중이어야 합니다."},
                                    status=status.HTTP_400_BAD_REQUEST)
            for o, i in zip(outs, ins):
                mp = cur[o]
                mp.participant = SessionParticipant.objects.get(id=i, session=session)
                mp.save(update_fields=["participant"])
        if discipline in _DISC_MAP:
            match.discipline = discipline
            match.save(update_fields=["discipline"])

    match.refresh_from_db()
    match = Match.objects.prefetch_related("players__participant__user").get(id=match.id)
    return Response(serialize_match(match))


# ===== 참가자 본인용 (앱) =====

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_status(request, session_id):
    """세션 내 '내 라이브 상태' (출석·현재경기·대기순번·게임수). 앱이 폴링."""
    session = get_object_or_404(MatchSession, id=session_id)
    sp = _my_participant(session, request.user)
    return Response(serialize_my_status(session, sp, request.user))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_status_by_schedule(request, schedule_id):
    """일정 기준 '내 상태'. 앱은 schedule_id만 알아도 세션 유무·내 상태 조회 가능."""
    schedule = get_object_or_404(BandSchedule, id=schedule_id)
    session = getattr(schedule, "match_session", None)
    approved = BandScheduleApplication.objects.filter(
        schedule=schedule, user=request.user, status="approved").exists()
    # 신청/대기 상태 + 대기 순번(1-base, 신청순)
    my_app = BandScheduleApplication.objects.filter(schedule=schedule, user=request.user).first()
    waiting_total = BandScheduleApplication.objects.filter(schedule=schedule, status="waiting").count()
    waiting_position = None
    if my_app and my_app.status == "waiting":
        _wids = list(BandScheduleApplication.objects.filter(
            schedule=schedule, status="waiting").order_by("applied_at").values_list("user_id", flat=True))
        if request.user.id in _wids:
            waiting_position = _wids.index(request.user.id) + 1
    waitlist_extra = {
        "application_status": my_app.status if my_app else None,
        "waiting_position": waiting_position,
        "waiting_total": waiting_total,
    }
    if session is None:
        return Response({
            "session_id": None, "session_status": None,
            "participant_id": None, "attendance": None, "games": None,
            "playing": False, "current_match": None,
            "queue_position": None, "queue_total": 0, "up_next": False,
            "approved": approved,
            **waitlist_extra,
        })
    sp = _my_participant(session, request.user)
    data = serialize_my_status(session, sp, request.user)
    data["approved"] = approved or sp is not None
    data.update(waitlist_extra)
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def my_checkin(request, session_id):
    """참가자 자가 출석/퇴장 (action: in|out). 세션의 승인 참가자 본인만."""
    session = get_object_or_404(MatchSession, id=session_id)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)
    sp = _my_participant(session, request.user)
    if sp is None:
        return Response({"detail": "이 번개의 승인 참가자만 출석할 수 있어요."},
                        status=status.HTTP_403_FORBIDDEN)
    action = request.data.get("action", "in")
    if action == "in":
        missing = request.user.match_profile_missing
        if missing:
            return Response({
                "detail": "출석 체크인 전에 프로필(실명·성별·급수)을 먼저 입력해주세요.",
                "code": "profile_incomplete",
                "missing": missing,
            }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        sp.attendance = SessionParticipant.Attendance.PRESENT
    elif action == "out":
        sp.attendance = SessionParticipant.Attendance.LEFT
    else:
        return Response({"detail": "action은 in 또는 out 이어야 합니다."},
                        status=status.HTTP_400_BAD_REQUEST)
    sp.save(update_fields=["attendance"])
    # 웹 번개 상세의 자가 체크인(checked_in_at)과 동기화
    BandScheduleApplication.objects.filter(
        schedule=session.schedule, user=request.user, status="approved"
    ).update(checked_in_at=timezone.now() if action == "in" else None)
    return Response(serialize_my_status(session, sp, request.user))


# ===== 파트너 (신청·승인·해제) =====

def _active_pair_for(session, *participant_ids):
    return Pair.objects.filter(session=session).filter(
        Q(p1_id__in=participant_ids) | Q(p2_id__in=participant_ids)).first()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def request_partner(request, session_id):
    """참가자가 다른 참가자에게 파트너 신청. (모임장 승인 대기)"""
    session = get_object_or_404(MatchSession, id=session_id)
    me = _my_participant(session, request.user)
    if me is None:
        return Response({"detail": "이 번개의 참가자만 신청할 수 있어요."},
                        status=status.HTTP_403_FORBIDDEN)
    to_sp = get_object_or_404(
        SessionParticipant, id=request.data.get("to_participant_id"), session=session)
    if to_sp.id == me.id:
        return Response({"detail": "자기 자신과는 파트너가 될 수 없어요."},
                        status=status.HTTP_400_BAD_REQUEST)
    if to_sp.user_id is None:
        return Response({"detail": "현장 인원과의 파트너는 모임장에게 요청해주세요."},
                        status=status.HTTP_400_BAD_REQUEST)
    if _active_pair_for(session, me.id, to_sp.id):
        return Response({"detail": "이미 다른 파트너와 묶여 있어요."},
                        status=status.HTTP_409_CONFLICT)
    if PartnerRequest.objects.filter(
            session=session, status=PartnerRequest.Status.PENDING,
            from_participant=me, to_participant=to_sp).exists():
        return Response({"detail": "이미 신청했어요."}, status=status.HTTP_409_CONFLICT)
    req = PartnerRequest.objects.create(
        session=session, from_participant=me, to_participant=to_sp,
        strict=bool(request.data.get("strict", False)))
    req = PartnerRequest.objects.select_related(
        "from_participant__user", "to_participant__user").get(id=req.id)
    return Response(serialize_partner_request(req), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_partner_requests(request, session_id):
    """대기 중 파트너 신청. 모임장=전체, 참가자=본인 관련만."""
    session = get_object_or_404(MatchSession, id=session_id)
    qs = PartnerRequest.objects.filter(
        session=session, status=PartnerRequest.Status.PENDING).select_related(
        "from_participant__user", "to_participant__user")
    if not _is_operator(request.user, session.schedule.band):
        me = _my_participant(session, request.user)
        if me is None:
            return Response({"requests": []})
        qs = qs.filter(Q(from_participant=me) | Q(to_participant=me))
    return Response({"requests": [serialize_partner_request(r) for r in qs]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def approve_partner_request(request, session_id, req_id):
    """모임장이 파트너 신청 승인 → 고정 쌍 생성."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    req = get_object_or_404(PartnerRequest, id=req_id, session=session)
    if req.status != PartnerRequest.Status.PENDING:
        return Response({"detail": "이미 처리된 신청입니다."}, status=status.HTTP_409_CONFLICT)
    if _active_pair_for(session, req.from_participant_id, req.to_participant_id):
        return Response({"detail": "이미 다른 파트너와 묶여 있어요."},
                        status=status.HTTP_409_CONFLICT)
    with transaction.atomic():
        pair = Pair.objects.create(
            session=session, p1=req.from_participant, p2=req.to_participant, strict=req.strict)
        req.status = PartnerRequest.Status.APPROVED
        req.resolved_at = timezone.now()
        req.save(update_fields=["status", "resolved_at"])
    pair = Pair.objects.select_related("p1__user", "p2__user").get(id=pair.id)
    return Response(serialize_pair(pair), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reject_partner_request(request, session_id, req_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    req = get_object_or_404(PartnerRequest, id=req_id, session=session)
    if req.status != PartnerRequest.Status.PENDING:
        return Response({"detail": "이미 처리된 신청입니다."}, status=status.HTTP_409_CONFLICT)
    req.status = PartnerRequest.Status.REJECTED
    req.resolved_at = timezone.now()
    req.save(update_fields=["status", "resolved_at"])
    return Response({"id": req.id, "status": req.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_partner_request(request, session_id, req_id):
    """신청자 본인이 승인 전 파트너 신청 취소."""
    session = get_object_or_404(MatchSession, id=session_id)
    req = get_object_or_404(PartnerRequest, id=req_id, session=session)
    me = _my_participant(session, request.user)
    if me is None or req.from_participant_id != me.id:
        return Response({"detail": "본인이 보낸 신청만 취소할 수 있어요."},
                        status=status.HTTP_403_FORBIDDEN)
    if req.status != PartnerRequest.Status.PENDING:
        return Response({"detail": "이미 처리된 신청입니다."}, status=status.HTTP_409_CONFLICT)
    req.status = PartnerRequest.Status.CANCELED
    req.resolved_at = timezone.now()
    req.save(update_fields=["status", "resolved_at"])
    return Response({"id": req.id, "status": req.status})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def pairs(request, session_id):
    """GET=쌍 목록(전체). POST=모임장이 직접 쌍 생성."""
    session = get_object_or_404(MatchSession, id=session_id)
    if request.method == "GET":
        rows = session.pairs.select_related("p1__user", "p2__user").all()
        return Response({"pairs": [serialize_pair(pr) for pr in rows]})
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    p1 = get_object_or_404(SessionParticipant, id=request.data.get("p1_id"), session=session)
    p2 = get_object_or_404(SessionParticipant, id=request.data.get("p2_id"), session=session)
    if p1.id == p2.id:
        return Response({"detail": "서로 다른 두 명이어야 해요."}, status=status.HTTP_400_BAD_REQUEST)
    if _active_pair_for(session, p1.id, p2.id):
        return Response({"detail": "이미 파트너로 묶인 사람이 있어요."},
                        status=status.HTTP_409_CONFLICT)
    pair = Pair.objects.create(
        session=session, p1=p1, p2=p2, strict=bool(request.data.get("strict", False)))
    pair = Pair.objects.select_related("p1__user", "p2__user").get(id=pair.id)
    return Response(serialize_pair(pair), status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_pair(request, session_id, pair_id):
    """쌍 해제. 모임장 또는 쌍의 당사자 본인. 진행 중·확정된 경기는 그대로, 다음 대진부터 반영."""
    session = get_object_or_404(MatchSession, id=session_id)
    pair = get_object_or_404(Pair, id=pair_id, session=session)
    if not _is_operator(request.user, session.schedule.band):
        me = _my_participant(session, request.user)
        if me is None or me.id not in (pair.p1_id, pair.p2_id):
            return Response({"detail": "본인 파트너만 해제할 수 있어요."},
                            status=status.HTTP_403_FORBIDDEN)
    pair.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ===== 코트 설정 (면 수·이름·제거) =====

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_court(request, session_id):
    """코트 추가(면 수 +)."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)
    with transaction.atomic():
        last = session.courts.order_by("-index").first()
        Court.objects.create(
            session=session, index=(last.index + 1) if last else 1,
            name=(request.data.get("name") or "").strip())
        session.court_count = session.courts.count()
        session.save(update_fields=["court_count", "updated_at"])
    return Response(serialize_session(session), status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def court_detail(request, session_id, index):
    """코트 이름 변경(PATCH) / 제거(DELETE). 진행 중 경기가 있으면 제거 불가."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    court = get_object_or_404(Court, session=session, index=index)
    if request.method == "PATCH":
        court.name = (request.data.get("name") or "").strip()
        court.save(update_fields=["name"])
        return Response(serialize_session(session))
    if court.matches.filter(status="playing").exists():
        return Response({"detail": "진행 중인 경기가 있어 제거할 수 없어요."},
                        status=status.HTTP_409_CONFLICT)
    with transaction.atomic():
        court.delete()
        session.court_count = session.courts.count()
        session.save(update_fields=["court_count", "updated_at"])
    return Response(serialize_session(session))


# ===== 임시(현장) 인원 추가 =====

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_participant(request, session_id):
    """계정 없는 현장 인원을 이름·성별·급수로 추가. 바로 참여중으로 들어간다."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)
    name = (request.data.get("name") or "").strip()
    gender = request.data.get("gender")
    level = request.data.get("level") or ""
    if not name:
        return Response({"detail": "이름을 입력해 주세요."}, status=status.HTTP_400_BAD_REQUEST)
    if gender not in ("male", "female"):
        return Response({"detail": "성별(male/female)을 선택해 주세요."},
                        status=status.HTTP_400_BAD_REQUEST)
    sp = SessionParticipant.objects.create(
        session=session, user=None, guest_name=name,
        base_level=level_to_score(level), gender=gender,
        attendance=SessionParticipant.Attendance.PRESENT)
    return Response(serialize_participant(sp), status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def edit_participant(request, session_id, pid):
    """세션 참가자 정보 수정(운영자) — 이름·급수·성별.
    세션 스냅샷(SessionParticipant)만 바꾸며 계정 유저 프로필 원본은 건드리지 않는다.
    (이 대진에서만 적용 · 세션 종료 후 세션 데이터에만 남음)
    보낸 필드만 부분 수정: name / level / gender."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)
    sp = get_object_or_404(SessionParticipant, id=pid, session=session)
    if "gender" in request.data and request.data.get("gender") not in ("male", "female"):
        return Response({"detail": "성별(male/female)을 선택해 주세요."},
                        status=status.HTTP_400_BAD_REQUEST)
    fields = set()
    # 회원 급수·성별을 세션에서 처음 덮어쓸 때: 현재 유효값을 스냅샷으로 고정하고 override 표시.
    # 이후 live_level_gender가 프로필 대신 이 스냅샷을 사용 — 프로필 원본은 불변.
    if sp.user_id and (("level" in request.data) or ("gender" in request.data)) and not sp.overridden:
        sp.base_level, sp.gender = sp.live_level_gender()
        sp.overridden = True
        fields.update(["base_level", "gender", "overridden"])
    if "name" in request.data:
        sp.guest_name = (request.data.get("name") or "").strip()  # 세션 표시 이름 override
        fields.add("guest_name")
    if "gender" in request.data:
        sp.gender = request.data.get("gender")
        fields.add("gender")
    if "level" in request.data:
        sp.base_level = level_to_score(request.data.get("level") or "")
        fields.add("base_level")
    if fields:
        sp.save(update_fields=list(fields))
    return Response(serialize_participant(sp))


# ===== 승인자 재동기화 (세션 시작 후 승인 보정) =====

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sync_participants(request, session_id):
    """세션 시작 후 승인된 신청자를 풀에 추가(스냅샷 1회 한계 보정). 운영자 전용.
    이미 들어온 사람은 건드리지 않고, 빠진 승인자만 추가한다."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)

    existing = set(session.participants.exclude(user__isnull=True)
                   .values_list("user_id", flat=True))
    apps = BandScheduleApplication.objects.filter(
        schedule=session.schedule, status="approved").select_related("user")
    added = 0
    with transaction.atomic():
        for app in apps:
            if app.user_id in existing:
                continue
            score, gender = _profile_level_gender(app.user)
            attendance = (SessionParticipant.Attendance.PRESENT if app.checked_in_at
                          else SessionParticipant.Attendance.NOT_PRESENT)
            SessionParticipant.objects.create(
                session=session, user=app.user, base_level=score, gender=gender,
                attendance=attendance)
            added += 1
    data = serialize_session(session)
    data["added"] = added
    return Response(data)


# ===== 예약 경기 (이후 예정) =====

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_reservation(request, session_id):
    """운영자가 대기열 4명을 골라 '이후 예정' 경기 예약. 자동 모드에서도 사용.
    예약된 4명은 자동 추천 풀에서 제외(확보)되고, 코트가 비면 자동보다 우선 투입."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)
    if session.status == MatchSession.Status.PREPARING:
        return Response({"detail": "먼저 [운영 시작]을 눌러 대진을 시작하세요."}, status=status.HTTP_409_CONFLICT)

    ids = request.data.get("participant_ids") or []
    if not isinstance(ids, (list, tuple)) or len({*ids}) != 4:
        return Response({"detail": "서로 다른 4명을 선택해야 합니다."},
                        status=status.HTTP_400_BAD_REQUEST)
    sps = list(SessionParticipant.objects.filter(id__in=ids, session=session))
    if len(sps) != 4:
        return Response({"detail": "참가자를 찾을 수 없습니다."},
                        status=status.HTTP_400_BAD_REQUEST)
    if any(sp.attendance != SessionParticipant.Attendance.PRESENT for sp in sps):
        return Response({"detail": "참여중인 사람만 예약할 수 있어요."},
                        status=status.HTTP_400_BAD_REQUEST)

    # 경기 중인 사람도 예약 허용 → 코트에서 나오면 후순위로 자동 투입(_consume_reservation).
    coach_ids = _coach_ids(session)
    reserved_ids = reserved_participant_ids(session)
    for sp in sps:
        if sp.id in coach_ids:
            return Response({"detail": "코치는 예약 경기에 넣을 수 없어요."},
                            status=status.HTTP_400_BAD_REQUEST)
        if sp.id in reserved_ids:
            return Response({"detail": "이미 다른 예약에 들어간 사람이 있어요."},
                            status=status.HTTP_409_CONFLICT)

    disc = request.data.get("discipline")
    if disc and disc not in Match.Discipline.values:
        return Response({"detail": "잘못된 종목"}, status=status.HTTP_400_BAD_REQUEST)
    # 운영자 수동 지정(대기열에서 직접 고른 4명)은 종목 모드 무시 — 남복/여복 모드여도 혼복 허용 (자동 추천만 모드 준수)

    next_order = (session.reservations.aggregate(Max("order"))["order__max"] or 0) + 1
    with transaction.atomic():
        r = ReservedMatch.objects.create(
            session=session, discipline=disc or "", created_by=request.user, order=next_order)
        for sp in sps:
            ReservedMatchPlayer.objects.create(reservation=r, participant=sp)
    r = ReservedMatch.objects.prefetch_related("players__participant__user").get(id=r.id)
    return Response(serialize_reservation(r), status=status.HTTP_201_CREATED)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def reservation_detail(request, session_id, reservation_id):
    """예약 경기 수정(PATCH: 멤버·종목 교체, id·큐 순서 유지) / 삭제(DELETE). 운영자 전용.
    PATCH body: participant_ids(4명 필수), discipline(선택·생략 시 성별 자동)."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    r = get_object_or_404(ReservedMatch, id=reservation_id, session=session)

    if request.method == "DELETE":
        r.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH — 멤버·종목만 교체, 코트/예약 순서는 건드리지 않음
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)
    ids = request.data.get("participant_ids") or []
    if not isinstance(ids, (list, tuple)) or len({*ids}) != 4:
        return Response({"detail": "서로 다른 4명을 선택해야 합니다."},
                        status=status.HTTP_400_BAD_REQUEST)
    sps = list(SessionParticipant.objects.filter(id__in=ids, session=session))
    if len(sps) != 4:
        return Response({"detail": "참가자를 찾을 수 없습니다."},
                        status=status.HTTP_400_BAD_REQUEST)
    if any(sp.attendance != SessionParticipant.Attendance.PRESENT for sp in sps):
        return Response({"detail": "참여중인 사람만 예약할 수 있어요."},
                        status=status.HTTP_400_BAD_REQUEST)
    # 경기 중인 사람도 예약 편집 후보 허용(item 15 일관) → 코트에서 나오면 후순위로 투입
    coach_ids = _coach_ids(session)
    # 이 예약의 기존 멤버는 중복 체크에서 제외(그대로 두거나 교체 가능)
    reserved_ids = reserved_participant_ids(session) - set(
        r.players.values_list("participant_id", flat=True))
    for sp in sps:
        if sp.id in coach_ids:
            return Response({"detail": "코치는 예약 경기에 넣을 수 없어요."},
                            status=status.HTTP_400_BAD_REQUEST)
        if sp.id in reserved_ids:
            return Response({"detail": "이미 다른 예약에 들어간 사람이 있어요."},
                            status=status.HTTP_409_CONFLICT)
    disc = request.data.get("discipline")
    if disc and disc not in Match.Discipline.values:
        return Response({"detail": "잘못된 종목"}, status=status.HTTP_400_BAD_REQUEST)
    # 운영자 수동 지정(대기열에서 직접 고른 4명)은 종목 모드 무시 — 남복/여복 모드여도 혼복 허용 (자동 추천만 모드 준수)

    with transaction.atomic():
        r.discipline = disc or ""
        r.save(update_fields=["discipline"])
        r.players.all().delete()
        for sp in sps:
            ReservedMatchPlayer.objects.create(reservation=r, participant=sp)
    r = ReservedMatch.objects.prefetch_related("players__participant__user").get(id=r.id)
    return Response(serialize_reservation(r))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def move_reservation(request, session_id, reservation_id):
    """예약 경기 순서 변경(↑↓). body: direction 'up'|'down'. 인접 예약과 자리 교환."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    direction = request.data.get("direction")
    if direction not in ("up", "down"):
        return Response({"detail": "direction은 up 또는 down이어야 합니다."},
                        status=status.HTTP_400_BAD_REQUEST)
    siblings = list(session.reservations.all())  # order, created_at 순
    idx = next((i for i, x in enumerate(siblings) if x.id == reservation_id), None)
    if idx is None:
        return Response({"detail": "예약을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
    target = idx - 1 if direction == "up" else idx + 1
    if 0 <= target < len(siblings):
        siblings[idx], siblings[target] = siblings[target], siblings[idx]
        with transaction.atomic():
            for i, x in enumerate(siblings):
                if x.order != i:
                    x.order = i
                    x.save(update_fields=["order"])
    return Response(serialize_session(session))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pause_session(request, session_id):
    """[일시 중단] / [재개] — body: paused(bool). 사진·공지 등 잠깐 멈출 때.
    진행 중 경기는 그대로 두고 '다음 경기 투입'만 막는다. 재개하면 빈 코트를 바로 채운다."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status != MatchSession.Status.ACTIVE:
        return Response({"detail": "진행 중인 대진에서만 일시 중단할 수 있어요."},
                        status=status.HTTP_409_CONFLICT)
    paused = bool(request.data.get("paused", True))
    if session.paused != paused:
        session.paused = paused
        session.save(update_fields=["paused", "updated_at"])
        if not paused and session.auto:
            # 재개 — 중단 동안 비어 있던 코트를 즉시 채운다
            for court in session.courts.all():
                if not court.matches.filter(status="playing").exists():
                    with transaction.atomic():
                        Court.objects.select_for_update().get(pk=court.pk)
                        if not court.matches.filter(status="playing").exists():
                            _fill_court(session, court, allow_auto=True)
            ensure_next_lineup(session)
    return Response(serialize_session(session))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def begin_session(request, session_id):
    """[운영 시작] — 준비(preparing) → 진행중(active). 자동이면 첫 경기 투입."""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다. 다시 하려면 리셋하세요."}, status=status.HTTP_409_CONFLICT)
    if session.status != MatchSession.Status.ACTIVE:
        session.status = MatchSession.Status.ACTIVE
        session.save(update_fields=["status", "updated_at"])
        ensure_next_lineup(session)
        session.refresh_from_db()
    return Response(serialize_session(session))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_session(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    session.status = MatchSession.Status.ENDED
    session.next_lineup = None
    session.save(update_fields=["status", "next_lineup", "updated_at"])
    return Response(serialize_session(session))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reset_session(request, session_id):
    """대진 세션 리셋 (운영자). body: mode = "game" | "full".
    - game: 경기·이력·예약·파트너·코치고정·개인 경기수만 초기화. 참가자·출석 유지.
    - full: 위 + 현장 게스트 삭제 + 전원 출석 초기화 → 최초 화면(체크인부터).
      (참가자 급수/성별 편집(override)은 유지)"""
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    # 종료된 세션도 리셋으로 되살릴 수 있게 허용 (리셋 = 준비 상태로 초기화)
    mode = request.data.get("mode", "game")
    if mode not in ("game", "full"):
        return Response({"detail": 'mode는 "game" 또는 "full" 이어야 합니다.'},
                        status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        # 경기·이력·예약·파트너·코치 초기화 (game/full 공통)
        Match.objects.filter(session=session).delete()          # MatchPlayer cascade
        Pair.objects.filter(session=session).delete()
        PartnerRequest.objects.filter(session=session).delete()
        ReservedMatch.objects.filter(session=session).delete()  # ReservedMatchPlayer cascade
        session.courts.update(coach=None, coach_resting=False)
        session.next_lineup = None                              # 확정 다음경기 초기화(stale 방지)
        session.status = MatchSession.Status.PREPARING          # 리셋 = 준비 상태로 → [운영 시작] 다시
        session.save(update_fields=["next_lineup", "status", "updated_at"])
        if mode == "full":
            session.participants.filter(user__isnull=True).delete()  # 현장 게스트 삭제
            # 원본 승인 명단과 재동기화 (최초 화면 + 최신 명단)
            approved_uids = set(BandScheduleApplication.objects.filter(
                schedule=session.schedule, status="approved").values_list("user_id", flat=True))
            # 더 이상 승인 아닌 회원(취소·강등) 제거
            session.participants.exclude(user__isnull=True).exclude(
                user_id__in=approved_uids).delete()
            # 세션에 빠진 승인자 편입
            existing = set(session.participants.values_list("user_id", flat=True))
            for app in BandScheduleApplication.objects.filter(
                    schedule=session.schedule, status="approved").select_related("user"):
                if app.user_id in existing:
                    continue
                score, gender = _profile_level_gender(app.user)
                SessionParticipant.objects.create(
                    session=session, user=app.user, base_level=score, gender=gender,
                    attendance=SessionParticipant.Attendance.NOT_PRESENT)
            # 전원 출석·경기수 초기화
            session.participants.update(
                games_mixed=0, games_mens=0, games_womens=0,
                last_game_ended_at=None,
                attendance=SessionParticipant.Attendance.NOT_PRESENT)
        else:
            session.participants.update(
                games_mixed=0, games_mens=0, games_womens=0, last_game_ended_at=None)

    session.refresh_from_db()
    return Response(serialize_session(session))
