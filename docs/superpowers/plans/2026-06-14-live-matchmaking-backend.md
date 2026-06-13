# 번개 실시간 자동 대진 — 백엔드 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 번개(BandSchedule) 참가자 리스트로, 코트가 빌 때마다 다음 경기를 자동 추천하는 흐름형 대진 시스템의 백엔드(매칭 코어 + 영속 모델 + REST API)를 구현한다.

**Architecture:** 매칭 규칙은 Django와 무관한 **순수 파이썬 패키지**(`band/matchmaking/`)로 구현하고 단위 테스트로 검증한다. 그 위에 영속 모델(`band/match_models.py`)과 DRF 함수형 뷰(`band/api/match_views.py`)를 얹는다. 코어는 "상태 dict → 다음 경기 추천"만 책임지고, DB·HTTP는 어댑터가 변환한다.

**Tech Stack:** Python 3, Django 5.2.8, Django REST Framework 3.16(함수형 `@api_view`), simplejwt, Django TestCase(`python manage.py test`).

**참고 스펙:** [docs/superpowers/specs/2026-06-14-live-matchmaking-design.md](../specs/2026-06-14-live-matchmaking-design.md)

---

## 설계 결정 요약 (스펙에서)

- **흐름형(rolling)**: 고정 라운드표 아님. 코트가 비면 그 코트만 다음 4명 추천.
- **종목 모드**(세션 중 토글): `혼복만`/`남복·여복만`/`전부 섞기`.
- **성향 프리셋**(토글): `균형파`(기본)/`박빙파`.
- **대기열 정렬**: 경기수 적은 순 → 동률이면 쉰 시간 긴 순.
- **우선순위**: 코트 안 놀리기 > 균등 출전 > 모드 준수 > 균형·다양성.
- **혼복 불가 시**: 자동 변경 X → 운영자에게 선택 요청(`NeedOperatorChoice`).
- **출석 상태**(양방향 토글): 미출석/참여중/퇴장. 참여중만 대진 풀.
- **급수 점수**: 자강7·S6·A5·B4·C3·D2·왕초심1. 혼복 여자 = `max(1, base - femaleAdjust)`, femaleAdjust 기본 1.
- **자동 확정 + 편집 가능**: 추천은 즉시 확정, 운영자가 swap/종목 변경 가능.
- **규모**: 최대 50명/8코트. 후보 윈도우(대기열 앞쪽 일부)로 제한해 조합 폭발 방지.

---

## 파일 구조

**신규 — 매칭 코어(순수 파이썬, Django 무관):**
- `band/matchmaking/__init__.py` — 공개 API re-export
- `band/matchmaking/types.py` — Enum/dataclass(`Discipline`, `Mode`, `Preset`, `Weights`, `Player`, `GamePlan`, `NeedOperatorChoice`, `PairStats`)
- `band/matchmaking/scoring.py` — 급수→점수, 유효 점수
- `band/matchmaking/selection.py` — 대기열 정렬
- `band/matchmaking/cost.py` — 팀 분할, 비용 함수
- `band/matchmaking/engine.py` — `recommend_next_game()` 오케스트레이터

**신규 — 영속/어댑터/API:**
- `band/match_models.py` — `MatchSession`, `SessionParticipant`, `Court`, `Match`, `MatchPlayer`
- `band/match_state.py` — DB ↔ 코어 상태 어댑터(`build_pool()`, `build_pairstats()`)
- `band/api/match_views.py` — DRF 엔드포인트
- `band/api/match_serializers.py` — 응답 직렬화

**신규 — 테스트(패키지로):**
- `band/tests/__init__.py`
- `band/tests/test_scoring.py`, `test_selection.py`, `test_cost.py`, `test_engine.py`
- `band/tests/test_match_api.py`

**수정:**
- `band/models.py` — 맨 끝에 `from band.match_models import *  # noqa` 추가(모델 등록)
- `band/api/urls.py` — 매칭 엔드포인트 라우트 추가

---

## Phase 1 — 매칭 코어 (순수 파이썬, TDD)

### Task 1: 타입 정의 (`types.py`)

순수 데이터 구조. 다른 모든 코어 모듈이 의존한다.

**Files:**
- Create: `band/matchmaking/__init__.py`
- Create: `band/matchmaking/types.py`
- Create: `band/tests/__init__.py`
- Test: `band/tests/test_scoring.py`(다음 태스크에서 사용, 지금은 import 확인만)

- [ ] **Step 1: 코어 패키지 디렉터리와 빈 `__init__.py` 생성**

`band/matchmaking/__init__.py` 내용:

```python
from band.matchmaking.types import (
    Discipline, Mode, Preset, Weights, PRESETS,
    Player, GamePlan, NeedOperatorChoice, PairStats,
)
from band.matchmaking.scoring import level_to_score, effective_score
from band.matchmaking.selection import queue_order
from band.matchmaking.cost import best_split, game_cost
from band.matchmaking.engine import recommend_next_game

__all__ = [
    "Discipline", "Mode", "Preset", "Weights", "PRESETS",
    "Player", "GamePlan", "NeedOperatorChoice", "PairStats",
    "level_to_score", "effective_score", "queue_order",
    "best_split", "game_cost", "recommend_next_game",
]
```

`band/tests/__init__.py`: 빈 파일.

- [ ] **Step 2: `types.py` 작성**

```python
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
    base_level: int      # 1..7 (왕초심1 .. 자강7)
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
```

- [ ] **Step 3: import 동작 확인**

`band/matchmaking/scoring.py`, `selection.py`, `cost.py`, `engine.py`는 아직 없어 `__init__.py` import가 깨진다. **각 모듈을 빈 스텁으로 먼저 생성**(`pass` 한 줄)해 import만 통과시킨다. 실제 구현은 각 태스크에서.

Run: `python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','badmintok.settings'); django.setup(); from band.matchmaking.types import Player, PRESETS, Preset; print(PRESETS[Preset.BALANCED])"`
Expected: `Weights(balance=3, partner=2, opponent=1, fairness=1)`

- [ ] **Step 4: 커밋**

```bash
git add band/matchmaking/ band/tests/__init__.py
git commit -m "feat(match): 매칭 코어 타입 정의"
```

---

### Task 2: 점수 환산 (`scoring.py`)

**Files:**
- Modify: `band/matchmaking/scoring.py`
- Test: `band/tests/test_scoring.py`

