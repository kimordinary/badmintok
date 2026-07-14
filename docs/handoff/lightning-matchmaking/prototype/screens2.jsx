// ===== screens2.jsx — 출석 체크 / 개인 카운트 / 모달 =====

// ---------- 출석 체크 화면 ----------
const STATUS_STYLE = {
  미출석: { fg: 'var(--muted)', bg: 'var(--surface-3)', label: '미출석', dot: '#c2cad6' },
  참여중: { fg: 'var(--brand-ink)', bg: 'var(--brand-tint)', label: '참여중', dot: 'var(--brand)' },
  퇴장: { fg: 'var(--danger)', bg: 'var(--danger-tint)', label: '퇴장', dot: 'var(--danger)' },
};

// ---------- 참가자 추가 (바텀시트) ----------
function AddParticipantModal({ onAdd, onClose }) {
  const [name, setName] = useState('');
  const [level, setLevel] = useState('');
  const [gender, setGender] = useState('');
  const nameRef = useRef(null);
  // 시트가 올라온 뒤 포커스(scrollIntoView로 화면이 튀지 않게 preventScroll)
  useEffect(() => {
    const t = setTimeout(() => { if (nameRef.current) nameRef.current.focus({ preventScroll: true }); }, 340);
    return () => clearTimeout(t);
  }, []);
  const ok = name.trim() !== '' && level !== '' && gender !== '';
  const submit = () => { if (ok) onAdd({ name: name.trim(), level, gender }); };
  const labelStyle = { fontSize: 13, fontWeight: 800, color: 'var(--ink-2)', letterSpacing: '-.02em', marginBottom: 8, display: 'block' };
  return (
    <ModalShell onClose={onClose} width={460}>
      <div style={{ padding: 24 }}>
        <div style={{ fontSize: 19, fontWeight: 900, letterSpacing: '-.03em', color: 'var(--ink)' }}>참가자 추가</div>
        <div style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600, marginTop: 4, marginBottom: 20 }}>명단에 없는 인원을 이번 게임에 임시로 추가해요. 바로 참여중으로 들어갑니다.</div>

        {/* 이름 */}
        <label style={labelStyle}>이름</label>
        <input ref={nameRef} value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') submit(); }} placeholder="이름 입력" maxLength={12} style={{
          width: '100%', padding: '12px 14px', borderRadius: 12, border: '1px solid var(--line-2)', background: 'var(--surface-2)',
          fontSize: 15, fontWeight: 700, color: 'var(--ink)', outline: 'none', fontFamily: 'inherit', marginBottom: 18,
        }} />

        {/* 급수 */}
        <label style={labelStyle}>급수</label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 18 }}>
          {LEVEL_ORDER.map((lv) => (
            <button key={lv} onClick={() => setLevel(lv)} style={{
              padding: '9px 15px', borderRadius: 10, fontSize: 14, fontWeight: 800, letterSpacing: '-.02em', whiteSpace: 'nowrap',
              background: level === lv ? 'var(--brand)' : 'var(--surface)', color: level === lv ? '#fff' : 'var(--ink-2)',
              border: level === lv ? '1px solid var(--brand)' : '1px solid var(--line-2)',
            }}>{lv}</button>
          ))}
        </div>

        {/* 성별 */}
        <label style={labelStyle}>성별</label>
        <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
          {[['M', '남자', 'var(--men)'], ['F', '여자', 'var(--women)']].map(([g, l, col]) => (
            <button key={g} onClick={() => setGender(g)} style={{
              flex: 1, padding: '12px', borderRadius: 12, fontSize: 15, fontWeight: 800, letterSpacing: '-.02em',
              background: gender === g ? col : 'var(--surface)', color: gender === g ? '#fff' : 'var(--ink-2)',
              border: gender === g ? `1px solid ${col}` : '1px solid var(--line-2)',
            }}>{l}</button>
          ))}
        </div>

        <Btn variant="primary" size="lg" full disabled={!ok} onClick={submit}>추가</Btn>
      </div>
    </ModalShell>
  );
}

// ---------- 참가자 편집 (바텀시트) ----------
function EditParticipantModal({ p, onSave, onClose }) {
  const [name, setName] = useState(p.name || '');
  const [level, setLevel] = useState(p.level || '');
  const [gender, setGender] = useState(p.gender || '');
  const nameRef = useRef(null);
  useEffect(() => {
    const t = setTimeout(() => { if (nameRef.current) nameRef.current.focus({ preventScroll: true }); }, 340);
    return () => clearTimeout(t);
  }, []);
  const ok = name.trim() !== '' && level !== '' && gender !== '';
  const submit = () => { if (ok) onSave(p.id, { name: name.trim(), level, gender }); };
  const labelStyle = { fontSize: 13, fontWeight: 800, color: 'var(--ink-2)', letterSpacing: '-.02em', marginBottom: 8, display: 'block' };
  return (
    <ModalShell onClose={onClose} width={460}>
      <div style={{ padding: 24 }}>
        <div style={{ fontSize: 19, fontWeight: 900, letterSpacing: '-.03em', color: 'var(--ink)' }}>참가자 편집</div>
        <div style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600, marginTop: 4, marginBottom: 20 }}>이름·급수·성별을 수정해요.</div>

        {/* 이름 */}
        <label style={labelStyle}>이름</label>
        <input ref={nameRef} value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') submit(); }} placeholder="이름 입력" maxLength={12} style={{
          width: '100%', padding: '12px 14px', borderRadius: 12, border: '1px solid var(--line-2)', background: 'var(--surface-2)',
          fontSize: 15, fontWeight: 700, color: 'var(--ink)', outline: 'none', fontFamily: 'inherit', marginBottom: 18,
        }} />

        {/* 급수 */}
        <label style={labelStyle}>급수</label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginBottom: 18 }}>
          {LEVEL_ORDER.map((lv) => (
            <button key={lv} onClick={() => setLevel(lv)} style={{
              padding: '9px 15px', borderRadius: 10, fontSize: 14, fontWeight: 800, letterSpacing: '-.02em', whiteSpace: 'nowrap',
              background: level === lv ? 'var(--brand)' : 'var(--surface)', color: level === lv ? '#fff' : 'var(--ink-2)',
              border: level === lv ? '1px solid var(--brand)' : '1px solid var(--line-2)',
            }}>{lv}</button>
          ))}
        </div>

        {/* 성별 */}
        <label style={labelStyle}>성별</label>
        <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
          {[['M', '남자', 'var(--men)'], ['F', '여자', 'var(--women)']].map(([g, l, col]) => (
            <button key={g} onClick={() => setGender(g)} style={{
              flex: 1, padding: '12px', borderRadius: 12, fontSize: 15, fontWeight: 800, letterSpacing: '-.02em',
              background: gender === g ? col : 'var(--surface)', color: gender === g ? '#fff' : 'var(--ink-2)',
              border: gender === g ? `1px solid ${col}` : '1px solid var(--line-2)',
            }}>{l}</button>
          ))}
        </div>

        <Btn variant="primary" size="lg" full disabled={!ok} onClick={submit}>저장</Btn>
      </div>
    </ModalShell>
  );
}

