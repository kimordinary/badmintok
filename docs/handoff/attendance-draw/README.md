# 출석 화면 — 추첨(Lottery) 핸드오프

태블릿 운영석의 **출석 체크 화면**에 추첨 기능을 추가한다. 참여중 명단에서 1명을 무작위로 뽑고, 0.6초 룰렛 후 모달로 발표하며, 같은 사람이 다시 뽑히지 않는다(영구 저장).

이 문서는 **앱 1:1 포팅**을 위한 정본이다. 디자인·동작·문구·간격을 그대로 맞춘다.
- **정본 소스(React)**: `match_ui_demo/screens2.jsx` — 추첨 관련 코드 발췌본 → [`prototype/draw-snippet.jsx`](./prototype/draw-snippet.jsx)
- **상위 핸드오프**: [`../lightning-matchmaking/README.md`](../lightning-matchmaking/README.md) (디자인 토큰·전체 화면 매핑)

---

## 1. 결정 사양 (요구사항)

| 항목 | 값 | 근거 |
|---|---|---|
| 대상 풀 | `status === '참여중'` 인 참가자만 | 출석 안 했거나 퇴장한 사람은 추첨 X |
| 뽑는 인원 | 1명 고정 | 단순함 우선 |
| 결과 표시 | 중앙 모달 | 발표 분위기 |
| 중복 제어 | 한 번 뽑힌 사람 자동 제외 | 영구 저장 (localStorage / SharedPreferences 등) |
| 풀 빔 처리 | 안내 후 **수동 초기화** (자동 reset 안 함) | 의도치 않은 재추첨 방지 |
| 애니메이션 | 0.6초 룰렛 (55ms 간격으로 이름 휙휙 바뀜 → 멈춤) | 분위기 살리기 |
| 룰렛 중 인터랙션 | 모든 버튼·외부 클릭 비활성화 | 오작동 방지 |

---

## 2. 진입 — 헤더 버튼

위치: 출석 체크 화면 **헤더 우측 새로고침 ↻ 버튼 바로 오른쪽**.

```
[ ← 운영 화면 ]  출석 체크         …   [ ↻ ] [ 추첨  N ]  [참여중 …] [미출석 …]
```

- 라벨: `추첨` (이모지/아이콘 없음) + 뒤에 **남은 대상 수 N**(opacity 0.55, fontWeight 700, fontSize 12.5)
- N = `참여중 수 − 이미 뽑힌 수`
- 클릭: 풀이 비었으면 안내 알림, 아니면 모달 띄우고 룰렛 시작
- title/aria-label: `참여중에서 1명 추첨 (남은 대상 N명)` / `추첨`
- 스타일: 새로고침 버튼과 동일한 `navBtnStyle` 베이스
  - `padding: 9px 12px`, `fontSize: 14`, `lineHeight: 1`, `display: inline-flex`, `alignItems: center`, `gap: 6`

---

## 3. 모달 — 룰렛 → 발표

### 레이아웃 (중앙 정렬, width 460, padding 32, textAlign center)

```
┌────────────────────────────────────────────┐
│                추첨 결과                    │   ← 13px / 800 / muted / letter .05em
│                                            │
│             [    이름    ]                  │   ← 56px / 900 / ink / letter -.04em
│                                            │      룰렛 동안엔 풀에서 순환,
│                                            │      멈춘 뒤 살짝 scale(1.04) 확대
│                                            │
│           [ 급수칩 ] [ 성별칩 ]              │   ← 13px / 800 / 라운드 999 / padding 5px 11px
│                                            │
│            3 / 12 추첨 완료                 │   ← 12.5px / 700 / muted
│                                            │
│  [ 기록 초기화 ] [ 한 번 더 ] [   닫기   ]   │   ← 14~14.5px / 800 / 12px 패딩
│        flex 1        1        1.4         │      앞 둘 = ghost(line-2 보더),
│                                            │      닫기 = primary(brand)
└────────────────────────────────────────────┘
```

### 색·토큰

| 요소 | 토큰 |
|---|---|
| 모달 배경 | `--surface`, radius 22 (중앙), shadow `--sh-3` |
| 모달 백드롭 | `rgba(17,22,31,.5)` (`fadeIn .18s`) |
| 헤더 라벨 | `--muted` |
| 큰 이름 | `--ink` |
| 급수칩 | bg `--brand-tint`, fg `--brand-ink` |
| 성별칩 (남) | bg `--men`, fg `#fff` |
| 성별칩 (여) | bg `--women`, fg `#fff` |
| 카운터 | `--muted` |
| `기록 초기화` / `한 번 더` | bg `--surface-2`, fg `--ink-2`, border `--line-2` |
| `닫기`(활성) | bg `--brand`, fg `#fff` |
| `닫기`(룰렛 중) | bg `--surface-3`, fg `#fff`, cursor `not-allowed` |