- [ ] **Step 1: 실패 테스트 작성** — `band/tests/test_scoring.py`

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python manage.py test band.tests.test_scoring -v 2`
Expected: FAIL (`ImportError` 또는 `AttributeError: ... level_to_score`)

- [ ] **Step 3: 구현** — `band/matchmaking/scoring.py`

```python
from band.matchmaking.types import Player, Discipline, FEMALE

LEVEL_SCORE = {
    "master": 7, "s": 6, "a": 5, "b": 4, "c": 3, "d": 2, "beginner": 1,
}


def level_to_score(level: str) -> int:
    return LEVEL_SCORE.get((level or "").lower(), 1)


def effective_score(player: Player, discipline: Discipline, female_adjust: int = 1) -> int:
    base = player.base_level
    if discipline == Discipline.MIXED and player.gender == FEMALE:
        return max(1, base - female_adjust)
    return base
```

- [ ] **Step 4: 통과 확인**

Run: `python manage.py test band.tests.test_scoring -v 2`
Expected: PASS (8 tests)

- [ ] **Step 5: 커밋**

```bash
git add band/matchmaking/scoring.py band/tests/test_scoring.py
git commit -m "feat(match): 급수 점수·유효 점수 환산"
```

---

### Task 3: 대기열 정렬 (`selection.py`)

정렬 규칙: **경기수 적은 순 → 동률이면 쉰 시간 긴 순**. 쉰 시간이 길다 = `last_game_ended_at`이 더 과거(작은 값). 아직 안 뛴 사람(`None`)은 "무한히 오래 쉼" → 가장 앞.

**Files:**
- Modify: `band/matchmaking/selection.py`
- Test: `band/tests/test_selection.py`

- [ ] **Step 1: 실패 테스트 작성** — `band/tests/test_selection.py`

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python manage.py test band.tests.test_selection -v 2`
Expected: FAIL

- [ ] **Step 3: 구현** — `band/matchmaking/selection.py`

```python
from band.matchmaking.types import Player

NEVER_PLAYED = float("-inf")  # 동률 시 가장 앞으로


def queue_order(players: list[Player]) -> list[Player]:
    def key(p: Player):
        rested_marker = p.last_game_ended_at if p.last_game_ended_at is not None else NEVER_PLAYED
        return (p.total_games, rested_marker)
    return sorted(players, key=key)
```

- [ ] **Step 4: 통과 확인**

Run: `python manage.py test band.tests.test_selection -v 2`
Expected: PASS (3 tests)

- [ ] **Step 5: 커밋**

```bash
git add band/matchmaking/selection.py band/tests/test_selection.py
git commit -m "feat(match): 대기열 우선순위 정렬"
```

---

### Task 4: 팀 분할 + 비용 함수 (`cost.py`)

주어진 4명과 종목에 대해, 가능한 팀 분할(2:2) 중 비용이 최소인 것을 고른다.
- 혼복: 각 팀이 남1·여1이어야 정상. 성비가 안 맞으면(남3여1 등) **동성 페어 1팀 허용**.
- 비용 = `w_balance·(팀점수합차)² + w_partner·파트너중복 + w_opponent·상대중복`.
  (fairness는 후보 선택 단계(engine)에서 가산하므로 여기선 제외.)

**Files:**
- Modify: `band/matchmaking/cost.py`
- Test: `band/tests/test_cost.py`

- [ ] **Step 1: 실패 테스트 작성** — `band/tests/test_cost.py`

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python manage.py test band.tests.test_cost -v 2`
Expected: FAIL

- [ ] **Step 3: 구현** — `band/matchmaking/cost.py`

```python
from itertools import combinations
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
        # 남남 vs 여여 → 혼복 아님
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
    """4명 + 종목 → 비용 최소 팀 분할. 불가하면 None."""
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
```

- [ ] **Step 4: 통과 확인**

Run: `python manage.py test band.tests.test_cost -v 2`
Expected: PASS (5 tests)

- [ ] **Step 5: 커밋**

```bash
git add band/matchmaking/cost.py band/tests/test_cost.py
git commit -m "feat(match): 팀 분할 + 비용 함수"
```

---

### Task 5: 추천 엔진 (`engine.py`)

코어의 입구. 대기열에서 후보 윈도우(앞 `window`명)를 뽑고, 4명 조합 × 가능한 종목을 열거해 **(비용 + fairness 가산)** 최소를 고른다. 모드별로 후보 종목을 제한한다.

- 후보 4명 조합: `C(window, 4)` (window=8 → 70개, 사소).
- fairness 가산 = `w_fairness × Σ(4명의 total_games)` → 덜 뛴 사람 조합을 선호.
- `MIXED_ONLY`인데 어떤 조합으로도 혼복이 안 되면(여자/남자 전무) → `NeedOperatorChoice`.

**Files:**
- Modify: `band/matchmaking/engine.py`
- Test: `band/tests/test_engine.py`

- [ ] **Step 1: 실패 테스트 작성** — `band/tests/test_engine.py`

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python manage.py test band.tests.test_engine -v 2`
Expected: FAIL

- [ ] **Step 3: 구현** — `band/matchmaking/engine.py`

```python
from itertools import combinations
from band.matchmaking.types import (
    Player, Discipline, Mode, Preset, PRESETS, GamePlan,
    NeedOperatorChoice, PairStats, MALE, FEMALE,
)
from band.matchmaking.selection import queue_order
from band.matchmaking.cost import best_split


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
            from band.matchmaking.cost import game_cost
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
    # (윈도우가 아니라 전체 pool 기준으로 가능한 종목을 후보로)
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
```

- [ ] **Step 4: 통과 확인**

Run: `python manage.py test band.tests.test_engine -v 2`
Expected: PASS (5 tests)

- [ ] **Step 5: 전체 코어 테스트 + 커밋**

Run: `python manage.py test band.tests.test_scoring band.tests.test_selection band.tests.test_cost band.tests.test_engine -v 2`
Expected: PASS (전체)

```bash
git add band/matchmaking/engine.py band/tests/test_engine.py band/matchmaking/__init__.py
git commit -m "feat(match): 다음 경기 추천 엔진"
```

---

## Phase 2 — 영속 모델 + 상태 어댑터

### Task 6: 영속 모델 (`match_models.py`)

