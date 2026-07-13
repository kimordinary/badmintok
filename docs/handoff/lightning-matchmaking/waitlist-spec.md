# 번개 대기하기(Waitlist) 기능 — 앱/서버 구현 스펙

> 정원 마감 시 "대기 신청"을 받고, 모임장이 자리를 열어 수동 승격하는 기능.
> **이 문서는 앱팀이 서버 API와 1:1로 매칭해 구현할 수 있도록 작성.** 추측 없이 이 문서대로 구현.
> 작성 2026-07-14. 서버 구현과 함께 갱신.

---

## 0. 용어
- **참가(승인)** = `approved` — 정원 안에 든 확정 참가자
- **대기** = `waiting` — 정원 초과로 대기 등록한 사람 (신규 상태)
- **승격** = 모임장이 대기자를 `waiting → approved`로 올리는 것 (수동, 자동 아님)
- **정원** = `max_participants` (번개 일정 필드, 기존)
- **대기 정원** = **5명 고정** (상수 `WAITLIST_CAPACITY = 5`)

---

## 1. 데이터 모델

### BandScheduleApplication.status (기존 + 신규)
| 값 | 뜻 | 비고 |
|---|---|---|
| `pending` | 승인 대기(모임장 승인 전) | 기존 |
| `approved` | 참가 확정 | 기존. 정원에 포함 |
| `rejected` | 거부됨 | 기존 |
| `cancelled` | 취소됨 | 기존 |
| **`waiting`** | **정원초과 대기** | **신규 추가** |

- `applied_at` (기존): 신청 시각 → **대기 순번의 기준** (오래된 순 = 대기 1번)
- 마이그레이션: `status` choices에 `waiting` 추가 (AlterField, 데이터 영향 없음). **prod에서 `migrate` 필요.**

### 정원 계산
- `current_participants` = `status='approved'` 인원 수 (기존)
- `waiting_count` = `status='waiting'` 인원 수 (신규)
- **정원 마감** = `max_participants and current_participants >= max_participants`
- **대기 마감** = `waiting_count >= 5`

---

## 2. 상태 전이 규칙

```
[신청 버튼 클릭]
   ├─ 정원 미달 → pending (기존 승인 흐름) 또는 즉시 approved (밴드 정책)
   └─ 정원 마감 & 대기 < 5 → waiting  ← 신규
      정원 마감 & 대기 = 5 → 거부(“대기 마감”)

[모임장 승격]  waiting → approved   (자리가 있을 때만; 아무 대기자나 선택 가능)

[참가자 취소(본인)]        approved/waiting → cancelled
[모임장 참석 취소]         approved → cancelled  ← 신규 (자리 1개 생김)
```

- **승격 조건**: `current_participants < max_participants` 일 때만 승격 허용. (자리 없으면 400)
- **승격 대상**: 대기자 **아무나** 모임장이 선택 (맨 앞 강제 아님).

### 재신청 통일 규칙 (중요)
- `cancelled` / `rejected` 상태는 **"신청 안 한 사람"과 완전히 동일 취급**한다.
  - 정원 미달 → 다시 신청(pending/approved)
  - 정원 마감 & 대기<5 → **waiting** (재신청도 대기로 감)
- UI에서 **"다시 신청하기" 별도 문구/버튼을 두지 않는다.** 처음 상태와 똑같이 `참가 신청하기` / `대기하기` 버튼만 노출.
- (현재 버그) schedule_apply가 정원 마감 시 재신청도 막고, schedule_detail이 cancelled를 "다시 신청하기"로 따로 표시 → **이 특수 처리를 제거**하고 위 규칙으로 통일.

---

## 3. 서버 API (앱 ↔ 서버) — ✅ 구현 완료

> 베이스 URL: `/api/bands/`  ·  인증: JWT  ·  아래 경로는 전부 이 prefix 뒤에 붙음.