> 디자인 토큰 정의는 상위 핸드오프 `lightning-matchmaking/prototype/index.html`의 `:root` 참고.

---

## 4. 동작 시퀀스

```
[추첨 버튼 클릭]
   │
   ├─ drawPool.length === 0  →  안내(alert)
   │     "남은 추첨 대상이 없어요. 모달에서 [기록 초기화] 후 다시 진행해주세요."
   │
   └─ winner = drawPool[ random ]
         setDrawResult(winner)        ← 모달 표시
         setDrawnIds += winner.id      ← 즉시 영구 저장
         │
         ▼
   [모달 mount → rolling=true]
       ▶ 55ms 간격으로 tick++
       ▶ display = pool[tick % pool.length]
       ▶ Date.now() − start ≥ 600  →  rolling=false, interval clear
       ▶ display = winner
       ▶ scale(1.04) 트랜지션 (.2s)
       ▶ 버튼 활성화
         │
         ▼
   [사용자 선택]
       ▶ 닫기      → onClose() : setDrawResult(null)
       ▶ 한 번 더   → onClose() → setTimeout(handleDraw, 60)
       ▶ 기록 초기화 → setDrawnIds(empty) → onClose()
```

### 엣지

- `pool.length <= 1` → 룰렛 스킵, winner 즉시 표시 (무한 깜빡 방지)
- 룰렛 중 모달 외부 클릭 → 무시 (onClose 비활성)
- 영구 저장 실패(try/catch) → 메모리 Set만 유지, 다음 추첨에는 영향 X
- 풀에서 사람이 빠질 때(참여중 → 미출석/퇴장) → 카운터 N도 즉시 감소

---

## 5. 상태 / 영구 저장

### 상태(React 기준)

```jsx
const [drawResult, setDrawResult] = useState(null);   // { id, name, level, gender } | null
const [drawnIds, setDrawnIds]     = useState(new Set()); // 누적된 winner id Set
```

### 영구 저장 키

| 환경 | 키 | 값 |
|---|---|---|
| Web (React) | `localStorage.bm_drawn_ids` | `JSON.stringify([...drawnIds])` (예: `[3,7,12]`) |
| iOS / Android (Flutter) | `SharedPreferences("bm_drawn_ids")` | 동일 JSON 문자열 |
| RN | `AsyncStorage.setItem('bm_drawn_ids', ...)` | 〃 |
| Native iOS | `UserDefaults` `bm_drawn_ids` | 〃 |
| Native Android | `SharedPreferences` `bm_drawn_ids` | 〃 |

> **키 이름은 플랫폼 간 통일** — 향후 동일 사용자가 웹/앱을 오가도 추첨 기록 호환.

### 초기화 정책

- `기록 초기화` 버튼 외에는 자동 reset하지 않는다.
- 세션 종료/새 세션 시작 시점에 자동 reset이 필요하면 별도 정책 협의(현재 안 함).

---

## 6. 1:1 매핑 — React jsx ↔ 앱 위젯

> Flutter 기준 예시. RN/네이티브도 위젯·뷰 이름만 바꾸면 동일.

| React (정본) | Flutter 위젯 | 비고 |
|---|---|---|
| 헤더 `<button>` | `OutlinedButton` / `TextButton` + `Row(Text+Text)` | navBtnStyle = surface-3 배경, 14px/800. **아이콘/이모지 없음, 텍스트만** |
| 남은 인원 `<span>N</span>` | `Text('$n', style: TextStyle(opacity: 0.55))` | 0.55 = `Color.withOpacity(0.55)` |
| `<ModalShell width={460} center>` | `Dialog(child: Container(width: 460))` | iPad/태블릿 기준. 폰은 너비 92% |
| 모달 백드롭 | `Dialog(barrierColor: Color.fromRGBO(17,22,31,0.5))` | `barrierDismissible: !rolling` |
| 큰 이름 텍스트 | `Text(name, style: TextStyle(fontSize: 56, fontWeight: w900, letterSpacing: -2.2))` | `letterSpacing -.04em ≈ -2.24` |
| scale(1.04) 트랜지션 | `AnimatedScale(scale: rolling ? 1.0 : 1.04, duration: 200ms)` | |
| 급수칩 / 성별칩 | `Container(decoration: BoxDecoration(borderRadius: 999), padding: EdgeInsets.symmetric(h:11, v:5))` | 토큰 색 동일 적용 |
| 3버튼 행 | `Row(children: [Expanded(flex:10..), Expanded(flex:10..), Expanded(flex:14..)])` | flex 비율 1 : 1 : 1.4 |
| 룰렛 setInterval | `Timer.periodic(Duration(milliseconds:55), ...)` + 누적 시간 600ms 체크 → cancel | |
| `localStorage` | `SharedPreferences` (`shared_preferences` 패키지) | 키 `bm_drawn_ids` |