// 개인 경기기록 시트 — 총 경기·종목별·파트너/상대 이력
function RecordSheet({ p, participants, onClose }) {
  const nameOf = (id) => (participants.find((x) => x.id === id) || {}).name || '?';
  const partners = Object.entries(p.partnerCount || {}).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]);
  const opps = Object.entries(p.opponentCount || {}).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]);
  const g = p.games || { 혼복: 0, 남복: 0, 여복: 0 };
  const Tag = ({ id, n }) => (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '5px 10px', borderRadius: 999, background: 'var(--surface-2)', border: '1px solid var(--line)', fontSize: 12.5, fontWeight: 700, color: 'var(--ink-2)' }}>
      {nameOf(id)}<span style={{ color: 'var(--brand-ink)', fontWeight: 900 }}>{n}</span>
    </span>
  );
  return (
    <ModalShell onClose={onClose} width={460}>
      <div style={{ padding: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
          <LevelChip level={p.level} size={34} />
          <div style={{ flex: 1, minWidth: 0 }}><NameWithGender p={p} size={19} /></div>
          <div style={{ textAlign: 'center', flexShrink: 0 }}>
            <div style={{ fontSize: 26, fontWeight: 900, color: 'var(--brand-ink)', lineHeight: 1, letterSpacing: '-.03em' }}>{p.totalGames}</div>
            <div style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 700, marginTop: 2 }}>총 경기</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          {[['혼복', g.혼복, 'mix'], ['남복', g.남복, 'men'], ['여복', g.여복, 'women']].map(([label, n, c]) => (
            <div key={label} style={{ flex: 1, background: `var(--${c}-tint)`, border: `1px solid var(--${c}-line)`, borderRadius: 12, padding: '11px 8px', textAlign: 'center' }}>
              <div style={{ fontSize: 21, fontWeight: 900, color: `var(--${c}-ink)`, lineHeight: 1 }}>{n}</div>
              <div style={{ fontSize: 11.5, fontWeight: 800, color: `var(--${c}-ink)`, marginTop: 5 }}>{label}</div>
            </div>
          ))}
        </div>
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--ink-2)', marginBottom: 9 }}>함께 뛴 파트너 <span style={{ color: 'var(--muted)', fontWeight: 700 }}>{partners.length}명</span></div>
          {partners.length ? <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>{partners.map(([id, n]) => <Tag key={id} id={id} n={n} />)}</div> : <div style={{ fontSize: 12.5, color: 'var(--muted)', fontWeight: 600 }}>아직 없어요</div>}
        </div>
        <div style={{ marginBottom: 22 }}>
          <div style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--ink-2)', marginBottom: 9 }}>맞붙은 상대 <span style={{ color: 'var(--muted)', fontWeight: 700 }}>{opps.length}명</span></div>
          {opps.length ? <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>{opps.map(([id, n]) => <Tag key={id} id={id} n={n} />)}</div> : <div style={{ fontSize: 12.5, color: 'var(--muted)', fontWeight: 600 }}>아직 없어요</div>}
        </div>
        <Btn variant="ghost" size="lg" full onClick={onClose}>닫기</Btn>
      </div>
    </ModalShell>
  );
}

