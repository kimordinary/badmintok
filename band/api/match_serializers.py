from band.match_models import SessionParticipant, Match, Pair, PartnerRequest
from band.match_state import build_pool, build_pairstats
from band.matchmaking.selection import queue_order


def serialize_pair(pair):
    return {
        "id": pair.id,
        "strict": pair.strict,
        "members": [
            {"participant_id": pair.p1_id, "name": pair.p1.user.activity_name},
            {"participant_id": pair.p2_id, "name": pair.p2.user.activity_name},
        ],
    }


def serialize_partner_request(req):
    return {
        "id": req.id,
        "status": req.status,
        "strict": req.strict,
        "from": {"participant_id": req.from_participant_id,
                 "name": req.from_participant.user.activity_name},
        "to": {"participant_id": req.to_participant_id,
               "name": req.to_participant.user.activity_name},
    }


def serialize_participant(sp):
    return {
        "id": sp.id,
        "user_id": sp.user_id,
        "name": sp.user.activity_name,
        "gender": sp.gender,
        "base_level": sp.base_level,
        "attendance": sp.attendance,
        "games_mixed": sp.games_mixed,
        "games_mens": sp.games_mens,
        "games_womens": sp.games_womens,
        "total_games": sp.games_mixed + sp.games_mens + sp.games_womens,
    }


def serialize_match(match):
    teams = {1: [], 2: []}
    for mp in match.players.select_related("participant__user").all():
        teams[mp.team].append({
            "participant_id": mp.participant_id,
            "name": mp.participant.user.activity_name,
            "base_level": mp.participant.base_level,
            "gender": mp.participant.gender,
        })
    return {
        "id": match.id,
        "discipline": match.discipline,
        "status": match.status,
        "team1": teams[1],
        "team2": teams[2],
    }


def serialize_session(session):
    participants = list(session.participants.select_related("user"))
    court_rows = list(session.courts.select_related("coach__user").all())
    coach_ids = {c.coach_id for c in court_rows if c.coach_id}

    # 코치 커버리지: 출석 비-코치 중 그 코치와 한 번이라도 친 사람 수 / 전체
    coverage = {}
    if coach_ids:
        stats = build_pairstats(session)
        present_ids = [p.id for p in participants
                       if p.attendance == "present" and p.id not in coach_ids]
        for cid in coach_ids:
            met = sum(1 for pid in present_ids
                      if stats.partner_count(pid, cid) + stats.opponent_count(pid, cid) > 0)
            coverage[cid] = {"met": met, "total": len(present_ids)}

    courts = []
    on_court_ids = set()
    for court in court_rows:
        current = court.matches.filter(status="playing").prefetch_related(
            "players__participant__user").first()
        if current:
            on_court_ids.update(mp.participant_id for mp in current.players.all())
        coach = None
        if court.coach_id:
            coach = {"participant_id": court.coach_id,
                     "name": court.coach.user.activity_name,
                     "coverage": coverage.get(court.coach_id)}
        courts.append({
            "index": court.index,
            "match": serialize_match(current) if current else None,
            "coach": coach,
        })
    # 코치는 본인 코트에 고정되어 일반 대기열에서 제외
    pool = build_pool(session, on_court_participant_ids=on_court_ids | coach_ids)
    queue = [{"participant_id": p.id, "name": p.name, "total_games": p.total_games}
             for p in queue_order(pool)]
    pairs = session.pairs.select_related("p1__user", "p2__user").all()
    pending = session.partner_requests.filter(
        status=PartnerRequest.Status.PENDING).select_related(
        "from_participant__user", "to_participant__user")
    return {
        "id": session.id,
        "status": session.status,
        "discipline_mode": session.discipline_mode,
        "preset": session.preset,
        "court_count": session.court_count,
        "participants": [serialize_participant(p) for p in participants],
        "courts": courts,
        "queue": queue,
        "pairs": [serialize_pair(pr) for pr in pairs],
        "partner_requests": [serialize_partner_request(r) for r in pending],
    }


def serialize_my_status(session, sp):
    """요청자 본인의 라이브 상태 (앱 참가자가 폴링). sp=None이면 비참가자."""
    playing_matches = list(
        Match.objects.filter(session=session, status="playing")
        .select_related("court")
        .prefetch_related("players__participant__user"))
    on_court_ids = set()
    current = None
    my_team = None
    for m in playing_matches:
        team_by_pid = {mp.participant_id: mp.team for mp in m.players.all()}
        on_court_ids.update(team_by_pid)
        if sp and sp.id in team_by_pid:
            current = m
            my_team = team_by_pid[sp.id]

    pool = build_pool(session, on_court_participant_ids=on_court_ids)
    order = queue_order(pool)
    queue_total = len(order)
    queue_position = None
    if sp:
        for i, p in enumerate(order):
            if p.id == sp.id:
                queue_position = i + 1
                break

    empty_courts = max(0, session.courts.count() - len(playing_matches))
    playing = current is not None
    # 다음 경기 후보: 대기열 상위 (빈 코트 × 4) 또는 최소 4명 안에 들면 곧 입장
    up_next = (not playing) and queue_position is not None and \
        queue_position <= max(4, empty_courts * 4)

    current_match = None
    if current is not None:
        cm = serialize_match(current)
        cm["court_index"] = current.court.index
        cm["my_team"] = my_team
        cm["is_coach_court"] = current.court.coach_id is not None
        current_match = cm

    games = None
    if sp:
        games = {
            "mixed": sp.games_mixed, "mens": sp.games_mens, "womens": sp.games_womens,
            "total": sp.games_mixed + sp.games_mens + sp.games_womens,
        }

    return {
        "session_id": session.id,
        "session_status": session.status,
        "participant_id": sp.id if sp else None,
        "attendance": sp.attendance if sp else None,
        "games": games,
        "playing": playing,
        "current_match": current_match,
        "queue_position": queue_position,
        "queue_total": queue_total,
        "up_next": up_next,
    }
