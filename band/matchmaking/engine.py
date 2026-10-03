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
    # unknown(무관)은 남/여 어느 쪽으로도 세지 않는다 → 성별 종목에서 자동 제외
    males = sum(1 for p in combo if p.gender == MALE)
    females = sum(1 for p in combo if p.gender == FEMALE)
    if discipline == Discipline.MENS:
        return males == 4
    if discipline == Discipline.WOMENS:
        return females == 4
    # MIXED: 남2여2만. 3:1은 한 팀이 동성(남복/여복)이 되어 혼복이 아니다.
    # 모두 모드면 남는 성별이 남복/여복으로 자동 재분배되고, 혼복만 모드면 코트가 비어 성비 문제를 드러낸다.
    return males == 2 and females == 2


# 평균보다 이만큼(경기) 덜 뛰면 '동일 급수'의 급수 폭 조건을 완전히 푼다.
# 혼자 뜬 급수(자강 1명 등)는 비슷한 짝이 없어 계속 대기하게 되므로, 뒤처진 만큼 조건을 풀어
# 경기 수 격차를 막는다. 시뮬 기준 1.0이 최적 — 격차는 밸런스 수준(1.4경기)이면서 급수 폭은 절반 이하.
SPAN_RELAX_GAMES = 1.0

# 오래 못 뛴 사람을 데려가는 보상 가중치(제곱). 급수가 튀어 균형이 안 맞는 사람의 방치를 막는다.
CATCHUP_W = 6.0


def _span_penalty(four, weights, avg_games: float = 0.0) -> float:
    """4명의 급수 폭(최고-최저) 페널티. 폭 0~1은 무페널티, 2부터 제곱으로 커진다.
    두 팀 합이 같아도(자강+초심 vs A+C) 폭이 넓으면 '동일 급수'가 아니므로 비용을 매긴다.

    단, 혼자 뜬 급수(자강 1명 등)는 비슷한 짝이 없어 영원히 대기하게 되므로,
    평균보다 덜 뛴 사람이 끼면 폭 조건을 점점 완화한다(1경기 뒤처질수록 벌점 1/2, 1/3 …).
    weights.span=0인 '밸런스' 프리셋에서는 작동하지 않는다."""
    if not weights.span:
        return 0.0
    lv = [p.base_level for p in four]
    sp = max(lv) - min(lv)
    if sp <= 1:
        return 0.0
    deficit = max(0.0, avg_games - min(p.total_games for p in four))
    if deficit >= SPAN_RELAX_GAMES:
        return 0.0        # 이만큼 뒤처지면 급수 조건을 완전히 푼다 — 경기 수 격차가 벌어지지 않게
    return weights.span * (sp - 1) ** 2 * (1.0 - deficit / SPAN_RELAX_GAMES)


def recommend_next_game(pool: list[Player], mode: Mode, preset: Preset,
                        stats: PairStats, female_adjust: int = 1,
                        window: int = 12) -> GamePlan | NeedOperatorChoice | None:
    if len(pool) < 4:
        return None

    weights = PRESETS[preset]
    order = queue_order(pool)
    # 동일 급수는 비슷한 급수 4명을 모을 기회를 늘리려 후보를 넓게 본다(콘솔과 동일: 16)
    candidates = order[:max(16 if weights.span else window, 4)]
    allowed = _disciplines_for_mode(mode)

    # 혼복은 2남2여가 필요한데, 성비가 치우치면 대기 상위 N명 안에 소수 성별이 2명 미만일 수 있다.
    # 풀에는 짝이 있는데 창 밖이라 '구성 불가'가 되는 걸 막기 위해 소수 성별 상위 2명을 보강한다.
    if Discipline.MIXED in allowed:
        for g in (MALE, FEMALE):
            short = 2 - sum(1 for p in candidates if p.gender == g)
            if short > 0:
                have = {p.id for p in candidates}
                candidates = candidates + [p for p in order
                                           if p.gender == g and p.id not in have][:short]

    # 남녀 번갈아 유도(강제 아님): 남복/여복 모드에서 '덜 뛴 성별' 종목에 우선순위 부여
    gender_avg = {}
    if mode == Mode.SINGLES_GENDER:
        males_g = [p for p in pool if p.gender == MALE]
        females_g = [p for p in pool if p.gender == FEMALE]
        gender_avg[Discipline.MENS] = (sum(p.total_games for p in males_g) / len(males_g)) if males_g else 0
        gender_avg[Discipline.WOMENS] = (sum(p.total_games for p in females_g) / len(females_g)) if females_g else 0

    best = None
    best_score = None
    avg_games = (sum(p.total_games for p in pool) / len(pool)) if pool else 0.0
    for combo in combinations(candidates, 4):
        span = _span_penalty(combo, weights, avg_games)   # 조합(4명) 속성 — 팀 분배와 무관하므로 1회
        # 급수가 혼자 튀는 사람(D·초심 사이의 A 1명 등)은 어떻게 묶어도 팀 균형이 안 맞아
        # 균형 벌점이 공정성을 영구히 이겨 한 경기도 못 뛰는 일이 생긴다.
        # 뒤처진 정도를 제곱으로 보상해 반드시 차례가 오게 한다(제곱이라 오래 쉴수록 급격히 우선).
        catchup = CATCHUP_W * max(0.0, avg_games - min(p.total_games for p in combo)) ** 2
        for disc in allowed:
            if not _discipline_feasible(combo, disc):
                continue
            split = best_split(list(combo), disc, weights, stats, female_adjust)
            if split is None:
                continue
            base = game_cost(list(combo), split.team1, split.team2, disc,
                             weights, stats, female_adjust)
            fairness = weights.fairness * sum(p.total_games for p in combo)
            # 그 종목 성별이 이미 많이 뛰었으면 페널티 → 덜 뛴 성별이 먼저 선택됨(번갈아)
            balance = weights.fairness * gender_avg.get(disc, 0) * 2
            score = base + fairness + balance + span - catchup
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

