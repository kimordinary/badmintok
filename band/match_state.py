from band.matchmaking.types import Player, PairStats
from band.match_models import SessionParticipant, MatchPlayer, Match


def build_pool(session, on_court_participant_ids=None) -> list[Player]:
    on_court = on_court_participant_ids or set()
    pool = []
    qs = session.participants.filter(
        attendance=SessionParticipant.Attendance.PRESENT
    ).exclude(id__in=on_court)
    for sp in qs:
        pool.append(Player(
            id=sp.id,
            name=sp.user.activity_name,
            gender=sp.gender,
            base_level=sp.base_level,
            games_mixed=sp.games_mixed,
            games_mens=sp.games_mens,
            games_womens=sp.games_womens,
            last_game_ended_at=(sp.last_game_ended_at.timestamp()
                                if sp.last_game_ended_at else None),
        ))
    return pool


def build_pairstats(session) -> PairStats:
    partner = {}
    opponent = {}
    matches = Match.objects.filter(session=session).prefetch_related("players")
    for m in matches:
        team = {1: [], 2: []}
        for mp in m.players.all():
            team[mp.team].append(mp.participant_id)
        for t in (1, 2):
            for a, b in _pairs(team[t]):
                k = (a, b) if a < b else (b, a)
                partner[k] = partner.get(k, 0) + 1
        for a in team[1]:
            for b in team[2]:
                k = (a, b) if a < b else (b, a)
                opponent[k] = opponent.get(k, 0) + 1
    return PairStats(partner=partner, opponent=opponent)


def _pairs(ids):
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            yield ids[i], ids[j]
