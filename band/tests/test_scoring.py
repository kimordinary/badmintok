from django.test import SimpleTestCase
from band.matchmaking.scoring import level_to_score, effective_score
from band.matchmaking.types import Player, Discipline, MALE, FEMALE


class LevelToScoreTest(SimpleTestCase):
    def test_levels_map_1_to_7(self):
        self.assertEqual(level_to_score("master"), 7)
        self.assertEqual(level_to_score("s"), 6)
        self.assertEqual(level_to_score("a"), 5)
        self.assertEqual(level_to_score("b"), 4)
        self.assertEqual(level_to_score("c"), 3)
        self.assertEqual(level_to_score("d"), 2)
        self.assertEqual(level_to_score("beginner"), 1)

    def test_unknown_defaults_to_beginner(self):
        self.assertEqual(level_to_score(""), 1)
        self.assertEqual(level_to_score("xyz"), 1)


class EffectiveScoreTest(SimpleTestCase):
    def _p(self, gender, level):
        return Player(id=1, name="t", gender=gender, base_level=level)

    def test_mens_womens_no_adjust(self):
        p = self._p(FEMALE, 4)
        self.assertEqual(effective_score(p, Discipline.WOMENS), 4)
        self.assertEqual(effective_score(self._p(MALE, 4), Discipline.MENS), 4)

    def test_mixed_female_minus_adjust(self):
        p = self._p(FEMALE, 4)
        self.assertEqual(effective_score(p, Discipline.MIXED, female_adjust=1), 3)

    def test_mixed_male_no_adjust(self):
        self.assertEqual(effective_score(self._p(MALE, 4), Discipline.MIXED), 4)

    def test_mixed_female_clamped_at_1(self):
        self.assertEqual(effective_score(self._p(FEMALE, 1), Discipline.MIXED, female_adjust=1), 1)
