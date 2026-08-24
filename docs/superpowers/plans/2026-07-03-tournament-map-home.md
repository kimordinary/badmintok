# 전국 배드민턴 대회 "지도 홈" 재구현 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/badminton-tournament/` 목록 페이지를 "인터랙티브 대한민국 지도 = 지역 필터" 컨셉으로 재구현하되, 서버 렌더(SSR) + 시맨틱 마크업 + URL=필터상태로 SEO를 확보한다.

**Architecture:** Django SSR 뷰(`ContestPreviewView`)가 대회 리스트를 실제 HTML 본문(시맨틱 h1/h2 + `<a>` 카드)으로 렌더하고, 바닐라 JS가 그 위에서 지도·필터를 프로그레시브 인핸스먼트로 얹는다(리스트를 새로 그리지 않고 필터링만). 모바일/데스크톱은 DOM 스왑 없이 같은 마크업 + CSS로 900px에서 접힌다.

**Tech Stack:** Django 템플릿(`templates/contest/preview.html`, 인라인 style+script), 바닐라 JS(프레임워크 없음), 인라인 SVG 지도, Pretendard(CDN), `json_script` 필터.

## Global Constraints

- **디자인 원본:** `Badmintok 지도 홈.dc.html` (사용자가 별도 제공 예정). 색·타이포·간격·상태 로직은 이 파일과 `docs/design/` README가 최종 의도값. 픽셀 1:1 재현.
- **사이트 헤더 제외(사용자 지시):** README의 "모바일 헤더 로고 블록", "데스크톱 글로벌 내비(로고+메뉴)"는 구현하지 않는다. 기존 `base.html`의 사이트 공통 헤더를 그대로 쓴다. 페이지 콘텐츠(h1·검색·필터·지도·리스트)만 재구현.
- **브레이크포인트:** 900px. 미만=모바일 1열(헤더→검색→필터→지도→리스트), 이상=2열 그리드 `430px | 1fr`.
- **SSR 필수(협상 불가):** 리스트는 서버 HTML 본문에 텍스트로 존재. JS 클라이언트 렌더 금지. 무한스크롤 금지. 카드 전체가 `<a>` 링크. 이미지 alt = 대회명.
- **디자인 토큰(라이트):** bg#F3F6F4 surface#FFFFFF surface2#EAF1EC ink#122019 muted#5C6F65 line#DCE4DE accent#128A4D accent-strong#0B3D2E accent-soft#E1F2E8 포인트그린#2ECC71 warn#9A5B0B/soft#FBEEDA danger#C23B3B/soft#FBE3E3. 지도: 선택#0B3D2E/대회있음#8FD3A8/없음#DCE5DE, stroke#FFFFFF 0.8.
- **타이포:** Pretendard Variable(CDN, 폴백 -apple-system/'Apple SD Gothic Neo'/'Malgun Gothic'), 날짜·숫자열은 ui-monospace/'SF Mono'/monospace.
- **D-day 상태(접수마감 기준):** open(D-8+)=accent / soon(D-7이하)=warn / today(오늘 마감)=danger / closed(마감)=muted. 마감 행은 opacity .55, D-day 자리에 "접수 마감".
- **정렬:** 그룹 내 시작일 오름차순, 그룹은 월 오름차순.
- **리스트 행에 넣는 것:** 날짜(요일)·대회명·승급/비승급 배지·지역·체육관·후원사·접수 D-day·접수 마감일. 의도적 제외: 종목·급수·참가비·주최단체·포스터썸네일(리스트엔 안 넣음).

---

## 백엔드 무변경 (사용자 결정)

**`contests/views.py`·`contests/urls.py`는 손대지 않는다.** 지역/월 필터는 기존 방식(=`preview_data`로 전체 대회를 내려주고 JS가 클라이언트에서 필터링) 그대로 사용한다. 지도 핀 개수·시도 색 계산도 전체 데이터가 클라에 있어야 하므로 이 방식이 디자인에 부합한다.

- 리스트에 포스터 썸네일을 넣지 않으므로 `first_image` 백엔드 추가 불필요.
- 지역별 딥링크 URL(`/지역/서울/`)은 이번 범위에서 제외(추후 선택). 그로 인한 유일한 손실은 지역명 롱테일 SEO 유입뿐이며, SSR 리스트·h1/h2·JSON-LD 같은 핵심 SEO는 기존 `preview_data`로 그대로 확보된다.

