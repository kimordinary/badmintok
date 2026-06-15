from django.test import SimpleTestCase
from band.matchmaking.cost import best_split, game_cost
from band.matchmaking.types import (
    Player, Discipline, Preset, PRESETS, PairStats, MALE, FEMALE,
)


def P(pid, gender=MALE, level=3):
    return Player(id=pid, name=f"p{pid}", gender=gender, base_level=level)


class BestSplitTest(SimpleTestCase):
    def test_mens_balances_strong_with_weak(self):
        # 급수 7,1,4,4 → 균형 분할은 (7+1) vs (4+4) = 8:8
        players = [P(1, level=7), P(2, level=1), P(3, level=4), P(4, level=4)]
        split = best_split(players, Discipline.MENS,
                           PRESETS[Preset.BALANCED], PairStats(), female_adjust=1)
        sums = {
            tuple(sorted(split.team1)): None,
            tuple(sorted(split.team2)): None,
        }
        # 팀 합이 8:8 이 되는 쌍: {1,2} 와 {3,4}
        self.assertIn((1, 2), sums)
        self.assertIn((3, 4), sums)

    def test_mixed_normal_each_team_one_each_gender(self):
        players = [P(1, MALE, 4), P(2, MALE, 4), P(3, FEMALE, 4), P(4, FEMALE, 4)]
        split = best_split(players, Discipline.MIXED,
                           PRESETS[Preset.BALANCED], PairStats(), female_adjust=1)
        # 각 팀에 남1 여1
        genders = {p.id: p.gender for p in players}
        for team in (split.team1, split.team2):
            g = sorted(genders[pid] for pid in team)
            self.assertEqual(g, [FEMALE, MALE])

    def test_mixed_allows_same_gender_team_when_skewed(self):
        # 남3 여1 → best_split 이 None 이 아니라 동성팀 1개를 허용
        players = [P(1, MALE, 4), P(2, MALE, 4), P(3, MALE, 4), P(4, FEMALE, 4)]
        split = best_split(players, Discipline.MIXED,
                           PRESETS[Preset.BALANCED], PairStats(), female_adjust=1)
        self.assertIsNotNone(split)

    def test_mixed_impossible_when_no_female(self):
        players = [P(1, MALE), P(2, MALE), P(3, MALE), P(4, MALE)]
        split = best_split(players, Discipline.MIXED,
                           PRESETS[Preset.BALANCED], PairStats(), female_adjust=1)
        self.assertIsNone(split)


class GameCostTest(SimpleTestCase):
    def test_partner_repeat_adds_penalty(self):
        players = [P(1, level=4), P(2, level=4), P(3, level=4), P(4, level=4)]
        # 1·2 팀 / 3·4 팀, 1과 2가 이미 2번 파트너였음
        stats = PairStats(partner={(1, 2): 2})
        plan_team1 = (1, 2)
        plan_team2 = (3, 4)
        c = game_cost(players, plan_team1, plan_team2, Discipline.MENS,
                      PRESETS[Preset.BALANCED], stats, female_adjust=1)
        # 점수합 동일(8:8) → balance=0, partner=2*2=4
        self.assertEqual(c, 4.0)
