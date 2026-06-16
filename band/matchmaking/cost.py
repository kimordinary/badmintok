from band.matchmaking.types import (
    Player, Discipline, Weights, GamePlan, PairStats, MALE, FEMALE,
)
from band.matchmaking.scoring import effective_score

# 4명을 두 팀(2:2)으로 나누는 3가지 방법. 각 항목은 team1 인덱스 쌍.
_SPLITS = [((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))]


def _valid_for_discipline(team1_players, team2_players, discipline) -> bool:
    if discipline != Discipline.MIXED:
        return True  # 남복/여복은 성별 풀에서 이미 동성만 들어옴
    # 혼복: 정상은 각 팀 남1여1. 성비가 깨진 경우 동성팀 허용.
    # 단, "양 팀 모두 같은 성별"(예: 남남 vs 여여)은 혼복이 아니므로 제외.
    def is_same(team):
        return team[0].gender == team[1].gender
    if is_same(team1_players) and is_same(team2_players):
        return False
    return True


def game_cost(players, team1, team2, discipline, weights: Weights,
              stats: PairStats, female_adjust: int) -> float:
    by_id = {p.id: p for p in players}
    s1 = sum(effective_score(by_id[i], discipline, female_adjust) for i in team1)
    s2 = sum(effective_score(by_id[i], discipline, female_adjust) for i in team2)
    balance = (s1 - s2) ** 2
    partner = stats.partner_count(*team1) + stats.partner_count(*team2)
    opponent = sum(stats.opponent_count(a, b) for a in team1 for b in team2)
    return (weights.balance * balance
            + weights.partner * partner
            + weights.opponent * opponent)


def best_split(players, discipline, weights: Weights, stats: PairStats,
               female_adjust: int) -> GamePlan | None:
    assert len(players) == 4
    best = None
    best_cost = None
    for (a, b), (c, d) in _SPLITS:
        t1p = (players[a], players[b])
        t2p = (players[c], players[d])
        if not _valid_for_discipline(t1p, t2p, discipline):
            continue
        team1 = (t1p[0].id, t1p[1].id)
        team2 = (t2p[0].id, t2p[1].id)
        cost = game_cost(players, team1, team2, discipline, weights, stats, female_adjust)
        if best_cost is None or cost < best_cost:
            best_cost = cost
            best = GamePlan(discipline=discipline, team1=team1, team2=team2)
    return best