## File Structure

| 파일 | 책임 | 변경 |
|---|---|---|
| `templates/contest/preview.html` (884줄) | 페이지 전체 마크업 + 인라인 CSS + 인라인 JS 재작성 | Rewrite |
| (자산) 지도 SVG path·PIN 좌표 | 제공된 `.dc.html`에서 추출 → preview.html에 인라인 | 추출 |
| `contests/views.py`, `contests/urls.py` | — | **변경 없음** |

---

## Task 0: 지도 자산 추출 (BLOCKER — `.dc.html` 수령 후 착수)

**Files:**
- Read: `Badmintok 지도 홈.dc.html` (사용자 제공)

**Interfaces:**
- Produces: ① 17개 시도 `<path>` 데이터(viewBox `0 0 130 204`), ② `PIN` 좌표 객체(시도→x/y), ③ x-dc 템플릿의 정확한 클래스·스타일 값(README 대조), ④ path↔`Contest.Region` 라벨 매핑.

- [ ] **Step 1: SVG 블록 추출** — `<svg viewBox="0 0 130 204">`…`</svg>` 내부 17개 `<path>`와 지역 식별 속성 복사.
- [ ] **Step 2: PIN 객체 추출** — `<script data-dc-script>` 안 `PIN` 상수(시도별 x/y) 표로 정리.
- [ ] **Step 3: 지역명 매핑 확정** — path/PIN 키가 `Contest.Region.choices` 라벨과 1:1인지 대조표. 불일치는 정규화 규칙 명시.
- [ ] **Step 4: README 스타일 대조** — 색/간격/타이포가 Global Constraints와 일치 확인, 차이는 `.dc.html` 우선 기록.

> HTML 미수령 시 Task 0·6 착수 불가. Task 1·2·3·4·5·8·9는 지도 없이 선행 가능.

---

## Task 1: 프론트 — 템플릿 골격 (SSR 리스트 + 시맨틱 헤딩 + 반응형 단일 DOM)

**Files:**
- Rewrite: `templates/contest/preview.html` (구조 골격만)

**Interfaces:**
- Consumes: `preview_data`/`regions`/`active_region`/`active_month`/`today_iso`/`canonical_url`.
- Produces: 시맨틱 DOM — 보이는 `<h1>` 1개, 월그룹 `<h2>`, 서버 렌더 `<a class="row">` 리스트, 검색/필터/지도 컨테이너(빈 채로), `json_script` 데이터.

- [ ] **Step 1: base 확장 + 헤드** — `{% extends "base.html" %}`, title/OG/canonical 유지. 사이트 헤더는 base 것.
- [ ] **Step 2: 콘텐츠 골격** — `<main class="tour">`: (1) `<h1>전국 배드민턴 대회 일정 2026</h1>`+안내문, (2) 검색 input, (3) 필터 행(월 select + 승급/비승급 토글), (4) `<div class="tour-map">`(빈), (5) 활성필터 칩 영역, (6) 총개수, (7) 월별 `<h2>`+각 대회 `<a class="row" href>` SSR. JS 없이도 리스트가 완전히 보여야 함.
- [ ] **Step 3: 반응형 골격** — 하나의 마크업 + CSS 그리드 900px 접힘(스타일 Task 4). DOM 스왑 없음.
- [ ] **Step 4: 데이터 방출(하드닝)** — `{{ preview_data|json_script:"tourData" }}`, `regions`도 `json_script`.
- [ ] **Step 5: 렌더 확인** — `manage.py check` + `/badminton-tournament/` 200, JS 비활성에서 `<h1>`·`<a class="row"` grep 확인.
- [ ] **Step 6: 커밋** — `git commit -m "feat(contests): 지도 홈 템플릿 골격 — SSR 리스트 + 시맨틱 헤딩"`

---

## Task 2: 프론트 — 디자인 토큰 & 공통 스타일

**Files:**
- Modify: `templates/contest/preview.html` 인라인 style

- [ ] **Step 1: 토큰 정의** — `.tour{ --bg:#F3F6F4; … }` Global Constraints 값. Pretendard CDN(중복 로드 방지 확인).
- [ ] **Step 2: 레이아웃** — 기본 1열; `@media(min-width:900px){grid-template-columns:430px 1fr;min-height:720px}`. 왼쪽 패널(surface, 우측 1px line), 오른쪽 리스트(bg) 패딩 README 수치.
- [ ] **Step 3: 폼 컴포넌트** — 검색(focus outline 2px accent), 월 select pill(radius 999), 승급 토글 칩(비활성/활성 색 규칙).
- [ ] **Step 4: 시각 확인** — 데스크톱/모바일 접힘·색 확인(900px 전환).
- [ ] **Step 5: 커밋** — `git commit -m "style(contests): 지도 홈 디자인 토큰 및 레이아웃"`

