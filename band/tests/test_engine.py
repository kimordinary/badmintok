from django.test import SimpleTestCase
from band.matchmaking.engine import (
    recommend_next_game, recommend_with_pairs, pick_ace_three, build_ace_match)
from band.matchmaking.types import (
    Player, Discipline, Mode, Preset, PairStats, GamePlan,
    NeedOperatorChoice, PairUnit, MALE, FEMALE,
)


def P(pid, gender=MALE, level=3, games=0, last=None):
    g = {"games_mens": games} if gender == MALE else {"games_womens": games}
    return Player(id=pid, name=f"p{pid}", gender=gender, base_level=level, last_game_ended_at=last, **g)


class EngineTest(SimpleTestCase):
    def test_returns_none_when_fewer_than_four(self):
        result = recommend_next_game([P(1), P(2), P(3)], Mode.ALL,
                                     Preset.BALANCED, PairStats())
        self.assertIsNone(result)

    def test_mixed_only_picks_mixed(self):
        pool = [P(1, MALE, 4), P(2, MALE, 4), P(3, FEMALE, 4), P(4, FEMALE, 4)]
        result = recommend_next_game(pool, Mode.MIXED_ONLY, Preset.BALANCED, PairStats())
        self.assertIsInstance(result, GamePlan)
        self.assertEqual(result.discipline, Discipline.MIXED)

    def test_mixed_only_no_female_requests_operator_choice(self):
        pool = [P(1, MALE), P(2, MALE), P(3, MALE), P(4, MALE)]
        result = recommend_next_game(pool, Mode.MIXED_ONLY, Preset.BALANCED, PairStats())
        self.assertIsInstance(result, NeedOperatorChoice)
        self.assertIn(Discipline.MENS, result.options)

    def test_singles_gender_picks_same_gender_four(self):
        # 남자가 더 오래 쉼(앞순위) → 남복
        pool = [P(1, MALE, games=0), P(2, MALE, games=0), P(3, MALE, games=0),
                P(4, MALE, games=0), P(5, FEMALE, games=5), P(6, FEMALE, games=5)]
        result = recommend_next_game(pool, Mode.SINGLES_GENDER, Preset.BALANCED, PairStats())
        self.assertIsInstance(result, GamePlan)
        self.assertEqual(result.discipline, Discipline.MENS)

    def test_prefers_less_played_players(self):
        # 1~4는 0경기, 5~8은 5경기. 균형 동일하면 덜 뛴 1~4가 뽑혀야.
        pool = [P(i, MALE, 4, games=0) for i in range(1, 5)] + \
               [P(i, MALE, 4, games=5) for i in range(5, 9)]
        result = recommend_next_game(pool, Mode.ALL, Preset.BALANCED, PairStats())
        chosen = set(result.team1) | set(result.team2)
        self.assertEqual(chosen, {1, 2, 3, 4})


class PairEngineTest(SimpleTestCase):
    def test_no_pairs_falls_back_to_normal(self):
        pool = [P(1, MALE, 4), P(2, MALE, 4), P(3, FEMALE, 4), P(4, FEMALE, 4)]
        result = recommend_with_pairs(pool, [], Mode.ALL, Preset.BALANCED, PairStats())
        self.assertIsInstance(result, GamePlan)

    def test_pair_stays_on_same_team(self):
        # 여여 쌍(3,4) + 남자 4명 → 여복으로 3·4가 같은 팀
        pool = [P(1, MALE, 4), P(2, MALE, 4), P(5, FEMALE, 4), P(6, FEMALE, 4),
                P(3, FEMALE, 4), P(4, FEMALE, 4)]
        pairs = [PairUnit(a=3, b=4, strict=False)]
        result = recommend_with_pairs(pool, pairs, Mode.ALL, Preset.BALANCED, PairStats())
        self.assertIsInstance(result, GamePlan)
        self.assertEqual(result.discipline, Discipline.WOMENS)
        team_with_3 = result.team1 if 3 in result.team1 else result.team2
        self.assertIn(4, team_with_3)  # 3과 4는 항상 같은 팀

    def test_strict_pair_waits_when_discipline_disallowed(self):
        # strict 남남 쌍인데 mixed_only → 쌍은 대기, 나머지로 혼복 구성
        pool = [P(1, MALE, 4), P(2, MALE, 4),  # strict 쌍
                P(3, MALE, 4), P(4, FEMALE, 4), P(5, MALE, 4), P(6, FEMALE, 4)]
        pairs = [PairUnit(a=1, b=2, strict=True)]
        result = recommend_with_pairs(pool, pairs, Mode.MIXED_ONLY, Preset.BALANCED, PairStats())
        self.assertIsInstance(result, GamePlan)
        chosen = set(result.team1) | set(result.team2)
        self.assertNotIn(1, chosen)  # strict 쌍원은 혼복에서 제외
        self.assertNotIn(2, chosen)

    def test_best_effort_pair_can_play_separately(self):
        # best-effort 남남 쌍, mixed_only → 같이는 못 들어가도 각자 일반 큐 참여 가능
        pool = [P(1, MALE, 4), P(2, MALE, 4),
                P(3, FEMALE, 4), P(4, FEMALE, 4)]
        pairs = [PairUnit(a=1, b=2, strict=False)]
        result = recommend_with_pairs(pool, pairs, Mode.MIXED_ONLY, Preset.BALANCED, PairStats())
        self.assertIsInstance(result, GamePlan)
        chosen = set(result.team1) | set(result.team2)
        self.assertEqual(chosen, {1, 2, 3, 4})  # best-effort라 각자 들어감


class CoachEngineTest(SimpleTestCase):
    def test_pick_ace_three_prioritizes_unmet(self):
        pool = [P(i, MALE, 4, games=0) for i in range(1, 6)]
        # 1,2는 이미 코치 만남(met=1), 3,4,5는 못 만남(met=0) → 3,4,5 우선
        met = {1: 1, 2: 1, 3: 0, 4: 0, 5: 0}
        three = pick_ace_three(pool, met)
        self.assertEqual({p.id for p in three}, {3, 4, 5})

    def test_build_ace_match_keeps_coach_team_mixed(self):
        coach = P(99, MALE, 7)
        three = [P(1, FEMALE, 2), P(2, MALE, 4), P(3, MALE, 4)]
        plan = build_ace_match(coach, three)
        self.assertEqual(plan.discipline, Discipline.MIXED)
        # 코치(남)는 약체 여성과 한 팀 → team1에 99와 1
        coach_team = plan.team1 if 99 in plan.team1 else plan.team2
        self.assertIn(1, coach_team)

    def test_build_ace_match_all_male_is_mens(self):
        coach = P(99, MALE, 7)
        three = [P(1, MALE, 2), P(2, MALE, 4), P(3, MALE, 4)]
        plan = build_ace_match(coach, three)
        self.assertEqual(plan.discipline, Discipline.MENS)
        # 코치는 가장 약한 1과 한 팀
        coach_team = plan.team1 if 99 in plan.team1 else plan.team2
        self.assertIn(1, coach_team)

    def test_build_ace_match_needs_three(self):
        self.assertIsNone(build_ace_match(P(99), [P(1), P(2)]))
