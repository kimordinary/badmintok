from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class Discipline(str, Enum):
    MIXED = "mixed"     # 혼복
    MENS = "mens"       # 남복
    WOMENS = "womens"   # 여복


class Mode(str, Enum):
    MIXED_ONLY = "mixed_only"          # 혼복만
    SINGLES_GENDER = "singles_gender"  # 남복·여복만
    ALL = "all"                        # 전부 섞기


class Preset(str, Enum):
    BALANCED = "balanced"        # 균형파(기본)
    COMPETITIVE = "competitive"  # 박빙파


@dataclass(frozen=True)
class Weights:
    balance: float
    partner: float
    opponent: float
    fairness: float


PRESETS = {
    Preset.BALANCED: Weights(balance=3, partner=2, opponent=1, fairness=1),
    Preset.COMPETITIVE: Weights(balance=5, partner=1, opponent=0.5, fairness=1),
}

MALE = "male"
FEMALE = "female"


@dataclass
class Player:
    id: int
    name: str
    gender: str          # MALE | FEMALE
    base_level: int      # 1..7 (초심1 .. 자강7)
    games_mixed: int = 0
    games_mens: int = 0
    games_womens: int = 0
    last_game_ended_at: float | None = None  # epoch seconds. None = 아직 한 번도 안 뜀

    @property
    def total_games(self) -> int:
        return self.games_mixed + self.games_mens + self.games_womens


@dataclass(frozen=True)
class GamePlan:
    discipline: Discipline
    team1: tuple[int, int]  # player id 2명
    team2: tuple[int, int]


@dataclass(frozen=True)
class PairUnit:
    """고정 2인 팀. a·b는 participant id. strict=같이만(False=따로도 OK)."""
    a: int
    b: int
    strict: bool = False


@dataclass(frozen=True)
class NeedOperatorChoice:
    """현재 모드로 경기를 못 짤 때. 운영자에게 대안 종목 선택을 요청."""
    reason: str
    options: tuple[Discipline, ...]  # 대신 가능한 종목들


class PairStats:
    """파트너/상대 누적 횟수 조회. 코어는 이 인터페이스만 의존."""
    def __init__(self, partner=None, opponent=None):
        self._partner = partner or {}
        self._opponent = opponent or {}

    @staticmethod
    def _key(a: int, b: int) -> tuple[int, int]:
        return (a, b) if a < b else (b, a)

    def partner_count(self, a: int, b: int) -> int:
        return self._partner.get(self._key(a, b), 0)

    def opponent_count(self, a: int, b: int) -> int:
        return self._opponent.get(self._key(a, b), 0)

    def partners_of(self, pid: int) -> dict:
        """pid와 함께 뛴 파트너별 횟수 {상대 participant_id: count} (0회 제외)."""
        out = {}
        for (a, b), c in self._partner.items():
            if not c:
                continue
            if a == pid:
                out[b] = c
            elif b == pid:
                out[a] = c
        return out

    def opponents_of(self, pid: int) -> dict:
        """pid와 맞붙은 상대별 횟수 {상대 participant_id: count} (0회 제외)."""
        out = {}
        for (a, b), c in self._opponent.items():
            if not c:
                continue
            if a == pid:
                out[b] = c
            elif b == pid:
                out[a] = c
        return out