---

## Task 3: 프론트 — 리스트 행 카드 (모바일/데스크톱 통일)

**Files:**
- Modify: `templates/contest/preview.html` (`.row` 스타일 + SSR 카드 필드)

- [ ] **Step 1: 카드 마크업** — `<a class="row status-{{status}}">`: 날짜열(mono "07.18(토)"), 본문(제목+승급배지 / 지역·체육관 / 후원사), 우측(D-day 상태색 + "접수 ~MM.DD(요일)"). 서버 값 SSR.
- [ ] **Step 2: 반응형 grid** — 모바일 `48px 1fr`, 데스크톱 `96px 1fr 150px`. 한 마크업 + 미디어쿼리.
- [ ] **Step 3: 상태 스타일** — open(accent)/soon(warn)/today(danger)/closed(opacity .55, "접수 마감"). 서버 `dday`/`status` 사용.
- [ ] **Step 4: 승급 배지 + hover** — 배지(radius 4, 10/800), 데스크톱 hover `bg surface`.
- [ ] **Step 5: 시각 확인** — open/soon/today/closed·다일대회·후원사 없음·이미지 없음 케이스.
- [ ] **Step 6: 커밋** — `git commit -m "feat(contests): 대회 리스트 행 카드 (반응형 통일 + 상태색)"`

---

## Task 4: 프론트 — 지도 컴포넌트 (Task 0 자산 의존)

**Files:**
- Modify: `templates/contest/preview.html` (`.tour-map` + 지도 스타일 + 핀)

**Interfaces:**
- Consumes: Task 0의 17개 path·`PIN`·지역 매핑, `base` 지역별 개수.
- Produces: 클릭 가능 시도 SVG + 카운트 핀. `data-region` 속성으로 JS 식별.

- [ ] **Step 1: SVG 인라인** — Task 0 path를 `viewBox="0 0 130 204"`로 삽입, 각 path `data-region`. 채색 클래스 `.sido--selected/--has/--none`.
- [ ] **Step 2: 핀 오버레이** — `PIN` 좌표 %변환 절대배치 버튼 "{지역} {개수}"(기본/선택 색). 개수는 서버 초기값+JS 갱신.
- [ ] **Step 3: 반응형 크기** — 모바일 280px 중앙, 데스크톱 320px.
- [ ] **Step 4: 시각 확인** — 지도 형태·핀 위치 `.dc.html`과 1:1 비교.
- [ ] **Step 5: 커밋** — `git commit -m "feat(contests): 인터랙티브 시도 지도 + 카운트 핀"`

---

## Task 5: 프론트 — 필터/검색/지도 상태 로직 (프로그레시브 인핸스먼트)

**Files:**
- Modify: `templates/contest/preview.html` 인라인 script

**Interfaces:**
- Consumes: `tourData`(json_script), 초기 `active_region`/`active_month`, SSR `.row` 노드.
- Produces: `filters={month,qual,q}`+`region`. 파생 `base`(지역 제외)→핀/색, `list`(base∩region)→행 show/hide. URL 양방향 동기화. 리스트를 새로 그리지 않고 기존 `.row` show/hide.

- [ ] **Step 1: 상태·파생** — `tourData` 인덱스. `applyBase()`(month·qual·q), `applyList()`(base∩region). `.row[data-id]` show/hide.
- [ ] **Step 2: 지도·핀·총개수 갱신** — base 지역별 개수로 핀/색/총개수 갱신, 빈 월그룹 헤더 숨김.
- [ ] **Step 3: 이벤트 배선** — 검색(제목+지역+체육관 includes), 승급 칩 토글(상호배타·재클릭 해제), 월 select, 지도/핀 클릭(region 토글), 활성필터 칩 ✕ + "모두 지우기".
- [ ] **Step 4: URL 동기화** — region→`pushState('/badminton-tournament/지역/{region}/')`, month→`?month=`. popstate 처리. 초기 로드 `active_*`로 상태 세팅.
- [ ] **Step 5: 빈 상태** — `list` 0건이면 "조건에 맞는 대회가 없어요"+보조문+[필터 초기화].
- [ ] **Step 6: 하드닝** — `tourData`/`regions`를 `JSON.parse(...textContent)`로 읽기(raw 인젝션 제거 확인). 죽은 코드 없음.
- [ ] **Step 7: 동작 확인** — 지역 클릭→리스트/핀/URL, 뒤로가기, 검색, 승급 토글, 빈 상태, 마감 표시.
- [ ] **Step 8: 커밋** — `git commit -m "feat(contests): 지도/필터 프로그레시브 인핸스먼트 + URL 동기화"`

