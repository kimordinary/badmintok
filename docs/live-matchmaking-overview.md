# 번개 자동 대진(Live Matchmaking) — 운영 문서

> 모임장이 번개(행사) 당일 태블릿 1대로 자동 대진을 돌리고, **참가자는 앱에서 자기 상태를 실시간으로 받는** 기능의 **진입 경로 · 데이터 · 알고리즘 · API · 구현 현황**을 한곳에 정리한 living doc. 기능 추가/변경 시 여기를 갱신한다.

> **아키텍처 한 줄 요약**: 진짜 동작하는 백본은 **서버(DRF API + Python 매칭 엔진, `band/match_models.py`·`band/matchmaking/`·`band/api/match_views.py`)**. 앱(참가자·운영자 모두)이 이 API를 **폴링**으로 소비한다(WebSocket 아님 — WSGI/Gunicorn 그대로 배포). `static/match_console`(localhost:5500 데모 포함)은 **디자인 시안("그림")**이며 이 API와 연동돼 있지 않다. → 상세 API는 **8장**.

최종 갱신: 2026-06-18

---

## 1. 개요 / 전제

- **누가**: 번개의 모임장(host)만. (`can_manage` = BandMember role owner/admin 또는 사이트 관리자)
- **무엇**: 그 번개의 승인 참가자들로 복식 대진을 **자동 생성**(코트가 비는 대로 굴러가는 롤링 방식).
- **전제**: **한 번개 = 태블릿 1대**. 여러 명이 보는 화면이 아니라 모임장 **운영석(콘솔)**.
- 참가자는 **급수·성별이 항상 채워져 있어야** 함(매칭 필수값). 누락자는 대진에서 제외(추후: 신청/체크인 단계에서 거부 처리 예정).

---

## 2. 진입 경로 (플로우)

```
[번개 상세] (모임장)
   templates/band/schedule_detail.html · view: band.views.schedule_detail
   - 참가자 목록 "위에" 모임장 전용 [번개 시작 · 자동 대진] 버튼 (스크롤 없이 보이게)
   - 하단 "참가 신청" 흐름은 참가자용으로 그대로 유지
        │  GET /band/<band_id>/schedules/<schedule_id>/match/
        ▼
[대진 진입 화면]  (승인 참가자 → 대진 풀 로딩)
   templates/band/schedule_match.html · view: band.views.schedule_match
   - 승인 참가자를 {이름, 성별 M/F, 급수} 로 매핑해 보여줌
   - 급수·성별 누락자 경고
   - [출석 체크 시작] 버튼
        │  GET /band/<band_id>/schedules/<schedule_id>/console/
        ▼
[운영 콘솔]  (실제 자동 대진 화면)
   templates/band/schedule_console.html · view: band.views.schedule_console
   - 정적 콘솔(static/match_console/*) 을 풀스크린으로 로드
   - window.__BM_PARTICIPANTS__ 로 실제 참가자 주입
   - 출석 체크 화면으로 시작 → 운영 화면(코트/대기열/자동 대진)
```

> 앱(모바일)에서는 고정 하단바가 있어 진입 버튼 위치가 자유롭지만, **웹에서는 참가자 목록 위**에 둔다(당일 바로 보이게).

### 2.1 출석 — 호스트 수동 + 참가자 자가 체크인 (하이브리드)
- **호스트 수동**: 콘솔 출석 화면에서 직접 체크/퇴장 (기존).
- **참가자 자가 체크인**: 번개 상세에서 승인 참가자가 직접 출석.
  - `POST /band/<b>/schedules/<s>/checkin/` (`action=in|out`) → `BandScheduleApplication.checked_in_at` 기록/해제.
  - 버튼 누르면 **확인 모달**("지금 도착하셨나요? 체크인하면 바로 대진에 반영, 중간 퇴장 가능") → 확인 시 체크인.
  - **프로필(급수·성별) 미완성자는 차단** → "내정보 › 프로필 편집"으로 안내(서버에서도 가드).
  - 체크인 후 상태: "출석 완료 · 대진 참여 중" + [퇴장하기].
- **콘솔 반영(진입 시 1회 로드)**: `schedule_console`가 `checked_in_at` 있는 사람을 `status=참여중`으로 주입 → 콘솔 열면 자가 출석자는 미리 체크된 상태. (실시간 라이브 싱크는 미구현 — TODO)
- **TODO**: 체크인 버튼 **당일/시작시간 게이팅**(집에서 미리 누르기 방지)은 아직 없음.

