// ===== 출석 화면 추첨 — 정본 발췌 =====
// 원본: match_ui_demo/screens2.jsx (AttendanceScreen + DrawModal)
// 이 파일은 포팅 참고용 발췌본이다. 실제 동작은 원본 통합본을 그대로 본다.
// React 18 + Babel-standalone(JSX in browser) 가정.

// ---------- 1) AttendanceScreen 내부에 추가될 상태/핸들러 ----------
//
// function AttendanceScreen({ state, actions }) {
//   const { participants } = state;
//   const [filter, setFilter] = useState('전체');
//   const [query, setQuery]   = useState('');

// 추첨: 참여중에서 1명, 중복 제외(localStorage 영구), 0.6초 룰렛 후 발표
const [drawResult, setDrawResult] = useState(null); // { id, name, level, gender } | null
const [drawnIds, setDrawnIds] = useState(() => {
  try { return new Set(JSON.parse(localStorage.getItem('bm_drawn_ids') || '[]')); }
  catch { return new Set(); }
});
useEffect(() => {
  try { localStorage.setItem('bm_drawn_ids', JSON.stringify([...drawnIds])); } catch {}
}, [drawnIds]);

const drawPool = participants.filter((p) => p.status === '참여중' && !drawnIds.has(p.id));

const handleDraw = () => {
  if (drawPool.length === 0) {
    alert('남은 추첨 대상이 없어요. 모달에서 [기록 초기화] 후 다시 진행해주세요.');
    return;
  }
  const winner = drawPool[Math.floor(Math.random() * drawPool.length)];
  setDrawResult(winner);
  setDrawnIds((prev) => new Set([...prev, winner.id]));
};

const resetDraw = () => { setDrawnIds(new Set()); };


// ---------- 2) 헤더 — 새로고침 ↻ 옆에 들어가는 추첨 버튼 ----------
// 위치: 출석 체크 헤더 우측, 새로고침 버튼 바로 오른쪽.
// 아이콘/이모지 없이 "추첨" 텍스트 + 남은 인원 수.

<button
  onClick={handleDraw}
  title={`참여중에서 1명 추첨 (남은 대상 ${drawPool.length}명)`}
  aria-label="추첨"
  style={{
    ...navBtnStyle,
    padding: '9px 12px',
    fontSize: 14,
    lineHeight: 1,
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
  }}
>
  추첨 <span style={{ opacity: 0.55, fontWeight: 700, fontSize: 12.5 }}>{drawPool.length}</span>
</button>


// ---------- 3) AttendanceScreen return 닫기 직전에 들어가는 모달 렌더 ----------

{drawResult && (
  <DrawModal
    winner={drawResult}
    pool={participants.filter((p) => p.status === '참여중')}
    drawnCount={drawnIds.size}
    onClose={() => setDrawResult(null)}
    onAgain={() => { setDrawResult(null); setTimeout(handleDraw, 60); }}
    onReset={() => { resetDraw(); setDrawResult(null); }}
  />
)}


// ---------- 4) DrawModal 컴포넌트 (0.6초 룰렛 → 발표) ----------

function DrawModal({ winner, pool, drawnCount, onClose, onAgain, onReset }) {
  // 룰렛: 0.6초 동안 55ms 간격으로 풀에서 다음 사람 표시 → 시간 다 되면 winner 고정
  const [rolling, setRolling] = useState(true);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (pool.length <= 1) { setRolling(false); return; }
    const start = Date.now();
    const id = setInterval(() => {
      if (Date.now() - start >= 600) {
        setRolling(false);
        clearInterval(id);
        return;
      }
      setTick((t) => t + 1);
    }, 55);
    return () => clearInterval(id);
  }, []);

  const display = rolling ? pool[tick % pool.length] : winner;
  const genderColor = display.gender === 'F' ? 'var(--women)' : 'var(--men)';

  return (
    <ModalShell onClose={rolling ? () => {} : onClose} width={460} center>
      <div style={{ padding: 32, textAlign: 'center' }}>
        {/* 헤더 라벨 — 아이콘/이모지 없음 */}
        <div style={{
          fontSize: 13, fontWeight: 800, color: 'var(--muted)',
          letterSpacing: '.05em', marginBottom: 18,
        }}>추첨 결과</div>

        {/* 큰 이름 (룰렛 동안엔 풀 순환, 멈춘 뒤 살짝 scale-up) */}
        <div style={{
          fontSize: 56, fontWeight: 900, letterSpacing: '-.04em',
          color: 'var(--ink)', lineHeight: 1.05,
          minHeight: 70, display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: rolling ? 'none' : 'transform .2s ease',
          transform: rolling ? 'none' : 'scale(1.04)',
        }}>{display.name}</div>

        {/* 급수칩 / 성별칩 */}
        <div style={{ display: 'inline-flex', gap: 8, marginTop: 14, alignItems: 'center' }}>
          <span style={{
            padding: '5px 11px', borderRadius: 999, fontSize: 13, fontWeight: 800,
            background: 'var(--brand-tint)', color: 'var(--brand-ink)',
          }}>{display.level}</span>
          <span style={{
            padding: '5px 11px', borderRadius: 999, fontSize: 13, fontWeight: 800,
            background: genderColor, color: '#fff',
          }}>{display.gender === 'F' ? '여자' : '남자'}</span>
        </div>

        {/* 진행 카운터 */}
        <div style={{ fontSize: 12.5, color: 'var(--muted)', fontWeight: 700, marginTop: 18 }}>
          {drawnCount} / {pool.length} 추첨 완료
        </div>

        {/* 3버튼: 기록 초기화 / 한 번 더 / 닫기 (flex 1 : 1 : 1.4) */}
        <div style={{ display: 'flex', gap: 8, marginTop: 24 }}>
          <button onClick={onReset} disabled={rolling} style={{
            flex: 1, padding: '12px', borderRadius: 12,
            fontSize: 14, fontWeight: 800, letterSpacing: '-.02em',
            background: 'var(--surface-2)', color: 'var(--ink-2)',
            border: '1px solid var(--line-2)',
            opacity: rolling ? 0.5 : 1, cursor: rolling ? 'not-allowed' : 'pointer',
          }}>기록 초기화</button>

          <button onClick={onAgain} disabled={rolling} style={{
            flex: 1, padding: '12px', borderRadius: 12,
            fontSize: 14, fontWeight: 800, letterSpacing: '-.02em',
            background: 'var(--surface-2)', color: 'var(--ink-2)',
            border: '1px solid var(--line-2)',
            opacity: rolling ? 0.5 : 1, cursor: rolling ? 'not-allowed' : 'pointer',
          }}>한 번 더</button>

          <button onClick={onClose} disabled={rolling} style={{
            flex: 1.4, padding: '12px', borderRadius: 12,
            fontSize: 14.5, fontWeight: 800, letterSpacing: '-.02em',
            background: rolling ? 'var(--surface-3)' : 'var(--brand)',
            color: '#fff', border: 'none',
            cursor: rolling ? 'not-allowed' : 'pointer',
          }}>{rolling ? '추첨 중…' : '닫기'}</button>
        </div>
      </div>
    </ModalShell>
  );
}

// ===== 끝 =====
// 더 자세한 1:1 매핑·디자인 토큰·검증 체크리스트는 ../README.md 참고.
