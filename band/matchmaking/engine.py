from itertools import combinations
from band.matchmaking.types import (
    Player, Discipline, Mode, Preset, PRESETS, GamePlan,
    NeedOperatorChoice, PairStats, MALE, FEMALE,
)
from band.matchmaking.selection import queue_order
from band.matchmaking.cost import best_split, game_cost


def _disciplines_for_mode(mode: Mode) -> tuple[Discipline, ...]:
    if mode == Mode.MIXED_ONLY:
        return (Discipline.MIXED,)
    if mode == Mode.SINGLES_GENDER:
        return (Discipline.MENS, Discipline.WOMENS)
    return (Discipline.MIXED, Discipline.MENS, Discipline.WOMENS)


def _discipline_feasible(combo, discipline) -> bool:
    males = sum(1 for p in combo if p.gender == MALE)
    females = len(combo) - males
    if discipline == Discipline.MENS:
        return males == 4
    if discipline == Discipline.WOMENS:
        return females == 4
    # MIXED: 동성팀 1개까지 허용 → 남녀 각 최소 1명
    return males >= 1 and females >= 1


def recommend_next_game(pool: list[Player], mode: Mode, preset: Preset,
                        stats: PairStats, female_adjust: int = 1,
                        window: int = 8) -> GamePlan | NeedOperatorChoice | None:
    if len(pool) < 4:
        return None

    weights = PRESETS[preset]
    order = queue_order(pool)
    candidates = order[:max(window, 4)]
    allowed = _disciplines_for_mode(mode)

    best = None
    best_score = None
    for combo in combinations(candidates, 4):
        for disc in allowed:
            if not _discipline_feasible(combo, disc):
                continue
            split = best_split(list(combo), disc, weights, stats, female_adjust)
            if split is None:
                continue
            base = game_cost(list(combo), split.team1, split.team2, disc,
                             weights, stats, female_adjust)
            fairness = weights.fairness * sum(p.total_games for p in combo)
            score = base + fairness
            if best_score is None or score < best_score:
                best_score = score
                best = split

    if best is not None:
        return best

    # 현재 모드로 아무 조합도 못 짬 → 운영자에게 대안 종목 제시
    fallback = []
    for disc in (Discipline.MENS, Discipline.WOMENS, Discipline.MIXED):
        if disc in allowed:
            continue  # 이미 시도했는데 실패
        if any(_discipline_feasible(c, disc) for c in combinations(order[:max(window, 4)], 4)):
            fallback.append(disc)
    return NeedOperatorChoice(
        reason=f"현재 모드({mode.value})로 경기를 구성할 수 없습니다.",
        options=tuple(fallback),
    )