---

## 3. 데이터 매핑 (DB → 대진 풀)

번개 = `Band(band_type="flash")` + `BandSchedule(일정)`. 참가자 = `BandScheduleApplication`.

| 대진 필드 | 출처 | 비고 |
|---|---|---|
| 참가자 명단 | `schedule.applications.filter(status="approved")` | 승인된 신청자만 |
| 이름 | `user.real_name` | = `UserProfile.name` (없으면 활동명) |
| 성별 | `user.profile.gender` → `M`/`F` | `male`→M, `female`→F, 그 외→누락 |
| 급수 | `user.profile.badminton_level` → 라벨 | master=자강, s=S, a=A, b=B, c=C, d=D, beginner=왕초심 |

- 급수·성별 둘 중 하나라도 비면 **누락자**로 분류 → 콘솔 풀에서 제외(진입 화면에서 경고).
- 콘솔 참가자 객체 형태:
  `{ id, name, gender:'M'|'F', level, status:'미출석', court:null, team:null, games:{혼복,남복,여복}, totalGames:0, lastFinished:null, partnerCount:{}, opponentCount:{} }`

---

## 4. 매칭 알고리즘 (코어: `match_ui_demo/core.jsx`, 콘솔: `static/match_console/core.jsx`)

### 4.1 큐(대기열) 정렬 — `sortQueue`
- **경기수 적은 사람 우선 → 동률이면 오래 쉰 사람 우선.** (공정성)

### 4.2 추천 — `recommendMatch(pool, mode, preset, nowTs, bias)`
- 대기열 상위 윈도우에서 4명 조합을 탐색, **코스트 최소** 조합 선택.
- 코스트 = 밸런스(실력차²) + 파트너 반복 + 상대 반복 + 공정성(대기열 앞 우대).
- **종목(mode)**: 혼복 / 남복·여복 / 모두. **성향(preset)**: 밸런스 / 동일 급수.
- 성비가 안 맞아 혼복이 안 되면 대안(남복/여복) 제안.

### 4.3 코치(자강) 고정 — 다중 코치 + 공동 우선
- **코트별 코치 고정**: `court.ace=true` + `court.coachId`. 코치는 그 코트에 예약(court 고정)되어 **대기열·카운트 공정성에서 자동 제외**.
- **3자리 선발** `pickAceThree(pool, metCount, nowTs)`:
  - **공동 우선**: `metCount`(사람별 "만난 코치 수")가 **적은 사람부터** = 아무 코치도 못 만난 사람 최우선.
  - 동률이면 sortQueue 순서(경기수·휴식).
- `buildAceMatch(ace, three)`: 코치+3명, 종목색은 성비로, 코치는 최약체와 한 팀(살짝 보정).
- 커버리지: 코치별로 "만난 사람 N/총원" 게이지를 코트 카드에 표시(경기 시작 버튼 위).
- 코치 지정/변경/해제: 코트 [편집]에서. 같은 코치를 다른 코트로 옮기면 기존 코트 자동 해제.

### 4.4 파트너(고정 2인 팀) — `recommendMatchPaired`
- 대회 연습 등으로 "둘이 같이 쳐주세요" 요청 → 두 사람을 **한 팀 고정 유닛(2슬롯)**으로 묶음.
- 종목 자동: 남남=남복, 여여=여복, 남여=혼복. 그 종목 경기에서만 같이 들어감.
- 토글 **`strict`**: `같이만`(=strict, 종목 안 맞으면 둘 다 대기·경기수 적음) / `따로도 OK`(=best-effort, 같이 우선·안 되면 각자 일반 큐).
- **best-effort 우선순위**: 쌍이 평균보다 앞서면 양보(`avg+0.5` 가드) → 다른 사람 경기수에 영향 거의 없음(시뮬: 2쌍이면 나머지 공정성 무손상).
- 상대는 **비-파트너**에서 뽑아 다른 쌍을 깨지 않음.
- **UI**: 만들기=출석 화면 "파트너 묶기"(2명 탭 + strict 토글), 표시·해제=대기열 "파트너 N쌍" 칩.
- **모임장 안내 멘트**: 2명 선택 시 하단에 "📢 두 분께 안내" 멘트를 종목·strict에 맞춰 **자동 생성** → 모임장이 그대로 읽어줌. 예) 따로도 OK = "혼복 경기에선 항상 같은 팀, 남복/여복 경기에선 각자 따로 들어갈 수 있고 경기 수는 일반보다 조금 적을 수 있어요." / 같이만 = "…남복/여복 경기가 돌 땐 두 분은 대기해서 경기 수가 적을 수 있어요."
- **정책**: "무조건 같이"는 약속하지 않음 → 신청 종목에선 항상 같이, 다른 종목에선 따로 가능, 경기수 조금 적을 수 있음을 **사전 안내**(기대관리).
- **한계**: 개수보다 **성비**(여여·혼복 쌍 많으면 여성 풀 고갈). 2쌍은 문제없음.

