from band.matchmaking.types import Player, PairStats, PairUnit
from band.match_models import (
    SessionParticipant, MatchPlayer, Match, Pair, ReservedMatchPlayer)


def build_player(sp) -> Player:
    return Player(
        id=sp.id,
        name=sp.display_name,
        gender=sp.gender,
        base_level=sp.base_level,
        games_mixed=sp.games_mixed,
        games_mens=sp.games_mens,
        games_womens=sp.games_womens,
        last_game_ended_at=(sp.last_game_ended_at.timestamp()
                            if sp.last_game_ended_at else None),
    )


def build_pool(session, on_court_participant_ids=None) -> list[Player]:
    on_court = on_court_participant_ids or set()
    qs = session.participants.filter(
        attendance=SessionParticipant.Attendance.PRESENT
    ).exclude(id__in=on_court)
    return [build_player(sp) for sp in qs]


def build_met_count(session, coach_ids, stats) -> dict:
    """현재 출석 참가자별 '만난 코치 수' (같이/상대로 한 번이라도 친 코치 수)."""
    met = {}
    present = session.participants.filter(
        attendance=SessionParticipant.Attendance.PRESENT)
    for sp in present:
        c = 0
        for cid in coach_ids:
            if cid == sp.id:
                continue
            if stats.partner_count(sp.id, cid) + stats.opponent_count(sp.id, cid) > 0:
                c += 1
        met[sp.id] = c
    return met


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


def build_pairs(session) -> list[PairUnit]:
    return [PairUnit(a=pr.p1_id, b=pr.p2_id, strict=pr.strict)
            for pr in Pair.objects.filter(session=session)]


def reserved_participant_ids(session) -> set:
    """예약 경기에 묶인 참가자 id (일반 풀·큐에서 제외해 확보)."""
    return set(ReservedMatchPlayer.objects.filter(
        reservation__session=session).values_list("participant_id", flat=True))