**Files:**
- Create: `band/match_models.py`
- Modify: `band/models.py` (끝에 import 추가)
- Create: migration (자동 생성)
- Test: `band/tests/test_match_models.py`

- [ ] **Step 1: 모델 작성** — `band/match_models.py`

```python
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from band.models import BandSchedule


class MatchSession(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", _("진행중")
        ENDED = "ended", _("종료")

    class DisciplineMode(models.TextChoices):
        MIXED_ONLY = "mixed_only", _("혼복만")
        SINGLES_GENDER = "singles_gender", _("남복·여복만")
        ALL = "all", _("전부 섞기")

    class Preset(models.TextChoices):
        BALANCED = "balanced", _("균형파")
        COMPETITIVE = "competitive", _("박빙파")

    schedule = models.OneToOneField(
        BandSchedule, on_delete=models.CASCADE,
        related_name="match_session", verbose_name=_("번개 일정"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    discipline_mode = models.CharField(
        max_length=20, choices=DisciplineMode.choices, default=DisciplineMode.ALL)
    preset = models.CharField(max_length=12, choices=Preset.choices, default=Preset.BALANCED)
    female_adjust = models.IntegerField(default=1)
    court_count = models.IntegerField(default=4)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="match_sessions")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("대진 세션")
        verbose_name_plural = _("대진 세션")


class SessionParticipant(models.Model):
    class Attendance(models.TextChoices):
        NOT_PRESENT = "not_present", _("미출석")
        PRESENT = "present", _("참여중")
        LEFT = "left", _("퇴장")

    session = models.ForeignKey(
        MatchSession, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    attendance = models.CharField(
        max_length=12, choices=Attendance.choices, default=Attendance.NOT_PRESENT)
    # 세션 시작 시점 스냅샷 (가입 정보가 바뀌어도 세션 내 일관)
    base_level = models.IntegerField()  # 1..7
    gender = models.CharField(max_length=10)  # male | female
    games_mixed = models.IntegerField(default=0)
    games_mens = models.IntegerField(default=0)
    games_womens = models.IntegerField(default=0)
    last_game_ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [["session", "user"]]
        verbose_name = _("대진 참가자")
        verbose_name_plural = _("대진 참가자")


class Court(models.Model):
    session = models.ForeignKey(MatchSession, on_delete=models.CASCADE, related_name="courts")
    index = models.IntegerField()  # 1..court_count

    class Meta:
        unique_together = [["session", "index"]]
        ordering = ["index"]


class Match(models.Model):
    class Status(models.TextChoices):
        PLAYING = "playing", _("진행중")
        DONE = "done", _("종료")

    class Discipline(models.TextChoices):
        MIXED = "mixed", _("혼복")
        MENS = "mens", _("남복")
        WOMENS = "womens", _("여복")

    session = models.ForeignKey(MatchSession, on_delete=models.CASCADE, related_name="matches")
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name="matches")
    discipline = models.CharField(max_length=10, choices=Discipline.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PLAYING)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("경기")
        verbose_name_plural = _("경기")


class MatchPlayer(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="players")
    participant = models.ForeignKey(SessionParticipant, on_delete=models.CASCADE)
    team = models.IntegerField()  # 1 | 2

    class Meta:
        unique_together = [["match", "participant"]]
```

- [ ] **Step 2: `band/models.py` 끝에 import 추가** (모델 등록)

`band/models.py` 파일 맨 마지막 줄에 추가:

```python
from band.match_models import (  # noqa: E402,F401
    MatchSession, SessionParticipant, Court, Match, MatchPlayer,
)
```

- [ ] **Step 3: 마이그레이션 생성·적용**

Run: `python manage.py makemigrations band && python manage.py migrate`
Expected: 새 마이그레이션 생성, 5개 테이블 추가, 에러 없음.

- [ ] **Step 4: 등록 확인 테스트** — `band/tests/test_match_models.py`

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from band.models import Band, BandSchedule, MatchSession, SessionParticipant
from django.utils import timezone

User = get_user_model()


class MatchModelsTest(TestCase):
    def test_create_session_and_participant(self):
        u = User.objects.create_user(email="a@a.com", password="x", activity_name="A")
        band = Band.objects.create(name="b", created_by=u)
        sch = BandSchedule.objects.create(
            band=band, title="t", start_datetime=timezone.now(), created_by=u)
        session = MatchSession.objects.create(schedule=sch, court_count=4, created_by=u)
        sp = SessionParticipant.objects.create(
            session=session, user=u, base_level=4, gender="male")
        self.assertEqual(session.participants.count(), 1)
        self.assertEqual(sp.attendance, "not_present")
```

> 주의: `Band`에는 `category` 필드가 없다(있는 건 `band_type` 기본 GROUP, `categories` 콤마 문자열, `region` 기본 ALL). 테스트는 `Band.objects.create(name="b", created_by=u)`로 최소 생성한다(나머지는 기본값). `BandSchedule`은 `band/title/start_datetime/created_by`가 필수.

- [ ] **Step 5: 테스트 통과 + 커밋**

Run: `python manage.py test band.tests.test_match_models -v 2`
Expected: PASS

```bash
git add band/match_models.py band/models.py band/migrations/ band/tests/test_match_models.py
git commit -m "feat(match): 대진 세션/참가자/코트/경기 모델"
```

---

### Task 7: DB ↔ 코어 상태 어댑터 (`match_state.py`)

DB 행을 코어 `Player` 리스트와 `PairStats`로 변환. 코어는 epoch seconds를 쓰므로 `last_game_ended_at`을 timestamp로 변환.

**Files:**
- Create: `band/match_state.py`
- Test: `band/tests/test_match_state.py`

- [ ] **Step 1: 실패 테스트 작성** — `band/tests/test_match_state.py`

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from band.models import Band, BandSchedule, MatchSession, SessionParticipant
from band.match_state import build_pool, build_pairstats

User = get_user_model()


class MatchStateTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(email="a@a.com", password="x", activity_name="A")
        band = Band.objects.create(name="b", created_by=self.u)
        sch = BandSchedule.objects.create(
            band=band, title="t", start_datetime=timezone.now(), created_by=self.u)
        self.session = MatchSession.objects.create(schedule=sch, court_count=2, created_by=self.u)

    def test_build_pool_only_present(self):
        SessionParticipant.objects.create(
            session=self.session, user=self.u, base_level=4, gender="male",
            attendance="present")
        u2 = User.objects.create_user(email="b@b.com", password="x", activity_name="B")
        SessionParticipant.objects.create(
            session=self.session, user=u2, base_level=3, gender="female",
            attendance="not_present")
        pool = build_pool(self.session)
        self.assertEqual([p.gender for p in pool], ["male"])  # present 만

    def test_pool_excludes_players_currently_on_court(self):
        # on_court_participant_ids 로 제외
        sp = SessionParticipant.objects.create(
            session=self.session, user=self.u, base_level=4, gender="male",
            attendance="present")
        pool = build_pool(self.session, on_court_participant_ids={sp.id})
        self.assertEqual(pool, [])
```