# 파트너 쌍이 전체 평균보다 이만큼(경기) 앞서면 그 판은 양보한다.
# 0 = 평균을 넘는 즉시 양보. 시뮬 기준 0이 가장 공평(일반 대기자와 차이 +0.4경기, 연속출전 동일).
PAIR_AHEAD_ALLOW = 0.0


def _pair_discipline(pa: Player, pb: Player) -> Discipline:
    if pa.gender == MALE and pb.gender == MALE:
        return Discipline.MENS
    if pa.gender == FEMALE and pb.gender == FEMALE:
        return Discipline.WOMENS
    return Discipline.MIXED


def _best_pair_game(pa, pb, disc, opp_pool, weights, stats, female_adjust, window):
    """파트너(pa,pb)를 team1 고정으로 두고, 비-파트너 풀에서 상대 2명을 최적 선택."""
    if weights.span:
        window = max(window, 16)   # 동일 급수: 비슷한 급수 상대를 찾을 기회를 넓힌다
    avg_games = (sum(p.total_games for p in opp_pool) / len(opp_pool)) if opp_pool else 0.0
    if disc == Discipline.MENS:
        cand = queue_order([p for p in opp_pool if p.gender == MALE])[:max(window, 2)]
    elif disc == Discipline.WOMENS:
        cand = queue_order([p for p in opp_pool if p.gender == FEMALE])[:max(window, 2)]
    else:
        # 혼복(파트너가 남-여): 상대도 남1여1이어야 2남2여가 된다.
        # 전체 상위 N명만 보면 한 성별로 치우쳐 짝을 못 찾을 수 있어 성별별로 후보를 확보한다.
        cand = (queue_order([p for p in opp_pool if p.gender == MALE])[:max(window, 2)]
                + queue_order([p for p in opp_pool if p.gender == FEMALE])[:max(window, 2)])
    if len(cand) < 2:
        return None
    team1 = (pa.id, pb.id)
    best = None
    best_score = None
    for x, y in combinations(cand, 2):
        if not _discipline_feasible((pa, pb, x, y), disc):
            continue    # 혼복이면 2남2여만 통과
        if not _valid_for_discipline((pa, pb), (x, y), disc):
            continue
        four = [pa, pb, x, y]
        team2 = (x.id, y.id)
        base = game_cost(four, team1, team2, disc, weights, stats, female_adjust)
        fairness = weights.fairness * (x.total_games + y.total_games)
        # 동일 급수면 파트너 쌍과 상대 2명의 급수 폭도 억제 (일반 추천과 같은 규칙)
        score = base + fairness + _span_penalty(four, weights, avg_games)
        if best_score is None or score < best_score:
            best_score = score
            best = GamePlan(discipline=disc, team1=team1, team2=team2)
    return best


def recommend_with_pairs(pool, pairs, mode: Mode, preset: Preset,
                         stats: PairStats, female_adjust: int = 1,
                         window: int = 12) -> GamePlan | NeedOperatorChoice | None:
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
        # 파트너는 코트가 빌 때마다 일반 대기자보다 먼저 시도되므로, 평균보다 앞서면 양보시킨다.
        # strict(같이만)도 동일 적용 — 양보해도 따로 들어가지 않으니 '같이 친다'는 약속은 유지되고
        # 순서만 공평해진다. (예전엔 strict가 이 체크를 건너뛰어 쉬지 않고 연속 출전했다)
        if pair_avg > avg + PAIR_AHEAD_ALLOW:
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

