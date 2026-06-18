from itertools import combinations
from band.matchmaking.types import (
    Player, Discipline, Mode, Preset, PRESETS, GamePlan,
    NeedOperatorChoice, PairStats, MALE, FEMALE,
)
from band.matchmaking.selection import queue_order
from band.matchmaking.cost import best_split, game_cost, _valid_for_discipline


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


# ===== 파트너(고정 2인 팀) 인지 추천 =====

def _pair_discipline(pa: Player, pb: Player) -> Discipline:
    if pa.gender == MALE and pb.gender == MALE:
        return Discipline.MENS
    if pa.gender == FEMALE and pb.gender == FEMALE:
        return Discipline.WOMENS
    return Discipline.MIXED


def _best_pair_game(pa, pb, disc, opp_pool, weights, stats, female_adjust, window):
    """파트너(pa,pb)를 team1 고정으로 두고, 비-파트너 풀에서 상대 2명을 최적 선택."""
    if disc == Discipline.MENS:
        cand = [p for p in opp_pool if p.gender == MALE]
    elif disc == Discipline.WOMENS:
        cand = [p for p in opp_pool if p.gender == FEMALE]
    else:
        cand = list(opp_pool)
    cand = queue_order(cand)[:max(window, 2)]
    if len(cand) < 2:
        return None
    team1 = (pa.id, pb.id)
    best = None
    best_score = None
    for x, y in combinations(cand, 2):
        if not _valid_for_discipline((pa, pb), (x, y), disc):
            continue
        four = [pa, pb, x, y]
        team2 = (x.id, y.id)
        base = game_cost(four, team1, team2, disc, weights, stats, female_adjust)
        fairness = weights.fairness * (x.total_games + y.total_games)
        score = base + fairness
        if best_score is None or score < best_score:
            best_score = score
            best = GamePlan(discipline=disc, team1=team1, team2=team2)
    return best


def recommend_with_pairs(pool, pairs, mode: Mode, preset: Preset,
                         stats: PairStats, female_adjust: int = 1,
                         window: int = 8) -> GamePlan | NeedOperatorChoice | None:
    """파트너 쌍을 우선 배정한 뒤 일반 추천. pairs: list[PairUnit]."""
    if not pairs:
        return recommend_next_game(pool, mode, preset, stats, female_adjust, window)

    weights = PRESETS[preset]
    by_id = {p.id: p for p in pool}
    allowed = _disciplines_for_mode(mode)
    active = [pr for pr in pairs if pr.a in by_id and pr.b in by_id]

    paired_ids = set()
    strict_ids = set()
    for pr in active:
        paired_ids.update((pr.a, pr.b))
        if pr.strict:
            strict_ids.update((pr.a, pr.b))

    avg = sum(p.total_games for p in pool) / len(pool) if pool else 0

    # 같이 들어갈 수 있는 쌍 후보 — 경기 적은 쌍 우선, best-effort는 평균보다 앞서면 양보
    seedable = []
    for pr in active:
        pa, pb = by_id[pr.a], by_id[pr.b]
        disc = _pair_discipline(pa, pb)
        if disc not in allowed:
            continue
        pair_avg = (pa.total_games + pb.total_games) / 2
        if not pr.strict and pair_avg > avg + 0.5:
            continue
        seedable.append((pair_avg, pr, pa, pb, disc))
    seedable.sort(key=lambda x: x[0])

    for _, pr, pa, pb, disc in seedable:
        opp_pool = [p for p in pool if p.id not in paired_ids]
        plan = _best_pair_game(pa, pb, disc, opp_pool, weights, stats, female_adjust, window)
        if plan is not None:
            return plan

    # 파트너로 못 짜면: strict 멤버만 제외하고 일반 추천 (best-effort는 일반 큐 참여)
    rest = [p for p in pool if p.id not in strict_ids]
    return recommend_next_game(rest, mode, preset, stats, female_adjust, window)


# ===== 코치(자강) 고정 코트 =====

def pick_ace_three(pool, met_count):
    """코치와 함께 들어갈 3명. '만난 코치 수' 적은 사람 우선(공동 우선), 동률은 큐 순서."""
    order = queue_order(pool)  # 경기수·휴식 기준 정렬
    ranked = sorted(order, key=lambda p: met_count.get(p.id, 0))  # stable=큐순서 유지
    return ranked[:3]


def build_ace_match(coach, three):
    """코치 + 3명 → GamePlan. 종목은 4명 성별로, 코치는 약체와 한 팀(밸런스 보정)."""
    if coach is None or len(three) < 3:
        return None
    four = [coach] + list(three)
    males = sum(1 for p in four if p.gender == MALE)
    if males == 4:
        disc = Discipline.MENS
    elif males == 0:
        disc = Discipline.WOMENS
    else:
        disc = Discipline.MIXED

    if disc == Discipline.MIXED:
        opp_gender = FEMALE if coach.gender == MALE else MALE
        cands = [p for p in three if p.gender == opp_gender] or list(three)
        mate = min(cands, key=lambda p: p.base_level)
    else:
        mate = min(three, key=lambda p: p.base_level)

    team2 = tuple(p.id for p in three if p.id != mate.id)
    return GamePlan(discipline=disc, team1=(coach.id, mate.id), team2=team2)
