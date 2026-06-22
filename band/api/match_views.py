from itertools import combinations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from band.models import BandMember, BandSchedule, BandScheduleApplication
from band.match_models import (
    MatchSession, SessionParticipant, Court, Match, MatchPlayer, Pair, PartnerRequest,
    ReservedMatch, ReservedMatchPlayer)
from band.matchmaking.scoring import level_to_score
from band.match_state import (
    build_pool, build_pairstats, build_pairs, build_player, build_met_count,
    reserved_participant_ids)
from band.matchmaking.engine import (
    recommend_next_game, recommend_with_pairs, _discipline_feasible,
    pick_ace_three, build_ace_match)
from band.matchmaking.types import Mode, Preset, Discipline, NeedOperatorChoice, GamePlan, PRESETS
from band.matchmaking.cost import best_split
from band.matchmaking.selection import queue_order
from band.api.match_serializers import (
    serialize_session, serialize_match, serialize_participant, serialize_my_status,
    serialize_pair, serialize_partner_request, serialize_reservation)


def _is_operator(user, band) -> bool:
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
            # 번개 상세에서 자가 출석 체크인(checked_in_at)한 사람은 바로 참여중으로
            attendance = (SessionParticipant.Attendance.PRESENT if app.checked_in_at
                          else SessionParticipant.Attendance.NOT_PRESENT)
            SessionParticipant.objects.create(
                session=session, user=app.user, base_level=score, gender=gender,
                attendance=attendance)

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
        session=session, court=court, discipline=plan.discipline.value)
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


def _fill_court(session, court, forced_discipline=None):
    """반환: (match | None, need: NeedOperatorChoice | None)"""
    coach_ids = _coach_ids(session)
    reserved_ids = reserved_participant_ids(session)
    # 코치는 본인 코트 고정, 예약 멤버는 확보 → 일반 풀(큐·공정성)에서 제외
    pool = build_pool(
        session,
        on_court_participant_ids=_on_court_ids(session) | coach_ids | reserved_ids)
    stats = build_pairstats(session)

    # 코치 고정 코트: 코치(출석 시) + '못 만난 사람 우선' 3명
    if court.coach_id is not None and forced_discipline is None:
        coach_sp = SessionParticipant.objects.filter(
            id=court.coach_id, session=session,
            attendance=SessionParticipant.Attendance.PRESENT).select_related("user").first()
        if coach_sp is not None:
            met = build_met_count(session, coach_ids, stats)
            three = pick_ace_three(pool, met)
            plan = build_ace_match(build_player(coach_sp), three)
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

    # 예약(이후 예정) 경기가 준비됐으면 자동 추천보다 우선 투입
    reserved = _consume_reservation(session, court, stats)
    if reserved is not None:
        return reserved, None

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
    court = get_object_or_404(Court, session=session, index=index)
    if court.matches.filter(status="playing").exists():
        return Response({"detail": "이미 진행 중인 경기가 있습니다."}, status=status.HTTP_409_CONFLICT)

    forced = request.data.get("discipline")
    pids = request.data.get("participant_ids")
    # 직접 채우기: participant_ids 지정 시 그 4명으로 즉시 투입(자동추천 무시)
    if pids:
        with transaction.atomic():
            match, err = _manual_fill(session, court, pids, forced)
        if err is not None:
            return Response({"match": None, "needs_choice": False, "detail": err},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"match": serialize_match(match), "needs_choice": False})

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


# ===== 참가자 본인용 (앱) =====

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_status(request, session_id):
    """세션 내 '내 라이브 상태' (출석·현재경기·대기순번·게임수). 앱이 폴링."""
    session = get_object_or_404(MatchSession, id=session_id)
    sp = _my_participant(session, request.user)
    return Response(serialize_my_status(session, sp))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_status_by_schedule(request, schedule_id):
    """일정 기준 '내 상태'. 앱은 schedule_id만 알아도 세션 유무·내 상태 조회 가능."""
    schedule = get_object_or_404(BandSchedule, id=schedule_id)
    session = getattr(schedule, "match_session", None)
    approved = BandScheduleApplication.objects.filter(
        schedule=schedule, user=request.user, status="approved").exists()
    if session is None:
        return Response({
            "session_id": None, "session_status": None,
            "participant_id": None, "attendance": None, "games": None,
            "playing": False, "current_match": None,
            "queue_position": None, "queue_total": 0, "up_next": False,
            "approved": approved,
        })
    sp = _my_participant(session, request.user)
    data = serialize_my_status(session, sp)
    data["approved"] = approved or sp is not None
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
    return Response(serialize_my_status(session, sp))


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
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    pair = get_object_or_404(Pair, id=pair_id, session=session)
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

    on_court = _on_court_ids(session)
    coach_ids = _coach_ids(session)
    reserved_ids = reserved_participant_ids(session)
    for sp in sps:
        if sp.id in on_court:
            return Response({"detail": "경기 중인 사람은 예약할 수 없어요."},
                            status=status.HTTP_400_BAD_REQUEST)
        if sp.id in coach_ids:
            return Response({"detail": "코치는 예약 경기에 넣을 수 없어요."},
                            status=status.HTTP_400_BAD_REQUEST)
        if sp.id in reserved_ids:
            return Response({"detail": "이미 다른 예약에 들어간 사람이 있어요."},
                            status=status.HTTP_409_CONFLICT)

    disc = request.data.get("discipline")
    if disc and disc not in Match.Discipline.values:
        return Response({"detail": "잘못된 종목"}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        r = ReservedMatch.objects.create(
            session=session, discipline=disc or "", created_by=request.user)
        for sp in sps:
            ReservedMatchPlayer.objects.create(reservation=r, participant=sp)
    r = ReservedMatch.objects.prefetch_related("players__participant__user").get(id=r.id)
    return Response(serialize_reservation(r), status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_reservation(request, session_id, reservation_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    r = get_object_or_404(ReservedMatch, id=reservation_id, session=session)
    r.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_session(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    session.status = MatchSession.Status.ENDED
    session.save(update_fields=["status", "updated_at"])
    return Response({"id": session.id, "status": session.status})
