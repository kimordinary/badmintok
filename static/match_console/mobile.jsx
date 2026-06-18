// ===== mobile.jsx — 스마트폰(세로) 버전 =====

function MobileApp({ state, actions }) {
  const { participants, courts, mode, preset, nowTs } = state;
  const [tab, setTab] = useState('court');
  const queue = useMemo(() => sortQueue(participants.filter((p) => p.status === '참여중' && p.court == null), nowTs), [participants, nowTs]);
  const recs = useMemo(() => {
    const taken = new Set();
    const out = {};
    for (const ct of courts) {
      if (ct.match) continue;
      const avail = participants.filter((p) => !taken.has(p.id));
      const r = recommendMatch(avail, mode, preset, nowTs);
      out[ct.no] = r;
      if (r.match) [...r.match.teamA, ...r.match.teamB].forEach((p) => taken.add(p.id));
    }
    return out;
  }, [participants, courts, mode, preset, nowTs]);
  const playing = participants.filter((p) => p.court != null).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg)' }}>
      {/* 상단바 */}
      <div style={{ flexShrink: 0, background: 'var(--surface)', borderBottom: '1px solid var(--line)', paddingTop: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '8px 16px 10px' }}>
          <img src="app-logo.png" alt="배드민톡" width={34} height={34} style={{ borderRadius: 9, display: 'block', flexShrink: 0 }} />
          <div style={{ flex: 1, fontSize: 12.5, color: 'var(--muted)', fontWeight: 600 }}>참여 {playing} · 대기 {queue.length}</div>
          <span style={{ width: 9, height: 9, borderRadius: 9, background: 'var(--brand)', animation: 'pulseRing 2s infinite' }} />
          <span style={{ fontSize: 11.5, fontWeight: 800, color: 'var(--brand-ink)' }}>LIVE</span>
        </div>
        {tab === 'court' && (
          <div style={{ display: 'flex', gap: 8, padding: '0 16px 12px', overflowX: 'auto' }}>
            <Segmented options={MODES} value={mode} onChange={actions.setMode} accent="var(--ink)" size="md" />
            <Segmented options={['밸런스', '동일 급수']} value={preset} onChange={actions.setPreset} accent="var(--brand)" size="md" />
          </div>
        )}
      </div>

      {/* 본문 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 14px 90px' }}>
        {tab === 'court' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {courts.map((ct) => (
              <CourtCard key={ct.no} court={ct} rec={recs[ct.no]} nowTs={nowTs} onEnd={actions.endMatch} onStart={actions.startMatch} onEdit={actions.openEdit} />
            ))}
          </div>
        )}
        {tab === 'queue' && (
          <div style={{ background: 'var(--surface)', borderRadius: 16, border: '1px solid var(--line)', overflow: 'hidden' }}>
            <div style={{ padding: '14px 16px 10px', borderBottom: '1px solid var(--line)', fontSize: 15, fontWeight: 900, letterSpacing: '-.03em' }}>대기열 <span style={{ color: 'var(--muted)' }}>· 덜 뛴 순</span></div>
            {queue.map((p, i) => {
              const rest = p.lastFinished == null ? null : Math.round((nowTs - p.lastFinished) / 60000);
              return (
                <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '11px 16px', borderTop: i === 0 ? 'none' : '1px solid var(--line)', background: i < 4 ? 'var(--brand-tint)' : 'transparent' }}>
                  <span style={{ width: 20, fontSize: 13, fontWeight: 900, color: i < 4 ? 'var(--brand-ink)' : 'var(--muted)', textAlign: 'center' }}>{i + 1}</span>
                  <LevelChip level={p.level} size={24} />
                  <div style={{ flex: 1 }}>
                    <NameWithGender p={p} size={15.5} />
                    <div style={{ fontSize: 11.5, color: 'var(--muted)', fontWeight: 600, marginTop: 2 }}>{p.totalGames}경기{rest != null ? ` · ${rest}분 휴식` : ' · 아직 안 뜀'}</div>
                  </div>
                  <CountPills games={p.games} compact />
                </div>
              );
            })}
            {queue.length === 0 && <div style={{ padding: 30, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>대기 인원이 없습니다.</div>}
          </div>
        )}
        {tab === 'attend' && <MobileAttendance state={state} actions={actions} />}
        {tab === 'counts' && <MobileCounts state={state} />}
      </div>

      {/* 하단 탭바 */}
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, background: 'var(--surface)', borderTop: '1px solid var(--line)', display: 'flex', padding: '8px 8px 22px', boxShadow: '0 -4px 16px rgba(17,22,31,.05)' }}>
        {[{ k: 'court', l: '코트', i: '🏸' }, { k: 'queue', l: '대기열', i: '⏱' }, { k: 'attend', l: '출석', i: '✓' }, { k: 'counts', l: '카운트', i: '📊' }].map((t) => (
          <button key={t.k} onClick={() => setTab(t.k)} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, padding: '6px 0', color: tab === t.k ? 'var(--brand-ink)' : 'var(--muted)' }}>
            <span style={{ fontSize: 19 }}>{t.i}</span>
            <span style={{ fontSize: 11, fontWeight: 800, letterSpacing: '-.02em' }}>{t.l}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function MobileAttendance({ state, actions }) {
  const { participants } = state;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ fontSize: 15, fontWeight: 900, letterSpacing: '-.03em', padding: '2px 2px 4px' }}>출석 체크 <span style={{ color: 'var(--muted)', fontWeight: 700, fontSize: 13 }}>· 참여 {participants.filter((p) => p.status === '참여중').length}명</span></div>
      {participants.map((p) => {
        const st = STATUS_STYLE[p.status];
        return (
          <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 11, background: 'var(--surface)', borderRadius: 14, border: '1px solid var(--line)', padding: 11, opacity: p.status === '퇴장' ? 0.65 : 1 }}>
            <LevelChip level={p.level} size={26} />
            <div style={{ flex: 1 }}>
              <NameWithGender p={p} size={15.5} />
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11.5, fontWeight: 800, color: st.fg, marginTop: 3 }}>
                <span style={{ width: 6, height: 6, borderRadius: 6, background: st.dot }} />{st.label}
              </span>
            </div>
            {p.status !== '참여중' ? (
              <Btn variant="primary" size="sm" onClick={() => actions.setStatus(p.id, '참여중')}>출석</Btn>
            ) : (
              <div style={{ display: 'flex', gap: 6 }}>
                <Btn variant="soft" size="sm" onClick={() => actions.setStatus(p.id, '미출석')}>취소</Btn>
                <Btn variant="ghost" size="sm" onClick={() => actions.setStatus(p.id, '퇴장')} style={{ color: 'var(--danger)' }}>퇴장</Btn>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function MobileCounts({ state }) {
  const active = state.participants.filter((p) => p.status !== '미출석');
  const sorted = [...active].sort((a, b) => b.totalGames - a.totalGames);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ fontSize: 15, fontWeight: 900, letterSpacing: '-.03em', padding: '2px 2px 4px' }}>개인별 카운트</div>
      {sorted.map((p) => (
        <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 11, background: 'var(--surface)', borderRadius: 14, border: '1px solid var(--line)', padding: 11 }}>
          <LevelChip level={p.level} size={26} />
          <div style={{ flex: 1 }}>
            <NameWithGender p={p} size={15} />
            <div style={{ marginTop: 5 }}><CountPills games={p.games} compact /></div>
          </div>
          <span style={{ fontSize: 20, fontWeight: 900, color: 'var(--ink)', letterSpacing: '-.03em' }}>{p.totalGames}</span>
        </div>
      ))}
      {sorted.length === 0 && <div style={{ padding: 30, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>출석한 참가자가 없습니다.</div>}
    </div>
  );
}

Object.assign(window, { MobileApp });
