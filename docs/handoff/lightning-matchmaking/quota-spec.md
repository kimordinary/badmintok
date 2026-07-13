# 번개 급수별 정원(Level Quota) 기능 — 앱/서버 구현 스펙

> 번개(일정) 생성 시 **급수·성별·인원을 제한**해서 모집하는 기능.
> 대기(Waitlist) 기능과 함께 동작한다 → [waitlist-spec.md](./waitlist-spec.md) 참조.
> 구현 상태: **웹 + REST API 완료 (2026-07-14)**.

---

## 0. 용어
- **정원제**: `use_level_quota=true`. 켜면 급수별로 정원을 정해 모집.
- **성별 나눔**: `quota_by_gender`. 정원을 급수 안에서 남/여로 쪼갤지 여부.
- **칸(cell)**: 정원 판정 단위. 성별 나눔 ON이면 `급수×성별`, OFF면 `급수` 하나.
- 급수 코드: `master`(자강) `s` `a` `b` `c` `d` `beginner`(초심)
- 성별 코드: `male` `female`

---

## 1. 데이터 모델 (BandSchedule)

| 필드 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `use_level_quota` | bool | `false` | 급수별 정원 사용 |
| `quota_by_gender` | bool | `false` | 정원을 급수 안에서 남/여로 나눌지 |
| `level_quota` | JSON | `{}` | 급수별 정원 값 (아래 형식) |

마이그레이션: `0033`(level_quota 등), `0034`(quota_by_gender).

### level_quota JSON 형식
**성별 나눔 ON** (`quota_by_gender=true`):
```json
{ "a": {"male": 7, "female": 3}, "b": {"male": 6, "female": 4} }
```
**성별 나눔 OFF** (`quota_by_gender=false`) — 성별 무관 총원:
```json
{ "a": {"total": 10}, "b": {"total": 8} }
```
- **키에 없는 급수 = 모집 안 함** (그 급수 프로필 유저는 신청 자체 불가).
- 최대 인원(`max_participants`)은 각 칸 합계로 자동 세팅(웹 UI 기준).

---

## 2. 신청 판정 규칙 (apply)

신청자의 프로필 급수(`badminton_level`)·성별(`gender`) 기준:

1. `use_level_quota=false` → 기존 총원(`max_participants`) 판정.
2. `use_level_quota=true`:
   - 신청자 급수가 `level_quota` 키에 **없으면** → `400` `"이 모임에서 모집하지 않는 급수예요."`
   - **성별 나눔 ON**: 해당 `급수·성별` 칸의 정원 vs 승인자 수 비교.
   - **성별 나눔 OFF**: 해당 `급수`의 `total` 정원 vs 승인자 수(성별 무관) 비교.
   - 칸이 **꽉 참** → `waiting`(대기) 등록 (대기 5명까지, 초과 시 `400`).
   - 자리 있음 → `approved`(자동승인) 또는 `pending`(승인제).

> 승인(`approve`)·승격(`promote`) 시에도 동일하게 **신청자 급수 칸 기준**으로 자리 확인.

---

## 3. 번개 생성/수정 화면 UI (웹 = 앱 동일 규격)

`templates/band/create.html` 기준. 앱도 동일 구성으로 구현.

1. **[급수별 정원 받기]** 토글 (`use_level_quota`)
   - OFF → 기존 "최대 참가 인원" 하나만.
   - ON → 아래 정원 박스 노출. 최대 인원은 합계로 자동 계산(읽기전용).
2. 박스 안 **[성별로 나눠 받기]** 서브 토글 (`quota_by_gender`)
   - **ON** → 급수마다 `남 / 여` 2칸 입력.
   - **OFF** → 급수마다 `정원` 1칸 입력 (성별 무관).
3. 급수 목록(자강·S·A·B·C·D·초심) 각 행: **체크박스로 모집 여부** + 정원 입력.
   - 체크 안 한 급수 = `level_quota`에 미포함 = 모집 안 함.
4. 하단 **총 정원** 자동 합산 표시.

**전송 형식**: 위 규칙대로 `level_quota` JSON을 만들어 함께 전송.

---

## 4. 급수별 현황 (detail 응답 `quota_status`)

`GET /api/bands/<bid>/schedules/<sid>/` 응답의 `quota_status` (정원제 아니면 `null`).
모집 급수만, 급수 순서(자강→초심)로 배열:

**성별 나눔 ON**:
```json
[
  { "level": "a", "label": "A", "by_gender": true,
    "male_approved": 5, "male_quota": 7,
    "female_approved": 2, "female_quota": 3 }
]
```
**성별 나눔 OFF**:
```json
[
  { "level": "a", "label": "A", "by_gender": false,
    "total_approved": 6, "total_quota": 10 }
]
```
- 표시 예: ON → `A  남 5/7 · 여 2/3`, OFF → `A  6/10명`.

---

## 5. 서버 API — ✅ 구현 완료

| 대상 | 경로 | 정원 관련 |
|---|---|---|
| 생성 | `POST /api/bands/<bid>/schedules/create/` | body에 `use_level_quota`·`quota_by_gender`·`level_quota` 저장 |
| 수정 | `POST /api/bands/<bid>/schedules/<sid>/update/` (또는 detail PATCH) | 동일 필드 부분 수정 |
| 상세 | `GET  /api/bands/<bid>/schedules/<sid>/` | 위 3필드 + `quota_status` 반환 |
| 신청 | `POST /api/bands/<bid>/schedules/<sid>/apply/` | §2 판정 |
| 승인/승격 | `.../applications/<aid>/approve/`·`/promote/` | 급수 칸 기준 자리 확인 |

- 생성/수정 body 예:
```json
{
  "title": "토요 번개", "start_datetime": "2026-07-18T10:00:00",
  "use_level_quota": true, "quota_by_gender": false,
  "level_quota": { "a": {"total": 10}, "b": {"total": 8} }
}
```

---

## 6. 앱 UI 명세 (Flutter)

### 6.1 번개 생성/수정 화면
- §3 규격 그대로: 정원 토글 → 성별 나눔 서브토글 → 급수별(체크+정원) → 총합.
- 성별 나눔 ON/OFF 전환 시 입력 칸을 `남/여` ↔ `정원 하나`로 스위치.
- 저장 시 `level_quota` JSON 조립(체크된 급수만).

### 6.2 번개 상세 (참가자)
- `quota_status`로 **급수별 현황 카드** 표시 (참가자 섹션 상단).
- 버튼 분기는 [waitlist-spec.md §5.1] + `is_full`(모든 칸 마감) 참고.
- 본인 급수 칸이 차면 신청 시 자동 `waiting`.

### 6.3 번개 상세 (모임장)
- 급수별 현황 + 대기 명단(승격) + 참가자 취소(kick). [waitlist-spec.md §5.2]

---

## 7. 앱 전달 체크리스트
- [ ] 생성/수정 화면에 정원 토글·성별 나눔·급수별 입력 UI
- [ ] `level_quota` JSON 조립/파싱 (ON/OFF 두 형식)
- [ ] 상세 화면 `quota_status` 현황 카드
- [ ] apply 에러 메시지 처리 (미모집 급수/대기 마감)
- [ ] `is_full`·`waiting_*`로 버튼 분기 (waitlist-spec 연동)
