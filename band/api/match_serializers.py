from band.match_models import SessionParticipant
from band.match_state import build_pool
from band.matchmaking.selection import queue_order


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
    for mp in match.players.all():
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
    courts = []
    on_court_ids = set()
    for court in session.courts.all():
        current = court.matches.filter(status="playing").prefetch_related(
            "players__participant__user").first()
        if current:
            on_court_ids.update(mp.participant_id for mp in current.players.all())
        courts.append({
            "index": court.index,
            "match": serialize_match(current) if current else None,
        })
    pool = build_pool(session, on_court_participant_ids=on_court_ids)
    queue = [{"participant_id": p.id, "name": p.name, "total_games": p.total_games}
             for p in queue_order(pool)]
    return {
        "id": session.id,
        "status": session.status,
        "discipline_mode": session.discipline_mode,
        "preset": session.preset,
        "court_count": session.court_count,
        "participants": [serialize_participant(p) for p in participants],
        "courts": courts,
        "queue": queue,
    }
