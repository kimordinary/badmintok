# 참가자 화면 상태 ↔ `/me/` 매핑 (앱 1:1 구현용)

> 참가자 대진 화면은 **자체 판단 로직 없이** `GET /api/bands/match/<sid>/me/` 응답만 보고 그린다.
> 2초 폴링이라 서버 상태가 바뀌면 새로고침 없이 2초 내 자동 반영. 자동/수동 모드 동일(‪`/me/`는 코트·대기 상태로만 판정).
> 디자인 정본: [prototype/screens.jsx](./prototype/screens.jsx) `ParticipantScreen`(상태 배너 로직).

---

## 1. `/me/` 주요 필드
```json
{
  "attendance": "not_present | present | left",
  "profile": { "complete": true, "missing": [] },
  "playing": false,
  "current_match": {
    "id": 12, "discipline": "mixed", "status": "playing",
    "started_at": "2026-07-15T01:30:07.364119+00:00",
    "court_index": 0, "my_team": 1, "is_coach_court": false,
    "team1": [ {"participant_id":1,"name":"홍길동","base_level":3,"gender":"male"} ],
    "team2": [ ... ]
  },
  "queue_position": 3,
  "queue_total": 8,
  "up_next": true,
  "up_next_level": 0,
  "games": { "mixed": 1, "mens": 0, "womens": 0, "total": 1 }
}
```
- 코트 밖/대기 상태면 `current_match: null`, `playing: false`.
- `up_next_level`: **0=곧 입장, 1=다음다음, null=해당 없음**. (`up_next`는 `up_next_level===0`과 동일, 하위호환 유지)
- `current_match.started_at`: 경기 시작 시각(ISO8601). **위치는 `current_match` 바로 아래** (`current_match.match.started_at` 아님).

---

## 2. 상태 → 화면 매핑 (앱 판정 순서, 위부터 먼저 매칭)

| # | 화면 | `/me/` 조건 |
|---|---|---|
| 1 | **프로필 미완성** | `attendance!="present/left"` + (`profile.complete=false` 또는 `profile=null`) |
| 2 | **출석 전** | `attendance!="present/left"` + `profile.complete=true` |
| 3 | **퇴장(쉬는 중)** | `attendance="left"` |
| 4 | **코치 고정** | `playing=true` + `current_match.is_coach_court=true` |
| 5 | **입장(코트로!)** | `playing=true` + `current_match` + `started_at`이 **2분 이내** |
| 6 | **경기 중** | `playing=true` + `current_match` (`started_at` 2분 초과) |
| 7 | **곧 입장** | `playing=false` + `up_next_level=0` (=`up_next=true`) |
| 8 | **다음다음** | `playing=false` + `up_next_level=1` |
| 9 | **대기 N번째** | `playing=false` + `queue_position=N` |
| 10 | **대기** | 위 아무것도 아님 |

> **2분 규칙**: `now - started_at < 120초` → "입장(지금 코트로)", 초과 → "경기 중". 앱이 로컬 시계로 계산(폴링 사이 전환).

---

## 3. 전이 시나리오 (자동·수동 동일 — 서버 검증 완료)
```
출석 전 →(체크인)→ 대기N/대기 →(배정 확정)→ 곧 입장
       →(코트 시작)→ 입장 →(2분 후)→ 경기 중 →(경기 끝)→ 대기N
       →(퇴장)→ 쉬는 중 →(복귀)→ …
```
각 단계에서 `/me/`가 위 표 값으로 바뀌는지 실측 검증 완료(2026-07-15).

---

## 4. 출석 체크인
- `POST /api/bands/match/<sid>/me/checkin/` body `{ "action": "in" | "out" }`
- **승인 참가자만** 가능(비참가자 `403`).
- `action:"in"` + 프로필 미완성 → `422` `{ "code":"profile_incomplete", "missing":[...] }`. 앱은 서버 `detail` 메시지 그대로 노출.
- `action:"out"`(퇴장)은 프로필 게이트 없이 항상 허용.

---

## 5. 이 화면에 빠지기 쉬운 요소 (구현 체크)
- [ ] **상태 배너**(위 10종) — 지금 앱에 이게 빠져 있으면 최우선. `prototype`의 상단 카드
- [ ] **다음 경기 멤버 카드**: `current_match.team1/team2` 또는 곧 입장 시 다음 경기 4명
- [ ] **오늘 내 경기 수**: `games.total`
- [ ] **입장/경기중 구분**: `started_at` 2분 규칙
- [ ] **다음다음**: `up_next_level=1`
