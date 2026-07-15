# 번개 자동 대진 — 앱 핸드오프 패키지

모바일 앱 팀 전달용. **디자인(화면) ↔ API ↔ 동작**을 한곳에 매핑한다.
전체 사양(진입 경로·데이터 매핑·매칭 알고리즘·API 전체·푸시)은 → [`live-matchmaking-overview.md`](./live-matchmaking-overview.md) (이 폴더 안).

**관련 스펙 문서**:
- 참가자 화면 상태(대진): [participant-status-spec.md](./participant-status-spec.md) — `/me/` 응답 → 상태 배너 10종 매핑 (started_at·up_next_level 포함)
- 대기하기(Waitlist): [waitlist-spec.md](./waitlist-spec.md) — 정원 마감 시 대기·승격·참석취소·대기순번·쪽지
- 급수별 정원(Level Quota): [quota-spec.md](./quota-spec.md) — 급수·성별 정원 모집, 성별 나눔 토글, 급수별 현황

- **운영석(호스트)**: 가로 태블릿 1대. 코트/대기열/자동 대진·출석·코치·파트너 운영.
- **참가자**: 세로 모바일. 내 상태(다음 경기·대기순번)·자가 체크인·파트너 신청.
- **실시간**: 폴링(2~3초). 인증: JWT Bearer. WebSocket 아님.
- 화면은 React 프로토타입 기준. **스크린샷이 아니라 아래 `prototype/` 소스 코드가 진짜 디자인 명세**다.

---

## ⭐ 디자인 소스 코드 (`prototype/`) — 이걸 보고 구현

스크린샷은 참조용. **레이아웃·간격·색·컴포넌트는 이 실행 가능한 React 프로토타입 코드가 정본**이다.
열어보는 법: `prototype/` 폴더에서 정적 서버 실행(`python3 -m http.server`) 후 브라우저로 열면 그대로 동작.

| 파일 | 역할 | 앱에서 |
|---|---|---|
| `index.html` | **디자인 토큰(`:root` CSS 변수)** + 폰트(Pretendard) + 로딩 | 토큰을 앱 테마로 그대로 이식 |
| `ui.jsx` | **공용 컴포넌트**: `LevelChip`(급수칩)·`NameWithGender`·`DisciplineBadge`(종목)·`Btn`·`Segmented`·`CountPills` 등 | 컴포넌트 단위로 1:1 포팅 |
| `screens.jsx` | 운영 화면(코트 카드·대기열 패널·코치 게이지·도움말) | 레이아웃·스타일 포팅 |
| `screens2.jsx` | 출석 체크·개인 카운트·각종 모달(참가자 추가/코트 설정/파트너) | 〃 |
| `mobile.jsx` | 모바일(참가자) 래퍼 | 〃 |
| `app.jsx` | 루트 상태·네비·디바이스 프레임 | 화면 전환 구조 참고 |
| `core.jsx` | ⚠️ **데모용 더미 데이터 + 매칭 알고리즘(JS)** | **포팅하지 말 것** — 매칭은 전부 서버 API가 처리. 앱은 응답만 렌더 |

> **핵심 분리**: `ui.jsx`/`screens*.jsx`/`app.jsx`/`index.html`(토큰) = **그대로 옮길 디자인**. `core.jsx`의 추천·코스트·큐 로직은 **서버에 이미 구현**(`band/matchmaking/`)되어 API로 나오므로 앱에선 버린다. 앱이 할 일 = API 응답 → 이 컴포넌트들로 렌더 + 사용자 액션 → API 호출.

### 디자인 토큰 (전체는 `prototype/index.html` `:root`)
```
브랜드(코트 그린)  --brand #12a565 / --brand-ink #0c7f4e / --brand-tint #e7f6ee
중립             --bg #eef0f4 / --surface #fff / --ink #11161f / --ink-2 #475063 / --muted #8b94a6 / --line #e3e7ee
종목            혼복 --mix #8b5cf6 · 남복 --men #3b82f6 · 여복 --women #ec4899  (각 -ink/-tint/-line)
상태            --warn #e0871b / --danger #e5484d
반경·그림자      --card-radius 18px / --r-sm·md·lg·xl / --sh-1·2·3
폰트            Pretendard Variable
```
급수 색 램프(진→연): 자강 #11161f → S #2b3344 → A #414b60 → B #5b6678 → C #828c9e → D #c2cad6 → 왕초심 #e1e6ee (`ui.jsx` `LEVEL_STYLE`).

---

## 화면 ↔ 기능 ↔ API

### 1. 운영 화면 (태블릿) — `screenshots/tablet-1-운영화면.png`
호스트 메인. 코트별 추천 경기 + [경기 시작]/[편집], 우측 대기열(다음 경기/예약/대기 순번), 상단 종목·성향·자동/수동 토글, 출석/카운트 카운터.
- 상태 조회: `GET /api/bands/match/<sid>/` (courts·queue·participants·pairs·coach 포함)
- 코트 채우기/종료: `POST .../courts/<i>/fill/` · `POST .../courts/<i>/end/`
- 경기 수정(교체/종목): `PATCH .../matches/<mid>/`
- 종목/성향: `POST .../mode/` · `POST .../preset/`

### 2. 출석 체크 (태블릿) — `screenshots/tablet-2-출석체크.png`
참가자 출석/퇴장 토글, 필터(전체/미출석/참여중/퇴장), 검색, [참가자 추가], 파트너 묶기.
**헤더 우측 ↻ 새로고침** = 서버 출석 재조회(참가자가 폰에서 체크인한 걸 반영).
- 운영자 출석 변경: `POST .../participants/<pid>/attendance/`
- (참가자 본인 체크인은 4번 화면 / `POST .../me/checkin/`)
- 새로고침: `GET /api/bands/match/<sid>/` 재호출(또는 폴링)

### 3. 개인 카운트 (태블릿) — `screenshots/tablet-3-개인카운트.png`
참가자별 누적 경기 수(혼복/남복/여복) 한눈에. 공정성 모니터링용.
- `GET /api/bands/match/<sid>/` → `participants[].games_*`, `total_games`

### 4. 참가자 화면 (모바일) — `screenshots/mobile-1-참가자화면.png`
참가자 본인 폰. 알림 배너(곧 경기/대기 N번째), 내 카드(오늘 N경기), 다음 경기 멤버, [파트너 게임 신청하기], [퇴장하기].
- 내 상태(폴링): `GET /api/bands/match/<sid>/me/` (`current_match`·`queue_position`·`up_next`·`games`)
  - 일정만 알 때: `GET /api/bands/match/schedules/<schedule_id>/me/`
- 자가 체크인/퇴장: `POST /api/bands/match/<sid>/me/checkin/` (`action: in|out`)
- 파트너 신청: `POST .../partner-requests/create/` (`to_participant_id`, `strict`)

---

## 푸시 알림 (FCM)
디바이스 토큰 등록: `POST /api/notifications/devices/register/`. 이벤트:

| 이벤트 | type | 수신자 |
|---|---|---|
| 다음 경기 배정 | `match_next_game` | 그 경기 4명(코치 제외) |
| 파트너 신청 받음 | `partner_request` | 신청 받은 사람 |
| 파트너 확정 | `partner_approved` | 양쪽 |

`data.related_band_schedule_id`로 해당 번개 화면 진입 → 4번 화면 폴링.

---

## 미수록(요청 시 추가 캡처 가능)
코치 고정 코트 / 파트너 묶기·신청 바텀시트 / 참가자 추가 모달 / 코트 설정 / 도움말 오버레이.
