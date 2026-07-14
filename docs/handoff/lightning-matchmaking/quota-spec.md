# 번개 정원(급수·성별) 기능 — 앱/서버 구현 스펙

> 번개(일정) 생성 시 **급수·성별·인원을 제한**해서 모집하는 기능.
> 대기(Waitlist)와 함께 동작 → [waitlist-spec.md](./waitlist-spec.md).
> 구현 상태: **웹 + REST API 완료**. 마이그레이션 `0033`·`0034`·`0035`.

---

## 0. 모드 정리 (핵심)

`use_level_quota`(급수로 나눔?)와 `quota_by_gender`(성별로 나눔?)는 **독립(직교)**. 조합 4가지:

| use_level_quota | quota_by_gender | 모드 | 정원 칸(cell) | 정원 저장 필드 |
|:-:|:-:|---|---|---|
| false | false | 제한 없음 | 전체 총원 | `max_participants` |
| true | false | 급수별 | 급수 | `level_quota {lv:{total}}` |
| **false** | **true** | **성별 전용** | **성별** | **`gender_quota {male,female}`** |
| true | true | 급수+성별 | 급수×성별 | `level_quota {lv:{male,female}}` |

- 급수 코드: `master`(자강) `s` `a` `b` `c` `d` `beginner`(초심)
- 성별 코드: `male` `female`
- **칸에 없는 급수/성별 = 모집 안 함** (그 프로필 유저는 신청 불가).

---

## 1. 데이터 모델 (BandSchedule)

| 필드 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `use_level_quota` | bool | `false` | 급수별 정원 사용 |
| `quota_by_gender` | bool | `false` | 성별로 나눔 (use_level_quota와 **독립**) |
| `level_quota` | JSON | `{}` | 급수 모드용 |
| `gender_quota` | JSON | `{}` | 성별 전용 모드용 (신규) |

**level_quota** (급수 모드) — 성별 나눔 ON: `{"a":{"male":7,"female":3}}` / OFF: `{"a":{"total":10}}`
**gender_quota** (성별 전용) — `{"male":10,"female":10}` · 키 없는 성별은 모집 안 함 (예: `{"male":10}` = 남자만)

`max_participants`는 각 칸 합계로 자동 세팅.

---

## 2. 신청 판정 규칙 (apply) — 4모드 통합

신청자 프로필 급수(`badminton_level`)·성별(`gender`) 기준. 칸을 정하고 그 칸 정원 vs 승인자 수 비교, 꽉 차면 `waiting`(대기 5명까지, 초과 `400`):

1. **제한 없음** → 칸 = 전체(`max_participants`).
2. **급수별** → 칸 = 급수. 급수 키 없으면 `400 "이 모임에서 모집하지 않는 급수예요."`
3. **성별 전용** (신규) → 칸 = 성별.
   - 신청자 `gender`가 없으면 → `400 "성별 정보가 없어요. 프로필 성별을 확인하세요."`
   - `gender_quota`에 그 성별 키 없으면 → `400 "이 모임에서 모집하지 않는 성별이에요."`
   - **급수는 판정 안 함** (모든 급수 허용, 급수 미입력자도 신청 가능).
4. **급수+성별** → 칸 = 급수×성별.

> 승인(`approve`)·승격(`promote`) 시에도 동일하게 **신청자 칸 기준**으로 자리 확인.

---

## 3. 생성/수정 화면 UI (웹 = 앱 동일 규격)

`templates/band/create.html` 기준. **두 토글 독립**:

1. **[급수별 정원 받기]** (`use_level_quota`)
2. **[성별로 나눠 받기]** (`quota_by_gender`) — 이제 급수 토글과 무관하게 단독 ON 가능

입력 영역은 조합에 따라 전환:
- 급수 ON → 급수 리스트(체크박스 + 정원). 성별도 ON이면 급수마다 `남/여`, 아니면 `정원`.
- 급수 OFF & 성별 ON → **남/여 2줄 입력** (한 성별만 받으려면 다른 쪽 0/빈칸).
- 둘 다 OFF → 입력 없음(총원만).

하단 **총 정원** 자동 합산. 전송 시 `level_quota_json` / `gender_quota_json` 조립.

---

## 4. 상세(detail) 응답

`GET /api/bands/<bid>/schedules/<sid>/`:
```json
{
  "use_level_quota": false,
  "quota_by_gender": true,
  "level_quota": {},
  "gender_quota": { "male": 10, "female": 10 },
  "quota_status": null,
  "gender_status": {
    "male_approved": 4, "male_quota": 10,
    "female_approved": 6, "female_quota": 10
  },
  "is_full": false
}
```
- **급수 모드** → `quota_status` 채움 (배열), `gender_status=null`.
  - 배열 항목: `{level,label,by_gender, (male_approved/male_quota/female_approved/female_quota) 또는 (total_approved/total_quota)}`
- **성별 전용** → `gender_status` 채움, `quota_status=null`.
- **is_full**: 모든 칸 마감 시 true (버튼 분기용).

---

## 5. 생성/수정 API

`POST .../schedules/create/` · `.../update/` body:
```json
{
  "use_level_quota": false,
  "quota_by_gender": true,
  "gender_quota": { "male": 10, "female": 10 }
}
```
- 검증: `quota_by_gender=true && use_level_quota=false`인데 `gender_quota` 비면 → `400 "성별 정원을 입력하세요."`
- `use_level_quota=true`면 `gender_quota` 무시(급수 모드 우선).

---

## 6. 하위호환
- 기존 번개(성별 나눔이 급수 모드 하위였던 것)는 4모드 표의 1·2·4번으로 그대로 동작.
- 신규 3번(성별 전용) 브랜치는 기존 데이터와 안 겹침 → 안전.
- `gender_quota` 기본 `{}` → 기존 응답/판정 영향 없음.

---

## 7. 앱 UI (Flutter)
- 생성/수정: **두 독립 토글** + 조합별 입력 전환(§3). `level_quota`/`gender_quota` 조립·파싱.
- 상세(참가자): `quota_status`(급수) 또는 `gender_status`(성별) 현황 카드. `is_full`·`waiting_*`로 버튼 분기.
- 상세(모임장): 현황 + 대기 명단(승격) + 참가자 취소(kick) — [waitlist-spec.md](./waitlist-spec.md).

## 8. 검증 (2026-07-15)
성별 전용 모드 전 시나리오 통과: 남/여 칸 마감→대기, 성별정보 없음 차단, 미모집 성별 차단, gender_status·is_full 정확, 급수 모드 회귀 없음.
