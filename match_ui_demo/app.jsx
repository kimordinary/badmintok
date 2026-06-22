// ===== app.jsx — 루트: 상태/액션 + 디바이스 프레임 + 데모 네비 =====

// ---------- 초기 상태 (데모 시드) ----------
function initState() {
  const injected = typeof window !== 'undefined' && Array.isArray(window.__BM_PARTICIPANTS__);
  const ps = makeParticipants();
  const now = Date.now();
  // 데모: 전원 참여중으로 시작. 실제 연동(주입): 미출석 유지 → 출석 체크부터.
  if (!injected) ps.forEach((p) => { p.status = '참여중'; });

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
    pinnedMet: {}, // 코치별 만난 사람 { coachId: { pid: true } }  (코치는 court.coachId에 저장)
    pairs: [], // 파트너 고정 쌍 [{ id, members:[pid,pid], strict }]
    pairRequests: [], // 참가자 파트너 신청(승인 대기) [{ id, from, to }]
    screen: injected ? 'attendance' : 'main',
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
      // 자동 모드: 이미 알림 나간 '다음 경기'는 안 건드리고 항상 '이후 예정(예약)'에 추가.
      // 수동 모드: 빈 코트 있으면 바로 배치, 없으면 예약.
      const empty = !s.auto && s.courts.find((c) => !c.match && !c.pendingRemove && !c.ace);
      if (empty) return { modal: { type: 'edit', court: empty, match: { teamA, teamB, type } } };
      return { pending: [...s.pending, { id: 'g' + Date.now(), teamA, teamB, type }], toast: { kind: 'empty', courtName: '이후 예정', error: '예약됨', detail: '이후 예정에 추가했어요. 코트가 비면 우선 투입돼요.' } };
    }),
    cancelPending: (gid) => set((s) => ({ pending: s.pending.filter((g) => g.id !== gid) })),
    setPreset: (preset) => set({ preset }),
    switchScreen: (screen) => set({ screen }),
    setDevice: (device) => set({ device }),
    setTheme: (theme) => set({ theme }),

    // 출석 새로고침: 실제 콘솔(주입 모드)은 서버에서 출석 현황을 다시 불러온다(페이지 재로딩
    // → checked_in_at 재조회 → 새로 체크인한 사람 반영, 출석 화면으로 복귀). 순수 데모는
    // 불러올 서버가 없어 다른 화면으로 튀지 않고 그 자리에서만 갱신한다.
    refresh: () => {
      const injected = typeof window !== 'undefined' && Array.isArray(window.__BM_PARTICIPANTS__);
      if (injected) { location.reload(); return; }
      set({ nowTs: Date.now() });
    },

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

      // ---- 코치 코트: 코치는 남고, 나머지 3명만 복귀 + 코치 만남 기록 ----
      const aceCourt0 = s.courts.find((c) => c.no === court.no);
      if (aceCourt0 && aceCourt0.ace) {
        const aceId = aceCourt0.coachId;
        const tA = m.teamA.map((p) => p.id), tB = m.teamB.map((p) => p.id);
        const participants = s.participants.map((p) => {
          if (!ids.includes(p.id)) return p;
          const games = { ...p.games, [m.type]: p.games[m.type] + 1 };
          const sameTeam = tA.includes(p.id) ? tA : tB;
          const oppTeam = tA.includes(p.id) ? tB : tA;
          const partnerCount = { ...p.partnerCount };
          sameTeam.filter((x) => x !== p.id).forEach((x) => { partnerCount[x] = (partnerCount[x] || 0) + 1; });
          const opponentCount = { ...p.opponentCount };
          oppTeam.forEach((x) => { opponentCount[x] = (opponentCount[x] || 0) + 1; });
          // 코치: 코트 유지(큐엔 안 올라옴), 3명: 대기 복귀
          const base = { ...p, games, totalGames: p.totalGames + 1, lastFinished: now, partnerCount, opponentCount };
          return p.id === aceId ? base : { ...base, court: null, team: null };
        });
        const courts = s.courts.map((c) => (c.no === court.no ? { ...c, match: null } : c));
        const pinnedMet = { ...s.pinnedMet, [aceId]: { ...(s.pinnedMet[aceId] || {}) } };
        ids.filter((x) => x !== aceId).forEach((x) => { pinnedMet[aceId][x] = true; });
        if (s.auto) {
          const coachIds = new Set(s.courts.filter((c) => c.ace).map((c) => c.coachId));
          const metCount = {};
          Object.values(pinnedMet).forEach((mm) => Object.keys(mm).forEach((pid) => { metCount[pid] = (metCount[pid] || 0) + 1; }));
          const three = pickAceThree(participants.filter((p) => !coachIds.has(p.id)), metCount, now);
          if (three) {
            const ace = participants.find((p) => p.id === aceId);
            const match = buildAceMatch(ace, three);
            const applied = applyMatch({ participants, courts }, court, { ...match, startedAt: now });
            return { participants: applied.participants, courts: applied.courts, pinnedMet, nowTs: now,
              toast: { kind: 'call', courtNo: court.no, players: [...match.teamA, ...match.teamB], type: match.type, reason: '코치 고정', undo } };
          }
        }
        return { participants, courts, pinnedMet, nowTs: now,
          toast: { kind: 'empty', courtNo: court.no, error: '코치 코트 대기', detail: '대기 인원이 모이면 코치와 경기합니다.', undo } };
      }

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
      // 자동 배정: 예약(이후 예정) 우선 투입 → 없으면 자동 추천
      if (s.pending && s.pending.length) {
        const g = s.pending[0];
        const applied = applyMatch({ participants, courts }, court, { ...g, startedAt: now });
        return {
          participants: applied.participants, courts: applied.courts, pending: s.pending.slice(1), nowTs: now,
          toast: { kind: 'call', courtNo: court.no, courtName, players: [...g.teamA, ...g.teamB], type: g.type, reason: '예약', undo },
        };
      }
      const r = recommendMatchPaired(participants, s.mode, s.preset, now, s.pairs);
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
    openAddParticipant: () => set({ modal: { type: 'addParticipant' } }),

    // 파트너 묶기 / 해제
    addPair: (members, strict) => set((s) => {
      if (!members || members.length !== 2 || members[0] === members[1]) return {};
      const rest = s.pairs.filter((p) => !p.members.some((m) => members.includes(m))); // 이미 묶인 사람은 새로 덮어씀
      return { pairs: [...rest, { id: 'pair' + Date.now(), members: [...members], strict: !!strict }] };
    }),
    removePair: (pairId) => set((s) => ({ pairs: s.pairs.filter((p) => p.id !== pairId) })),

    // 참가자 파트너 신청(승인 대기) → 모임장이 승인/거절
    requestPair: (fromId, toId) => set((s) => {
      if (!fromId || !toId || fromId === toId) return {};
      const used = (id) => s.pairs.some((p) => p.members.includes(id)) || s.pairRequests.some((r) => r.from === id || r.to === id);
      if (used(fromId) || used(toId)) return {};
      return { pairRequests: [...s.pairRequests, { id: 'req' + Date.now(), from: fromId, to: toId }] };
    }),
    approvePairRequest: (reqId) => set((s) => {
      const r = s.pairRequests.find((x) => x.id === reqId);
      if (!r) return { pairRequests: s.pairRequests.filter((x) => x.id !== reqId) };
      const rest = s.pairs.filter((p) => !p.members.some((m) => [r.from, r.to].includes(m)));
      return { pairs: [...rest, { id: 'pair' + Date.now(), members: [r.from, r.to], strict: false }], pairRequests: s.pairRequests.filter((x) => x.id !== reqId) };
    }),
    rejectPairRequest: (reqId) => set((s) => ({ pairRequests: s.pairRequests.filter((x) => x.id !== reqId) })),

    // 코치 고정/해제 (코트별, 다중 코치 가능). id=null → courtNo 코치 해제.
    togglePinned: (id, courtNo) => set((s) => {
      let participants = s.participants.map((p) => ({ ...p }));
      const freeCourt = (no) => { participants = participants.map((p) => (p.court === no ? { ...p, court: null, team: null } : p)); };
      let courts = s.courts.map((c) => ({ ...c }));
      // 같은 코치가 다른 코트에 있으면 그쪽을 먼저 해제(옮기기)
      if (id) courts.forEach((c) => { if (c.ace && c.coachId === id && c.no !== courtNo) { freeCourt(c.no); c.ace = false; c.coachId = undefined; c.match = null; } });
      freeCourt(courtNo); // 대상 코트 인원 대기 복귀
      courts = courts.map((c) => (c.no === courtNo ? { ...c, ace: !!id, coachId: id || undefined, match: null } : c));
      const pinnedMet = { ...s.pinnedMet };
      if (id) {
        participants = participants.map((p) => (p.id === id ? { ...p, status: '참여중', court: courtNo, team: null } : p));
        if (!pinnedMet[id]) pinnedMet[id] = {};
      }
      return { courts, participants, pinnedMet, modal: null };
    }),

    // 명단에 없는 임시 참가자 추가 (세션 한정). 바로 참여중으로 편입.
    addParticipant: (info) => set((s) => {
      const name = (info.name || '').trim();
      if (!name || !info.level || !info.gender) return {};
      const np = {
        id: 'px' + Date.now(), name, gender: info.gender, level: info.level,
        status: '참여중', court: null, team: null,
        games: { 혼복: 0, 남복: 0, 여복: 0 }, totalGames: 0, lastFinished: null,
        partnerCount: {}, opponentCount: {}, temp: true,
      };
      return { participants: [...s.participants, np], modal: null };
    }),

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
  // 실제 연동(주입) 시 데모 크롬·디바이스 베젤 없이 풀스크린 운영석으로
  const embedded = typeof window !== 'undefined' && Array.isArray(window.__BM_PARTICIPANTS__);

  // 화면 선택
  let screen;
  if (st.screen === 'participant') {
    screen = <ParticipantScreen state={st} actions={actions} />;
  } else if (st.device === 'mobile') {
    screen = <MobileApp state={st} actions={actions} />;
  } else if (st.screen === 'attendance') {
    screen = <AttendanceScreen state={st} actions={actions} />;
  } else if (st.screen === 'counts') {
    screen = <CountsScreen state={st} actions={actions} />;
  } else {
    screen = <MainScreen state={st} actions={actions} />;
  }

  const overlays = (
    <>
      {st.modal && st.modal.type === 'honWarn' && (
        <HonWarnModal male={st.modal.m} female={st.modal.f} device={st.device} onResolve={actions.honWarnPick} onIgnore={actions.closeModal} />
      )}
      {st.modal && st.modal.type === 'alert' && (
        <AlertModal court={st.modal.court} rec={st.modal.rec} onPick={(t) => actions.pickAlt(st.modal.court, t)} onClose={actions.closeModal} />
      )}
      {st.modal && st.modal.type === 'edit' && (
        <EditModal court={st.modal.court} match={st.modal.match} bench={bench} onConfirm={actions.confirmEdit} onClose={actions.closeModal} participants={st.participants} coachIds={st.courts.filter((c) => c.ace).map((c) => c.coachId)} onTogglePin={actions.togglePinned} />
      )}
      {st.modal && st.modal.type === 'checkin' && (
        <CheckinModal participants={st.participants} onCheckin={(id) => actions.setStatus(id, '참여중')} onClose={actions.closeModal} />
      )}
      {st.modal && st.modal.type === 'settings' && (
        <SettingsModal courts={st.courts} onSet={actions.setCourtCount} onToggleRemove={actions.toggleRemoveCourt} onRename={actions.renameCourt} onClose={actions.closeModal} />
      )}
      {st.modal && st.modal.type === 'addParticipant' && (
        <AddParticipantModal onAdd={actions.addParticipant} onClose={actions.closeModal} />
      )}
      {st.toast && <CallToast toast={st.toast} onUndo={actions.undo} onDismiss={actions.dismissToast} onPick={(t) => actions.pickAlt({ no: st.toast.courtNo }, t)} />}
    </>
  );

  // 실제 연동: 태블릿 사이즈(1194×834) 고정 + 화면 맞춰 스케일 (데모 크롬·베젤 없음)
  if (embedded) {
    return (
      <ThemeContext.Provider value={st.theme}>
        <div style={{ width: '100vw', height: '100vh', overflow: 'hidden', background: '#0b0e14' }}>
          <DeviceFrame device="tablet" theme={st.theme} bare>
            {screen}
            {overlays}
          </DeviceFrame>
        </div>
      </ThemeContext.Provider>
    );
  }

  // 데모: 디바이스 프레임 + 데모 네비
  return (
    <ThemeContext.Provider value={st.theme}>
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <DemoNav device={st.device} setDevice={actions.setDevice} screen={st.screen} switchScreen={actions.switchScreen} theme={st.theme} setTheme={actions.setTheme} onReset={() => setSt((s) => ({ ...initState(), theme: s.theme, device: s.device, screen: s.screen }))} />
      <div style={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)', padding: 24 }}>
        <DeviceFrame device={st.device} theme={st.theme}>
          {screen}
          {overlays}
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
          {[{ k: 'main', l: '운영 화면' }, { k: 'attendance', l: '출석 체크' }, { k: 'counts', l: '개인 카운트' }, { k: 'participant', l: '참가자 화면' }].map((t) => (
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
function DeviceFrame({ device, theme, children, bare }) {
  const W = device === 'tablet' ? 1194 : 390;
  const H = device === 'tablet' ? 834 : 844;
  const bezel = bare ? 0 : (device === 'tablet' ? 16 : 13);
  const wrapRef = useRef(null);
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const fit = () => {
      const r = el.getBoundingClientRect();
      const ow = W + bezel * 2, oh = H + bezel * 2;
      // bare(운영): 화면 채우게 업스케일 허용. 데모: 1배 이하만.
      setScale(Math.min(bare ? Infinity : 1, r.width / ow, r.height / oh));
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, [device, bare]);

  return (
    <div ref={wrapRef} style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{
        transform: `scale(${scale})`, transformOrigin: 'center center',
        padding: bezel, background: bare ? 'transparent' : '#0b0e14', borderRadius: bare ? 0 : (device === 'tablet' ? 34 : 46),
        boxShadow: bare ? 'none' : 'var(--sh-3)', flexShrink: 0,
      }}>
        <div data-theme={theme} style={{ position: 'relative', width: W, height: H, borderRadius: bare ? 0 : (device === 'tablet' ? 20 : 34), overflow: 'hidden', background: 'var(--bg)' }}>
          {children}
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