### 추천 Flutter 클래스 구조

```
lib/features/attendance/draw/
├── attendance_draw_controller.dart     # 상태 (drawnIds, currentWinner) + 영구화
├── attendance_draw_button.dart         # 헤더에 들어가는 🎲 버튼 (남은 N 표시)
├── attendance_draw_modal.dart          # 룰렛 + 발표 다이얼로그
└── draw_storage.dart                   # SharedPreferences 래퍼 (load/save/reset)
```

`Riverpod` 사용 시: `StateNotifier<DrawState>` 하나로 충분 (`drawnIds`, `lastWinner`, `pool`).

---

## 7. 디자인 토큰 매핑 (앱 테마로 이식)

상위 핸드오프의 `:root` 변수에서 그대로 가져온다. **이미 다른 화면을 포팅했다면 토큰이 정의돼 있을 것 — 그대로 재사용.**

| CSS 변수 | 값(라이트) | 용도(추첨에서) |
|---|---|---|
| `--brand` | `#12a565` | "닫기" 활성 버튼 |
| `--brand-ink` | `#0c7f4e` | 급수칩 fg |
| `--brand-tint` | `#e7f6ee` | 급수칩 bg |
| `--men` | `#3b82f6` | 남자 성별칩 |
| `--women` | `#ec4899` | 여자 성별칩 |
| `--surface` | `#ffffff` | 모달 배경 |
| `--surface-2` | _상위 README 참고_ | "기록 초기화" / "한 번 더" 배경 |
| `--surface-3` | _상위 README 참고_ | "닫기" 비활성 배경, navBtnStyle 배경 |
| `--ink` | `#11161f` | 큰 이름 |
| `--ink-2` | `#475063` | navBtnStyle 텍스트, 부버튼 텍스트 |
| `--muted` | `#8b94a6` | 헤더 라벨, 카운터, "남은 N" 보조 |
| `--line-2` | _상위 README 참고_ | 부버튼 보더 |
| `--sh-3` | _상위 README 참고_ | 모달 그림자 |

### 폰트
- Pretendard Variable
- 큰 이름: `56 / 900 / -.04em letter-spacing / line-height 1.05`
- 라벨/카운터: `12.5–13 / 700–800`
- 버튼: `14–14.5 / 800 / -.02em`

---

## 8. 검증 체크리스트 (앱 QA)

- [ ] 새로고침 버튼 **우측**에 `추첨` 버튼이 같은 높이로 정렬되는가? (아이콘/이모지 없이 텍스트만)
- [ ] 남은 인원 수가 실시간으로 줄어드는가? (참여중 5명 중 1명 뽑힘 → 4로 표시)
- [ ] 룰렛 중 외부 영역 터치/뒤로가기/버튼이 **모두** 비활성화되는가?
- [ ] 0.6초 후 정확히 winner로 멈추는가? (랜덤한 이름에 멈추지 않는지)
- [ ] winner 등장 시 살짝 확대(scale 1.04) 트랜지션이 보이는가?
- [ ] 같은 사람이 두 번째 추첨에서 나오지 않는가?
- [ ] 앱 강제 종료 후 재실행해도 뽑힌 기록이 유지되는가?
- [ ] 풀이 비면 안내가 뜨고, 자동 초기화되지 않는가?
- [ ] `기록 초기화` 누르면 즉시 `남은 N = 참여중 수`로 복원되는가?
- [ ] `한 번 더`가 모달을 닫은 뒤 새 추첨을 자동 시작하는가?
- [ ] 풀에 1명만 있을 때(룰렛 스킵) 즉시 발표되는가?
- [ ] 모달 백드롭 색이 정확히 `rgba(17,22,31,.5)`로 보이는가?
- [ ] 헤더 버튼·모달 어느 곳에도 🎲 같은 주사위 아이콘/이모지가 **없어야** 한다 (텍스트 라벨만 사용).

---

## 9. 파일 목록

```
docs/handoff/attendance-draw/
├── README.md                   ← 이 문서 (정본)
└── prototype/
    └── draw-snippet.jsx        ← screens2.jsx 추첨 부분 발췌 (그대로 보면서 포팅)
```

전체 React 프로토타입(다른 화면 포함)은 [`../lightning-matchmaking/prototype/`](../lightning-matchmaking/prototype/) 참조.