---

## Task 6: SEO — JSON-LD (ItemList > SportsEvent 중첩) + 메타

**Files:**
- Modify: `templates/contest/preview.html` (`<head>` JSON-LD)

- [ ] **Step 1: JSON-LD 템플릿** — README 예시 형태로 `{% for %}` 렌더, 각 ListItem.item에 SportsEvent(name/startDate/endDate/eventStatus/location Place+addressRegion/url/offers). 상세 `get_jsonld()`와 정합.
- [ ] **Step 2: 헤딩/메타 점검** — 보이는 `<h1>` 1개, 월 `<h2>` 계층, title/description/OG 정체성. 지역 페이지는 "{지역} 배드민턴 대회"로 변주(선택).
- [ ] **Step 3: 검증** — `manage.py check` + JSON 유효성(`python -m json.tool`).
- [ ] **Step 4: 커밋** — `git commit -m "feat(contests): 목록 JSON-LD를 SportsEvent 중첩으로 강화"`

---

## Task 7: 하드닝 & 정리 & 최종 회귀

**Files:**
- Modify: `templates/contest/preview.html`, `contests/tests/test_preview.py`

- [ ] **Step 1: 인젝션 차단 테스트**

```python
    def test_script_injection_in_title_is_safe(self):
        Contest.objects.create(title="위험</script>대회", slug="x1", schedule_start="2099-01-01", region="서울")
        resp = self.client.get(reverse("contests:list"))
        self.assertEqual(resp.status_code, 200)
```

- [ ] **Step 2: 실패→구현→통과** — `json_script`로 통과. Run: `.venv/bin/python manage.py test contests -v 2`
- [ ] **Step 3: empty/loading/error 최종 확인** — 빈 DB, 필터 0건, 지역 0건 empty-state.
- [ ] **Step 4: 접근성/링크** — 카드 전체 `<a>`, 이미지 alt=대회명, 색대비 AA, 키보드 포커스.
- [ ] **Step 5: 전체 회귀** — Run: `.venv/bin/python manage.py test contests -v 2` + `manage.py check`. all pass.
- [ ] **Step 6: 커밋** — `git commit -m "chore(contests): 지도 홈 하드닝·정리·회귀 테스트"`

---

## Self-Review 체크리스트

- SSR: Task 1(리스트 SSR) + Task 6(JSON-LD) 커버. (기존 `preview_data` 그대로 사용)
- 반응형 단일 DOM 900px: Task 1·2 커버.
- 필터 상태: 클라이언트 JS 필터(Task 5)로 처리. 서버 딥링크 URL은 이번 범위 제외(백엔드 무변경).
- 시맨틱 h1/h2: Task 1·6 커버.
- 지도(1:1): Task 0+4 → `.dc.html` 수령 전까지 blocked.
- 빈/마감/상태: Task 3·5·7 커버.
- 하드닝(|safe 제거): Task 1-Step4 + Task 7 커버.
- 백엔드: **무변경.** 후원사·dday·status·scope는 이미 `preview_data`에 존재(views.py L188–224), 이미지는 리스트 미사용이라 불필요.
- 헤더 제외: Global Constraints 명시, 어떤 태스크도 헤더 마크업 안 만듦.

## 미결/HTML 의존 항목

1. `Badmintok 지도 홈.dc.html` 미수령 → Task 0·4 대기. 나머지(1·2·3·5·6·7)는 선행 가능.
2. 지역 딥링크 URL(`/지역/서울/`)은 이번 범위 제외(백엔드 무변경 결정). 지역명 롱테일 SEO를 원하면 추후 별도 작업으로 서버 라우팅 추가.
3. 월 필터 UI("전체 기간 + N개월")는 기존 `preview_data` 범위(2개월 전~미래 전체) 안에서 JS로 처리(Task 5).
</parameter>
</invoke>
