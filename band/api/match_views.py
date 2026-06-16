from itertools import combinations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from band.models import BandMember, BandSchedule, BandScheduleApplication
from band.match_models import MatchSession, SessionParticipant, Court, Match, MatchPlayer
from band.matchmaking.scoring import level_to_score
from band.match_state import build_pool, build_pairstats
from band.matchmaking.engine import recommend_next_game, _discipline_feasible
from band.matchmaking.types import Mode, Preset, Discipline, NeedOperatorChoice, GamePlan, PRESETS
from band.matchmaking.cost import best_split
from band.matchmaking.selection import queue_order
from band.api.match_serializers import serialize_session, serialize_match, serialize_participant


def _is_operator(user, band) -> bool:
    return BandMember.objects.filter(
        band=band, user=user, status="active",
        role__in=["owner", "admin"]).exists()


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

    with transaction.atomic():
        session = MatchSession.objects.create(
            schedule=schedule, court_count=court_count,
            discipline_mode=mode, preset=preset, created_by=request.user)
        for i in range(1, court_count + 1):
            Court.objects.create(session=session, index=i)
        apps = BandScheduleApplication.objects.filter(
            schedule=schedule, status="approved").select_related("user")
        for app in apps:
            score, gender = _profile_level_gender(app.user)
            SessionParticipant.objects.create(
                session=session, user=app.user, base_level=score, gender=gender,
                attendance=SessionParticipant.Attendance.NOT_PRESENT)

    return Response(serialize_session(session), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def session_state(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    return Response(serialize_session(session))


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
    session.save(update_fields=["discipline_mode", "updated_at"])
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
    session.save(update_fields=["preset", "updated_at"])
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


def _on_court_ids(session):
    ids = set()
    for m in Match.objects.filter(session=session, status="playing").prefetch_related("players"):
        ids.update(mp.participant_id for mp in m.players.all())
    return ids


def _create_match(session, court, plan: GamePlan):
    match = Match.objects.create(
        session=session, court=court, discipline=plan.discipline.value)
    for pid in plan.team1:
        MatchPlayer.objects.create(match=match, participant_id=pid, team=1)
    for pid in plan.team2:
        MatchPlayer.objects.create(match=match, participant_id=pid, team=2)
    return match


def _fill_court(session, court, forced_discipline=None):
    """반환: (match | None, need: NeedOperatorChoice | None)"""
    pool = build_pool(session, on_court_participant_ids=_on_court_ids(session))
    stats = build_pairstats(session)

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

    result = recommend_next_game(
        pool, _MODE_MAP[session.discipline_mode], _PRESET_MAP[session.preset],
        stats, female_adjust=session.female_adjust)
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
    court = get_object_or_404(Court, session=session, index=index)
    if court.matches.filter(status="playing").exists():
        return Response({"detail": "이미 진행 중인 경기가 있습니다."}, status=status.HTTP_409_CONFLICT)

    forced = request.data.get("discipline")
    forced_disc = _DISC_MAP.get(forced) if forced else None
    with transaction.atomic():
        match, need = _fill_court(session, court, forced_disc)
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
def end_court(request, session_id, index):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)
    court = get_object_or_404(Court, session=session, index=index)
    match = court.matches.filter(status="playing").prefetch_related("players__participant").first()
    if match is None:
        return Response({"detail": "진행 중인 경기가 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    with transaction.atomic():
        match.status = "done"
        match.ended_at = now
        match.save(update_fields=["status", "ended_at"])
        disc_field = {"mixed": "games_mixed", "mens": "games_mens", "womens": "games_womens"}[match.discipline]
        for mp in match.players.all():
            sp = mp.participant
            setattr(sp, disc_field, getattr(sp, disc_field) + 1)
            sp.last_game_ended_at = now
            sp.save(update_fields=[disc_field, "last_game_ended_at"])
        new_match, need = _fill_court(session, court)

    if need is not None:
        return Response({"ended": match.id, "match": None, "needs_choice": True,
                         "reason": need.reason, "options": [d.value for d in need.options]})
    return Response({
        "ended": match.id,
        "match": serialize_match(new_match) if new_match else None,
        "needs_choice": False,
    })


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def edit_match(request, session_id, match_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if session.status == MatchSession.Status.ENDED:
        return Response({"detail": "종료된 세션입니다."}, status=status.HTTP_409_CONFLICT)
    match = get_object_or_404(Match, id=match_id, session=session, status="playing")

    swap = request.data.get("swap")          # [out_participant_id, in_participant_id]
    discipline = request.data.get("discipline")

    if swap is not None:
        if not isinstance(swap, (list, tuple)) or len(swap) != 2:
            return Response({"detail": "swap은 [out_id, in_id] 형식이어야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

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
        if discipline in _DISC_MAP:
            match.discipline = discipline
            match.save(update_fields=["discipline"])

    match.refresh_from_db()
    match = Match.objects.prefetch_related("players__participant__user").get(id=match.id)
    return Response(serialize_match(match))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_session(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    session.status = MatchSession.Status.ENDED
    session.save(update_fields=["status", "updated_at"])
    return Response({"id": session.id, "status": session.status})
