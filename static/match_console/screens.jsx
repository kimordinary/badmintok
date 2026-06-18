// ===== screens.jsx — 태블릿 메인 / 출석 / 카운트 / 모달 =====

// ---------- 미니 코트 (팀A | 네트 | 팀B) ----------
function MiniCourt({ type, teamA, teamB, recommend = false }) {
  const theme = useTheme();
  const clean = theme === 'clean';
  const c = disciplineColor(type);
  const tint = `var(--${c}-tint)`;
  const line = `var(--${c}-line)`;
  const main = `var(--${c})`;
  const TeamSide = ({ team, align }) => (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 11, padding: '4px 2px', alignItems: align === 'right' ? 'flex-end' : 'flex-start' }}>
      {team.map((p) => (
        <PlayerCell key={p.id} p={p} levelSize={22} nameSize={16.5} reverse={align === 'right'} />
      ))}
    </div>
  );
  return (
    <div style={{
      position: 'relative', display: 'flex', alignItems: 'stretch',
      background: tint, border: `1.5px solid ${line}`, borderRadius: clean ? 16 : 14, padding: '12px 14px',
    }}>
      {/* 코트 라인 모티프 (스포티에서만) */}
      {!clean && <div style={{ position: 'absolute', inset: 6, border: `1.5px dashed ${line}`, borderRadius: 9, pointerEvents: 'none' }} />}
      <TeamSide team={teamA} align="left" />
      {/* 네트 */}
      <div style={{ width: 0, alignSelf: 'stretch', position: 'relative', margin: '0 8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ position: 'absolute', top: 0, bottom: 0, width: clean ? 1 : 2, background: clean ? 'var(--line-2)' : `repeating-linear-gradient(${main}, ${main} 4px, transparent 4px, transparent 8px)`, opacity: clean ? 1 : 0.5 }} />
        <span style={{ position: 'relative', zIndex: 1, background: tint, color: clean ? 'var(--muted)' : main, fontSize: 11, fontWeight: 900, padding: '3px 0', letterSpacing: '.05em' }}>VS</span>
      </div>
      <TeamSide team={teamB} align="right" />
    </div>
  );
}

// ---------- 코트 카드 ----------
function CourtCard({ court, rec, nowTs, auto, onEnd, onStart, onEdit, onManualFill, acePinned, coachName, coverage }) {
  const theme = useTheme();
  const clean = theme === 'clean';
  const strip = false; // 코트 상단 종목색 스트립 제거 (색 보더 촌스러움)
  const emphasizeEmpty = theme !== 'sporty';
  const playing = court.match != null;
  const type = playing ? court.match.type : rec && rec.match ? rec.match.type : null;
  const c = type ? disciplineColor(type) : null;
  const accent = c ? `var(--${c})` : 'var(--line-2)';
  const a = acePinned ? true : auto; // 코치 코트는 항상 추천+시작 방식

  return (
      <div style={{
      background: court.pendingRemove ? 'var(--warn-tint)' : (emphasizeEmpty && !playing ? '#f2faf5' : 'var(--surface)'), borderRadius: 'var(--card-radius)', boxShadow: 'var(--sh-2)',
      border: court.pendingRemove ? '1px solid var(--warn-tint)' : '1px solid var(--line)', overflow: 'hidden', display: 'flex', flexDirection: 'column',
      borderTop: court.pendingRemove ? '4px solid var(--warn)' : (strip ? `4px solid ${playing ? accent : 'var(--line-2)'}` : '1px solid var(--line)'),
    }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px 8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <span style={{
            width: 30, height: 30, borderRadius: 9, background: 'var(--ink)', color: '#fff',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
              <rect x="3.5" y="4.5" width="17" height="15" rx="2" stroke="currentColor" strokeWidth="1.7" />
              <line x1="12" y1="4.5" x2="12" y2="19.5" stroke="currentColor" strokeWidth="1.7" />
              <line x1="3.5" y1="9.5" x2="20.5" y2="9.5" stroke="currentColor" strokeWidth="1.1" />
              <line x1="3.5" y1="14.5" x2="20.5" y2="14.5" stroke="currentColor" strokeWidth="1.1" />
            </svg>
          </span>
          <span style={{ fontSize: 16, fontWeight: 800, color: 'var(--ink)', letterSpacing: '-.02em', whiteSpace: 'nowrap' }}>{court.name || court.no + '번 코트'}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {court.pendingRemove && (
            <span style={{ fontSize: 11.5, fontWeight: 800, color: '#fff', background: 'var(--warn)', padding: '3px 8px', borderRadius: 7, whiteSpace: 'nowrap' }}>종료 후 제거</span>
          )}
          {playing && court.match.startedAt && (
            <span style={{ fontSize: 12, fontWeight: 800, color: 'var(--ink-2)', background: 'var(--surface-3)', padding: '3px 8px', borderRadius: 7, whiteSpace: 'nowrap' }}>
              {Math.max(0, Math.round((nowTs - court.match.startedAt) / 60000))}분째
            </span>
          )}
          {acePinned && <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11.5, fontWeight: 800, color: 'var(--hl)', background: '#eef0ff', padding: '3px 8px', borderRadius: 7, whiteSpace: 'nowrap' }}>👑 코치 고정</span>}
          {type && <DisciplineBadge type={type} />}
          {!playing && !type && !acePinned && <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--muted)' }}>대기</span>}
        </div>
      </div>

      <div style={{ padding: '4px 14px 0', flex: 1 }}>
        {playing ? (
          <MiniCourt type={type} teamA={court.match.teamA} teamB={court.match.teamB} />
        ) : a && rec && rec.match ? (
          <div style={{ position: 'relative' }}>
            <MiniCourt type={type} teamA={rec.match.teamA} teamB={rec.match.teamB} recommend />
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '28px 0', textAlign: 'center' }}>
            {a && (
              <div style={{ width: 46, height: 46, borderRadius: 14, background: rec && rec.error === '혼복 불가' ? 'var(--warn-tint)' : 'var(--surface-3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Shuttle size={24} color={rec && rec.error === '혼복 불가' ? 'var(--warn)' : 'var(--muted)'} />
              </div>
            )}
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-2)' }}>{!a ? '비어 있음' : (rec ? rec.error : '추천 대기')}</div>
            <div style={{ fontSize: 12.5, color: 'var(--muted)', maxWidth: 180 }}>{!a ? '선수를 직접 넣어 주세요' : (rec ? rec.detail : '대기 인원이 모이면 추천됩니다.')}</div>
          </div>
        )}
      </div>

      {/* 푸터 액션 */}
      <div style={{ padding: 14 }}>
        {acePinned && coverage && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--muted)', whiteSpace: 'nowrap' }}>{coachName} 코치와 만남</span>
            <div style={{ flex: 1, height: 6, borderRadius: 4, background: '#eef1f5', overflow: 'hidden' }}>
              <div style={{ width: (coverage.total ? coverage.met / coverage.total * 100 : 0) + '%', height: '100%', background: 'var(--hl)' }} />
            </div>
            <span style={{ fontSize: 11.5, fontWeight: 800, color: 'var(--hl)', whiteSpace: 'nowrap' }}>{coverage.met}/{coverage.total}</span>
          </div>
        )}
        <div style={{ display: 'flex', gap: 9 }}>
        {playing ? (
          <>
            <Btn variant="primary" size="lg" full onClick={() => onEnd(court)} style={{ flex: 1 }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
                <svg width="15" height="15" viewBox="0 0 24 24"><rect x="5" y="5" width="14" height="14" rx="3" fill="currentColor"/></svg>
                경기 종료
              </span>
            </Btn>
            <Btn variant="ghost" size="lg" onClick={() => onEdit(court)}>{acePinned ? '코치' : '편집'}</Btn>
          </>
        ) : a && rec && rec.match ? (
          <>
            <Btn variant="primary" size="lg" full onClick={() => onStart(court, rec.match)} style={{ flex: 1 }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>▶ 경기 시작</span>
            </Btn>
            <Btn variant="ghost" size="lg" onClick={() => acePinned ? onEdit(court) : onStart(court, rec.match, true)}>{acePinned ? '코치' : '편집'}</Btn>
          </>
        ) : !auto && !acePinned ? (
          <>
            <Btn variant="primary" size="lg" full onClick={() => onManualFill(court)} style={{ flex: 1 }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>＋ 직접 채우기</span>
            </Btn>
            {rec && rec.match && <Btn variant="ghost" size="lg" onClick={() => onStart(court, rec.match)}>추천 채우기</Btn>}
          </>
        ) : rec && rec.error === '혼복 불가' && rec.suggestion ? (
          <Btn variant="ghost" size="lg" full onClick={() => onEdit(court, rec)} style={{ flex: 1, color: 'var(--warn)', borderColor: 'var(--warn)' }}>
            모임장 선택 필요
          </Btn>
        ) : (
          <Btn variant="soft" size="lg" full disabled style={{ flex: 1 }}>대기 중</Btn>
        )}
        </div>
      </div>
    </div>
  );
}

// ---------- 컨트롤 바 ----------
function ControlBar({ mode, setMode, preset, setPreset, auto, setAuto, stats, onSwitch, onCheckin, onSettings, onHelp }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 18, padding: '14px 22px',
      background: 'var(--surface)', borderBottom: '1px solid var(--line)', boxShadow: 'var(--sh-1)', flexShrink: 0,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
        <img src="app-logo.png" alt="배드민톡" width={40} height={40} style={{ borderRadius: 11, display: 'block', flexShrink: 0 }} />
      </div>

      <div data-help="modes" style={{ display: 'flex', alignItems: 'center', gap: 18, marginLeft: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--muted)', letterSpacing: '-.01em', whiteSpace: 'nowrap' }}>종목</span>
          <Segmented options={MODES} value={mode} onChange={setMode} accent="var(--ink)" />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--muted)', letterSpacing: '-.01em', whiteSpace: 'nowrap' }}>게임</span>
          <Segmented options={['밸런스', '동일 급수']} value={preset} onChange={setPreset} accent="var(--brand)" />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--muted)', letterSpacing: '-.01em', whiteSpace: 'nowrap' }}>운영</span>
          <div style={{ display: 'inline-flex', background: 'var(--surface-3)', borderRadius: 9, padding: 3, gap: 2 }}>
            {[['자동', true], ['수동', false]].map(([l, v]) => (
              <button key={l} onClick={() => setAuto(v)} style={{
                padding: '6px 13px', borderRadius: 7, fontSize: 13, fontWeight: 800, letterSpacing: '-.02em', whiteSpace: 'nowrap',
                color: auto === v ? 'var(--ink)' : 'var(--muted)', background: auto === v ? 'var(--surface)' : 'transparent', boxShadow: auto === v ? 'var(--sh-2)' : 'none',
              }}>{l}</button>
            ))}
          </div>
        </div>
      </div>

      {/* 도움말 버튼 (운영↔참여중 가운데 빈 공간) */}
      <button onClick={onHelp} aria-label="도움말" style={{
        marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 4, padding: '4px 9px', borderRadius: 999,
        border: '1px solid var(--line-2)', background: 'var(--surface)', color: 'var(--muted)', fontSize: 11.5, fontWeight: 800, letterSpacing: '-.02em', whiteSpace: 'nowrap',
      }}>
        <span style={{ width: 13, height: 13, borderRadius: 999, border: '1.5px solid var(--muted)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 9, flexShrink: 0 }}>?</span>
        도움말
      </button>

      <div data-help="rightnav" style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 16 }}>
        <Stat label="참여중" value={stats.playing} accent="var(--brand-ink)" />
        <Stat label="대기" value={stats.waiting} accent="var(--ink)" />
        <div style={{ width: 1, height: 28, background: 'var(--line)' }} />
        <button onClick={() => onSwitch('attendance')} style={{ ...navBtnStyle, ...(stats.noShow > 0 ? { background: 'var(--warn-tint)', color: 'var(--warn)' } : {}) }}>출석</button>
        <button onClick={() => onSwitch('counts')} style={navBtnStyle}>카운트</button>
        <button onClick={onSettings} title="코트 설정" style={{ ...navBtnStyle, padding: '9px 12px', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><rect x="3.5" y="4.5" width="17" height="15" rx="2" stroke="currentColor" strokeWidth="1.7" /><line x1="12" y1="4.5" x2="12" y2="19.5" stroke="currentColor" strokeWidth="1.7" /><line x1="3.5" y1="9.5" x2="20.5" y2="9.5" stroke="currentColor" strokeWidth="1.1" /><line x1="3.5" y1="14.5" x2="20.5" y2="14.5" stroke="currentColor" strokeWidth="1.1" /></svg>
          코트 {stats.courtCount}면
        </button>
      </div>
    </div>
  );
}
const navBtnStyle = { padding: '9px 15px', borderRadius: 10, fontSize: 14, fontWeight: 800, color: 'var(--ink-2)', background: 'var(--surface-3)', letterSpacing: '-.02em', whiteSpace: 'nowrap' };
function Stat({ label, value, accent }) {
  return (
    <div style={{ textAlign: 'center', minWidth: 44 }}>
      <div style={{ fontSize: 22, fontWeight: 900, color: accent, lineHeight: 1, letterSpacing: '-.03em' }}>{value}</div>
      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--muted)', marginTop: 3 }}>{label}</div>
    </div>
  );
}

// ---------- 대기열: 다음 경기 미니 블록 (실제 추천 4명) ----------
function QueueNextBlock({ courtNo, courtName, match, preview = false, label, onCancel }) {
  const c = disciplineColor(match.type);
  const TeamCol = ({ team, align }) => (
    <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 7, alignItems: align === 'right' ? 'flex-end' : 'flex-start' }}>
      {team.map((p) => (
        <PlayerCell key={p.id} p={p} levelSize={18} nameSize={14} reverse={align === 'right'} gap={6} />
      ))}
    </div>
  );
  return (
    <div style={{ background: 'var(--surface)', border: preview ? '1px dashed var(--line-2)' : '1px solid var(--line-2)', borderRadius: 14, borderTop: preview ? '3px dashed var(--muted)' : '1px solid var(--line-2)', overflow: 'hidden', marginBottom: 10 }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '9px 11px', background: preview ? 'var(--surface-2)' : `var(--${c}-tint)`, borderBottom: '1px solid var(--line)' }}>
        <span style={{ fontSize: 12, fontWeight: 900, letterSpacing: '-.02em', color: preview ? 'var(--ink-2)' : 'var(--brand-ink)', whiteSpace: 'nowrap' }}>{label || (preview ? '이후 예정' : '다음 경기')}</span>
        {preview && !label && (
          <span style={{ fontSize: 10.5, fontWeight: 800, color: 'var(--muted)', background: 'var(--surface-3)', padding: '2px 7px', borderRadius: 6, whiteSpace: 'nowrap' }}>잠정</span>
        )}
        <DisciplineBadge type={match.type} />
        {onCancel && <button onClick={onCancel} style={{ marginLeft: 'auto', width: 22, height: 22, borderRadius: 7, background: 'var(--surface-3)', color: 'var(--muted)', fontSize: 13, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>✕</button>}
      </div>
      {/* 팀A | 네트 | 팀B */}
      <div style={{ display: 'flex', alignItems: 'stretch', padding: '10px 12px' }}>
        <TeamCol team={match.teamA} align="left" />
        <div style={{ width: 0, alignSelf: 'stretch', position: 'relative', margin: '0 8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ position: 'absolute', top: 2, bottom: 2, width: 1, background: 'var(--line-2)' }} />
          <span style={{ position: 'relative', zIndex: 1, background: 'var(--surface)', color: 'var(--muted)', fontSize: 10, fontWeight: 900, padding: '2px 0', letterSpacing: '.04em' }}>VS</span>
        </div>
        <TeamCol team={match.teamB} align="right" />
      </div>
    </div>
  );
}

// ---------- 대기열 행 (리스트 공용) ----------
function QueueRow({ p, rank, nowTs, highlight, selectable, selected, onToggle }) {
  const restMin = p.lastFinished == null ? null : Math.round((nowTs - p.lastFinished) / 60000);
  const first = p.totalGames === 0;
  const longWait = !first && restMin != null && restMin >= 20;
  const Wrap = selectable ? 'button' : 'div';
  return (
    <Wrap onClick={selectable ? onToggle : undefined} style={{
      width: '100%', display: 'flex', alignItems: 'center', gap: 10, padding: '8px 8px', borderRadius: 12, textAlign: 'left',
      background: (selected || (!selectable && highlight)) ? 'var(--brand-tint)' : 'transparent',
      border: selected ? '1px solid var(--brand)' : '1px solid transparent',
      cursor: selectable ? 'pointer' : 'default',
    }}>
      {selectable ? (
        <span style={{ width: 20, height: 20, borderRadius: 6, flexShrink: 0, border: selected ? 'none' : '1.5px solid var(--line-2)', background: selected ? 'var(--brand)' : 'transparent', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
          {selected && <svg width="12" height="12" viewBox="0 0 24 24" fill="none"><path d="M5 12.5l4.5 4.5L19 7" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" strokeLinejoin="round" /></svg>}
        </span>
      ) : (
        <span style={{ width: 20, textAlign: 'center', fontSize: 13, fontWeight: 900, color: highlight ? 'var(--brand-ink)' : 'var(--muted)' }}>{rank}</span>
      )}
      <LevelChip level={p.level} size={22} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <NameWithGender p={p} size={14.5} />
          {first && <span style={{ fontSize: 10.5, fontWeight: 800, color: 'var(--brand-ink)', background: '#fff', border: '1px solid var(--brand)', padding: '1px 6px', borderRadius: 6, whiteSpace: 'nowrap' }}>첫 경기</span>}
          {longWait && <span style={{ fontSize: 10.5, fontWeight: 800, color: '#fff', background: 'var(--warn)', padding: '1px 6px', borderRadius: 6, whiteSpace: 'nowrap' }}>오래 대기</span>}
        </div>
        <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2, fontWeight: 600 }}>
          {p.totalGames}경기{restMin != null ? ` · ${restMin}분 휴식` : ' · 아직 안 뜀'}
        </div>
      </div>
    </Wrap>
  );
}

// ---------- 대기열 패널 ----------
function QueuePanel({ queue, nextUp, nowTs, manual, onMakeGame, pending, onCancelPending, pairs, participants, onRemovePair }) {
  const nameOf = (id) => { const p = (participants || []).find((x) => x.id === id); return p ? p.name : '?'; };
  const [view, setView] = useState('block'); // 'block' | 'list'
  const [sel, setSel] = useState([]); // 수동: 대기열에서 고른 선수들
  const [q, setQ] = useState(''); // 수동: 이름·급수 검색
  const toggle = (p) => setSel((s) => s.find((x) => x.id === p.id) ? s.filter((x) => x.id !== p.id) : (s.length < 4 ? [...s, p] : s));
  const isSel = (p) => !!sel.find((x) => x.id === p.id);
  const qq = q.trim().toLowerCase();
  const show = (p) => qq === '' || p.name.toLowerCase().includes(qq) || (p.level && p.level.toLowerCase().includes(qq));
  // 다음 차례 look-ahead: #1=다음 경기(확정), #2·3=이후 예정(잠정)
  const groups = nextUp.groups;
  const nextIds = new Set();
  groups.forEach((m) => [...m.teamA, ...m.teamB].forEach((p) => nextIds.add(p.id)));
  const waitingError = groups.length === 0 ? nextUp.err : null;
  const rest = queue.filter((p) => !nextIds.has(p.id));

  return (
    <aside data-help="queue" style={{ width: 336, flexShrink: 0, background: 'var(--surface)', borderLeft: '1px solid var(--line)', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '16px 18px 12px', borderBottom: '1px solid var(--line)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 16, fontWeight: 900, letterSpacing: '-.03em', color: 'var(--ink)' }}>대기열</span>
          <span style={{ fontSize: 12.5, fontWeight: 800, color: 'var(--muted)', background: 'var(--surface-3)', padding: '3px 9px', borderRadius: 8 }}>{queue.length}명 대기</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 9, gap: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 600 }}>덜 뛴 사람 · 오래 쉰 순</span>
          {/* 뷰 토글 */}
          <div style={{ display: 'inline-flex', background: 'var(--surface-3)', borderRadius: 9, padding: 3, gap: 2, flexShrink: 0 }}>
            {[{ k: 'block', l: '블록' }, { k: 'list', l: '리스트' }].map((v) => (
              <button key={v.k} onClick={() => setView(v.k)} style={{
                padding: '5px 12px', borderRadius: 7, fontSize: 12.5, fontWeight: 800, letterSpacing: '-.02em',
                color: view === v.k ? 'var(--ink)' : 'var(--muted)', background: view === v.k ? 'var(--surface)' : 'transparent',
                boxShadow: view === v.k ? 'var(--sh-2)' : 'none', whiteSpace: 'nowrap',
              }}>{v.l}</button>
            ))}
          </div>
        </div>
        {manual && (
          <div style={{ position: 'relative', marginTop: 10, display: 'flex', alignItems: 'center' }}>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="이름·급수로 검색" style={{ width: '100%', padding: '8px 30px 8px 12px', borderRadius: 9, border: '1px solid var(--line-2)', background: 'var(--surface-2)', fontSize: 13, fontWeight: 600, color: 'var(--ink)', outline: 'none', fontFamily: 'inherit' }} />
            {q && <button onClick={() => setQ('')} style={{ position: 'absolute', right: 8, width: 20, height: 20, borderRadius: 10, background: 'var(--surface-3)', color: 'var(--muted)', fontSize: 12, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>✕</button>}
          </div>
        )}
        {/* 파트너 쌍 표시 + 해제 (만들기는 출석 화면) */}
        {pairs && pairs.length > 0 && (
          <div style={{ marginTop: 11, display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--muted)', letterSpacing: '-.01em' }}>파트너 {pairs.length}쌍</span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {pairs.map((pr) => (
                <span key={pr.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 6px 4px 10px', borderRadius: 999, background: 'var(--brand-tint)', border: '1px solid rgba(18,165,101,.3)', fontSize: 11.5, fontWeight: 800, color: 'var(--brand-ink)', whiteSpace: 'nowrap' }}>
                  {nameOf(pr.members[0])}·{nameOf(pr.members[1])}
                  {pr.strict && <span style={{ fontSize: 9.5, fontWeight: 800, color: '#fff', background: 'var(--brand)', padding: '1px 4px', borderRadius: 5 }}>같이만</span>}
                  <button onClick={() => onRemovePair(pr.id)} title="파트너 해제" style={{ width: 15, height: 15, borderRadius: 8, background: 'var(--brand)', color: '#fff', fontSize: 9, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>✕</button>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 12px 16px' }}>
        {view === 'block' ? (
          <>
            {/* 수동 예약 경기 (빈 코트 없을 때 쌓임 → 코트 비면 투입) */}
            {(pending || []).map((g) => <QueueNextBlock key={g.id} match={g} label="예약 경기" onCancel={() => onCancelPending(g.id)} />)}
            {/* 다음 경기(확정) + 이후 예정(잠정) */}
            {groups.map((m, i) => <QueueNextBlock key={i} match={m} preview={i > 0} />)}
            {waitingError && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px', borderRadius: 12, background: 'var(--warn-tint)', marginBottom: 10 }}>
                <span style={{ fontSize: 15 }}>⚠️</span>
                <span style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--warn)', letterSpacing: '-.01em' }}>{waitingError} — 모임장 선택 필요</span>
              </div>
            )}
            {/* 이후 대기 */}
            {rest.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: groups.length ? '14px 4px 8px' : '2px 4px 8px' }}>
                <span style={{ fontSize: 12, fontWeight: 900, letterSpacing: '-.02em', color: 'var(--ink-2)' }}>이후 대기</span>
                <div style={{ flex: 1, height: 1, background: 'var(--line)' }} />
                <span style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--muted)' }}>{rest.length}명</span>
              </div>
            )}
            {rest.filter(show).map((p, i) => <QueueRow key={p.id} p={p} rank={i + 1} nowTs={nowTs} selectable={manual} selected={isSel(p)} onToggle={() => toggle(p)} />)}
            {qq !== '' && rest.filter(show).length === 0 && <div style={{ padding: 20, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>검색 결과가 없습니다.</div>}
            {queue.length === 0 && <div style={{ padding: 30, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>대기 인원이 없습니다.</div>}
            {queue.length > 0 && rest.length === 0 && groups.length > 0 && <div style={{ padding: '14px 4px', textAlign: 'center', color: 'var(--muted)', fontSize: 12.5, fontWeight: 600 }}>이후 대기 인원이 없습니다.</div>}
          </>
        ) : (
          <>
            {/* 리스트: 전체 우선순위 일렬, 상위 4명 강조 */}
            {queue.filter(show).map((p, i) => <QueueRow key={p.id} p={p} rank={i + 1} nowTs={nowTs} highlight={!manual && i < 4} selectable={manual} selected={isSel(p)} onToggle={() => toggle(p)} />)}
            {queue.length === 0 && <div style={{ padding: 30, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>대기 인원이 없습니다.</div>}
          </>
        )}
      </div>
      {manual && sel.length > 0 && (
        <div style={{ flexShrink: 0, borderTop: '1px solid var(--line)', padding: '12px 14px', background: 'var(--surface)', boxShadow: '0 -4px 14px rgba(17,22,31,.06)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--ink)' }}>{sel.length}/4명 선택</span>
            <button onClick={() => setSel([])} style={{ fontSize: 12, fontWeight: 700, color: 'var(--muted)', padding: '2px 6px' }}>해제</button>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
            {sel.map((p) => (
              <span key={p.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '5px 5px 5px 10px', borderRadius: 999, background: 'var(--brand-tint)', border: '1px solid var(--brand)', fontSize: 12.5, fontWeight: 800, color: 'var(--brand-ink)' }}>
                {p.name}
                <button onClick={() => toggle(p)} style={{ width: 16, height: 16, borderRadius: 8, background: 'var(--brand)', color: '#fff', fontSize: 10, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>✕</button>
              </span>
            ))}
          </div>
          <button disabled={sel.length !== 4} onClick={() => { onMakeGame(sel); setSel([]); }} style={{
            width: '100%', padding: '13px', borderRadius: 12, fontSize: 14.5, fontWeight: 800, letterSpacing: '-.02em',
            background: sel.length === 4 ? 'var(--brand)' : 'var(--surface-3)', color: sel.length === 4 ? '#fff' : 'var(--muted)',
            cursor: sel.length === 4 ? 'pointer' : 'not-allowed',
          }}>{sel.length === 4 ? '이 4명으로 경기 만들기' : `${4 - sel.length}명 더 선택`}</button>
        </div>
      )}
    </aside>
  );
}

// ---------- 도움말 온보딩 오버레이 (범례형 · 인디고 강조 · 위치 측정) ----------
// 강조 영역 3개. rect는 런타임에 [data-help] 요소를 측정해 채움(하드코딩 X).
const HELP_ZONES = [
  { key: 'modes', n: '1', title: '종목 · 게임 · 운영' },
  { key: 'court', n: '2', title: '코트' },
  { key: 'queue', n: '3', title: '대기열' },
];
// 자연 줄바꿈(칸 폭에 맞춰 채움) + keep-all. 대괄호 액션은 nbsp로 줄 끝에서 안 쪼개짐.
const HELP_DESC = {
  auto: [
    '종목(혼복·남복여복·모두), 게임 성향, 운영 방식(자동·수동)을 여기서 정해요.',
    '경기가 끝나면 [경기 종료]를 누르면 다음 경기가 자동으로 투입돼요.',
    '덜 뛴 사람·오래 쉰 순으로 정렬돼요. 다음 경기를 자동으로 추천해 줘요.',
  ],
  manual: [
    '종목(혼복·남복여복·모두), 게임 성향, 운영 방식(자동·수동)을 여기서 정해요.',
    '빈 코트는 [직접 채우기]로 멤버를 정해요. 경기가 끝나면 [경기 종료]를 누르면 예약 경기가 자동으로 투입돼요.',
    '덜 뛴 사람·오래 쉰 순으로 정렬돼요. 4명을 골라 [경기 만들기]를 누르면 빈 코트엔 바로, 다 차 있으면 예약 경기로 쌓였다가 코트가 비는 대로 투입돼요.',
  ],
};

function HelpBadge({ n, size = 26, pop = 0, ring = true }) {
  return (
    <span style={{
      width: size, height: size, borderRadius: '50%', flexShrink: 0,
      background: 'var(--hl)', color: '#fff', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.52, fontWeight: 900, letterSpacing: '-.02em',
      boxShadow: ring ? '0 2px 8px rgba(10,107,66,.45), 0 0 0 3px rgba(18,165,101,.22)' : '0 2px 6px rgba(10,107,66,.35)',
      animation: `badgePop .4s cubic-bezier(.16,1,.3,1) ${pop}s both`,
    }}>{n}</span>
  );
}

function HelpZoneRing({ z, i }) {
  const r = z.ring;
  return (
    <div style={{ position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, pointerEvents: 'none', animation: `ringIn .4s cubic-bezier(.16,1,.3,1) ${0.05 + i * 0.06}s both` }}>
      <div style={{ position: 'absolute', inset: 0, borderRadius: 16, border: '2px solid var(--hl)', background: 'rgba(18,165,101,.04)', boxShadow: '0 0 0 4px rgba(18,165,101,.12), 0 14px 44px rgba(10,107,66,.30)' }} />
      <div style={{ position: 'absolute', top: 10, left: 10 }}>
        <HelpBadge n={z.n} size={28} pop={0.14 + i * 0.06} />
      </div>
    </div>
  );
}

function HelpLegend({ auto }) {
  const desc = HELP_DESC[auto ? 'auto' : 'manual'];
  return (
    <div style={{ display: 'flex', alignItems: 'stretch', background: 'var(--surface)', borderRadius: 18, boxShadow: '0 10px 30px rgba(17,22,31,.16), 0 3px 10px rgba(17,22,31,.10)', padding: 6, animation: 'cardIn .42s cubic-bezier(.16,1,.3,1) .18s both' }}>
      {HELP_ZONES.map((z, i) => (
        <React.Fragment key={z.n}>
          {i > 0 && <div style={{ width: 1, background: 'var(--line)', margin: '10px 0', alignSelf: 'stretch' }} />}
          <div style={{ width: 340, padding: '14px 18px', display: 'flex', gap: 11 }}>
            <HelpBadge n={z.n} size={26} pop={0.24 + i * 0.06} />
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 15.5, fontWeight: 800, letterSpacing: '-.03em', color: 'var(--ink)', marginBottom: 4, whiteSpace: 'nowrap' }}>{z.title}</div>
              <p style={{ margin: 0, fontSize: 12.5, fontWeight: 500, lineHeight: 1.5, color: 'var(--ink-2)', letterSpacing: '-.01em', wordBreak: 'keep-all' }}>{desc[i]}</p>
            </div>
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}

function CoachMark({ auto, onClose }) {
  const overlayRef = useRef(null);
  const [zones, setZones] = useState([]);
  useLayoutEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) return;
    const root = overlay.parentElement; // MainScreen 루트(position:relative)
    const rr = root.getBoundingClientRect();
    const scale = root.offsetWidth ? rr.width / root.offsetWidth : 1; // 디바이스 프레임 scale 보정
    const W = root.offsetWidth, H = root.offsetHeight, PAD = 6;
    const measured = HELP_ZONES.map((z, i) => {
      const el = root.querySelector(`[data-help="${z.key}"]`);
      if (!el) return null;
      const b = el.getBoundingClientRect();
      let x = (b.left - rr.left) / scale - PAD, y = (b.top - rr.top) / scale - PAD;
      let w = b.width / scale + PAD * 2, h = b.height / scale + PAD * 2;
      if (x < 3) { w += x - 3; x = 3; }
      if (y < 3) { h += y - 3; y = 3; }
      if (x + w > W - 3) w = W - 3 - x;
      if (y + h > H - 3) h = H - 3 - y;
      return { ...z, ring: { x, y, w, h }, i };
    }).filter(Boolean);
    // 코트(②)·대기열(③)이 맞붙어 PAD가 겹치면 경계 중간에서 갈라 8px 간격
    const court = measured.find((z) => z.key === 'court');
    const queue = measured.find((z) => z.key === 'queue');
    if (court && queue) {
      const cRight = court.ring.x + court.ring.w;
      if (cRight > queue.ring.x) {
        const mid = (cRight + queue.ring.x) / 2;
        court.ring.w = mid - 4 - court.ring.x;
        const qx = mid + 4;
        queue.ring.w -= qx - queue.ring.x;
        queue.ring.x = qx;
      }
    }
    setZones(measured);
  }, [auto]);
  return (
    <div ref={overlayRef} onClick={onClose} style={{ position: 'absolute', inset: 0, zIndex: 60, cursor: 'pointer', animation: 'ovFade .25s ease both' }}>
      <div style={{ position: 'absolute', inset: 0, background: 'rgba(10,13,20,.70)' }} />
      {zones.map((z) => <HelpZoneRing key={z.key} z={z} i={z.i} />)}
      {/* 힌트 + 범례를 하단 정렬 컬럼으로 묶음 → 카드 높이가 달라져도 힌트가 항상 카드 위 */}
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 26, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, pointerEvents: 'none' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderRadius: 999, background: 'rgba(21,23,28,.82)', color: '#fff', fontSize: 13, fontWeight: 700, letterSpacing: '-.02em', whiteSpace: 'nowrap', animation: 'cardIn .4s ease .5s both' }}>
          <span style={{ fontSize: 13 }}>👆</span> 아무 곳이나 누르면 닫혀요
        </span>
        <HelpLegend auto={auto} />
      </div>
    </div>
  );
}

// ---------- 메인 운영 화면 (태블릿) ----------
function MainScreen({ state, actions }) {
  const [coach, setCoach] = useState(false);
  const { participants, courts, mode, preset } = state;
  const nowTs = state.nowTs;
  const pool = participants;
  const pendingIds = useMemo(() => new Set((state.pending || []).flatMap((g) => [...g.teamA, ...g.teamB].map((p) => p.id))), [state.pending]);
  const queue = useMemo(
    () => sortQueue(pool.filter((p) => p.status === '참여중' && p.court == null && !pendingIds.has(p.id)), nowTs),
    [pool, nowTs, pendingIds]
  );
  const coachIds = useMemo(() => new Set(courts.filter((c) => c.ace).map((c) => c.coachId)), [courts]);
  // 빈 코트별 추천 (코치 코트들 먼저 → 나머지 순차)
  const recs = useMemo(() => {
    const taken = new Set();
    const out = {};
    const poolView = pool.map((p) => ({ ...p }));
    // 공동 우선: 사람별 만난 코치 수
    const metCount = {};
    Object.values(state.pinnedMet || {}).forEach((mm) => Object.keys(mm).forEach((pid) => { metCount[pid] = (metCount[pid] || 0) + 1; }));
    for (const ct of courts) {
      if (!ct.ace || ct.match || ct.pendingRemove) continue;
      const ace = poolView.find((p) => p.id === ct.coachId);
      const three = ace ? pickAceThree(poolView.filter((p) => !coachIds.has(p.id) && !taken.has(p.id)), metCount, nowTs) : null;
      out[ct.no] = three ? { match: buildAceMatch(ace, three) } : { error: '대기 부족', detail: '코치와 칠 대기 인원이 부족합니다.' };
      if (three) three.forEach((p) => taken.add(p.id));
    }
    for (const ct of courts) {
      if (ct.match || ct.pendingRemove || ct.ace) continue;
      const avail = poolView.filter((p) => !taken.has(p.id) && !coachIds.has(p.id));
      const r = recommendMatchPaired(avail, mode, preset, nowTs, state.pairs);
      out[ct.no] = r;
      if (r.match) [...r.match.teamA, ...r.match.teamB].forEach((p) => taken.add(p.id));
    }
    return out;
  }, [pool, courts, mode, preset, nowTs, coachIds, state.pinnedMet, state.pairs]);

  // 코치별 커버리지·이름 (코트번호 → {name, coverage})
  const coachInfo = useMemo(() => {
    const others = pool.filter((p) => p.status === '참여중' && !coachIds.has(p.id));
    const total = others.length;
    const map = {};
    for (const ct of courts) {
      if (!ct.ace || !ct.coachId) continue;
      const met = (state.pinnedMet && state.pinnedMet[ct.coachId]) || {};
      map[ct.no] = { name: (pool.find((p) => p.id === ct.coachId) || {}).name, coverage: { met: others.filter((p) => met[p.id]).length, total } };
    }
    return map;
  }, [pool, courts, coachIds, state.pinnedMet]);

  // 대기열 "다음 차례" look-ahead: 코트 상태와 무관하게 다음 3경기를 순차 계산
  // (#1=다음 경기 확정, #2·3=이후 예정 잠정). 뽑힌 4명을 빼고 다시 추천하는 식.
  const nextUp = useMemo(() => {
    if (!state.auto) return { groups: [], err: null }; // 수동 모드: 추천 안 함
    const taken = new Set();
    const poolView = pool.map((p) => ({ ...p }));
    const groups = [];
    let err = null;
    for (let i = 0; i < 3; i++) {
      const avail = poolView.filter((p) => !taken.has(p.id) && !coachIds.has(p.id));
      const r = recommendMatchPaired(avail, mode, preset, nowTs, state.pairs);
      if (r && r.match) {
        groups.push(r.match);
        [...r.match.teamA, ...r.match.teamB].forEach((p) => taken.add(p.id));
      } else { if (r && r.error && !err) err = r.error; break; }
    }
    return { groups, err };
  }, [pool, mode, preset, nowTs, state.auto, coachIds, state.pairs]);

  const stats = {
    playing: pool.filter((p) => p.court != null).length,
    waiting: queue.length,
    noShow: pool.filter((p) => p.status === '미출석').length,
    courtCount: courts.filter((c) => !c.pendingRemove).length,
  };

  // 안전장치: 대기(벤치) 인원이 너무 적으면 경고. 벤치 = 출석 − 코트×4.
  // 벤치 0~1이면 매번 같은 사람끼리 치게 되고 균형도 무너짐(권장: 2팀=4명 이상).
  const presentCount = pool.filter((p) => p.status === '참여중').length;
  const bench = presentCount - stats.courtCount * 4;
  const lowBench = presentCount >= 4 && bench < 4;

  return (
    <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg)' }}>
      <ControlBar mode={mode} setMode={actions.setMode} preset={preset} setPreset={actions.setPreset} auto={state.auto} setAuto={actions.setAuto} stats={stats} onSwitch={actions.switchScreen} onCheckin={actions.openCheckin} onSettings={actions.openSettings} onHelp={() => setCoach(true)} />
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <main data-help="court" style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(330px, 1fr))', gap: 16 }}>
            {courts.map((ct) => (
              <CourtCard key={ct.no} court={ct} rec={recs[ct.no]} nowTs={nowTs} auto={state.auto} onEnd={actions.endMatch} onStart={actions.startMatch} onEdit={actions.openEdit} onManualFill={actions.manualFill} acePinned={ct.ace} coachName={coachInfo[ct.no] && coachInfo[ct.no].name} coverage={coachInfo[ct.no] && coachInfo[ct.no].coverage} />
            ))}
          </div>
        </main>
        <QueuePanel queue={queue} nextUp={nextUp} nowTs={nowTs} manual={!state.auto} onMakeGame={actions.makeGameFromQueue} pending={state.pending} onCancelPending={actions.cancelPending} pairs={state.pairs} participants={pool} onRemovePair={actions.removePair} />
      </div>

      {/* 플로팅 경고 (벤치 부족 — 상시 조건이라 떠 있음) */}
      {lowBench && (
        <div style={{ position: 'absolute', top: 76, left: 20, right: 356, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 9, zIndex: 30, pointerEvents: 'none' }}>
          {lowBench && (
            <div style={{ pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', borderRadius: 14, background: 'var(--surface)', border: `1px solid ${bench <= 1 ? 'var(--danger)' : 'var(--warn)'}`, boxShadow: 'var(--sh-3)', maxWidth: '100%', animation: 'slideUp .22s ease both' }}>
              <span style={{ fontSize: 18, flexShrink: 0 }}>{bench <= 1 ? '🔴' : '⚠️'}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: bench <= 1 ? 'var(--danger)' : 'var(--ink)', letterSpacing: '-.01em', lineHeight: 1.4 }}>
                {bench <= 1 ? `대기 인원이 ${Math.max(0, bench)}명 — 매번 같은 사람끼리 치게 됩니다. 코트를 줄이세요.` : `대기 인원이 ${bench}명이라 여유가 적어요 — 대기 4명 이상(2팀) 권장.`}
              </span>
            </div>
          )}
        </div>
      )}

      {coach && <CoachMark auto={state.auto} onClose={() => setCoach(false)} />}
    </div>
  );
}

Object.assign(window, { MainScreen, CourtCard, MiniCourt, ControlBar, QueuePanel, QueueNextBlock, QueueRow, CoachMark });
