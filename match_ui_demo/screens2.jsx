// ===== screens2.jsx — 출석 체크 / 개인 카운트 / 모달 =====

// ---------- 출석 체크 화면 ----------
const STATUS_STYLE = {
  미출석: { fg: 'var(--muted)', bg: 'var(--surface-3)', label: '미출석', dot: '#c2cad6' },
  참여중: { fg: 'var(--brand-ink)', bg: 'var(--brand-tint)', label: '참여중', dot: 'var(--brand)' },
  퇴장: { fg: 'var(--danger)', bg: 'var(--danger-tint)', label: '퇴장', dot: 'var(--danger)' },
};

function AttendanceScreen({ state, actions }) {
  const { participants } = state;
  const [filter, setFilter] = useState('전체');
  const [query, setQuery] = useState('');
  const counts = {
    전체: participants.length,
    미출석: participants.filter((p) => p.status === '미출석').length,
    참여중: participants.filter((p) => p.status === '참여중').length,
    퇴장: participants.filter((p) => p.status === '퇴장').length,
  };
  const q = query.trim();
  const list = participants.filter((p) => (filter === '전체' || p.status === filter) && (q === '' || p.name.includes(q) || p.level.includes(q)));

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
        <div style={{ marginLeft: 'auto', position: 'relative', display: 'flex', alignItems: 'center' }}>
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" style={{ position: 'absolute', left: 13, pointerEvents: 'none' }}><circle cx="11" cy="11" r="7" stroke="var(--muted)" strokeWidth="2" /><path d="M20 20l-3.2-3.2" stroke="var(--muted)" strokeWidth="2" strokeLinecap="round" /></svg>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="이름·급수로 검색" style={{
            width: 220, padding: '10px 34px 10px 38px', borderRadius: 999, border: '1px solid var(--line-2)',
            background: 'var(--surface)', fontSize: 14, fontWeight: 600, color: 'var(--ink)', outline: 'none', fontFamily: 'inherit',
          }} />
          {query && <button onClick={() => setQuery('')} style={{ position: 'absolute', right: 10, width: 20, height: 20, borderRadius: 10, background: 'var(--surface-3)', color: 'var(--muted)', fontSize: 12, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>}
        </div>
      </div>

      {/* 카드 그리드 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 22 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12 }}>
          {list.map((p) => {
            const st = STATUS_STYLE[p.status];
            return (
              <div key={p.id} style={{
                background: 'var(--surface)', borderRadius: 16, border: '1px solid var(--line)', padding: 14,
                boxShadow: 'var(--sh-1)', display: 'flex', flexDirection: 'column', gap: 12,
                opacity: p.status === '퇴장' ? 0.7 : 1, transition: 'opacity .2s',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
                  <LevelChip level={p.level} size={30} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <NameWithGender p={p} size={17} />
                  </div>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 10px', borderRadius: 999, background: st.bg, color: st.fg, fontSize: 12.5, fontWeight: 800 }}>
                    <span style={{ width: 7, height: 7, borderRadius: 7, background: st.dot }} />{st.label}
                  </span>
                </div>
                {/* 토글 버튼 */}
                <div style={{ display: 'flex', gap: 8 }}>
                  {p.status !== '참여중' ? (
                    <Btn variant="primary" size="md" full onClick={() => actions.setStatus(p.id, '참여중')} style={{ flex: 1 }}>출석 체크</Btn>
                  ) : (
                    <Btn variant="soft" size="md" full onClick={() => actions.setStatus(p.id, '미출석')} style={{ flex: 1, color: 'var(--ink-2)' }}>출석 취소</Btn>
                  )}
                  {p.status === '참여중' && (
                    <Btn variant="ghost" size="md" onClick={() => actions.setStatus(p.id, '퇴장')} style={{ color: 'var(--danger)', borderColor: 'var(--line-2)' }}>퇴장</Btn>
                  )}
                  {p.status === '퇴장' && (
                    <Btn variant="ghost" size="md" onClick={() => actions.setStatus(p.id, '참여중')}>재합류</Btn>
                  )}
                </div>
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
function EditModal({ court, match, bench, onConfirm, onClose }) {
  const init = match ? [...match.teamA, ...match.teamB] : [];
  const [slots, setSlots] = useState(init);
  const [type, setType] = useState(match ? match.type : '혼복');
  const [picking, setPicking] = useState(null); // 교체할 슬롯 index

  const replace = (q) => {
    const next = [...slots];
    next[picking] = q;
    setSlots(next);
    setPicking(null);
  };
  const teamA = [slots[0], slots[1]];
  const teamB = [slots[2], slots[3]];

  return (
    <ModalShell onClose={onClose} width={560}>
      <div style={{ padding: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <div style={{ fontSize: 19, fontWeight: 900, letterSpacing: '-.03em', color: 'var(--ink)', whiteSpace: 'nowrap' }}>{court.no}번 코트 경기 편집</div>
          <DisciplineBadge type={type} size="lg" />
        </div>
        <div style={{ fontSize: 13, color: 'var(--muted)', fontWeight: 600, marginBottom: 16 }}>선수를 탭해 대기열의 다른 사람과 교체하거나, 종목을 바꿀 수 있어요.</div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
          {['혼복', '남복', '여복'].map((t) => (
            <button key={t} onClick={() => setType(t)} style={{
              flex: 1, padding: '9px 0', borderRadius: 10, fontSize: 14, fontWeight: 800,
              border: type === t ? `2px solid var(--${disciplineColor(t)})` : '1px solid var(--line-2)',
              background: type === t ? `var(--${disciplineColor(t)}-tint)` : 'var(--surface)',
              color: type === t ? `var(--${disciplineColor(t)}-ink)` : 'var(--ink-2)',
            }}>{t}</button>
          ))}
        </div>

        {/* 팀 슬롯 */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 18 }}>
          {[{ team: teamA, label: '팀 A', base: 0 }, { team: teamB, label: '팀 B', base: 2 }].map((side) => (
            <div key={side.label} style={{ flex: 1, background: 'var(--surface-2)', borderRadius: 14, padding: 12 }}>
              <div style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--muted)', marginBottom: 8 }}>{side.label}</div>
              {side.team.map((p, j) => {
                const idx = side.base + j;
                return (
                  <button key={idx} onClick={() => setPicking(idx)} style={{
                    width: '100%', display: 'flex', alignItems: 'center', gap: 9, padding: 8, borderRadius: 10, marginBottom: j === 0 ? 6 : 0,
                    background: picking === idx ? 'var(--brand-tint)' : 'var(--surface)',
                    border: picking === idx ? '2px solid var(--brand)' : '1px solid var(--line)', textAlign: 'left',
                  }}>
                    {p ? <><LevelChip level={p.level} size={22} /><NameWithGender p={p} size={15} /></> : <span style={{ color: 'var(--muted)', fontSize: 14 }}>빈 자리</span>}
                    <span style={{ marginLeft: 'auto', fontSize: 12, fontWeight: 700, color: 'var(--brand-ink)', whiteSpace: 'nowrap' }}>{picking === idx ? '선택 ↓' : (p ? '교체' : '선택')}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>

        {/* 대기열에서 교체 후보 */}
        {picking != null && (
          <div style={{ marginBottom: 18, animation: 'slideUp .2s ease both' }}>
            <div style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--ink-2)', marginBottom: 8 }}>대기열에서 선택</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, maxHeight: 150, overflowY: 'auto' }}>
              {bench.filter((b) => !slots.some((s) => s && s.id === b.id)).map((b) => (
                <button key={b.id} onClick={() => replace(b)} style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '7px 11px', borderRadius: 10, background: 'var(--surface-2)', border: '1px solid var(--line)' }}>
                  <LevelChip level={b.level} size={20} />
                  <NameWithGender p={b} size={14} />
                  <span style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 700, whiteSpace: 'nowrap' }}>{b.totalGames}경기</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: 10 }}>
          <Btn variant="ghost" size="lg" full onClick={onClose}>취소</Btn>
          <Btn variant="primary" size="lg" full disabled={slots.some((s) => !s)} onClick={() => onConfirm(court, { teamA, teamB, type })}>{match && court.match ? '변경 저장' : '이 구성으로 시작'}</Btn>
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