- [ ] **Step 2: 실패 확인**

Run: `python manage.py test band.tests.test_match_state -v 2`
Expected: FAIL

- [ ] **Step 3: 구현** — `band/match_state.py`

```python
from band.matchmaking.types import Player, PairStats
from band.match_models import SessionParticipant, MatchPlayer, Match


def build_pool(session, on_court_participant_ids=None) -> list[Player]:
    on_court = on_court_participant_ids or set()
    pool = []
    qs = session.participants.filter(
        attendance=SessionParticipant.Attendance.PRESENT
    ).exclude(id__in=on_court)
    for sp in qs:
        pool.append(Player(
            id=sp.id,
            name=sp.user.activity_name,
            gender=sp.gender,
            base_level=sp.base_level,
            games_mixed=sp.games_mixed,
            games_mens=sp.games_mens,
            games_womens=sp.games_womens,
            last_game_ended_at=(sp.last_game_ended_at.timestamp()
                                if sp.last_game_ended_at else None),
        ))
    return pool


def build_pairstats(session) -> PairStats:
    """완료된 경기 이력에서 파트너/상대 누적 횟수 집계."""
    partner = {}
    opponent = {}
    matches = Match.objects.filter(session=session).prefetch_related("players")
    for m in matches:
        team = {1: [], 2: []}
        for mp in m.players.all():
            team[mp.team].append(mp.participant_id)
        for t in (1, 2):
            for a, b in _pairs(team[t]):
                k = (a, b) if a < b else (b, a)
                partner[k] = partner.get(k, 0) + 1
        for a in team[1]:
            for b in team[2]:
                k = (a, b) if a < b else (b, a)
                opponent[k] = opponent.get(k, 0) + 1
    return PairStats(partner=partner, opponent=opponent)


def _pairs(ids):
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            yield ids[i], ids[j]
```

- [ ] **Step 4: 통과 확인**

Run: `python manage.py test band.tests.test_match_state -v 2`
Expected: PASS (2 tests)

- [ ] **Step 5: 커밋**

```bash
git add band/match_state.py band/tests/test_match_state.py
git commit -m "feat(match): DB↔코어 상태 어댑터"
```

---

## Phase 3 — REST API

권한: 해당 밴드의 `BandMember.role in (owner, admin)` 만 운영 가능. 헬퍼 `_require_operator(request, session)`로 통일.

### API 계약 (프런트엔드가 의존할 인터페이스)

| 메서드 | 경로 | 동작 |
|--------|------|------|
| POST | `/api/band/match/schedules/<schedule_id>/start/` | 세션 생성(승인 신청자 → 참가자), court_count·mode·preset 설정 |
| GET | `/api/band/match/<session_id>/` | 전체 상태(코트·진행경기·대기열 순서·개인 카운트) |
| POST | `/api/band/match/<session_id>/mode/` | `{discipline_mode}` 변경 |
| POST | `/api/band/match/<session_id>/preset/` | `{preset}` 변경 |
| POST | `/api/band/match/<session_id>/participants/<pid>/attendance/` | `{attendance}` 토글 |
| POST | `/api/band/match/<session_id>/courts/<index>/end/` | 진행 경기 종료(카운트 반영) → 다음 경기 자동 추천·생성. 불가 시 `needs_choice` 반환 |
| POST | `/api/band/match/<session_id>/courts/<index>/fill/` | 빈 코트 채우기(시작 시/운영자 선택 후). `{discipline?}` 강제 종목 옵션 |
| PATCH | `/api/band/match/<session_id>/matches/<match_id>/` | 편집: `{swap:[pid_a,pid_b]}` 또는 `{discipline}` |
| POST | `/api/band/match/<session_id>/end/` | 세션 종료 |

### Task 8: 세션 시작 + 상태 조회

**Files:**
- Create: `band/api/match_serializers.py`
- Create: `band/api/match_views.py`
- Modify: `band/api/urls.py`
- Test: `band/tests/test_match_api.py`

- [ ] **Step 1: 실패 테스트 작성** — `band/tests/test_match_api.py`

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from band.models import Band, BandMember, BandSchedule, BandScheduleApplication
from accounts.models import UserProfile

User = get_user_model()