def pick_ace_three(pool, met_count, mode=None, coach=None, with_coach=None):
    """코치와 함께 들어갈 3명.

    우선순위 2단:
      1차 '만난 코치 수'(met_count) — 아직 어떤 코치와도 못 친 사람을 먼저 (형평성, 기존 정책)
      2차 '이 코치와 친 횟수'(with_coach) — 같은 등급이면 이 코치와 덜 친 사람을 먼저
          (코치가 2명일 때 이미 이 코치와 친 사람이 또 뽑히는 중복·반복 방지)
    둘 다 '제외'가 아니라 '순서'라서, 안 친 사람이 없거나 부족하면 친 사람이 그대로 들어간다.

    남복/여복 모드: 코치 무관 동성 3명(남3 or 여3). 남·여 모두 3명 미만이면 [] (모수 부족).
    혼복만 모드: 코치 포함 2남2여가 되도록 반대 성별 2명 + 동성 1명. 못 맞추면 [] (코트 비움)."""
    wc = with_coach or {}
    cov = lambda p: (met_count.get(p.id, 0), wc.get(p.id, 0))   # 커버리지 우선순위 2단
    order = queue_order(pool)  # 경기수·휴식 기준 정렬
    if mode == Mode.MIXED_ONLY and coach is not None:
        opp = [p for p in order if p.gender != coach.gender and p.gender in (MALE, FEMALE)]
        same = [p for p in order if p.gender == coach.gender]
        if len(opp) < 2 or len(same) < 1:
            return []   # 2남2여를 못 만듦 → 코트를 비워 성비 문제를 드러낸다
        # 코치와 가장 덜 만난 반대 성별이 앵커(=코치의 짝) → 급수 근접으로 나머지 둘
        anchor = min(opp, key=cov)
        band = lambda p: (lambda d: 0 if d <= 1 else d)(abs(p.base_level - anchor.base_level))
        key = lambda p: (band(p),) + cov(p)
        opp2 = sorted([p for p in opp if p.id != anchor.id], key=key)[:1]
        same1 = sorted(same, key=key)[:1]
        if not opp2 or not same1:
            return []
        return [anchor] + opp2 + same1
    if mode == Mode.SINGLES_GENDER:
        males = [p for p in order if p.gender == MALE]
        females = [p for p in order if p.gender == FEMALE]
        groups = [g for g in (males, females) if len(g) >= 3]
        if not groups:
            return []  # 남·여 모두 3명 미만 → 코치 코트 못 채움(모수 부족)
        # 커버리지 우선: 코치와 덜 만난(met 합 낮은) 성별을 이번 판 코치 코트로
        order = min(groups, key=lambda g: (sum(met_count.get(p.id, 0) for p in g[:3]),
                                           sum(wc.get(p.id, 0) for p in g[:3])))
    if len(order) < 3:
        return []
    # 앵커=코치와 가장 덜 만난 사람 → 급수 근접 2명(preset 반영), 동률은 커버리지
    anchor = min(order, key=cov)
    band = lambda p: (lambda d: 0 if d <= 1 else d)(abs(p.base_level - anchor.base_level))
    rest = sorted([p for p in order if p.id != anchor.id],
                  key=lambda p: (band(p),) + cov(p))[:2]
    if len(rest) < 2:
        return []
    return [anchor] + rest


def build_ace_match(coach, three, mode=None):
    """코치 + 3명 → GamePlan. 코치는 약체와 한 팀(밸런스 보정).
    남복/여복 모드: 코치는 얹힘 → 종목은 나머지 3명 동성 기준(남3=남복·여3=여복).
    그 외: 4명 성별로 종목 자동."""
    if coach is None or len(three) < 3:
        return None
    if mode == Mode.SINGLES_GENDER:
        m3 = sum(1 for p in three if p.gender == MALE)
        f3 = sum(1 for p in three if p.gender == FEMALE)
        disc = Discipline.MENS if m3 == 3 else Discipline.WOMENS if f3 == 3 else Discipline.MIXED
    elif mode == Mode.MIXED_ONLY:
        # 모드가 혼복만이면 코치 코트도 혼복이어야 한다(4명 전원 남자면 남복이 되던 문제).
        # pick_ace_three가 2남2여를 보장하지만, 직접 호출 등으로 깨진 조합이 오면 코트를 비운다.
        if not _discipline_feasible([coach] + list(three), Discipline.MIXED):
            return None
        disc = Discipline.MIXED
    else:
        four = [coach] + list(three)
        males = sum(1 for p in four if p.gender == MALE)
        females = sum(1 for p in four if p.gender == FEMALE)
        if males == 4:
            disc = Discipline.MENS
        elif females == 4:
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