### 3.1 참가자 본인 — 신청/대기/취소
| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/bands/<bid>/schedules/<sid>/apply/` | 참가 신청. **정원 마감 시 자동 `waiting` 생성**(막지 않음). 재신청(rejected/cancelled)도 신규와 동일 취급(applied_at 갱신) |
| POST | `/api/bands/<bid>/schedules/<sid>/cancel/` | 본인 신청/대기 취소 → `cancelled` |
| GET | `/api/bands/match/schedules/<sid>/me/` | 내 상태 (아래 응답) |

**apply 요청 body**: `{ "notes": "" }` (선택)

**apply 응답 `201`**: `{ "message": str, "status": "approved" | "pending" | "waiting" }`
- `approved`: 자리 있음 + 자동승인(requires_approval=false)
- `pending`: 자리 있음 + 승인제
- `waiting`: 정원(또는 급수 칸) 마감 → 대기 등록

**apply 에러 `400`** (`{ "error": str }`):
- `이미 신청하셨습니다.`
- `이 모임에서 모집하지 않는 급수예요. (프로필 급수를 확인하세요)` — 정원제에서 모집 안 한 급수
- `참가·대기 인원이 모두 마감되었습니다.` — 대기 정원(5명)까지 참
- `신청 마감일이 지났습니다.` / `모집이 마감되었습니다.`

**me 응답 `200`** (대기 관련 핵심 필드):
```json
{
  "application_status": "approved" | "pending" | "waiting" | null,
  "waiting_position": 3,      // 대기면 1-base 순번, 아니면 null
  "waiting_total": 5,         // 총 대기 인원
  "approved": true
  // 세션(운영중)이 있으면 대진 관련 필드가 추가로 병합됨
}
```

### 3.2 모임장 — 대기/참가 관리
| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `.../schedules/<sid>/applications/<aid>/promote/` | 대기자 승격 `waiting→approved`. **자리 없으면 400**. 정원제면 신청자 급수 칸 기준 |
| POST | `.../schedules/<sid>/applications/<aid>/kick/` | **참석 취소** `approved→cancelled`. 자리 1개 생김 |
| POST | `.../schedules/<sid>/applications/<aid>/approve/` | pending 승인. 정원제면 칸 확인 |

- 응답: `{ "message": str }` / 에러 `{ "error": str }` (`400`/`403`)
- 권한: 모임 owner/admin 또는 사이트 관리자.
- **대기 명단은 별도 엔드포인트 없음** → §3.3 `detail` 응답의 `applications`(관리자 조회 시 waiting 포함, 신청순) + `waiting_count` 사용.

### 3.3 일정 상세 (detail) — 대기·정원 필드
`GET /api/bands/<bid>/schedules/<sid>/` 응답에 추가된 필드:
```json
{
  "is_full": true,                 // 정원제면 모든 칸 마감 시 true (버튼 분기용)
  "waiting_count": 2,
  "waitlist_capacity": 5,
  "my_waiting_position": null,     // 본인이 대기면 순번, 아니면 null
  "use_level_quota": true,
  "quota_by_gender": false,
  "level_quota": { "a": {"total": 10}, "b": {"total": 8} },
  "quota_status": [ /* 급수별 현황 — quota-spec.md §4 참조 */ ],
  "applications": [
    { "id": 1, "user": {…}, "status": "approved", "status_display": "참가",
      "notes": "", "applied_at": "2026-07-14T…", "reviewed_at": "2026-07-14T…" }
    // 관리자 조회 시 status=pending/waiting 항목도 신청순으로 포함
  ]
}
```
- **일반 사용자**: `applications`에 `approved`만. 본인 대기 상태는 `me` 또는 `user_application` 사용.
- **관리자**: `approved`+`pending`+`waiting` (신청순 applied_at ASC), rejected/cancelled 제외.

### 3.4 쪽지/알림
- `POST /api/bands/<bid>/schedules/<sid>/notices/`
- body: `{ "message": str(1~500), "recipient_user_id": int | null }`
- **동작**: `Notification.objects.create()` → post_save 시그널로 **FCM 푸시 + 앱 알림함 저장** (둘 다).
- **수신 대상**: 개별 발송(`recipient_user_id` 지정)은 `approved`+`waiting` 허용 → 대기자에게 "자리 났어요" 발송 가능. 전체 발송(`null`)은 approved만.
- 응답 `201`: `{ "message": "알림이 발송되었습니다.", "recipient_count": N }`

---

## 4. 웹 UI (templates/band/schedule_detail.html)

### 4.1 참가/대기 버튼 (본인 시점)
- 정원 미달 → **"참가 신청하기"** (기존)
- 정원 마감 & 대기<5 → **"대기하기 (현재 N/5)"**
- 대기 5명 → **"대기 마감"** (비활성)
- 내가 대기 중 → **"대기 X번째예요"** 배지 + 취소 버튼

### 4.2 모임장 — 대기 명단
- 참가자 목록 아래 **"대기 N명"** 섹션 (신청순)
- 각 대기자 행: 이름·급수·성별·"대기 X번" + **[승격]** 버튼(자리 있을 때 활성)

### 4.3 이름 클릭 모달 (participantNoteModal) — 참가 취소 추가
- 기존: 이름 / 신청 일시 / 신청 메모 / "이 참가자에게 알림 보내기"(텍스트+발송)
- **추가**: 모임장이 볼 때 하단에 **[참가 취소]** 버튼 (approved 참가자 대상) → `kick` API 호출 → 자리 1개 생김

---

## 5. 앱 UI 명세 (Flutter)

### 5.1 참가자 화면 (번개 상세)
- **버튼 상태** (§4.1과 동일): 신청하기 / 대기하기(N/5) / 대기마감 / 대기중(X번째)
- **대기 순번 표시**: `me` API의 `waiting_position` / `waiting_total` → "대기 3번째 (총 5명)"
- 대기 취소 버튼

### 5.2 모임장 화면 (번개 상세)
- **대기 명단**: `waitlist` API → 신청순 리스트, 각 항목에 [승격] 버튼
- **참가자 목록**: 이름 탭 → 모달(메모·알림·**참가 취소**)
- 자리 나면 → 대기자에게 **쪽지 발송**("대기 인원이 생겼어요") = notice_send API

### 5.3 알림 수신 (참가자)
- 모임장이 보낸 쪽지 → **FCM 푸시** + **앱 알림함**에 표시 (기존 Notification 흐름)

---

## 6. 구현 체크리스트 (서버) — ✅ 완료

**웹(Django 템플릿) + REST API 양쪽 구현 완료.**

- [x] `BandScheduleApplication.Status`에 `WAITING = "waiting"` 추가 + 마이그레이션 `0032`
- [x] `schedule_apply` (웹) / `band_schedule_apply` (API): 정원 마감 시 `waiting` 생성 (대기 5명이면 거부)
- [x] `me` 응답에 `application_status`·`waiting_position`·`waiting_total` (`my_status_by_schedule`)
- [x] 대기 명단: 별도 API 대신 `detail` 응답 `applications`(관리자 waiting 포함) + `waiting_count`
- [x] `promote` API (`band_schedule_application_promote`) — 자리 있을 때만, 정원제 칸 기준
- [x] `kick` API (`band_schedule_application_kick`) — 모임장 참석 취소
- [x] `notice_send` 수신 대상에 `waiting` 포함 (개별 발송)
- [x] `schedule_detail.html`: 버튼 분기 / 대기 명단 / 이름 모달 [참가 취소]

> **검증**: apply→approved/waiting, 미모집 급수 차단, promote 자리없음 거부, kick→자리생성→promote→approved 전 시나리오 통과 (2026-07-14).

## 7. 앱 전달 체크리스트
- [ ] 버튼 4상태 + 대기 순번 표시
- [ ] 모임장 대기 명단 + 승격
- [ ] 이름 모달 참가 취소
- [ ] 쪽지 발송(대기자 대상) + 알림 수신