### 4.5 운영 모드
- **자동**: 코트가 비면 다음 경기를 자동 추천·투입.
- **수동**: 대기열에서 4명 골라 [경기 만들기] → 빈 코트면 바로, 차 있으면 예약 경기로 쌓였다 투입. 빈 코트는 [직접 채우기].

---

## 5. 시뮬레이션 결론 (핵심 수치)

실제 매칭 엔진으로 51명/3시간 시뮬레이션. 상세: `match_ui_demo/report-*.html`.

- **알고리즘 견고성**: 일반 운영에서 비코치 참가자 경기수는 **1~2게임 차이**로 균등(편차 0.2~0.5).
- **코치 고정 영향**: 코치를 큐·카운트에서 빼면 나머지 공정성은 **사실상 무영향**.
- **코치 커버리지(게임시간 종속, 코트수 무관)**:
  - 15분 게임 → 코치당 ~37/50명(~75%)
  - **10분 게임 → 전원(100%)** (코치 ~19게임 × 3자리 = ~57 ≥ 50, 여유분이 "타이밍 충돌(만날 사람이 경기 중)"을 흡수)
  - 경계 ≈ 10.6분(코치 17게임 필요). 인원 ↑면 한계도 ↑(코치 2면/세션연장 필요).
- **코치 2명 + 공동 우선**: "최소 한 코치는 꼭" 만남 → 15분에도 **100%**. (대신 "두 코치 다 만남"은 줄어드는 트레이드오프)

> 시뮬은 8회 평균의 모델 결과. 실제 운영 노이즈(게임시간 들쭉날쭉·종료 누락·중도 이탈) 감안하면 "100% 보장"보다 "**사실상 전원**"이 정직한 표현.

---

## 6. 구현 현황

### 6.1 웹 통합 (Django, 본 레포)
| 파일 | 내용 | 상태 |
|---|---|---|
| `band/urls.py` | `schedule_match`, `schedule_console`, `schedule_checkin` 라우트 | ✅ |
| `band/views.py` | `schedule_match`(풀 매핑·요약·누락), `schedule_console`(콘솔 주입·출석 반영), `schedule_checkin`(자가 출석 토글) | ✅ |
| `band/models.py` | `BandScheduleApplication.checked_in_at` (마이그 0025) | ✅ |
| `templates/band/schedule_detail.html` | 참가자 목록 위 [번개 시작](모임장) + 하단 자가 체크인 UI·확인 모달·프로필 게이팅 | ✅ |
| `templates/band/schedule_match.html` | 진입 화면(요약·명단·그레이스케일 급수 램프·반응형·sticky CTA) | ✅ |
| `templates/band/schedule_match.html` | 진입 화면(명단·누락 경고·출석 시작) | ✅ |
| `templates/band/schedule_console.html` | 풀스크린 콘솔 + 참가자 주입 | ✅ |
| `static/match_console/*` | 콘솔 정적 자산(core/ui/screens/app jsx 등) | ✅ |

### 6.2 콘솔(대진 화면) — `match_ui_demo/` (디자인·로직 원본, 미커밋) / 운영용 `static/match_console/`
- React+Babel 단일 페이지 프로토타입(localhost:5500). 코트/대기열/출석/카운트/코트설정/도움말/코치 고정 전부 구현.
- `window.__BM_PARTICIPANTS__` 주입(=embedded) 시 실제 데이터로, 없으면 데모 51명으로 동작.
- **embedded(운영) 렌더**: 데모 크롬(DemoNav: 프로토타입 배지·디바이스/테마 토글·초기화)·디바이스 베젤 **없이**, **태블릿 1194×834 고정 캔버스 + 화면 맞춰 스케일**한 풀스크린. → **localhost:5500 데모 디자인을 태블릿에 그대로 사용**(분기: `embedded` 플래그, `<DeviceFrame bare>`). 화면 전환(운영↔출석↔카운트)은 ControlBar 버튼/← 운영 화면으로.