function AttendanceScreen({ state, actions }) {
  const { participants } = state;
  const [filter, setFilter] = useState('전체');
  const [query, setQuery] = useState('');
  // 추첨: 참여중에서 1명, 중복 제외(localStorage 영구), 0.6초 룰렛 후 발표
  const [drawResult, setDrawResult] = useState(null); // { name, level, gender } | null
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
  // 파트너 묶기 모드
  const [pairing, setPairing] = useState(false);
  const [psel, setPsel] = useState([]); // 선택된 2명
  const [pstrict, setPstrict] = useState(false); // 같이만(strict)
  const pairs = state.pairs || [];
  const reqs = state.pairRequests || [];
  const reqName = (pid) => (participants.find((p) => p.id === pid) || {}).name;
  const partnerName = {};
  pairs.forEach((pr) => {
    const nx = (participants.find((p) => p.id === pr.members[0]) || {}).name;
    const ny = (participants.find((p) => p.id === pr.members[1]) || {}).name;
    partnerName[pr.members[0]] = ny; partnerName[pr.members[1]] = nx;
  });
  const pselHas = (p) => psel.some((x) => x.id === p.id);
  const togglePsel = (p) => setPsel((s) => s.find((x) => x.id === p.id) ? s.filter((x) => x.id !== p.id) : (s.length < 2 ? [...s, p] : [s[1], p]));
  const doPair = () => { if (psel.length === 2) { actions.addPair(psel.map((p) => p.id), pstrict); setPsel([]); setPstrict(false); } };
  // 모임장이 두 분께 그대로 읽어줄 안내 멘트 (종목·strict 반영)
  const pairMsg = () => {
    if (psel.length !== 2) return '';
    const m = psel.filter((p) => p.gender === 'M').length;
    const type = m === 2 ? '남복' : m === 0 ? '여복' : '혼복';
    const other = type === '혼복' ? '남복/여복' : '혼복';
    return pstrict
      ? `${type} 경기에선 항상 두 분이 같은 팀이에요. ${other} 경기가 돌 땐 두 분은 대기해서 경기 수가 적을 수 있어요.`
      : `${type} 경기에선 항상 두 분이 같은 팀이에요. ${other} 경기에선 각자 따로 들어갈 수 있고, 경기 수는 일반보다 조금 적을 수 있어요.`;
  };
  const counts = {
    전체: participants.length,
    미출석: participants.filter((p) => p.status === '미출석').length,
    참여중: participants.filter((p) => p.status === '참여중').length,
    퇴장: participants.filter((p) => p.status === '퇴장').length,
  };
  const q = query.trim();
  const pairedIds = new Set(pairs.flatMap((pr) => pr.members));
  const list = participants.filter((p) => (filter === '전체' || p.status === filter) && (q === '' || p.name.includes(q) || p.level.includes(q)) && !pairedIds.has(p.id));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg)' }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '14px 22px', background: 'var(--surface)', borderBottom: '1px solid var(--line)', boxShadow: 'var(--sh-1)', flexShrink: 0 }}>
        <button onClick={() => actions.switchScreen('main')} style={{ ...navBtnStyle, padding: '9px 14px' }}>← 운영 화면</button>
        <div>
          <div style={{ fontSize: 18, fontWeight: 900, letterSpacing: '-.03em', color: 'var(--ink)', lineHeight: 1 }}>출석 체크</div>
          <div style={{ fontSize: 12.5, color: 'var(--muted)', fontWeight: 600, marginTop: 4 }}>온 사람만 체크인하면 대진에 들어갑니다. 늦참·조퇴는 언제든 토글.</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={() => actions.refresh ? actions.refresh() : location.reload()} title="새로고침" aria-label="새로고침" style={{ ...navBtnStyle, padding: '9px 12px', fontSize: 17, lineHeight: 1 }}>↻</button>
          <button onClick={handleDraw} title={`참여중에서 1명 추첨 (남은 대상 ${drawPool.length}명)`} aria-label="추첨" style={{ ...navBtnStyle, padding: '9px 12px', fontSize: 14, lineHeight: 1, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            추첨 <span style={{ opacity: 0.55, fontWeight: 700, fontSize: 12.5 }}>{drawPool.length}</span>
          </button>
          <Stat label="참여중" value={counts.참여중} accent="var(--brand-ink)" />
          <Stat label="미출석" value={counts.미출석} accent="var(--muted)" />
        </div>
      </div>

      {/* 필터 + 검색 */}
      <div style={{ padding: '14px 22px 0', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'inline-flex', gap: 8 }}>
          {['전체', '미출석', '참여중', '퇴장'].map((f) => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: '9px 16px', borderRadius: 999, fontSize: 14, fontWeight: 800, letterSpacing: '-.02em',
              background: filter === f ? 'var(--ink)' : 'var(--surface)', color: filter === f ? '#fff' : 'var(--ink-2)',
              border: filter === f ? 'none' : '1px solid var(--line-2)',
            }}>{f} <span style={{ opacity: 0.6 }}>{counts[f]}</span></button>
          ))}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" style={{ position: 'absolute', left: 13, pointerEvents: 'none' }}><circle cx="11" cy="11" r="7" stroke="var(--muted)" strokeWidth="2" /><path d="M20 20l-3.2-3.2" stroke="var(--muted)" strokeWidth="2" strokeLinecap="round" /></svg>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="이름·급수로 검색" style={{
              width: 220, padding: '10px 34px 10px 38px', borderRadius: 999, border: '1px solid var(--line-2)',
              background: 'var(--surface)', fontSize: 14, fontWeight: 600, color: 'var(--ink)', outline: 'none', fontFamily: 'inherit',
            }} />
            {query && <button onClick={() => setQuery('')} style={{ position: 'absolute', right: 10, width: 20, height: 20, borderRadius: 10, background: 'var(--surface-3)', color: 'var(--muted)', fontSize: 12, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>}
          </div>
          <button onClick={() => { setPairing((v) => !v); setPsel([]); }} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 15px', borderRadius: 999, background: pairing ? 'var(--brand)' : 'var(--surface)', color: pairing ? '#fff' : 'var(--ink-2)', border: pairing ? 'none' : '1px solid var(--line-2)', fontSize: 14, fontWeight: 800, letterSpacing: '-.02em', whiteSpace: 'nowrap', flexShrink: 0 }}>
            {pairing ? '묶기 종료' : '파트너 묶기'}
            {!pairing && reqs.length > 0 && <span style={{ minWidth: 18, height: 18, padding: '0 5px', borderRadius: 999, background: 'var(--danger)', color: '#fff', fontSize: 11, fontWeight: 900, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>{reqs.length}</span>}
          </button>
          <button onClick={() => actions.openAddParticipant()} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 16px', borderRadius: 999, background: 'var(--ink)', color: '#fff', fontSize: 14, fontWeight: 800, letterSpacing: '-.02em', whiteSpace: 'nowrap', flexShrink: 0 }}>
            <span style={{ fontSize: 17, lineHeight: 1, marginTop: -1 }}>＋</span> 참가자 추가
          </button>
        </div>
      </div>
      {pairing && (
        <div style={{ padding: '10px 22px 0', flexShrink: 0 }}>
          <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--brand-ink)', background: 'var(--brand-tint)', border: '1px solid rgba(18,165,101,.3)', borderRadius: 10, padding: '9px 13px' }}>
            파트너로 게임하고 싶은 <b>2명</b>을 선택해주세요. 같은 종목 경기에선 항상 같은 팀으로 들어갈 수 있어요.
          </div>
        </div>
      )}
      {/* 참가자 파트너 신청 (승인 대기) */}
      {!pairing && reqs.length > 0 && (
        <div style={{ padding: '10px 22px 0', flexShrink: 0 }}>
          <div style={{ background: 'var(--warn-tint)', border: '1px solid var(--warn)', borderRadius: 12, padding: '12px 14px' }}>
            <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--warn)', marginBottom: 9 }}>👥 파트너 신청 {reqs.length}건 있어요 — 승인해주세요</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {reqs.map((r) => (
                <div key={r.id} style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'var(--surface)', borderRadius: 11, padding: '8px 8px 8px 13px', border: '1px solid var(--line)' }}>
                  <span style={{ fontSize: 14, fontWeight: 800, color: 'var(--ink)', whiteSpace: 'nowrap' }}>{reqName(r.from)} · {reqName(r.to)}</span>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <button onClick={() => actions.rejectPairRequest(r.id)} style={{ padding: '6px 12px', borderRadius: 8, background: 'var(--surface-3)', border: '1px solid var(--line-2)', color: 'var(--ink-2)', fontSize: 12.5, fontWeight: 800, cursor: 'pointer' }}>거절</button>
                    <button onClick={() => actions.approvePairRequest(r.id)} style={{ padding: '6px 14px', borderRadius: 8, background: 'var(--brand)', border: 'none', color: '#fff', fontSize: 12.5, fontWeight: 800, cursor: 'pointer' }}>승인</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 카드 그리드 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 22 }}>
        {/* 파트너 묶음 (일반 명단에서 빼서 박스로) */}
        {!pairing && pairs.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '0 2px 10px' }}>
              <span style={{ fontSize: 14, fontWeight: 900, letterSpacing: '-.02em', color: 'var(--ink)' }}>👥 파트너 {pairs.length}쌍</span>
              <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)' }}>둘이 항상 같은 팀</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
              {pairs.map((pr) => {
                const mem = pr.members.map((id) => participants.find((p) => p.id === id)).filter(Boolean);
                return (
                  <div key={pr.id} style={{ background: 'var(--brand-tint)', border: '1px solid var(--brand)', borderRadius: 16, padding: 12 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 9, padding: '0 2px' }}>
                      <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--brand-ink)' }}>파트너</span>
                      {pr.strict && <span style={{ fontSize: 10, fontWeight: 800, color: '#fff', background: 'var(--brand)', padding: '1px 6px', borderRadius: 5 }}>같이만</span>}
                      <button onClick={() => actions.removePair(pr.id)} style={{ marginLeft: 'auto', fontSize: 11.5, fontWeight: 800, color: 'var(--muted)', padding: '3px 8px', borderRadius: 7, background: 'var(--surface)', border: '1px solid var(--line-2)', cursor: 'pointer' }}>해제</button>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {mem.map((p) => {
                        const st = STATUS_STYLE[p.status];
                        return (
                          <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 9, background: 'var(--surface)', borderRadius: 11, padding: '9px 11px' }}>
                            <LevelChip level={p.level} size={26} />
                            <div style={{ flex: 1, minWidth: 0 }}><NameWithGender p={p} size={15} /></div>
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 8px', borderRadius: 999, background: st.bg, color: st.fg, fontSize: 11.5, fontWeight: 800, flexShrink: 0 }}>
                              <span style={{ width: 6, height: 6, borderRadius: 6, background: st.dot }} />{st.label}
                            </span>
                            {p.status !== '참여중' ? (
                              <button onClick={() => actions.setStatus(p.id, '참여중')} style={{ padding: '6px 11px', borderRadius: 8, background: 'var(--brand)', color: '#fff', border: 'none', fontSize: 12, fontWeight: 800, cursor: 'pointer', flexShrink: 0 }}>출석</button>
                            ) : (
                              <button onClick={() => actions.setStatus(p.id, '퇴장')} style={{ padding: '6px 11px', borderRadius: 8, background: 'var(--surface-3)', color: 'var(--danger)', border: '1px solid var(--line-2)', fontSize: 12, fontWeight: 800, cursor: 'pointer', flexShrink: 0 }}>퇴장</button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
          {list.map((p) => {
            const st = STATUS_STYLE[p.status];
            const sel = pselHas(p);
            const mate = partnerName[p.id];
            return (
              <div key={p.id} onClick={pairing ? () => togglePsel(p) : undefined} style={{
                background: sel ? 'var(--brand-tint)' : 'var(--surface)', borderRadius: 16, padding: 14,
                border: sel ? '2px solid var(--brand)' : '1px solid var(--line)',
                boxShadow: 'var(--sh-1)', display: 'flex', flexDirection: 'column', gap: 12,
                opacity: p.status === '퇴장' ? 0.7 : 1, transition: 'opacity .2s',
                cursor: pairing ? 'pointer' : 'default',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
                  <LevelChip level={p.level} size={30} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <NameWithGender p={p} size={17} />
                    {mate && <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--brand-ink)', marginTop: 2 }}>👥 파트너 · {mate}</div>}
                  </div>
                  {pairing ? (
                    <span style={{ width: 22, height: 22, borderRadius: 7, flexShrink: 0, border: sel ? 'none' : '1.5px solid var(--line-2)', background: sel ? 'var(--brand)' : 'transparent', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                      {sel && <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M5 12.5l4.5 4.5L19 7" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" /></svg>}
                    </span>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 10px', borderRadius: 999, background: st.bg, color: st.fg, fontSize: 12.5, fontWeight: 800 }}>
                        <span style={{ width: 7, height: 7, borderRadius: 7, background: st.dot }} />{st.label}
                      </span>
                      <button onClick={() => actions.openEditParticipant(p)} title="편집" style={{ width: 30, height: 30, borderRadius: 9, border: '1px solid var(--line-2)', background: 'var(--surface)', color: 'var(--ink-2)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', flexShrink: 0 }}>
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none"><path d="M4 20h4L18.5 9.5a2.12 2.12 0 0 0-3-3L5 17v3z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /><path d="M13 7l3 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
                      </button>
                    </div>
                  )}
                </div>
                {/* 액션 버튼 (파트너 모드에선 숨김) */}
                {!pairing && (
                <div style={{ display: 'flex', gap: 8 }}>
                  {p.status === '참여중' ? (
                    <>
                      <Btn variant="soft" size="md" onClick={() => actions.setStatus(p.id, '미출석')} style={{ flex: 1, color: 'var(--ink-2)' }}>출석 취소</Btn>
                      <Btn variant="ghost" size="md" onClick={() => actions.setStatus(p.id, '퇴장')} style={{ color: 'var(--danger)', borderColor: 'var(--line-2)' }}>퇴장</Btn>
                    </>
                  ) : (
                    <Btn variant="primary" size="md" full onClick={() => actions.setStatus(p.id, '참여중')} style={{ flex: 1 }}>{p.status === '퇴장' ? '재합류' : '출석 체크'}</Btn>
                  )}
                  <Btn variant="ghost" size="md" onClick={() => actions.openRecord(p)}>기록</Btn>
                </div>
                )}
              </div>
            );
          })}
        </div>
        {list.length === 0 && (
          <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--muted)' }}>
            <div style={{ fontSize: 15, fontWeight: 700 }}>'{q}' 검색 결과가 없습니다</div>
            <div style={{ fontSize: 13, marginTop: 4 }}>이름 또는 급수로 검색해 보세요.</div>
          </div>
        )}
      </div>

      {/* 파트너 묶기 하단 바 */}
      {pairing && psel.length > 0 && (
        <div style={{ flexShrink: 0, borderTop: '1px solid var(--line)', background: 'var(--surface)', padding: '12px 22px', boxShadow: '0 -4px 14px rgba(17,22,31,.06)', display: 'flex', flexDirection: 'column', gap: 11 }}>
          {psel.length === 2 && (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '9px 13px', borderRadius: 10, background: 'var(--brand-tint)', border: '1px solid rgba(18,165,101,.3)' }}>
              <span style={{ fontSize: 13.5, fontWeight: 800, color: 'var(--brand-ink)', flexShrink: 0, whiteSpace: 'nowrap' }}>📢 두 분께 안내</span>
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-2)', lineHeight: 1.55, letterSpacing: '-.01em' }}>“{pairMsg()}”</span>
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {psel.map((p) => (
              <span key={p.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 6px 6px 11px', borderRadius: 999, background: 'var(--brand-tint)', border: '1px solid rgba(18,165,101,.3)', fontSize: 13, fontWeight: 800, color: 'var(--brand-ink)' }}>
                {p.name}
                <button onClick={() => togglePsel(p)} style={{ width: 17, height: 17, borderRadius: 9, background: 'var(--brand)', color: '#fff', fontSize: 10, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>
              </span>
            ))}
            {psel.length === 1 && <span style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 700 }}>1명 더 선택</span>}
          </div>
          {/* 같이만 / 따로도 OK 토글 */}
          <div style={{ marginLeft: 'auto', display: 'inline-flex', background: 'var(--surface-3)', borderRadius: 9, padding: 3, gap: 2, flexShrink: 0 }}>
            {[['따로도 OK', false], ['같이만', true]].map(([l, v]) => (
              <button key={l} onClick={() => setPstrict(v)} title={v ? '같이 못 들어가는 종목이면 대기(경기수 적음)' : '같이 우선, 안 되면 따로 출전'} style={{
                padding: '7px 12px', borderRadius: 7, fontSize: 12.5, fontWeight: 800, letterSpacing: '-.02em', whiteSpace: 'nowrap',
                color: pstrict === v ? 'var(--ink)' : 'var(--muted)', background: pstrict === v ? 'var(--surface)' : 'transparent', boxShadow: pstrict === v ? 'var(--sh-2)' : 'none',
              }}>{l}</button>
            ))}
          </div>
          <button disabled={psel.length !== 2} onClick={doPair} style={{ flexShrink: 0, padding: '11px 20px', borderRadius: 11, fontSize: 14.5, fontWeight: 800, letterSpacing: '-.02em', background: psel.length === 2 ? 'var(--brand)' : 'var(--surface-3)', color: psel.length === 2 ? '#fff' : 'var(--muted)', cursor: psel.length === 2 ? 'pointer' : 'not-allowed' }}>파트너 묶기</button>
          </div>
        </div>
      )}

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
    </div>
  );
}

// ---------- 개인별 카운트 화면 ----------
function CountsScreen({ state, actions }) {
  const { participants } = state;
  const [gender, setGender] = useState('전체');
  const [query, setQuery] = useState('');
  const active = participants.filter((p) => p.status !== '미출석');
  const sorted = [...active].sort((a, b) => b.totalGames - a.totalGames);
  const max = Math.max(1, ...sorted.map((p) => p.totalGames));
  const gcount = { M: active.filter((p) => p.gender === 'M').length, F: active.filter((p) => p.gender === 'F').length };
  const q = query.trim();
  const list = sorted.filter((p) =>
    (gender === '전체' || p.gender === (gender === '남자' ? 'M' : 'F')) &&
    (q === '' || p.name.includes(q) || p.level.includes(q))
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '14px 22px', background: 'var(--surface)', borderBottom: '1px solid var(--line)', boxShadow: 'var(--sh-1)', flexShrink: 0 }}>
        <button onClick={() => actions.switchScreen('main')} style={{ ...navBtnStyle, padding: '9px 14px' }}>← 운영 화면</button>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <div style={{ fontSize: 18, fontWeight: 900, letterSpacing: '-.03em', color: 'var(--ink)', lineHeight: 1, whiteSpace: 'nowrap' }}>개인별 출전 카운트</div>
          <div style={{ fontSize: 12.5, color: 'var(--muted)', fontWeight: 600 }}>참가자들의 게임 횟수를 한 눈에 확인할 수 있어요.</div>
        </div>
      </div>

      {/* 성별 필터 + 검색 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 22px', background: 'var(--surface)', borderBottom: '1px solid var(--line)', flexShrink: 0 }}>
        <div style={{ display: 'flex', gap: 7 }}>
          {[['전체', active.length], ['남자', gcount.M], ['여자', gcount.F]].map(([f, n]) => (
            <button key={f} onClick={() => setGender(f)} style={{
              padding: '7px 14px', borderRadius: 9, fontSize: 13, fontWeight: 800, letterSpacing: '-.02em', whiteSpace: 'nowrap',
              background: gender === f ? 'var(--ink)' : 'var(--surface)', color: gender === f ? '#fff' : 'var(--ink-2)',
              border: gender === f ? 'none' : '1px solid var(--line-2)',
            }}>{f} {n}</button>
          ))}
        </div>
        <div style={{ position: 'relative', marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="이름·급수로 검색" style={{
            width: 200, padding: '8px 30px 8px 12px', borderRadius: 9, border: '1px solid var(--line-2)', background: 'var(--surface-2)', fontSize: 13, fontWeight: 600, color: 'var(--ink)', outline: 'none', fontFamily: 'inherit',
          }} />
          {query && <button onClick={() => setQuery('')} style={{ position: 'absolute', right: 8, width: 20, height: 20, borderRadius: 10, background: 'var(--surface-3)', color: 'var(--muted)', fontSize: 12, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>}
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 22 }}>
        <div style={{ maxWidth: 760, margin: '0 auto', background: 'var(--surface)', borderRadius: 18, border: '1px solid var(--line)', boxShadow: 'var(--sh-2)', overflow: 'hidden' }}>
          {list.map((p, i) => (
            <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '13px 18px', borderTop: i === 0 ? 'none' : '1px solid var(--line)' }}>
              <LevelChip level={p.level} size={28} />
              <div style={{ width: 132, flexShrink: 0 }}>
                <NameWithGender p={p} size={16} />
                <div style={{ fontSize: 11.5, color: p.court != null ? 'var(--brand-ink)' : 'var(--muted)', fontWeight: 700, marginTop: 3 }}>
                  {p.court != null ? `${p.court}번 코트 경기 중` : '대기'}
                </div>
              </div>
              {/* 막대 */}
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ flex: 1, height: 12, background: 'var(--surface-3)', borderRadius: 7, overflow: 'hidden', display: 'flex' }}>
                  {['혼복', '남복', '여복'].map((d) => {
                    const w = (p.games[d] / max) * 100;
                    const col = d === '혼복' ? 'var(--mix)' : d === '남복' ? 'var(--men)' : 'var(--women)';
                    return w > 0 ? <div key={d} style={{ width: w + '%', background: col }} /> : null;
                  })}
                </div>
                <span style={{ fontSize: 18, fontWeight: 900, color: 'var(--ink)', minWidth: 24, textAlign: 'right', letterSpacing: '-.03em' }}>{p.totalGames}</span>
              </div>
              <CountPills games={p.games} />
            </div>
          ))}
          {list.length === 0 && <div style={{ padding: 40, textAlign: 'center', color: 'var(--muted)' }}>{active.length === 0 ? '출석한 참가자가 없습니다.' : '검색 결과가 없습니다.'}</div>}
        </div>
      </div>
    </div>
  );
}

// ---------- 모달 셸 ----------
function ModalShell({ children, onClose, width = 460, center = false }) {
  const sheet = !center && useTheme() !== 'sporty';
  return (
    <div onClick={onClose} style={{
      position: 'absolute', inset: 0, background: 'rgba(17,22,31,.5)',
      display: 'flex', alignItems: sheet ? 'flex-end' : 'center', justifyContent: 'center', zIndex: 50, animation: 'fadeIn .18s ease',
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        width: sheet ? '100%' : width, maxWidth: sheet ? '100%' : '92%', maxHeight: sheet ? '90%' : '88%', overflowY: 'auto', background: 'var(--surface)',
        borderRadius: sheet ? '26px 26px 0 0' : 22, boxShadow: 'var(--sh-3)',
        animation: sheet ? 'sheetUp .3s cubic-bezier(.16,1,.3,1) both' : 'popIn .24s ease both',
      }}>
        {sheet && <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 10 }}><div style={{ width: 42, height: 5, borderRadius: 5, background: 'var(--line-2)' }} /></div>}
        {children}
      </div>
    </div>
  );
}

