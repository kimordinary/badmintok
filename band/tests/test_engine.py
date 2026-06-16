from django.test import SimpleTestCase
from band.matchmaking.engine import recommend_next_game
from band.matchmaking.types import (
    Player, Discipline, Mode, Preset, PairStats, GamePlan,
    NeedOperatorChoice, MALE, FEMALE,
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