### 6.3 서버 매칭 백본 (DRF API + Python 엔진) — **앱 연동의 진짜 구현**
| 파일 | 내용 | 상태 |
|---|---|---|
| `band/match_models.py` | MatchSession·SessionParticipant·Court·Match·MatchPlayer + **Pair·PartnerRequest** + **Court.coach** | ✅ |
| `band/matchmaking/` | engine(recommend_next_game·**recommend_with_pairs**·**pick_ace_three/build_ace_match**)·cost·scoring·selection·types(**PairUnit**) | ✅ |
| `band/match_state.py` | build_pool·build_pairstats·**build_pairs**·**build_met_count**·build_player | ✅ |
| `band/api/match_views.py` | 운영자 API(세션·코트·매치) + **참가자 본인 API** + **파트너 신청/승인** + **코치 고정** | ✅ |
| `band/api/match_serializers.py` | serialize_session(코치 커버리지·파트너 포함)·serialize_my_status·serialize_pair 등 | ✅ |
| 테스트 | `band/tests/test_engine.py`·`test_match_api.py` 등 (84+ tests) | ✅ |
| 마이그레이션 | 0026(Pair·PartnerRequest)·0027(Court.coach) — **prod 수동 적용 필요** | ⚠️ |

### 6.4 미구현 / TODO
- [ ] 급수·성별 누락자 **신청/체크인 단계 거부** 처리(현재는 세션 생성 시 base_level 폴백=왕초심1).
- [ ] 출석/시작시간 **게이팅**(집에서 미리 체크인 방지).
- [ ] `static/match_console`(그림)를 이 API에 실제 연결할지 결정 — 현재는 미연동 시안. 운영도 앱에서 할 거면 콘솔 JS는 폐기 후보.
- [x] ~~푸시 알림 연동(다음 경기/파트너 신청·승인 → FCM)~~ → 9장.
- [ ] 코치 커버리지/게임시간 등 운영 설정의 서버 저장(코트 이름 등).

---

## 7. 앱(모바일) 적용 시 고려
- 진입 버튼: 앱은 **고정 하단바**가 있으니 거기서 "대진 운영" 진입(웹처럼 목록 위에 끼울 필요 X).
- 운영석(호스트)은 가로(태블릿) 기준 설계 — 앱에서도 운영석은 태블릿/가로 권장.
- 참가자는 세로(폰)에서 **내 상태 화면**만 폴링(8.2). 데이터 매핑·알고리즘은 서버가 전담하므로 앱은 표시·액션만.
- 급수·성별 필수 규칙은 신청 단계에서 강제(누락자 못 들어오게)하면 누락 처리가 단순해짐.

---

## 8. 서버 API (앱 백본)

- **베이스**: `/api/bands/...` (namespace `band_api`, `band/api/urls.py`).
- **인증**: JWT Bearer (`Authorization: Bearer <access>`). 발급: `POST /accounts/api/token/`.
- **권한**: 운영자 액션 = 밴드 owner/admin(`_is_operator`). 참가자 액션 = 그 세션의 SessionParticipant 본인.
- **실시간**: 폴링. 참가자 화면은 8.2 `me`를 2~3초 간격, 호스트는 8.1 `state`를 폴링.
- `<sid>` = MatchSession id, `<schedule_id>` = BandSchedule id, `<pid>` = SessionParticipant id.

### 8.1 운영자 — 세션·코트·매치
| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `match/schedules/<schedule_id>/start/` | 세션 시작. body: `court_count`, `discipline_mode`, `preset`. 승인 참가자를 스냅샷(급수·성별). **`checked_in_at` 있는 사람은 출석(present)으로 시작.** → 201 세션 전체 |
| GET | `match/<sid>/` | 세션 전체 상태(참가자·코트·큐·**pairs**·**partner_requests**·코트별 **coach+coverage**) |
| POST | `match/<sid>/mode/` · `match/<sid>/preset/` | 종목 모드 / 성향 변경 |
| POST | `match/<sid>/participants/<pid>/attendance/` | 운영자가 출석 변경. body: `attendance`(not_present\|present\|left) |
| POST | `match/<sid>/courts/<i>/fill/` | 빈 코트 채우기(자동 추천·**파트너/코치 반영**). body 선택: `discipline`(강제). 응답: `match` / `needs_choice`+`options` / 인원부족 |
| POST | `match/<sid>/courts/<i>/end/` | 진행 경기 종료(카운트++·휴식 갱신) + 자동 리필 |
| PATCH | `match/<sid>/matches/<mid>/` | 경기 수정. body: `swap:[out_pid,in_pid]` / `discipline` |
| POST | `match/<sid>/end/` | 세션 종료 |