class MatchApiSetup(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(email="o@o.com", password="x", activity_name="Owner")
        UserProfile.objects.update_or_create(
            user=self.owner, defaults={"badminton_level": "b", "gender": "male"})
        self.band = Band.objects.create(name="b", created_by=self.owner)
        BandMember.objects.create(band=self.band, user=self.owner, role="owner", status="active")
        self.schedule = BandSchedule.objects.create(
            band=self.band, title="t", start_datetime=timezone.now(), created_by=self.owner)
        self.client.force_authenticate(self.owner)

    def _approved_applicant(self, email, level, gender):
        u = User.objects.create_user(email=email, password="x", activity_name=email[:3])
        UserProfile.objects.update_or_create(
            user=u, defaults={"badminton_level": level, "gender": gender})
        BandScheduleApplication.objects.create(
            schedule=self.schedule, user=u, status="approved")
        return u


class StartSessionTest(MatchApiSetup):
    def test_start_creates_session_with_present_participants_snapshot(self):
        self._approved_applicant("m1@x.com", "a", "male")
        self._approved_applicant("f1@x.com", "c", "female")
        resp = self.client.post(
            f"/api/band/match/schedules/{self.schedule.id}/start/",
            {"court_count": 2, "discipline_mode": "all", "preset": "balanced"},
            format="json")
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(len(data["participants"]), 2)
        # 급수 a=5 점수로 스냅샷
        levels = sorted(p["base_level"] for p in data["participants"])
        self.assertEqual(levels, [3, 5])  # c=3, a=5

    def test_non_operator_forbidden(self):
        stranger = User.objects.create_user(email="s@s.com", password="x", activity_name="S")
        self.client.force_authenticate(stranger)
        resp = self.client.post(
            f"/api/band/match/schedules/{self.schedule.id}/start/",
            {"court_count": 2}, format="json")
        self.assertEqual(resp.status_code, 403)


class StateTest(MatchApiSetup):
    def test_get_state_returns_courts_and_queue(self):
        self._approved_applicant("m1@x.com", "a", "male")
        start = self.client.post(
            f"/api/band/match/schedules/{self.schedule.id}/start/",
            {"court_count": 2}, format="json").json()
        sid = start["id"]
        resp = self.client.get(f"/api/band/match/{sid}/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["courts"]), 2)
        self.assertIn("queue", body)
```

- [ ] **Step 2: 실패 확인**

Run: `python manage.py test band.tests.test_match_api -v 2`
Expected: FAIL (404 — 라우트 없음)

- [ ] **Step 3: 직렬화 헬퍼 작성** — `band/api/match_serializers.py`

```python
from band.match_models import SessionParticipant
from band.match_state import build_pool
from band.matchmaking.selection import queue_order


def serialize_participant(sp):
    return {
        "id": sp.id,
        "user_id": sp.user_id,
        "name": sp.user.activity_name,
        "gender": sp.gender,
        "base_level": sp.base_level,
        "attendance": sp.attendance,
        "games_mixed": sp.games_mixed,
        "games_mens": sp.games_mens,
        "games_womens": sp.games_womens,
        "total_games": sp.games_mixed + sp.games_mens + sp.games_womens,
    }


def serialize_match(match):
    teams = {1: [], 2: []}
    for mp in match.players.all():
        teams[mp.team].append({
            "participant_id": mp.participant_id,
            "name": mp.participant.user.activity_name,
            "base_level": mp.participant.base_level,
            "gender": mp.participant.gender,
        })
    return {
        "id": match.id,
        "discipline": match.discipline,
        "status": match.status,
        "team1": teams[1],
        "team2": teams[2],
    }


def serialize_session(session):
    participants = list(session.participants.select_related("user"))
    courts = []
    on_court_ids = set()
    for court in session.courts.all():
        current = court.matches.filter(status="playing").prefetch_related(
            "players__participant__user").first()
        if current:
            on_court_ids.update(mp.participant_id for mp in current.players.all())
        courts.append({
            "index": court.index,
            "match": serialize_match(current) if current else None,
        })
    pool = build_pool(session, on_court_participant_ids=on_court_ids)
    queue = [{"participant_id": p.id, "name": p.name, "total_games": p.total_games}
             for p in queue_order(pool)]
    return {
        "id": session.id,
        "status": session.status,
        "discipline_mode": session.discipline_mode,
        "preset": session.preset,
        "court_count": session.court_count,
        "participants": [serialize_participant(p) for p in participants],
        "courts": courts,
        "queue": queue,
    }
```

- [ ] **Step 4: 뷰 작성(시작 + 상태 + 권한 헬퍼)** — `band/api/match_views.py`

```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction

from band.models import BandMember, BandSchedule, BandScheduleApplication
from band.match_models import MatchSession, SessionParticipant, Court
from band.matchmaking.scoring import level_to_score
from band.api.match_serializers import serialize_session


def _is_operator(user, band) -> bool:
    return BandMember.objects.filter(
        band=band, user=user, status="active",
        role__in=["owner", "admin"]).exists()


def _profile_level_gender(user):
    profile = getattr(user, "profile", None)
    level = getattr(profile, "badminton_level", "") if profile else ""
    gender = getattr(profile, "gender", "unknown") if profile else "unknown"
    return level_to_score(level), gender


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_session(request, schedule_id):
    schedule = get_object_or_404(BandSchedule, id=schedule_id)
    if not _is_operator(request.user, schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    if hasattr(schedule, "match_session"):
        return Response({"detail": "이미 대진 세션이 있습니다.", "id": schedule.match_session.id},
                        status=status.HTTP_409_CONFLICT)

    court_count = int(request.data.get("court_count", 4))
    mode = request.data.get("discipline_mode", MatchSession.DisciplineMode.ALL)
    preset = request.data.get("preset", MatchSession.Preset.BALANCED)

    with transaction.atomic():
        session = MatchSession.objects.create(
            schedule=schedule, court_count=court_count,
            discipline_mode=mode, preset=preset, created_by=request.user)
        for i in range(1, court_count + 1):
            Court.objects.create(session=session, index=i)
        apps = BandScheduleApplication.objects.filter(
            schedule=schedule, status="approved").select_related("user")
        for app in apps:
            score, gender = _profile_level_gender(app.user)
            SessionParticipant.objects.create(
                session=session, user=app.user, base_level=score, gender=gender,
                attendance=SessionParticipant.Attendance.NOT_PRESENT)

    return Response(serialize_session(session), status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def session_state(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    return Response(serialize_session(session))
```

- [ ] **Step 5: 라우트 추가** — `band/api/urls.py` 의 `urlpatterns` 끝에:

```python
    # 대진 (matchmaking)
    path('match/schedules/<int:schedule_id>/start/', match_views.start_session, name='match_start'),
    path('match/<int:session_id>/', match_views.session_state, name='match_state'),
```

그리고 파일 상단 import에 추가:

```python
from . import match_views
```

- [ ] **Step 6: 통과 확인**

Run: `python manage.py test band.tests.test_match_api -v 2`
Expected: PASS (4 tests)

- [ ] **Step 7: 커밋**

```bash
git add band/api/match_views.py band/api/match_serializers.py band/api/urls.py band/tests/test_match_api.py
git commit -m "feat(match): 세션 시작·상태 조회 API"
```

---

### Task 9: 토글 API (모드 / 성향 / 출석)

**Files:**
- Modify: `band/api/match_views.py`
- Modify: `band/api/urls.py`
- Test: `band/tests/test_match_api.py` (TogglesTest 추가)

- [ ] **Step 1: 실패 테스트 추가** — `band/tests/test_match_api.py` 끝에

```python
class TogglesTest(MatchApiSetup):
    def _session(self):
        return self.client.post(
            f"/api/band/match/schedules/{self.schedule.id}/start/",
            {"court_count": 2}, format="json").json()

    def test_set_mode(self):
        sid = self._session()["id"]
        resp = self.client.post(f"/api/band/match/{sid}/mode/",
                                {"discipline_mode": "mixed_only"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["discipline_mode"], "mixed_only")

    def test_set_preset(self):
        sid = self._session()["id"]
        resp = self.client.post(f"/api/band/match/{sid}/preset/",
                                {"preset": "competitive"}, format="json")
        self.assertEqual(resp.json()["preset"], "competitive")

    def test_toggle_attendance_back_and_forth(self):
        u = self._approved_applicant("m1@x.com", "a", "male")
        sid = self._session()["id"]
        pid = next(p["id"] for p in self.client.get(f"/api/band/match/{sid}/").json()["participants"]
                   if p["user_id"] == u.id)
        r1 = self.client.post(f"/api/band/match/{sid}/participants/{pid}/attendance/",
                              {"attendance": "present"}, format="json")
        self.assertEqual(r1.json()["attendance"], "present")
        r2 = self.client.post(f"/api/band/match/{sid}/participants/{pid}/attendance/",
                              {"attendance": "left"}, format="json")
        self.assertEqual(r2.json()["attendance"], "left")
```

- [ ] **Step 2: 실패 확인**

Run: `python manage.py test band.tests.test_match_api.TogglesTest -v 2`
Expected: FAIL (404)

- [ ] **Step 3: 뷰 추가** — `band/api/match_views.py` 끝에

```python
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_mode(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    mode = request.data.get("discipline_mode")
    if mode not in MatchSession.DisciplineMode.values:
        return Response({"detail": "잘못된 모드"}, status=status.HTTP_400_BAD_REQUEST)
    session.discipline_mode = mode
    session.save(update_fields=["discipline_mode", "updated_at"])
    return Response(serialize_session(session))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_preset(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    preset = request.data.get("preset")
    if preset not in MatchSession.Preset.values:
        return Response({"detail": "잘못된 성향"}, status=status.HTTP_400_BAD_REQUEST)
    session.preset = preset
    session.save(update_fields=["preset", "updated_at"])
    return Response(serialize_session(session))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_attendance(request, session_id, pid):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    sp = get_object_or_404(SessionParticipant, id=pid, session=session)
    value = request.data.get("attendance")
    if value not in SessionParticipant.Attendance.values:
        return Response({"detail": "잘못된 출석 상태"}, status=status.HTTP_400_BAD_REQUEST)
    sp.attendance = value
    sp.save(update_fields=["attendance"])
    from band.api.match_serializers import serialize_participant
    return Response(serialize_participant(sp))
```

- [ ] **Step 4: 라우트 추가** — `band/api/urls.py`

```python
    path('match/<int:session_id>/mode/', match_views.set_mode, name='match_set_mode'),
    path('match/<int:session_id>/preset/', match_views.set_preset, name='match_set_preset'),
    path('match/<int:session_id>/participants/<int:pid>/attendance/',
         match_views.set_attendance, name='match_attendance'),
```

- [ ] **Step 5: 통과 확인 + 커밋**

Run: `python manage.py test band.tests.test_match_api -v 2`
Expected: PASS

```bash
git add band/api/match_views.py band/api/urls.py band/tests/test_match_api.py
git commit -m "feat(match): 모드·성향·출석 토글 API"
```

---

### Task 10: 경기 종료 + 다음 경기 자동 추천 (`courts/<index>/end`, `fill`)

핵심 흐름. 종료 시 진행 경기를 `done`으로 바꾸고 4명의 카운트·`last_game_ended_at`을 갱신한 뒤, 코어로 다음 경기를 추천해 새 `Match`를 만든다. 추천 불가(`NeedOperatorChoice`)면 경기 생성 없이 `needs_choice`를 반환한다.

**Files:**
- Modify: `band/api/match_views.py`
- Modify: `band/api/urls.py`
- Test: `band/tests/test_match_api.py` (FlowTest 추가)

- [ ] **Step 1: 실패 테스트 추가** — `band/tests/test_match_api.py` 끝에

```python
class FlowTest(MatchApiSetup):
    def _present_session(self, specs):
        # specs: [(email, level, gender), ...] 모두 present 로 시작
        for email, level, gender in specs:
            self._approved_applicant(email, level, gender)
        sid = self.client.post(
            f"/api/band/match/schedules/{self.schedule.id}/start/",
            {"court_count": 1, "discipline_mode": "all"}, format="json").json()["id"]
        for p in self.client.get(f"/api/band/match/{sid}/").json()["participants"]:
            self.client.post(f"/api/band/match/{sid}/participants/{p['id']}/attendance/",
                             {"attendance": "present"}, format="json")
        return sid

    def test_fill_empty_court_creates_match(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female")])
        resp = self.client.post(f"/api/band/match/{sid}/courts/1/fill/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.json()["match"])
        # 상태 조회 시 코트1에 진행 경기
        state = self.client.get(f"/api/band/match/{sid}/").json()
        self.assertIsNotNone(state["courts"][0]["match"])

    def test_end_increments_counts_and_refills(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female"),
            ("e@x.com", "b", "male"), ("f@x.com", "b", "male"),
            ("g@x.com", "b", "female"), ("h@x.com", "b", "female")])
        self.client.post(f"/api/band/match/{sid}/courts/1/fill/", {}, format="json")
        resp = self.client.post(f"/api/band/match/{sid}/courts/1/end/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        # 끝난 4명은 카운트 1, 새 경기 생성됨
        state = self.client.get(f"/api/band/match/{sid}/").json()
        played = [p for p in state["participants"] if p["total_games"] == 1]
        self.assertEqual(len(played), 4)
        self.assertIsNotNone(state["courts"][0]["match"])

    def test_mixed_only_impossible_returns_needs_choice(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "male"), ("d@x.com", "b", "male")])
        self.client.post(f"/api/band/match/{sid}/mode/",
                         {"discipline_mode": "mixed_only"}, format="json")
        resp = self.client.post(f"/api/band/match/{sid}/courts/1/fill/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["needs_choice"])
        self.assertIn("mens", resp.json()["options"])

    def test_fill_with_forced_discipline(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "male"), ("d@x.com", "b", "male")])
        self.client.post(f"/api/band/match/{sid}/mode/",
                         {"discipline_mode": "mixed_only"}, format="json")
        resp = self.client.post(f"/api/band/match/{sid}/courts/1/fill/",
                                {"discipline": "mens"}, format="json")
        self.assertIsNotNone(resp.json()["match"])
        self.assertEqual(resp.json()["match"]["discipline"], "mens")
```

- [ ] **Step 2: 실패 확인**

Run: `python manage.py test band.tests.test_match_api.FlowTest -v 2`
Expected: FAIL (404)

- [ ] **Step 3: 추천·생성 헬퍼 + 뷰 작성** — `band/api/match_views.py` 끝에

```python
from django.utils import timezone
from band.match_models import Match, MatchPlayer, Court
from band.match_state import build_pool, build_pairstats
from band.matchmaking.engine import recommend_next_game
from band.matchmaking.types import Mode, Preset, Discipline, NeedOperatorChoice, GamePlan
from band.matchmaking.cost import best_split
from band.matchmaking.types import PRESETS
from band.api.match_serializers import serialize_match

_MODE_MAP = {
    "mixed_only": Mode.MIXED_ONLY,
    "singles_gender": Mode.SINGLES_GENDER,
    "all": Mode.ALL,
}
_PRESET_MAP = {"balanced": Preset.BALANCED, "competitive": Preset.COMPETITIVE}
_DISC_MAP = {"mixed": Discipline.MIXED, "mens": Discipline.MENS, "womens": Discipline.WOMENS}


def _on_court_ids(session):
    ids = set()
    for m in Match.objects.filter(session=session, status="playing").prefetch_related("players"):
        ids.update(mp.participant_id for mp in m.players.all())
    return ids


def _create_match(session, court, plan: GamePlan):
    match = Match.objects.create(
        session=session, court=court, discipline=plan.discipline.value)
    for pid in plan.team1:
        MatchPlayer.objects.create(match=match, participant_id=pid, team=1)
    for pid in plan.team2:
        MatchPlayer.objects.create(match=match, participant_id=pid, team=2)
    return match


def _fill_court(session, court, forced_discipline=None):
    """반환: (match | None, need: NeedOperatorChoice | None)"""
    pool = build_pool(session, on_court_participant_ids=_on_court_ids(session))
    stats = build_pairstats(session)

    if forced_discipline is not None:
        # 운영자가 종목을 강제 → 그 종목으로 best_split (윈도우 앞 4명 중 가능한 조합)
        from itertools import combinations
        from band.matchmaking.selection import queue_order
        from band.matchmaking.engine import _discipline_feasible
        weights = PRESETS[_PRESET_MAP[session.preset]]
        order = queue_order(pool)
        for combo in combinations(order[:8], 4):
            if not _discipline_feasible(combo, forced_discipline):
                continue
            split = best_split(list(combo), forced_discipline, weights, stats, session.female_adjust)
            if split:
                return _create_match(session, court, split), None
        return None, NeedOperatorChoice(reason="강제 종목 구성 불가", options=())

    result = recommend_next_game(
        pool, _MODE_MAP[session.discipline_mode], _PRESET_MAP[session.preset],
        stats, female_adjust=session.female_adjust)
    if isinstance(result, GamePlan):
        return _create_match(session, court, result), None
    if isinstance(result, NeedOperatorChoice):
        return None, result
    return None, None  # 인원 부족(None)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def fill_court(request, session_id, index):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    court = get_object_or_404(Court, session=session, index=index)
    if court.matches.filter(status="playing").exists():
        return Response({"detail": "이미 진행 중인 경기가 있습니다."}, status=status.HTTP_409_CONFLICT)

    forced = request.data.get("discipline")
    forced_disc = _DISC_MAP.get(forced) if forced else None
    with transaction.atomic():
        match, need = _fill_court(session, court, forced_disc)
    if need is not None:
        return Response({"match": None, "needs_choice": True,
                         "reason": need.reason,
                         "options": [d.value for d in need.options]})
    if match is None:
        return Response({"match": None, "needs_choice": False,
                         "detail": "대기 인원이 부족합니다."})
    return Response({"match": serialize_match(match), "needs_choice": False})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_court(request, session_id, index):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    court = get_object_or_404(Court, session=session, index=index)
    match = court.matches.filter(status="playing").prefetch_related("players__participant").first()
    if match is None:
        return Response({"detail": "진행 중인 경기가 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

    now = timezone.now()
    with transaction.atomic():
        match.status = "done"
        match.ended_at = now
        match.save(update_fields=["status", "ended_at"])
        disc_field = {"mixed": "games_mixed", "mens": "games_mens", "womens": "games_womens"}[match.discipline]
        for mp in match.players.all():
            sp = mp.participant
            setattr(sp, disc_field, getattr(sp, disc_field) + 1)
            sp.last_game_ended_at = now
            sp.save(update_fields=[disc_field, "last_game_ended_at"])
        new_match, need = _fill_court(session, court)

    if need is not None:
        return Response({"ended": match.id, "match": None, "needs_choice": True,
                         "reason": need.reason, "options": [d.value for d in need.options]})
    return Response({
        "ended": match.id,
        "match": serialize_match(new_match) if new_match else None,
        "needs_choice": False,
    })
```

> 주의: `engine._discipline_feasible`를 재사용하므로 Task 5에서 모듈 레벨 함수로 정의돼 있어야 한다(이미 그렇게 작성됨).

- [ ] **Step 4: 라우트 추가** — `band/api/urls.py`

```python
    path('match/<int:session_id>/courts/<int:index>/fill/', match_views.fill_court, name='match_fill'),
    path('match/<int:session_id>/courts/<int:index>/end/', match_views.end_court, name='match_end_court'),
```

- [ ] **Step 5: 통과 확인 + 커밋**

Run: `python manage.py test band.tests.test_match_api -v 2`
Expected: PASS

```bash
git add band/api/match_views.py band/api/urls.py band/tests/test_match_api.py
git commit -m "feat(match): 경기 종료·다음경기 자동추천 API"
```

---

### Task 11: 경기 편집 (swap / 종목 변경) + 세션 종료

**Files:**
- Modify: `band/api/match_views.py`
- Modify: `band/api/urls.py`
- Test: `band/tests/test_match_api.py` (EditTest 추가)

- [ ] **Step 1: 실패 테스트 추가** — `band/tests/test_match_api.py` 끝에

```python
class EditTest(FlowTest):
    def test_swap_replaces_player_in_match(self):
        sid = self._present_session([
            ("a@x.com", "b", "male"), ("b@x.com", "b", "male"),
            ("c@x.com", "b", "female"), ("d@x.com", "b", "female"),
            ("e@x.com", "b", "male")])
        match = self.client.post(f"/api/band/match/{sid}/courts/1/fill/", {}, format="json").json()["match"]
        in_ids = {p["participant_id"] for p in match["team1"] + match["team2"]}
        state = self.client.get(f"/api/band/match/{sid}/").json()
        bench = next(p["participant_id"] for p in state["queue"]
                     if p["participant_id"] not in in_ids)
        leaving = next(iter(in_ids))
        resp = self.client.patch(f"/api/band/match/{sid}/matches/{match['id']}/",
                                 {"swap": [leaving, bench]}, format="json")
        self.assertEqual(resp.status_code, 200)
        new_ids = {p["participant_id"] for p in resp.json()["team1"] + resp.json()["team2"]}
        self.assertIn(bench, new_ids)
        self.assertNotIn(leaving, new_ids)

    def test_end_session(self):
        sid = self._present_session([("a@x.com", "b", "male")])
        resp = self.client.post(f"/api/band/match/{sid}/end/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ended")
```

- [ ] **Step 2: 실패 확인**

Run: `python manage.py test band.tests.test_match_api.EditTest -v 2`
Expected: FAIL (404)

- [ ] **Step 3: 뷰 작성** — `band/api/match_views.py` 끝에

```python
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def edit_match(request, session_id, match_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    match = get_object_or_404(Match, id=match_id, session=session, status="playing")

    swap = request.data.get("swap")          # [out_participant_id, in_participant_id]
    discipline = request.data.get("discipline")

    with transaction.atomic():
        if swap:
            out_id, in_id = swap
            mp = get_object_or_404(MatchPlayer, match=match, participant_id=out_id)
            # 들어올 사람은 present 이고 다른 코트에 없어야
            if in_id in _on_court_ids(session):
                return Response({"detail": "교체 대상이 이미 경기 중입니다."},
                                status=status.HTTP_400_BAD_REQUEST)
            in_sp = get_object_or_404(SessionParticipant, id=in_id, session=session,
                                      attendance="present")
            mp.participant = in_sp
            mp.save(update_fields=["participant"])
        if discipline in _DISC_MAP:
            match.discipline = discipline
            match.save(update_fields=["discipline"])

    match.refresh_from_db()
    match = Match.objects.prefetch_related("players__participant__user").get(id=match.id)
    return Response(serialize_match(match))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_session(request, session_id):
    session = get_object_or_404(MatchSession, id=session_id)
    if not _is_operator(request.user, session.schedule.band):
        return Response({"detail": "운영 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
    session.status = MatchSession.Status.ENDED
    session.save(update_fields=["status", "updated_at"])
    return Response({"id": session.id, "status": session.status})
```

- [ ] **Step 4: 라우트 추가** — `band/api/urls.py`

```python
    path('match/<int:session_id>/matches/<int:match_id>/', match_views.edit_match, name='match_edit'),
    path('match/<int:session_id>/end/', match_views.end_session, name='match_end_session'),
```

- [ ] **Step 5: 전체 테스트 + 커밋**

Run: `python manage.py test band -v 2`
Expected: PASS (전체 매칭 관련)

```bash
git add band/api/match_views.py band/api/urls.py band/tests/test_match_api.py
git commit -m "feat(match): 경기 편집·세션 종료 API"
```

---

## Phase 4 — UI (별도 계획)

프런트엔드(운영자 화면)는 **별도 계획서**로 진행한다. claude.ai에서 받은 디자인 코드(React)를 가져온 뒤:
- 위 API 계약(Phase 3 표)을 그대로 소비.
- 화면: 출석 체크 / 메인 운영(코트 그리드·모드/성향 토글) / 대기열 / 개인 카운트 / 혼복부족 선택 모달.
- 웹은 Django 템플릿 또는 SPA로 API 호출, 앱은 동일 API 사용.

이 계획서 범위는 **백엔드까지**. UI 시작 시 새 spec/plan을 작성한다.

---

## 자기 검토 결과 (스펙 대비)

- ✅ 흐름형 모델 → Task 10(end/fill 코트 단위 추천)
- ✅ 종목 모드 토글 → Task 9 set_mode, Task 10에서 현재 모드 사용
- ✅ 성향 프리셋 → types PRESETS, Task 9 set_preset
- ✅ 대기열 정렬(경기수→쉰시간) → Task 3
- ✅ 우선순위(코트 안 놀리기/균등/모드/균형) → engine fairness 가산 + fill 로직 + NeedOperatorChoice
- ✅ 혼복 불가 시 운영자 선택 → engine NeedOperatorChoice, end/fill의 needs_choice
- ✅ 동성페어 유연 허용 → cost `_valid_for_discipline`, engine `_discipline_feasible`
- ✅ 급수 점수·femaleAdjust → Task 2
- ✅ 출석 상태 양방향 토글 → Task 9
- ✅ 자동확정+편집(swap/종목) → Task 10 자동 생성, Task 11 edit
- ✅ 개인 카운트(혼복/남복/여복) → 모델 필드 + serialize_participant
- ✅ 회원 신청자 기준 → start_session이 approved 신청자만
- ✅ 규모(윈도우 제한) → engine window=8
- ⚠️ 알림 UX 세부 → UI 계획에서(여기선 needs_choice 데이터까지 제공)

**확인 완료된 가정:**
- ✅ `UserProfile.user` related_name = `"profile"` ([accounts/models.py:115](../../../accounts/models.py#L115)) → 뷰의 `user.profile` 접근 유효.
- ✅ `Band`에 `category` 필드 없음 → 테스트는 `name`/`created_by`만으로 최소 생성.

**실행 시 확인할 가정:**
- `Band`/`BandSchedule`에 위 외 추가 필수(널 불가·기본값 없음) 필드가 있으면 테스트 setUp에서 채울 것.
- 동시성: 운영자가 버튼을 직렬로 누르는 전제. `transaction.atomic` + 코트 진행경기 존재 체크로 중복 생성 방지.