// ---------- 추첨 결과 모달 (0.6초 룰렛 → 발표) ----------
function DrawModal({ winner, pool, drawnCount, onClose, onAgain, onReset }) {
  // 룰렛 단계: 0.6초 동안 이름들이 빠르게 휙휙 바뀌다 winner로 고정
  const [rolling, setRolling] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (pool.length <= 1) { setRolling(false); return; }
    const start = Date.now();
    const id = setInterval(() => {
      if (Date.now() - start >= 600) { setRolling(false); clearInterval(id); return; }
      setTick((t) => t + 1);
    }, 55);
    return () => clearInterval(id);
  }, []);
  const display = rolling ? pool[tick % pool.length] : winner;
  const genderColor = display.gender === 'F' ? 'var(--women)' : 'var(--men)';
  return (
    <ModalShell onClose={rolling ? () => {} : onClose} width={460} center>
      <div style={{ padding: 32, textAlign: 'center' }}>
        <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--muted)', letterSpacing: '.05em', marginBottom: 18 }}>추첨 결과</div>
        <div style={{
          fontSize: 56, fontWeight: 900, letterSpacing: '-.04em', color: 'var(--ink)', lineHeight: 1.05,
          minHeight: 70, display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: rolling ? 'none' : 'transform .2s ease', transform: rolling ? 'none' : 'scale(1.04)',
        }}>{display.name}</div>
        <div style={{ display: 'inline-flex', gap: 8, marginTop: 14, alignItems: 'center' }}>
          <span style={{ padding: '5px 11px', borderRadius: 999, fontSize: 13, fontWeight: 800, background: 'var(--brand-tint)', color: 'var(--brand-ink)' }}>{display.level}</span>
          <span style={{ padding: '5px 11px', borderRadius: 999, fontSize: 13, fontWeight: 800, background: genderColor, color: '#fff' }}>{display.gender === 'F' ? '여자' : '남자'}</span>
        </div>
        <div style={{ fontSize: 12.5, color: 'var(--muted)', fontWeight: 700, marginTop: 18 }}>
          {drawnCount} / {pool.length} 추첨 완료
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 24 }}>
          <button onClick={onReset} disabled={rolling} style={{
            flex: 1, padding: '12px', borderRadius: 12, fontSize: 14, fontWeight: 800, letterSpacing: '-.02em',
            background: 'var(--surface-2)', color: 'var(--ink-2)', border: '1px solid var(--line-2)',
            opacity: rolling ? 0.5 : 1, cursor: rolling ? 'not-allowed' : 'pointer',
          }}>기록 초기화</button>
          <button onClick={onAgain} disabled={rolling} style={{
            flex: 1, padding: '12px', borderRadius: 12, fontSize: 14, fontWeight: 800, letterSpacing: '-.02em',
            background: 'var(--surface-2)', color: 'var(--ink-2)', border: '1px solid var(--line-2)',
            opacity: rolling ? 0.5 : 1, cursor: rolling ? 'not-allowed' : 'pointer',
          }}>한 번 더</button>
          <button onClick={onClose} disabled={rolling} style={{
            flex: 1.4, padding: '12px', borderRadius: 12, fontSize: 14.5, fontWeight: 800, letterSpacing: '-.02em',
            background: rolling ? 'var(--surface-3)' : 'var(--brand)', color: '#fff', border: 'none',
            cursor: rolling ? 'not-allowed' : 'pointer',
          }}>{rolling ? '추첨 중…' : '닫기'}</button>
        </div>
      </div>
    </ModalShell>
  );
}

