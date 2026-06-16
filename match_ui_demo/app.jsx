// ===== app.jsx — 루트: 상태/액션 + 디바이스 프레임 + 데모 네비 =====

// ---------- 초기 상태 (데모 시드) ----------
function initState() {
  const ps = makeParticipants();
  const now = Date.now();
  // 실제 명단(51명) — 전원 참여중, 경기 이력 없음(세션 시작 상태)
  ps.forEach((p) => { p.status = '참여중'; });

  // 코트 8면, 모두 비어있음 (시스템이 바로 다음 경기를 추천)
  const courts = [];
  for (let i = 1; i <= 8; i++) courts.push({ no: i, match: null });

  return {
    participants: ps,
    courts,
    mode: '모두',
    preset: '밸런스',
    auto: true,
    pending: [], // 수동: 빈 코트 없을 때 예약된 경기들 (코트 비면 투입)
    screen: 'main',
    device: 'tablet',
    modal: null,
    theme: 'clean',
    toast: null,
    nowTs: now,
  };
}

function App() {
  const [st, setSt] = useState(initState);
  const set = (patch) => setSt((s) => ({ ...s, ...(typeof patch === 'function' ? patch(s) : patch) }));

  // 시간 흐름 (휴식시간 표시 갱신)
  useEffect(() => {
    const t = setInterval(() => setSt((s) => ({ ...s, nowTs: Date.now() })), 15000);
    return () => clearInterval(t);
  }, []);

  // 토스트 자동 해제
  useEffect(() => {
    if (!st.toast) return;
    const t = setTimeout(() => setSt((s) => (s.toast ? { ...s, toast: null } : s)), 7000);
    return () => clearTimeout(t);
  }, [st.toast]);

  const findRec = (s, courtNo) => {
    const taken = new Set();
    for (const ct of s.courts) {
      if (ct.match || ct.pendingRemove) continue;
      const avail = s.participants.filter((p) => !taken.has(p.id));
      const r = recommendMatch(avail, s.mode, s.preset, s.nowTs);
      if (ct.no === courtNo) return r;
      if (r.match) [...r.match.teamA, ...r.match.teamB].forEach((p) => taken.add(p.id));
    }
    return null;
  };

  const actions = {
    setMode: (mode) => set((s) => {
      // 혼복으로 바꿀 때 성비가 안 맞으면(적은 성별이 코트를 못 채움) 확인 모달
      if (mode === '혼복') {
        const present = s.participants.filter((p) => p.status === '참여중');
        const M = present.filter((p) => p.gender === 'M').length;
        const F = present.length - M;
        const courtCount = s.courts.filter((c) => !c.pendingRemove).length;
        if (present.length >= 4 && M !== F && Math.floor(Math.min(M, F) / 2) < courtCount + 2) {
          return { mode, modal: { type: 'honWarn', m: M, f: F } };
        }
      }
      return { mode };
    }),
    honWarnPick: (mode) => set({ mode, modal: null }), // 모달에서 종목 전환 + 닫기
    setAuto: (auto) => set({ auto }),
    manualFill: (court) => set({ modal: { type: 'edit', court, match: null } }), // 수동: 빈 슬롯 편집 모달
    makeGameFromQueue: (players) => set((s) => {
      // 대기열에서 고른 4명으로 경기 만들기 → 균형 분할 + 종목 추론
      const males = players.filter((p) => p.gender === 'M').length;
      const type = males === 4 ? '남복' : males === 0 ? '여복' : '혼복';
      const sorted = [...players].sort((a, b) => LEVEL_SCORE[b.level] - LEVEL_SCORE[a.level]);
      const teamA = [sorted[0], sorted[3]], teamB = [sorted[1], sorted[2]]; // 1·4 / 2·3 균형
      const empty = s.courts.find((c) => !c.match && !c.pendingRemove);
      // 빈 코트 있으면 편집 모달로 바로 배치, 없으면 "예약 경기"로 대기열에 쌓음
      if (empty) return { modal: { type: 'edit', court: empty, match: { teamA, teamB, type } } };
      return { pending: [...s.pending, { id: 'g' + Date.now(), teamA, teamB, type }], toast: { kind: 'empty', error: '예약됨', detail: '빈 코트가 없어 예약했어요. 코트가 비면 자동 투입돼요.' } };
    }),
    cancelPending: (gid) => set((s) => ({ pending: s.pending.filter((g) => g.id !== gid) })),
    setPreset: (preset) => set({ preset }),
    switchScreen: (screen) => set({ screen }),
    setDevice: (device) => set({ device }),
    setTheme: (theme) => set({ theme }),

    setStatus: (id, status) => set((s) => ({
      participants: s.participants.map((p) => {
        if (p.id !== id) return p;
        // 퇴장/미출석으로 바꿔도 진행 중 경기는 유지 (코트에서 빼지 않음)
        return { ...p, status };
      }),
    })),

    endMatch: (court) => set((s) => {
      const now = Date.now();
      const m = s.courts.find((c) => c.no === court.no).match;
      if (!m) return {};
      const undo = { participants: s.participants, courts: s.courts };
      const ids = [...m.teamA, ...m.teamB].map((p) => p.id);
      const teamAids = m.teamA.map((p) => p.id), teamBids = m.teamB.map((p) => p.id);
      const participants = s.participants.map((p) => {
        if (!ids.includes(p.id)) return p;
        const games = { ...p.games, [m.type]: p.games[m.type] + 1 };
        const sameTeam = teamAids.includes(p.id) ? teamAids : teamBids;
        const oppTeam = teamAids.includes(p.id) ? teamBids : teamAids;
        const partnerCount = { ...p.partnerCount };
        sameTeam.filter((x) => x !== p.id).forEach((x) => { partnerCount[x] = (partnerCount[x] || 0) + 1; });
        const opponentCount = { ...p.opponentCount };
        oppTeam.forEach((x) => { opponentCount[x] = (opponentCount[x] || 0) + 1; });
        return { ...p, court: null, team: null, games, totalGames: p.totalGames + 1, lastFinished: now, partnerCount, opponentCount };
      });
      const courts = s.courts.map((c) => (c.no === court.no ? { ...c, match: null } : c));
      // 예약 제거 코트였으면 종료 시 아예 제거 (재추천 안 함)
      const targetCourt = s.courts.find((c) => c.no === court.no);
      const courtName = targetCourt && targetCourt.name;
      if (targetCourt && targetCourt.pendingRemove) {
        return {
          participants, courts: courts.filter((c) => c.no !== court.no), nowTs: now,
          toast: { kind: 'empty', courtNo: court.no, courtName, error: '코트 제거됨', detail: `${courtName || court.no + '번 코트'}를 운영에서 제외했습니다.`, undo },
        };
      }
      // 수동 모드: 자동 배정 안 함. 단, 예약된 경기가 있으면 빈 코트에 투입.
      if (!s.auto) {
        if (s.pending && s.pending.length) {
          const g = s.pending[0];
          const applied = applyMatch({ participants, courts }, court, { ...g, startedAt: now });
          return {
            participants: applied.participants, courts: applied.courts, pending: s.pending.slice(1), nowTs: now,
            toast: { kind: 'call', courtNo: court.no, courtName, players: [...g.teamA, ...g.teamB], type: g.type, undo },
          };
        }
        return { participants, courts, nowTs: now, toast: { kind: 'empty', courtNo: court.no, courtName, error: '경기 종료', detail: '직접 채워 주세요.', undo } };
      }
      // 자동 배정: 빈 코트에 다음 경기 바로 올림 (원탭)
      const r = recommendMatch(participants, s.mode, s.preset, now);
      if (r.match) {
        const applied = applyMatch({ participants, courts }, court, { ...r.match, startedAt: now });
        return {
          participants: applied.participants, courts: applied.courts, nowTs: now,
          toast: { kind: 'call', courtNo: court.no, courtName, players: [...r.match.teamA, ...r.match.teamB], type: r.match.type, reason: r.match.reason, undo },
        };
      }
      return {
        participants, courts, nowTs: now,
        toast: { kind: r.error === '혼복 불가' ? 'alert' : 'empty', courtNo: court.no, courtName, error: r.error, detail: r.detail, rec: r, undo },
      };
    }),

    startMatch: (court, match, editFlag) => {
      if (editFlag) { set({ modal: { type: 'edit', court, match } }); return; }
      set((s) => applyMatch(s, court, match));
    },

    openEdit: (court, rec) => {
      if (rec && rec.error === '혼복 불가') { set({ modal: { type: 'alert', court, rec } }); return; }
      set({ modal: { type: 'edit', court, match: court.match } });
    },

    confirmEdit: (court, match) => set((s) => ({ ...applyMatch(s, court, match), modal: null })),

    pickAlt: (court, type) => set((s) => {
      const gender = type === '남복' ? 'M' : 'F';
      const eligible = sortQueue(s.participants.filter((p) => p.status === '참여중' && p.court == null && p.gender === gender), s.nowTs);
      if (eligible.length < 4) return { modal: null };
      const four = eligible.slice(0, 4);
      // 균형 split: 점수 정렬 후 1·4 / 2·3
      const sorted = [...four].sort((a, b) => LEVEL_SCORE[b.level] - LEVEL_SCORE[a.level]);
      const match = { type, teamA: [sorted[0], sorted[3]], teamB: [sorted[1], sorted[2]] };
      return { ...applyMatch(s, court, match), modal: null };
    }),

    closeModal: () => set({ modal: null }),
    openCheckin: () => set({ modal: { type: 'checkin' } }),
    openSettings: () => set({ modal: { type: 'settings' } }),

    // 스텝퍼: 개수를 목표치로 맞춤 (증설=빈 코트 추가, 감축=뒤 코트부터 빈 건 제거·경기 중은 pendingRemove)
    setCourtCount: (target) => set((s) => {
      const t = Math.max(1, target);
      const active = s.courts.filter((c) => !c.pendingRemove);
      if (t > active.length) {
        let courts = s.courts.map((c) => ({ ...c, pendingRemove: false }));
        let no = Math.max(0, ...courts.map((c) => c.no));
        const add = t - courts.length;
        for (let i = 0; i < add; i++) courts.push({ no: ++no, match: null });
        return { courts };
      }
      if (t < active.length) {
        let toCut = active.length - t;
        const order = [...s.courts].sort((a, b) => b.no - a.no);
        const removeIds = new Set();
        const pendIds = new Set();
        for (const c of order) {
          if (toCut <= 0) break;
          if (c.pendingRemove) continue;
          if (c.match) pendIds.add(c.no); else removeIds.add(c.no);
          toCut--;
        }
        const courts = s.courts
          .filter((c) => !removeIds.has(c.no))
          .map((c) => (pendIds.has(c.no) ? { ...c, pendingRemove: true } : c));
        return { courts };
      }
      return {};
    }),

    // 특정 코트 예약제거 토글 (경기 중일 때) / 빈 코트 즉시 제거
    toggleRemoveCourt: (courtNo) => set((s) => {
      if (s.courts.filter((c) => !c.pendingRemove).length <= 1) return {};
      const target = s.courts.find((c) => c.no === courtNo);
      if (!target) return {};
      if (target.match) return { courts: s.courts.map((c) => (c.no === courtNo ? { ...c, pendingRemove: !c.pendingRemove } : c)) };
      return { courts: s.courts.filter((c) => c.no !== courtNo) };
    }),
    // 코트 이름 변경 (빈 문자열이면 기본 'N번 코트'로 복귀)
    renameCourt: (courtNo, name) => set((s) => ({
      courts: s.courts.map((c) => (c.no === courtNo ? { ...c, name: name.trim() || undefined } : c)),
    })),
    undo: () => set((s) => (s.toast && s.toast.undo ? { ...s.toast.undo, toast: null, nowTs: Date.now() } : { toast: null })),
    dismissToast: () => set({ toast: null }),
  };

  function applyMatch(s, court, match) {
    const ids = [...match.teamA, ...match.teamB].map((p) => p.id);
    const participants = s.participants.map((p) => {
      if (!ids.includes(p.id)) return p;
      const team = match.teamA.some((x) => x.id === p.id) ? 'A' : 'B';
      return { ...p, court: court.no, team };
    });
    const fresh = (arr) => arr.map((p) => participants.find((x) => x.id === p.id));
    const startedAt = match.startedAt || Date.now();
    const courts = s.courts.map((c) => (c.no === court.no ? { ...c, match: { type: match.type, teamA: fresh(match.teamA), teamB: fresh(match.teamB), startedAt } } : c));
    return { participants, courts };
  }

  const bench = sortQueue(st.participants.filter((p) => p.status === '참여중' && p.court == null), st.nowTs);

  // 화면 선택
  let screen;
  if (st.device === 'mobile') {
    screen = <MobileApp state={st} actions={actions} />;
  } else if (st.screen === 'attendance') {
    screen = <AttendanceScreen state={st} actions={actions} />;
  } else if (st.screen === 'counts') {
    screen = <CountsScreen state={st} actions={actions} />;
  } else {
    screen = <MainScreen state={st} actions={actions} />;
  }

  return (
    <ThemeContext.Provider value={st.theme}>
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <DemoNav device={st.device} setDevice={actions.setDevice} screen={st.screen} switchScreen={actions.switchScreen} theme={st.theme} setTheme={actions.setTheme} onReset={() => setSt((s) => ({ ...initState(), theme: s.theme, device: s.device, screen: s.screen }))} />
      <div style={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', padding: 24 }}>
        <DeviceFrame device={st.device} theme={st.theme}>
          {screen}
          {st.modal && st.modal.type === 'honWarn' && (
            <HonWarnModal male={st.modal.m} female={st.modal.f} device={st.device} onResolve={actions.honWarnPick} onIgnore={actions.closeModal} />
          )}
          {st.modal && st.modal.type === 'alert' && (
            <AlertModal court={st.modal.court} rec={st.modal.rec} onPick={(t) => actions.pickAlt(st.modal.court, t)} onClose={actions.closeModal} />
          )}
          {st.modal && st.modal.type === 'edit' && (
            <EditModal court={st.modal.court} match={st.modal.match} bench={bench} onConfirm={actions.confirmEdit} onClose={actions.closeModal} />
          )}
          {st.modal && st.modal.type === 'checkin' && (
            <CheckinModal participants={st.participants} onCheckin={(id) => actions.setStatus(id, '참여중')} onClose={actions.closeModal} />
          )}
          {st.modal && st.modal.type === 'settings' && (
            <SettingsModal courts={st.courts} onSet={actions.setCourtCount} onToggleRemove={actions.toggleRemoveCourt} onRename={actions.renameCourt} onClose={actions.closeModal} />
          )}
          {st.toast && <CallToast toast={st.toast} onUndo={actions.undo} onDismiss={actions.dismissToast} onPick={(t) => actions.pickAlt({ no: st.toast.courtNo }, t)} />}
        </DeviceFrame>
      </div>
    </div>
    </ThemeContext.Provider>
  );
}

// ---------- 데모 네비 (프로토타입 전용 크롬) ----------
function DemoNav({ device, setDevice, screen, switchScreen, theme, setTheme, onReset }) {
  return (
    <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center', gap: 16, padding: '10px 20px', background: 'var(--ink)', color: '#fff' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
        <Shuttle size={18} color="#fff" />
        <span style={{ fontSize: 14.5, fontWeight: 800, letterSpacing: '-.02em', whiteSpace: 'nowrap' }}>번개 대진 운영</span>
        <span style={{ fontSize: 11.5, fontWeight: 700, color: 'rgba(255,255,255,.55)', background: 'rgba(255,255,255,.12)', padding: '3px 8px', borderRadius: 7 }}>프로토타입</span>
      </div>
      {device === 'tablet' && (
        <div style={{ display: 'flex', gap: 4, background: 'rgba(255,255,255,.1)', padding: 3, borderRadius: 999, marginLeft: 6 }}>
          {[{ k: 'main', l: '운영 화면' }, { k: 'attendance', l: '출석 체크' }, { k: 'counts', l: '개인 카운트' }].map((t) => (
            <button key={t.k} onClick={() => switchScreen(t.k)} style={{
              padding: '6px 13px', borderRadius: 999, fontSize: 13, fontWeight: 800, letterSpacing: '-.02em',
              color: screen === t.k ? 'var(--ink)' : 'rgba(255,255,255,.75)', background: screen === t.k ? '#fff' : 'transparent', whiteSpace: 'nowrap',
            }}>{t.l}</button>
          ))}
        </div>
      )}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={onReset} style={{ fontSize: 12.5, fontWeight: 700, color: 'rgba(255,255,255,.6)', padding: '6px 10px' }}>↺ 초기화</button>
        <div style={{ display: 'flex', gap: 4, background: 'rgba(255,255,255,.1)', padding: 3, borderRadius: 999 }}>
          {[{ k: 'tablet', l: '태블릿' }, { k: 'mobile', l: '모바일' }].map((d) => (
            <button key={d.k} onClick={() => setDevice(d.k)} style={{
              padding: '6px 14px', borderRadius: 999, fontSize: 13, fontWeight: 800, letterSpacing: '-.02em',
              color: device === d.k ? 'var(--ink)' : 'rgba(255,255,255,.75)', background: device === d.k ? '#fff' : 'transparent',
            }}>{d.l}</button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------- 디바이스 프레임 + 스케일러 ----------
function DeviceFrame({ device, theme, children }) {
  const W = device === 'tablet' ? 1194 : 390;
  const H = device === 'tablet' ? 834 : 844;
  const bezel = device === 'tablet' ? 16 : 13;
  const wrapRef = useRef(null);
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const fit = () => {
      const r = el.getBoundingClientRect();
      const ow = W + bezel * 2, oh = H + bezel * 2;
      setScale(Math.min(1, r.width / ow, r.height / oh));
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, [device]);

  return (
    <div ref={wrapRef} style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{
        transform: `scale(${scale})`, transformOrigin: 'center center',
        padding: bezel, background: '#0b0e14', borderRadius: device === 'tablet' ? 34 : 46,
        boxShadow: 'var(--sh-3)', flexShrink: 0,
      }}>
        <div data-theme={theme} style={{ position: 'relative', width: W, height: H, borderRadius: device === 'tablet' ? 20 : 34, overflow: 'hidden', background: 'var(--bg)' }}>
          {children}
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
