from django.test import SimpleTestCase
from band.matchmaking.selection import queue_order
from band.matchmaking.types import Player, MALE


def P(pid, games=0, last=None):
    return Player(id=pid, name=f"p{pid}", gender=MALE, base_level=3,
                  games_mens=games, last_game_ended_at=last)


class QueueOrderTest(SimpleTestCase):
    def test_fewer_games_first(self):
        order = queue_order([P(1, games=3), P(2, games=1), P(3, games=2)])
        self.assertEqual([p.id for p in order], [2, 3, 1])

    def test_tie_breaks_by_longer_rest(self):
        # 같은 1경기. p10은 100초에 끝남(최근), p11은 50초(오래 쉼) → p11 먼저
        order = queue_order([P(10, games=1, last=100.0), P(11, games=1, last=50.0)])
        self.assertEqual([p.id for p in order], [11, 10])

    def test_never_played_comes_before_rested(self):
        # 둘 다 0경기지만 last=None(아예 안 뜀)이 last=10보다 앞
        order = queue_order([P(20, games=0, last=10.0), P(21, games=0, last=None)])
        self.assertEqual([p.id for p in order], [21, 20])