// ---------- 혼복 부족 알림 모달 ----------
function AlertModal({ court, rec, onPick, onClose }) {
  const sugg = rec.suggestion;
  return (
    <ModalShell onClose={onClose} width={440}>
      <div style={{ padding: 26 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
          <div style={{ width: 46, height: 46, borderRadius: 14, background: 'var(--warn-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24 }}>⚠️</div>
          <div>
            <div style={{ fontSize: 19, fontWeight: 900, letterSpacing: '-.03em', color: 'var(--ink)' }}>혼복 인원이 부족합니다</div>
            <div style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600, marginTop: 2 }}>{court.no}번 코트 · 대기 남 {rec.m}명 / 여 {rec.f}명</div>
          </div>
        </div>
        <p style={{ fontSize: 14.5, color: 'var(--ink-2)', lineHeight: 1.6, margin: '0 0 20px', fontWeight: 500 }}>
          현재 대기 성비로는 혼복 팀을 만들 수 없어요. 코트를 놀리지 않으려면 종목을 양보할 수 있습니다.
          {sugg && <> 가장 자연스러운 대안은 <b style={{ color: 'var(--ink)' }}>{sugg}</b>입니다.</>}
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
          {sugg && <Btn variant="primary" size="lg" full onClick={() => onPick(sugg)}>{sugg}(으)로 이 코트 채우기</Btn>}
          <Btn variant="ghost" size="lg" full onClick={onClose}>비워두고 대기 (인원 충원 대기)</Btn>
        </div>
      </div>
    </ModalShell>
  );
}

// ---------- 경기 편집 모달 (사람 swap) ----------
function EditModal({ court, match, bench, onConfirm, onClose, participants, coachIds, onTogglePin, isPending = false }) {
  const init = match ? [...match.teamA, ...match.teamB] : [];
  const [slots, setSlots] = useState(init);
  const [type, setType] = useState(match ? match.type : '혼복');
  const [picking, setPicking] = useState(null); // 교체할 슬롯 index
  const [showCoach, setShowCoach] = useState(false);
  const [q, setQ] = useState(''); // 교체 후보 이름 검색
  const [genderF, setGenderF] = useState('all'); // 'all' | 'M' | 'F'
  const [sortM, setSortM] = useState('smart'); // smart(비슷한 급수·같은 성별) | level(급수순) | wait(대기순)
  const [justReplaced, setJustReplaced] = useState(null); // 방금 교체된 슬롯 idx (잠깐 하이라이트)
  const coachSet = new Set(coachIds || []);
  // 코치 후보: 대기 중(court==null)이거나 이미 코치인 자강·S. 일반 경기 중인 사람은 빼면 원래 코트에 팬텀으로 남는 것 방지
  const candidates = (participants || []).filter((p) => p.status === '참여중' && (p.level === '자강' || p.level === 'S') && (p.court == null || coachSet.has(p.id)));
  const isAce = !!court.ace;
  const thisCoach = isAce && court.coachId ? (participants || []).find((p) => p.id === court.coachId) : null;
  const pin = (cid) => onTogglePin && onTogglePin(cid, court.no); // togglePinned가 모달 닫음
  const unpin = () => onTogglePin && onTogglePin(null, court.no);

  const CoachList = () => candidates.length > 0 ? (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7 }}>
      {candidates.map((p) => {
        const here = p.id === court.coachId;
        const elsewhere = coachSet.has(p.id) && !here;
        return (
          <button key={p.id} onClick={() => !here && pin(p.id)} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 13px', borderRadius: 10, fontSize: 13.5, fontWeight: 800, background: here ? '#eef0ff' : 'var(--surface)', border: `1px solid ${here ? '#d9ddff' : 'var(--line-2)'}`, color: here ? 'var(--hl)' : 'var(--ink-2)', whiteSpace: 'nowrap', opacity: elsewhere ? 0.65 : 1 }}>
            {p.name} <span style={{ fontSize: 11.5, color: 'var(--muted)' }}>{p.level}{elsewhere ? ' · 타코트' : ''}</span>
          </button>
        );
      })}
    </div>
  ) : (
    <div style={{ fontSize: 12.5, color: 'var(--muted)', fontWeight: 600 }}>고정할 자강·S 급수 참여 인원이 없습니다.</div>
  );

  // ===== 코치 코트: 코치 관리 전용 =====
  if (isAce) {
    return (
      <ModalShell onClose={onClose} width={460}>
        <div style={{ padding: 24 }}>
          <div style={{ fontSize: 19, fontWeight: 900, letterSpacing: '-.03em', color: 'var(--ink)' }}>{court.name || court.no + '번 코트'} · 👑 코치 고정</div>
          <div style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600, marginTop: 4, marginBottom: 18 }}>코치 고정 코트예요. 코치를 바꾸거나 해제할 수 있어요.</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', borderRadius: 12, background: '#eef0ff', border: '1px solid #d9ddff', marginBottom: 16 }}>
            <span style={{ fontSize: 15, fontWeight: 800, color: 'var(--hl)' }}>{thisCoach ? thisCoach.name : '코치'} {thisCoach ? <span style={{ fontWeight: 700 }}>({thisCoach.level})</span> : null} 고정 중</span>
            <button onClick={unpin} style={{ marginLeft: 'auto', padding: '7px 14px', borderRadius: 9, background: 'var(--surface)', border: '1px solid var(--line-2)', color: 'var(--danger)', fontSize: 13, fontWeight: 800 }}>해제</button>
          </div>
          <div style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--ink-2)', marginBottom: 8 }}>코치 변경</div>
          <CoachList />
          <div style={{ marginTop: 20 }}>
            <Btn variant="ghost" size="lg" full onClick={onClose}>닫기</Btn>
          </div>
        </div>
      </ModalShell>
    );
  }

  const replace = (q) => {
    const idx = picking;
    const next = [...slots];
    next[idx] = q;
    setSlots(next);
    setPicking(null);
    setJustReplaced(idx);
    setTimeout(() => setJustReplaced((cur) => (cur === idx ? null : cur)), 900);
  };
  const teamA = [slots[0], slots[1]];
  const teamB = [slots[2], slots[3]];

  // 교체 후보 계산 — 검색·성별 필터 + 정렬(스마트=탭한 선수와 비슷한 급수·같은 성별 우선)
  const LS = (typeof window !== 'undefined' && window.LEVEL_SCORE) || {};
  const target = picking != null ? slots[picking] : null;
  const qq = q.trim().toLowerCase();
  let cands = bench.filter((b) => !slots.some((s) => s && s.id === b.id));
  cands = cands.filter((b) => (qq === '' || b.name.toLowerCase().includes(qq)) && (genderF === 'all' || b.gender === genderF));
  if (sortM === 'level') cands = [...cands].sort((a, b) => (LS[b.level] || 0) - (LS[a.level] || 0));
  else if (sortM === 'smart' && target) cands = [...cands].sort((a, b) => {
    const sc = (x) => (x.gender === target.gender ? 0 : 100) + Math.abs((LS[x.level] || 0) - (LS[target.level] || 0));
    return sc(a) - sc(b);
  });
  const chip = (opts, val, setter) => (
    <div style={{ display: 'inline-flex', background: 'var(--surface-3)', borderRadius: 8, padding: 2, gap: 2 }}>
      {opts.map((o) => (
        <button key={o.v} onClick={() => setter(o.v)} style={{ padding: '5px 10px', borderRadius: 6, fontSize: 11.5, fontWeight: 800, letterSpacing: '-.02em', whiteSpace: 'nowrap', color: val === o.v ? 'var(--ink)' : 'var(--muted)', background: val === o.v ? 'var(--surface)' : 'transparent', boxShadow: val === o.v ? 'var(--sh-1)' : 'none' }}>{o.l}</button>
      ))}
    </div>
  );
  const restMinOf = (p) => (p.lastFinished == null ? null : Math.round((Date.now() - p.lastFinished) / 60000));

  return (
    <ModalShell onClose={onClose} width={560}>
      <div style={{ display: 'flex', flexDirection: 'column', height: 760, maxHeight: '90vh' }}>
        {/* ① 고정 상단: 제목·종목·슬롯 */}
        <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <div style={{ fontSize: 19, fontWeight: 900, letterSpacing: '-.03em', color: 'var(--ink)', whiteSpace: 'nowrap' }}>{isPending ? '예약 경기 편집' : court.no + '번 코트 경기 편집'}</div>
            <DisciplineBadge type={type} size="lg" />
          </div>
          <div style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600, marginBottom: 14 }}>바꿀 선수를 탭하면 아래에서 대타를 고를 수 있어요.</div>

          {onTogglePin && (
            <div style={{ marginBottom: 14, padding: '12px 14px', borderRadius: 12, background: showCoach ? '#eef0ff' : 'var(--surface-2)', border: `1px solid ${showCoach ? '#d9ddff' : 'var(--line)'}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 14, fontWeight: 800, color: showCoach ? 'var(--hl)' : 'var(--ink)' }}>👑 코치 고정</span>
                <span style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--muted)' }}>이 코트에 코치 1명 고정 · 모두 한 번씩</span>
                <button onClick={() => setShowCoach((v) => !v)} aria-label="코치 고정 토글" style={{ marginLeft: 'auto', width: 42, height: 24, borderRadius: 999, background: showCoach ? 'var(--hl)' : 'var(--line-2)', position: 'relative', flexShrink: 0, transition: 'background .15s' }}>
                  <span style={{ position: 'absolute', top: 3, left: showCoach ? 21 : 3, width: 18, height: 18, borderRadius: 999, background: '#fff', boxShadow: '0 1px 2px rgba(17,22,31,.2)', transition: 'left .15s' }} />
                </button>
              </div>
              {showCoach && (<div style={{ marginTop: 12 }}><CoachList /></div>)}
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
            {['혼복', '남복', '여복'].map((t) => (
              <button key={t} onClick={() => setType(t)} style={{ flex: 1, padding: '9px 0', borderRadius: 10, fontSize: 14, fontWeight: 800, border: type === t ? `2px solid var(--${disciplineColor(t)})` : '1px solid var(--line-2)', background: type === t ? `var(--${disciplineColor(t)}-tint)` : 'var(--surface)', color: type === t ? `var(--${disciplineColor(t)}-ink)` : 'var(--ink-2)' }}>{t}</button>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 12 }}>
            {[{ team: teamA, label: '팀 A', base: 0 }, { team: teamB, label: '팀 B', base: 2 }].map((side) => (
              <div key={side.label} style={{ flex: 1, background: 'var(--surface-2)', borderRadius: 14, padding: 12 }}>
                <div style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--muted)', marginBottom: 8 }}>{side.label}</div>
                {side.team.map((p, j) => {
                  const idx = side.base + j;
                  const hot = picking === idx || justReplaced === idx;
                  return (
                    <button key={idx} onClick={() => setPicking(idx)} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: 9, padding: 8, borderRadius: 10, marginBottom: j === 0 ? 6 : 0, background: hot ? 'var(--brand-tint)' : 'var(--surface)', border: hot ? '2px solid var(--brand)' : '1px solid var(--line)', textAlign: 'left', transition: 'background .3s ease, border-color .3s ease' }}>
                      {p ? <><LevelChip level={p.level} size={22} /><NameWithGender p={p} size={15} /></> : <span style={{ color: 'var(--muted)', fontSize: 14 }}>빈 자리</span>}
                      <span style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 700, color: justReplaced === idx ? 'var(--brand-ink)' : 'var(--brand-ink)', whiteSpace: 'nowrap' }}>{picking === idx ? '선택 ↓' : justReplaced === idx ? '교체됨 ✓' : (p ? '교체' : '선택')}</span>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>

        {/* ② 스크롤: 필터 + 교체 후보 리스트 */}
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', padding: '12px 24px 0' }}>
          {picking != null && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, padding: '8px 12px', borderRadius: 10, background: 'var(--brand-tint)', border: '1px solid var(--brand)' }}>
              <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--brand-ink)' }}>{target ? <><b>{target.name}</b> 자리 교체 중 — 아래에서 대타 선택</> : '빈 자리 채우기 — 아래에서 선택'}</span>
              <button onClick={() => setPicking(null)} style={{ marginLeft: 'auto', width: 20, height: 20, borderRadius: 10, background: 'var(--brand)', color: '#fff', fontSize: 11, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>✕</button>
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
            <div style={{ position: 'relative', flex: 1, minWidth: 120, display: 'flex', alignItems: 'center' }}>
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="이름 검색" style={{ width: '100%', padding: '7px 26px 7px 11px', borderRadius: 9, border: '1px solid var(--line-2)', background: 'var(--surface-2)', fontSize: 13, fontWeight: 600, color: 'var(--ink)', outline: 'none', fontFamily: 'inherit' }} />
              {q && <button onClick={() => setQ('')} style={{ position: 'absolute', right: 6, width: 18, height: 18, borderRadius: 9, background: 'var(--surface-3)', color: 'var(--muted)', fontSize: 11, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>}
            </div>
            {chip([{ v: 'smart', l: '추천' }, { v: 'level', l: '급수순' }, { v: 'wait', l: '대기순' }], sortM, setSortM)}
            {chip([{ v: 'all', l: '전체' }, { v: 'M', l: '남' }, { v: 'F', l: '여' }], genderF, setGenderF)}
          </div>
          <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', paddingBottom: 8 }}>
            {picking == null ? (
              <div style={{ padding: '40px 12px', textAlign: 'center', color: 'var(--muted)', fontSize: 13.5, fontWeight: 600, lineHeight: 1.6 }}>위에서 <b style={{ color: 'var(--ink-2)' }}>바꿀 선수</b>를 탭하면<br />여기에 대타 후보가 떠요</div>
            ) : cands.length === 0 ? (
              <div style={{ padding: '40px 12px', textAlign: 'center', color: 'var(--muted)', fontSize: 13.5, fontWeight: 600 }}>조건에 맞는 대기 인원이 없어요</div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {cands.map((b) => (
                  <button key={b.id} onClick={() => replace(b)} style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '11px 13px', borderRadius: 11, background: 'var(--surface-2)', border: '1px solid var(--line)', textAlign: 'left', minWidth: 0 }}>
                    <LevelChip level={b.level} size={26} />
                    <NameWithGender p={b} size={16.5} />
                    <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--muted)', fontWeight: 700, whiteSpace: 'nowrap', flexShrink: 0 }}>{b.totalGames}경기</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ③ 고정 하단: 버튼 */}
        <div style={{ display: 'flex', gap: 10, padding: '12px 24px 18px', flexShrink: 0, borderTop: '1px solid var(--line)', background: 'var(--surface)' }}>
          <Btn variant="ghost" size="lg" full onClick={onClose}>취소</Btn>
          <Btn variant="primary" size="lg" full disabled={slots.length !== 4 || slots.some((s) => !s)} onClick={() => onConfirm(court, { teamA, teamB, type, startedAt: court.match && court.match.startedAt })}>{match && court.match ? '변경 저장' : '이 구성으로 시작'}</Btn>
        </div>
      </div>
    </ModalShell>
  );
}

// ---------- 혼복만 성비 경고 모달 (혼복 선택 시) — claude.ai 디자인 이식 ----------
function RatioBar({ male, female }) {
  const total = male + female || 1;
  const mPct = Math.round((male / total) * 100);
  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 7 }}>
        <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--men-ink)', letterSpacing: '-.02em' }}>
          남 {male}<span style={{ color: 'var(--muted)', fontWeight: 700, marginLeft: 4 }}>{mPct}%</span>
        </span>
        <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--women-ink)', letterSpacing: '-.02em' }}>
          <span style={{ color: 'var(--muted)', fontWeight: 700, marginRight: 4 }}>{100 - mPct}%</span>여 {female}
        </span>
      </div>
      <div style={{ display: 'flex', height: 10, borderRadius: 6, overflow: 'hidden', background: 'var(--surface-3)' }}>
        <div style={{ width: mPct + '%', background: 'var(--men)', transformOrigin: 'left', animation: 'barGrow .5s cubic-bezier(.16,1,.3,1) both' }} />
        <div style={{ width: (100 - mPct) + '%', background: 'var(--women)', transformOrigin: 'right', animation: 'barGrow .5s cubic-bezier(.16,1,.3,1) .06s both' }} />
      </div>
      <div style={{ marginTop: 8, fontSize: 12, fontWeight: 600, color: 'var(--muted)', letterSpacing: '-.01em' }}>
        혼복(남2 : 여2)은 {Math.min(male, female)}경기까지만 가능해요
      </div>
    </div>
  );
}

function ChoiceButton({ title, sub, accent, onClick }) {
  const [hover, setHover] = useState(false);
  const [press, setPress] = useState(false);
  return (
    <button onClick={onClick}
      onPointerEnter={() => setHover(true)} onPointerLeave={() => { setHover(false); setPress(false); }}
      onPointerDown={() => setPress(true)} onPointerUp={() => setPress(false)}
      style={{
        flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 5,
        padding: '14px 16px', borderRadius: 15, minHeight: 72, background: accent.bg, color: accent.fg,
        boxShadow: press ? 'none' : (hover ? accent.shadowHover : accent.shadow),
        transform: press ? 'translateY(1px)' : 'none', transition: 'transform .08s, box-shadow .15s, background .15s', textAlign: 'left',
      }}>
      <span style={{ fontSize: 16.5, fontWeight: 800, letterSpacing: '-.03em', whiteSpace: 'nowrap' }}>{title}</span>
      <span style={{ fontSize: 12, fontWeight: 600, opacity: 0.78, letterSpacing: '-.02em', whiteSpace: 'nowrap' }}>{sub}</span>
    </button>
  );
}

function HonWarnModal({ male, female, device, onResolve, onIgnore }) {
  const stack = device === 'mobile';
  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24, background: 'rgba(15,18,26,.42)', backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)', animation: 'fadeIn .2s ease' }}>
      <div style={{ width: 420, maxWidth: '100%', background: 'var(--surface)', borderRadius: 22, boxShadow: 'var(--sh-3)', padding: 26, animation: 'popIn .26s cubic-bezier(.16,1,.3,1) both' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 11px', borderRadius: 999, background: 'var(--surface-3)', color: 'var(--ink-2)', fontSize: 12.5, fontWeight: 800, letterSpacing: '-.02em' }}>현재 · 혼복만 모드</span>
        </div>
        <h2 style={{ margin: '0 0 8px', fontSize: 20, fontWeight: 800, letterSpacing: '-.035em', color: 'var(--ink)', lineHeight: 1.34, textWrap: 'balance', wordBreak: 'keep-all' }}>
          지금 성비<span style={{ whiteSpace: 'nowrap' }}>(남 {male} · 여 {female})</span>로는 혼복만 운영하기는 어려워요
        </h2>
        <p style={{ margin: '0 0 18px', fontSize: 15, fontWeight: 500, color: 'var(--ink-2)', lineHeight: 1.55, letterSpacing: '-.01em', wordBreak: 'keep-all' }}>모두나 남복/여복으로 바꾸면 다 같이 칠 수 있어요</p>
        <RatioBar male={male} female={female} />
        <div style={{ display: 'flex', flexDirection: stack ? 'column' : 'row', gap: 10 }}>
          <ChoiceButton title="모두로 바꾸기" sub="혼복·남복·여복 다 가능"
            accent={{ bg: 'var(--brand)', fg: '#fff', shadow: '0 2px 0 var(--brand-dk)', shadowHover: '0 4px 14px rgba(18,165,101,.32), 0 2px 0 var(--brand-dk)' }}
            onClick={() => onResolve('모두')} />
          <ChoiceButton title="남복·여복으로 바꾸기" sub="성별끼리 2:2로"
            accent={{ bg: 'var(--ink)', fg: '#fff', shadow: '0 2px 0 #000', shadowHover: '0 4px 14px rgba(17,22,31,.28), 0 2px 0 #000' }}
            onClick={() => onResolve('남복/여복')} />
        </div>
        <div style={{ textAlign: 'center', marginTop: 14 }}>
          <button onClick={onIgnore} className="ignore-link" style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--muted)', letterSpacing: '-.01em', padding: '6px 10px', borderRadius: 8 }}>그대로 혼복만 진행</button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { AttendanceScreen, CountsScreen, AlertModal, EditModal, ModalShell, STATUS_STYLE, CallToast, CheckinModal, SettingsModal, HonWarnModal, courtLabel });

// 코트 표시 이름 (커스텀 또는 기본)
function courtLabel(c) {
  return (c && c.name) || `${c.no}번 코트`;
}

// ---------- 코트 수 설정 모달 ----------
function SettingsModal({ courts, onSet, onToggleRemove, onRename, onClose }) {
  const active = courts.filter((c) => !c.pendingRemove).length;
  const sorted = [...courts].sort((a, b) => a.no - b.no);
  const [editing, setEditing] = useState(null); // 편집 중인 코트 no
  const [draft, setDraft] = useState('');
  const startEdit = (c) => { setEditing(c.no); setDraft(c.name || ''); };
  const commit = () => { if (editing != null) onRename(editing, draft); setEditing(null); setDraft(''); };

  return (
    <ModalShell onClose={onClose} width={460}>
      <div style={{ padding: 24 }}>
        <div style={{ fontSize: 19, fontWeight: 900, letterSpacing: '-.03em', color: 'var(--ink)' }}>코트 설정</div>
        <div style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600, marginTop: 4, marginBottom: 18 }}>오늘 사용할 코트 면 수와 이름을 정합니다. 게임 중에도 바꿀 수 있어요.</div>

        {/* 스텝퍼 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--surface-2)', borderRadius: 16, padding: '16px 20px', marginBottom: 18 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 900, color: 'var(--ink)', letterSpacing: '-.02em' }}>코트 면 수</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <button onClick={() => onSet(active - 1)} disabled={active <= 1} style={stepBtn(active <= 1)}>−</button>
            <span style={{ fontSize: 30, fontWeight: 900, color: 'var(--ink)', minWidth: 40, textAlign: 'center', letterSpacing: '-.03em' }}>{active}</span>
            <button onClick={() => onSet(active + 1)} style={stepBtn(false)}>+</button>
          </div>
        </div>

        {/* 코트별 상태 — 고정 높이(5행), 줄여도 유지 + 내부 스크롤 */}
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 8 }}>
          <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--ink-2)' }}>코트별 상태 · 이름</span>
          <span style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--muted)' }}>코트 이름도 변경할 수 있어요</span>
          <span style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--muted)', marginLeft: 'auto' }}>{sorted.length}면</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 7, marginBottom: 18, height: 274, overflowY: 'auto', paddingRight: 4 }}>
          {sorted.map((c) => {
            const pend = c.pendingRemove;
            const busy = c.match != null;
            const isEditing = editing === c.no;
            return (
              <div key={c.no} style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '10px 12px', borderRadius: 12, background: isEditing ? 'var(--brand-tint)' : pend ? 'var(--warn-tint)' : 'var(--surface-2)', opacity: pend ? 0.9 : 1, flexShrink: 0, border: isEditing ? '1px solid var(--brand)' : '1px solid transparent' }}>
                <span style={{ width: 28, height: 28, borderRadius: 8, background: pend ? 'var(--warn)' : 'var(--ink)', color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 900, flexShrink: 0 }}>{c.no}</span>
                {isEditing ? (
                  <>
                    <input
                      autoFocus value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') { setEditing(null); setDraft(''); } }}
                      placeholder={`${c.no}번 코트`} maxLength={12}
                      style={{ flex: 1, minWidth: 0, padding: '8px 10px', borderRadius: 9, border: '1px solid var(--brand)', background: 'var(--surface)', fontSize: 14.5, fontWeight: 800, color: 'var(--ink)', outline: 'none', fontFamily: 'inherit' }}
                    />
                    <Btn variant="primary" size="sm" onClick={commit}>저장</Btn>
                  </>
                ) : (
                  <>
                    <div style={{ flex: 1, minWidth: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 14.5, fontWeight: 800, color: 'var(--ink)', letterSpacing: '-.02em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{courtLabel(c)}</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: pend ? 'var(--warn)' : busy ? 'var(--brand-ink)' : 'var(--muted)', flexShrink: 0 }}>
                        {pend ? '제거 예정' : busy ? '경기 중' : '비어있음'}
                      </span>
                    </div>
                    {/* 이름 수정 버튼 (연한 회색) */}
                    <button onClick={() => startEdit(c)} title="이름 수정" style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '6px 10px', borderRadius: 9, background: 'var(--surface-3)', color: 'var(--muted)', border: '1px solid var(--line-2)', fontSize: 12.5, fontWeight: 700, whiteSpace: 'nowrap', flexShrink: 0 }}>
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none"><path d="M4 20h4l10-10-4-4L4 16v4z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/><path d="M13.5 6.5l4 4" stroke="currentColor" strokeWidth="2"/></svg>
                      이름
                    </button>
                    {pend ? (
                      <Btn variant="soft" size="sm" onClick={() => onToggleRemove(c.no)}>취소</Btn>
                    ) : (
                      <button onClick={() => onToggleRemove(c.no)} title="이 코트 제거" style={{ width: 32, height: 32, borderRadius: 9, background: 'var(--surface)', border: '1px solid var(--line-2)', color: 'var(--danger)', fontSize: 16, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>−</button>
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--muted)', fontWeight: 600, lineHeight: 1.5, marginBottom: 16 }}>
          경기 중인 코트를 줄이면 진행 경기는 그대로 두고 <b style={{ color: 'var(--warn)' }}>종료 후 자동 제거</b>됩니다. 빈 코트는 즉시 사라집니다.
        </div>
        <Btn variant="primary" size="lg" full onClick={onClose}>완료</Btn>
      </div>
    </ModalShell>
  );
}
function stepBtn(disabled) {
  return { width: 52, height: 52, borderRadius: 16, background: disabled ? 'var(--surface-3)' : 'var(--ink)', color: disabled ? 'var(--muted)' : '#fff', fontSize: 26, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: disabled ? 'not-allowed' : 'pointer', flexShrink: 0 };
}

// ---------- 호출 / 되돌리기 토스트 ----------
function CallToast({ toast, onUndo, onDismiss, onPick }) {
  const isCall = toast.kind === 'call';
  const isAlert = toast.kind === 'alert';
  const accent = isCall ? 'var(--brand)' : isAlert ? 'var(--warn)' : 'var(--ink-2)';
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom: 18, display: 'flex', justifyContent: 'center', zIndex: 40, pointerEvents: 'none' }}>
      <div style={{
        pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: 16,
        background: 'var(--ink)', color: '#fff', borderRadius: 16, padding: '14px 16px 14px 20px',
        boxShadow: 'var(--sh-3)', maxWidth: '90%', animation: 'slideUp .26s cubic-bezier(.16,1,.3,1) both',
      }}>
        <div style={{ width: 42, height: 42, borderRadius: 12, background: accent, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, flexShrink: 0 }}>
          {isCall ? '📣' : isAlert ? '⚠️' : '🏸'}
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 12.5, fontWeight: 800, color: 'rgba(255,255,255,.6)', letterSpacing: '-.01em', marginBottom: 3 }}>
            {isCall ? `${toast.courtName || toast.courtNo + '번 코트'} 호출` : `${toast.courtName || toast.courtNo + '번 코트'} · ${toast.error}`}
          </div>
          {isCall ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 9, flexWrap: 'wrap' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '2px 8px', borderRadius: 7, background: `var(--${disciplineColor(toast.type)})`, color: '#fff', fontSize: 12, fontWeight: 800 }}>{toast.type}</span>
              {toast.players.map((p, i) => (
                <span key={p.id} style={{ fontSize: 17, fontWeight: 800, letterSpacing: '-.03em', whiteSpace: 'nowrap' }}>
                  {p.name}<span style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,.5)', marginLeft: 3 }}>{p.level}</span>{i === 1 ? <span style={{ color: 'rgba(255,255,255,.4)', margin: '0 2px' }}> · </span> : ''}
                </span>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-.02em' }}>{toast.detail || '다음 경기를 만들 수 없습니다.'}</div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, marginLeft: 4, flexShrink: 0 }}>
          {isAlert && toast.rec && toast.rec.suggestion && (
            <button onClick={() => onPick(toast.rec.suggestion)} style={toastBtn('var(--warn)')}>{toast.rec.suggestion}로 채우기</button>
          )}
          <button onClick={onUndo} style={toastBtn('rgba(255,255,255,.16)')}>되돌리기</button>
          <button onClick={onDismiss} style={{ ...toastBtn('transparent'), color: 'rgba(255,255,255,.55)', padding: '9px 10px' }}>✕</button>
        </div>
      </div>
    </div>
  );
}
function toastBtn(bg) {
  return { background: bg, color: '#fff', borderRadius: 10, padding: '9px 14px', fontSize: 13.5, fontWeight: 800, letterSpacing: '-.02em', whiteSpace: 'nowrap' };
}

// ---------- 늦참 즉석 체크인 모달 ----------
function CheckinModal({ participants, onCheckin, onClose }) {
  const waiting = participants.filter((p) => p.status === '미출석');
  return (
    <ModalShell onClose={onClose} width={460}>
      <div style={{ padding: 24 }}>
        <div style={{ fontSize: 19, fontWeight: 900, letterSpacing: '-.03em', color: 'var(--ink)' }}>체크인</div>
        <div style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600, marginTop: 4, marginBottom: 16 }}>지금 도착한 사람을 체크하면 바로 대기열 최우선으로 들어갑니다.</div>
        {waiting.length === 0 ? (
          <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--muted)', fontSize: 14, fontWeight: 600 }}>미출석 인원이 없습니다 👍</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 18 }}>
            {waiting.map((p) => (
              <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 10, borderRadius: 12, background: 'var(--surface-2)' }}>
                <LevelChip level={p.level} size={22} />
                <NameWithGender p={p} size={15.5} />
                <Btn variant="primary" size="sm" onClick={() => onCheckin(p.id)} style={{ marginLeft: 'auto' }}>출석</Btn>
              </div>
            ))}
          </div>
        )}
        <Btn variant="ghost" size="lg" full onClick={onClose}>닫기</Btn>
      </div>
    </ModalShell>
  );
}