### 8.2 참가자 본인 (앱) — `me`
| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `match/schedules/<schedule_id>/me/` | **일정만 알아도** 내 상태. 세션 없으면 `session_id:null`+`approved`. 앱 진입 시 첫 호출 |
| GET | `match/<sid>/me/` | 내 라이브 상태(폴링): `attendance`·`games`·`playing`·`current_match`(court_index·my_team·**is_coach_court**)·`queue_position`·`queue_total`·**`up_next`**(다음 경기 후보 알림용) |
| POST | `match/<sid>/me/checkin/` | 본인 출석/퇴장. body: `action`(in\|out). **웹 `checked_in_at`과 양방향 동기화.** 세션 종료 시 409 |

### 8.3 파트너 (고정 2인 팀)
| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `match/<sid>/partner-requests/create/` | 참가자→참가자 신청. body: `to_participant_id`, `strict`(같이만 여부) |
| GET | `match/<sid>/partner-requests/` | 대기 신청. 운영자=전체, 참가자=본인 관련만(`! 배지`용) |
| POST | `match/<sid>/partner-requests/<rid>/approve/` | 운영자 승인 → **Pair 생성**(둘 중 누구든 이미 쌍이면 409) |
| POST | `match/<sid>/partner-requests/<rid>/reject/` | 운영자 거절 |
| GET·POST | `match/<sid>/pairs/` | GET=쌍 목록. POST=운영자 직접 묶기(body: `p1_id`,`p2_id`,`strict`) |
| DELETE | `match/<sid>/pairs/<pid>/` | 운영자 쌍 해제 |

> 엔진 규칙(4.4와 동일): 종목 자동(남남=남복·여여=여복·남여=혼복). `strict`=같이만(종목 안 맞으면 대기), 아니면 best-effort(평균보다 앞서면 양보·각자 일반 큐 참여). 상대는 비-파트너 풀에서.

### 8.4 코치(자강) 고정
| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `match/<sid>/courts/<i>/coach/` | 코트에 코치 지정/해제. body: `participant_id`(없으면 해제). 같은 코치는 한 코트만(다른 코트 자동 해제) |

> 동작(4.3과 동일): 코치는 **일반 큐·공정성에서 제외**, 본인 코트에 고정. fill 시 `pick_ace_three`(못 만난 코치 적은 사람 우선)로 3명 선발 + `build_ace_match`(코치는 약체와 한 팀). `state`의 코트별 `coach.coverage = {met,total}`로 커버리지 표시.

---

## 9. 푸시 알림 (FCM)

기존 알림 인프라(`notifications/`) 재사용 — **`Notification` 레코드를 만들면 `post_save` 시그널이 FCM 자동 발송**(`notifications/signals.py`의 `send_fcm_on_notification`). 디바이스 토큰은 `DeviceToken`(유저:N), 등록 `POST /api/notifications/devices/register/` · 해제 `POST /api/notifications/devices/unregister/`.

대진 이벤트별 알림(타입은 `Notification.Type`에 추가, 마이그 0008):

| 이벤트 | 타입 | 수신자 | 발생 위치 |
|---|---|---|---|
| **다음 경기 배정** (코트에 경기 생성) | `match_next_game` | 그 경기 4명 (**코트 코치 제외**) | `band/api/match_views._create_match` → `_notify_next_game` (선수 다 채운 뒤 직접 생성 — Match `post_save`는 선수 추가 전이라 시그널 부적합) |
| **파트너 신청 받음** | `partner_request` | 신청 받은 사람 | `notifications/signals.notify_on_partner_request` (PartnerRequest `post_save` created) |
| **파트너 확정**(승인) | `partner_approved` | 양쪽 2명 | 〃 (status=APPROVED) |

- 푸시 `data`에 `type`·`notification_id`·`related_band_schedule_id` 등 실려 앱 라우팅에 사용(앱은 `related_band_schedule_id`로 해당 번개 화면 진입 → 8.2 `me` 폴링).
- 전송은 **동기**(요청 중). Firebase 키 없으면 silent no-op(개발/테스트 안전). prod는 `FIREBASE_CREDENTIALS_PATH` 필요.
- '다음 경기' 외 '곧 입장(up_next)' 같은 소프트 알림은 앱이 8.2 `up_next` 폴링으로 처리(별도 푸시 없음).
