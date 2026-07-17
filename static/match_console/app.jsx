// ===== app.jsx — 루트: 상태/액션 + 디바이스 프레임 + 데모 네비 =====

// ---------- 초기 상태 (데모 시드) ----------
function initState() {
  const injected = typeof window !== 'undefined' && Array.isArray(window.__BM_PARTICIPANTS__);
  const ps = makeParticipants();
  const now = Date.now();
  // 전원 미출석으로 시작 → 출석 화면에서 직접 체크인.

  // 코트 8면, 모두 비어있음 (시스템이 바로 다음 경기를 추천)
  const courts = [];
  for (let i = 1; i <= 8; i++) courts.push({ no: i, match: null });

  return {
    participants: ps,
    courts,
    mode: '모두',
    preset: '밸런스',
    auto: true,
    layout: 'compact', // 'default'(현행) | 'compact'(1열 세로 코트+대기열 확대) — 기본 컴팩트
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

// ===== 서버 연동 (schedule_console 임베드 시에만 활성) =====
const CONNECTED = typeof window !== 'undefined' && window.__BM_SESSION_ID__ != null;
const API_BASE = (typeof window !== 'undefined' && window.__BM_API_BASE__) || '';
const CSRF = (typeof window !== 'undefined' && window.__BM_CSRF__) || '';

async function apiCall(path, method, body) {
  const opt = { method, credentials: 'same-origin', headers: {} };
  if (method !== 'GET') {
    opt.headers['X-CSRFToken'] = CSRF;
    opt.headers['Content-Type'] = 'application/json';
    if (body != null) opt.body = JSON.stringify(body);
  }
  const res = await fetch(API_BASE + path, opt);
  if (!res.ok) {
    let d = {}; try { d = await res.json(); } catch (e) {}
    const err = new Error(d.detail || ('HTTP ' + res.status)); err.data = d; err.status = res.status; throw err;
  }
  return res.status === 204 ? null : res.json();
}

const _srvGender = (g) => (g === 'male' ? 'M' : g === 'female' ? 'F' : '');
const _srvLevel = (bl) => LEVEL_ORDER[7 - bl] || 'D';   // base_level 7=자강 .. 1=초심
const _SRV_ATT = { present: '참여중', not_present: '미출석', left: '퇴장' };
const _SRV_MODE = { all: '모두', mixed: '혼복', singles_gender: '남복/여복' };
const _SRV_DISC = { mixed: '혼복', mens: '남복', womens: '여복' };
// 데모 → 서버 (액션 전송용)
const DISC_TO_SRV = { 혼복: 'mixed', 남복: 'mens', 여복: 'womens' };
const MODE_TO_SRV = { 모두: 'all', 혼복: 'mixed', '남복/여복': 'singles_gender' };
const PRESET_TO_SRV = { 밸런스: 'balanced', 경쟁: 'competitive' };
const LEVEL_TO_CODE = { 자강: 'master', S: 's', A: 'a', B: 'b', C: 'c', D: 'd', 초심: 'beginner' };

function mapServerMatch(m) {
  const pl = (x) => ({ id: String(x.participant_id), name: x.name, gender: _srvGender(x.gender), level: _srvLevel(x.base_level) });
  return { type: _SRV_DISC[m.discipline] || '혼복', teamA: (m.team1 || []).map(pl), teamB: (m.team2 || []).map(pl), startedAt: m.started_at ? new Date(m.started_at).getTime() : null };
}

// 서버 session_state → 데모 UI 상태(participants/courts/mode) 매핑
function mapServerState(d, prev) {
  const partCourt = {};
  (d.courts || []).forEach((c) => {
    if (c.match) [...(c.match.team1 || []), ...(c.match.team2 || [])].forEach((pl) => { partCourt[pl.participant_id] = c.index; });
    if (c.coach) partCourt[c.coach.participant_id] = c.index;
  });
  const participants = (d.participants || []).map((p) => ({
    id: String(p.id), name: p.name, gender: _srvGender(p.gender), level: _srvLevel(p.base_level),
    status: _SRV_ATT[p.attendance] || '미출석',
    court: partCourt[p.id] != null ? partCourt[p.id] : null, team: null,
    games: { 혼복: p.games_mixed || 0, 남복: p.games_mens || 0, 여복: p.games_womens || 0 },
    totalGames: p.total_games || 0, lastFinished: null,
    partnerCount: p.partner_count || {}, opponentCount: p.opponent_count || {},
  }));
  const courts = (d.courts || []).map((c) => ({
    no: c.index, name: c.name || undefined,
    match: c.match ? mapServerMatch(c.match) : null,
    ace: !!c.coach, coachId: c.coach ? String(c.coach.participant_id) : undefined,
  }));
  // 예약(reservations)·파트너(pairs)·파트너신청(partner_requests) 매핑
  const pmap = {}; participants.forEach((p) => { pmap[p.id] = p; });
  const plById = (pid) => pmap[String(pid)] || { id: String(pid), name: '', gender: 'M', level: 'D' };
  const pending = (d.reservations || []).map((r) => {
    const ply = (r.players || []).map((x) => plById(x.participant_id));
    return { id: r.id, teamA: ply.slice(0, 2), teamB: ply.slice(2, 4), type: _SRV_DISC[r.discipline] || '혼복' };
  });
  const pairs = (d.pairs || []).map((pr) => ({ id: pr.id, members: (pr.members || []).map((m) => String(m.participant_id)), strict: pr.strict }));
  const pairRequests = (d.partner_requests || []).map((r) => ({ id: r.id, from: String(r.from.participant_id), to: String(r.to.participant_id) }));
  return { participants, courts, pending, pairs, pairRequests, mode: _SRV_MODE[d.discipline_mode] || prev.mode };
}

function App() {
  const [st, setSt] = useState(initState);
  const set = (patch) => setSt((s) => ({ ...s, ...(typeof patch === 'function' ? patch(s) : patch) }));

  // 서버 상태 즉시 재조회 (액션 직후 낙관적 갱신 대신 서버 정본 반영)
  const refetch = () => apiCall('/', 'GET')
    .then((d) => d && setSt((s) => ({ ...s, ...mapServerState(d, s) })))
    .catch(() => {});
  // 액션 API 헬퍼: 성공 시 재조회, 실패 시 토스트
  const srv = (p, m, b) => apiCall(p, m, b).then(refetch).catch((e) =>
    set({ toast: { kind: 'alert', error: '오류', detail: e.message || '요청 실패' } }));

  // 서버 연동 모드: session_state 폴링 → 서버 상태로 렌더 (2.5초)
  useEffect(() => {
    if (!CONNECTED) return;
    let alive = true;
    const poll = () => apiCall('/', 'GET')
      .then((d) => { if (alive && d) setSt((s) => ({ ...s, ...mapServerState(d, s) })); })
      .catch(() => {});
    poll();
    const t = setInterval(poll, 2500);
    return () => { alive = false; clearInterval(t); };
  }, []);

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

  // '모두' 모드 종목 균등 손잡이: 완료(games)+진행중(코트) 누적으로 부족한 종목에 보너스.
  const buildBias = (s) => {
    if (s.mode !== '모두') return null;
    const counts = { 혼복: 0, 남복: 0, 여복: 0 };
    for (const p of s.participants) { counts.혼복 += p.games.혼복; counts.남복 += p.games.남복; counts.여복 += p.games.여복; }
    counts.혼복 /= 4; counts.남복 /= 4; counts.여복 /= 4;
    for (const c of s.courts) if (c.match && counts[c.match.type] != null) counts[c.match.type] += 1;
    return { counts, target: { 혼복: 1 / 3, 남복: 1 / 3, 여복: 1 / 3 }, K: 80 };
  };

  const findRec = (s, courtNo) => {
    const taken = new Set();
    const bias = buildBias(s);
    for (const ct of s.courts) {
      if (ct.match || ct.pendingRemove) continue;
      const avail = s.participants.filter((p) => !taken.has(p.id));
      const r = recommendMatch(avail, s.mode, s.preset, s.nowTs, bias);
      if (ct.no === courtNo) return r;
      if (r.match) {
        [...r.match.teamA, ...r.match.teamB].forEach((p) => taken.add(p.id));
        if (bias && bias.counts[r.match.type] != null) bias.counts[r.match.type] += 1;
      }
    }
    return null;
  };

  const actions = {
    setMode: (mode) => CONNECTED ? srv('/mode/', 'POST', { discipline_mode: MODE_TO_SRV[mode] }) : set((s) => {
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
    setLayout: (layout) => set({ layout }),
    manualFill: (court) => set({ modal: { type: 'edit', court, match: null } }), // 수동: 빈 슬롯 편집 모달
    makeGameFromQueue: (players) => CONNECTED ? srv('/reservations/', 'POST', { participant_ids: players.map((p) => Number(p.id)) }) : set((s) => {
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
    cancelPending: (gid) => CONNECTED ? srv('/reservations/' + gid + '/', 'DELETE') : set((s) => ({ pending: s.pending.filter((g) => g.id !== gid) })),
    setPreset: (preset) => CONNECTED ? srv('/preset/', 'POST', { preset: PRESET_TO_SRV[preset] }) : set({ preset }),
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

    setStatus: (id, status) => {
      if (CONNECTED) {
        const att = status === '참여중' ? 'present' : status === '퇴장' ? 'left' : 'not_present';
        return srv('/participants/' + id + '/attendance/', 'POST', { attendance: att });
      }
      return set((s) => {
      // 경기 중(실제 코트 배정·코치)인 사람은 바로 퇴장/미출석 불가 → 유령 방지. 먼저 대타 교체하거나 경기 종료 후 처리
      if (status === '퇴장' || status === '미출석') {
        const courtOf = s.courts.find((c) => (c.match && [...c.match.teamA, ...c.match.teamB].some((p) => p.id === id)) || (c.ace && c.coachId === id));
        if (courtOf) {
          const nm = (s.participants.find((p) => p.id === id) || {}).name || '이 분';
          return { toast: { kind: 'alert', courtNo: courtOf.no, courtName: courtOf.name, error: '경기 중', detail: `${nm} 님은 코트에서 경기 중이에요. 먼저 대타로 교체하거나 경기 종료 후 처리하세요.` } };
        }
      }
      return { participants: s.participants.map((p) => (p.id === id ? { ...p, status } : p)) };
      });
    },

    endMatch: (court) => CONNECTED ? srv('/courts/' + court.no + '/end/', 'POST') : set((s) => {
      const now = Date.now();
      const m = s.courts.find((c) => c.no === court.no).match;
      if (!m) return {};
      const undo = { participants: s.participants, courts: s.courts };
      const ids = [...m.teamA, ...m.teamB].map((p) => p.id);

      // ---- 코치 코트: 코치는 남고, 나머지 3명만 복귀 + 코치 만남 기록 ----
      const aceCourt0 = s.courts.find((c) => c.no === court.no);
      if (aceCourt0 && aceCourt0.ace && !aceCourt0.pendingRemove) {
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
          const pend = pendingIdsOf(s);
          const three = pickAceThree(participants.filter((p) => !coachIds.has(p.id) && !pend.has(p.id)), metCount, now, s.mode, ace.gender);
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
      const r = recommendMatchPaired(participants, s.mode, s.preset, now, s.pairs, buildBias(s));
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
      if (CONNECTED) {
        const ids = [...match.teamA, ...match.teamB].map((p) => Number(p.id));
        return srv('/courts/' + court.no + '/fill/', 'POST', { participant_ids: ids, discipline: DISC_TO_SRV[match.type] });
      }
      set((s) => applyMatch(s, court, match));
    },

    openEdit: (court, rec) => {
      if (rec && rec.error === '혼복 불가') { set({ modal: { type: 'alert', court, rec } }); return; }
      set({ modal: { type: 'edit', court, match: court.match } });
    },

    confirmEdit: (court, match) => CONNECTED ? (set({ modal: null }), srv('/courts/' + court.no + '/fill/', 'POST', { participant_ids: [...match.teamA, ...match.teamB].map((p) => Number(p.id)), discipline: DISC_TO_SRV[match.type] })) : set((s) => ({ ...applyMatch(s, court, match), modal: null })),

    // 예약 경기(pending) 편집 — 코트에 넣지 않고 예약 명단만 교체 (court 안 건드림)
    openEditPending: (g) => set({ modal: { type: 'edit', pending: g, court: { no: g.id, match: { type: g.type, teamA: g.teamA, teamB: g.teamB }, ace: false }, match: { type: g.type, teamA: g.teamA, teamB: g.teamB } } }),
    editPending: (pendingId, match) => CONNECTED ? (set({ modal: null }), srv('/reservations/' + pendingId + '/', 'PATCH', { participant_ids: [...match.teamA, ...match.teamB].map((p) => Number(p.id)), discipline: DISC_TO_SRV[match.type] })) : set((s) => ({
      pending: (s.pending || []).map((g) => (g.id === pendingId ? { ...g, teamA: match.teamA, teamB: match.teamB, type: match.type } : g)),
      modal: null,
    })),

    pickAlt: (court, type) => set((s) => {
      const gender = type === '남복' ? 'M' : 'F';
      const pend = pendingIdsOf(s);
      const eligible = sortQueue(s.participants.filter((p) => p.status === '참여중' && p.court == null && p.gender === gender && !pend.has(p.id)), s.nowTs);
      if (eligible.length < 4) return { modal: null };
      const four = eligible.slice(0, 4);
      // 균형 split: 점수 정렬 후 1·4 / 2·3
      const sorted = [...four].sort((a, b) => LEVEL_SCORE[b.level] - LEVEL_SCORE[a.level]);
      const match = { type, teamA: [sorted[0], sorted[3]], teamB: [sorted[1], sorted[2]] };
      return { ...applyMatch(s, court, match), modal: null };
    }),

    closeModal: () => set({ modal: null }),

    // 세션 리셋: 'game'=경기·이력만 초기화(사람·출석 유지) / 'full'=게스트 삭제+출석 초기화(최초 화면)
    reset: (mode) => CONNECTED ? srv('/reset/', 'POST', { mode }) : set((s) => {
      const clearGames = (p) => ({
        ...p, court: null, team: null,
        games: { 혼복: 0, 남복: 0, 여복: 0 }, totalGames: 0,
        lastFinished: null, partnerCount: {}, opponentCount: {},
      });
      const courts = s.courts.map((c) => ({ ...c, match: null, ace: false, coachId: undefined }));
      let participants = s.participants.map(clearGames);
      if (mode === 'full') {
        participants = participants.filter((p) => !p.temp).map((p) => ({ ...p, status: '미출석' }));
      }
      return {
        courts, participants, pairs: [], pairRequests: [], pending: [], pinnedMet: {}, modal: null,
      };
    }),

    openCheckin: () => set({ modal: { type: 'checkin' } }),
    openSettings: () => set({ modal: { type: 'settings' } }),
    openAddParticipant: () => set({ modal: { type: 'addParticipant' } }),
    openEditParticipant: (p) => set({ modal: { type: 'editParticipant', p } }),
    openRecord: (p) => set({ modal: { type: 'record', p } }),

    // 파트너 묶기 / 해제
    addPair: (members, strict) => CONNECTED ? srv('/pairs/', 'POST', { p1_id: Number(members[0]), p2_id: Number(members[1]), strict: !!strict }) : set((s) => {
      if (!members || members.length !== 2 || members[0] === members[1]) return {};
      const rest = s.pairs.filter((p) => !p.members.some((m) => members.includes(m))); // 이미 묶인 사람은 새로 덮어씀
      return { pairs: [...rest, { id: 'pair' + Date.now(), members: [...members], strict: !!strict }] };
    }),
    removePair: (pairId) => CONNECTED ? srv('/pairs/' + pairId + '/', 'DELETE') : set((s) => ({ pairs: s.pairs.filter((p) => p.id !== pairId) })),

    // 참가자 파트너 신청(승인 대기) → 모임장이 승인/거절
    requestPair: (fromId, toId) => CONNECTED ? srv('/pairs/', 'POST', { p1_id: Number(fromId), p2_id: Number(toId), strict: false }) : set((s) => {
      if (!fromId || !toId || fromId === toId) return {};
      const used = (id) => s.pairs.some((p) => p.members.includes(id)) || s.pairRequests.some((r) => r.from === id || r.to === id);
      if (used(fromId) || used(toId)) return {};
      return { pairRequests: [...s.pairRequests, { id: 'req' + Date.now(), from: fromId, to: toId }] };
    }),
    approvePairRequest: (reqId) => CONNECTED ? srv('/partner-requests/' + reqId + '/approve/', 'POST') : set((s) => {
      const r = s.pairRequests.find((x) => x.id === reqId);
      if (!r) return { pairRequests: s.pairRequests.filter((x) => x.id !== reqId) };
      const rest = s.pairs.filter((p) => !p.members.some((m) => [r.from, r.to].includes(m)));
      return { pairs: [...rest, { id: 'pair' + Date.now(), members: [r.from, r.to], strict: false }], pairRequests: s.pairRequests.filter((x) => x.id !== reqId) };
    }),
    rejectPairRequest: (reqId) => CONNECTED ? srv('/partner-requests/' + reqId + '/reject/', 'POST') : set((s) => ({ pairRequests: s.pairRequests.filter((x) => x.id !== reqId) })),

    // 코치 고정/해제 (코트별, 다중 코치 가능). id=null → courtNo 코치 해제.
    togglePinned: (id, courtNo) => CONNECTED ? srv('/courts/' + courtNo + '/coach/', 'POST', id ? { participant_id: Number(id) } : {}) : set((s) => {
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
    addParticipant: (info) => CONNECTED ? (set({ modal: null }), srv('/participants/', 'POST', { name: info.name, gender: info.gender === 'M' ? 'male' : 'female', level: LEVEL_TO_CODE[info.level] })) : set((s) => {
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

    // 참가자 정보 편집 (이름/급수/성별). 출석 화면에서 호출.
    editParticipant: (id, info) => CONNECTED ? (set({ modal: null }), srv('/participants/' + id + '/', 'PATCH', { name: info.name, gender: info.gender === 'M' ? 'male' : (info.gender === 'F' ? 'female' : undefined), level: LEVEL_TO_CODE[info.level] })) : set((s) => {
      const name = (info.name || '').trim();
      if (!name || !info.level || !info.gender) return {};
      return {
        participants: s.participants.map((p) => (p.id === id ? { ...p, name, level: info.level, gender: info.gender } : p)),
        modal: null,
      };
    }),

    // 스텝퍼: 개수를 목표치로 맞춤 (증설=빈 코트 추가, 감축=뒤 코트부터 빈 건 제거·경기 중은 pendingRemove)
    setCourtCount: (target) => { if (CONNECTED) { const cur = (st.courts || []).length; const calls = []; if (target > cur) { for (let i = 0; i < target - cur; i++) calls.push(apiCall('/courts/', 'POST', {})); } else { for (let i = cur - 1; i >= target; i--) { const cno = st.courts[i] && st.courts[i].no; if (cno != null) calls.push(apiCall('/courts/' + cno + '/', 'DELETE')); } } return Promise.all(calls).then(refetch).catch((e) => set({ toast: { kind: 'alert', error: '오류', detail: e.message } })); } return set((s) => {
      const t = Math.max(1, target);
      const active = s.courts.filter((c) => !c.pendingRemove);
      if (t > active.length) {
        let need = t - active.length;
        // 1) 제거예약(pendingRemove) 취소로 먼저 충당
        let courts = s.courts.map((c) => {
          if (need > 0 && c.pendingRemove) { need--; return { ...c, pendingRemove: false }; }
          return { ...c };
        });
        // 2) 부족분만 새 코트 추가
        let no = Math.max(0, ...courts.map((c) => c.no));
        for (let i = 0; i < need; i++) courts.push({ no: ++no, match: null });
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
        // 즉시 삭제되는 코트에 있던 인원(코치 포함)은 대기 복귀 (유령 방지)
        const participants = s.participants.map((p) => (removeIds.has(p.court) ? { ...p, court: null, team: null } : p));
        return { courts, participants };
      }
      return {};
    });
    },

    // 특정 코트 예약제거 토글 (경기 중일 때) / 빈 코트 즉시 제거
    toggleRemoveCourt: (courtNo) => CONNECTED ? srv('/courts/' + courtNo + '/', 'DELETE') : set((s) => {
      if (s.courts.filter((c) => !c.pendingRemove).length <= 1) return {};
      const target = s.courts.find((c) => c.no === courtNo);
      if (!target) return {};
      if (target.match) return { courts: s.courts.map((c) => (c.no === courtNo ? { ...c, pendingRemove: !c.pendingRemove } : c)) };
      // 빈 코트 즉시 삭제 — 그 코트에 court가 걸린 사람(코치 등)은 대기 복귀
      return {
        courts: s.courts.filter((c) => c.no !== courtNo),
        participants: s.participants.map((p) => (p.court === courtNo ? { ...p, court: null, team: null } : p)),
      };
    }),
    // 코트 이름 변경 (빈 문자열이면 기본 'N번 코트'로 복귀)
    renameCourt: (courtNo, name) => CONNECTED ? srv('/courts/' + courtNo + '/', 'PATCH', { name: name }) : set((s) => ({
      courts: s.courts.map((c) => (c.no === courtNo ? { ...c, name: name.trim() || undefined } : c)),
    })),
    undo: () => set((s) => (s.toast && s.toast.undo ? { ...s.toast.undo, toast: null, nowTs: Date.now() } : { toast: null })),
    dismissToast: () => set({ toast: null }),
  };

  function pendingIdsOf(s) {
    return new Set((s.pending || []).flatMap((g) => [...g.teamA, ...g.teamB].map((p) => p.id)));
  }
  function applyMatch(s, court, match) {
    const ids = [...match.teamA, ...match.teamB].map((p) => p.id);
    const participants = s.participants.map((p) => {
      if (ids.includes(p.id)) {
        const team = match.teamA.some((x) => x.id === p.id) ? 'A' : 'B';
        return { ...p, court: court.no, team };
      }
      // 이 코트에 있었으나 새 멤버에서 빠진 사람 → 대기열 복귀 (유령 상태 방지)
      if (p.court === court.no) return { ...p, court: null, team: null };
      return p;
    });
    const fresh = (arr) => arr.map((p) => participants.find((x) => x.id === p.id));
    const startedAt = match.startedAt || Date.now();
    const courts = s.courts.map((c) => (c.no === court.no ? { ...c, match: { type: match.type, teamA: fresh(match.teamA), teamB: fresh(match.teamB), startedAt } } : c));
    return { participants, courts };
  }

  const benchPend = pendingIdsOf(st);
  // 실제 코트 배정 기준(court 필드 꼬임 방어) — 편집 후보 목록도 유령을 대기자로 인식
  const benchOnCourt = new Set();
  st.courts.forEach((c) => {
    if (c.match) [...c.match.teamA, ...c.match.teamB].forEach((p) => benchOnCourt.add(p.id));
    if (c.ace && c.coachId) benchOnCourt.add(c.coachId);
  });
  const bench = sortQueue(st.participants.filter((p) => p.status === '참여중' && !benchOnCourt.has(p.id) && !benchPend.has(p.id)), st.nowTs);
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
        <EditModal court={st.modal.court} match={st.modal.match} bench={bench} isPending={!!st.modal.pending} onConfirm={st.modal.pending ? (c, m) => actions.editPending(st.modal.pending.id, m) : actions.confirmEdit} onClose={actions.closeModal} participants={st.participants} coachIds={st.courts.filter((c) => c.ace).map((c) => c.coachId)} onTogglePin={st.modal.pending ? undefined : actions.togglePinned} />
      )}
      {st.modal && st.modal.type === 'checkin' && (
        <CheckinModal participants={st.participants} onCheckin={(id) => actions.setStatus(id, '참여중')} onClose={actions.closeModal} />
      )}
      {st.modal && st.modal.type === 'settings' && (
        <SettingsModal courts={st.courts} onSet={actions.setCourtCount} onToggleRemove={actions.toggleRemoveCourt} onRename={actions.renameCourt} onReset={actions.reset} onClose={actions.closeModal} />
      )}
      {st.modal && st.modal.type === 'addParticipant' && (
        <AddParticipantModal onAdd={actions.addParticipant} onClose={actions.closeModal} />
      )}
      {st.modal && st.modal.type === 'editParticipant' && (
        <EditParticipantModal p={st.modal.p} onSave={actions.editParticipant} onClose={actions.closeModal} />
      )}
      {st.modal && st.modal.type === 'record' && (
        <RecordSheet p={st.modal.p} participants={st.participants} onClose={actions.closeModal} />
      )}
      {st.toast && <CallToast toast={st.toast} onUndo={actions.undo} onDismiss={actions.dismissToast} onPick={(t) => actions.pickAlt({ no: st.toast.courtNo }, t)} />}
    </>
  );

  // 5500 데모와 동일: 디바이스 프레임(아이패드 목업) + 상단바 + 회색 배경 그대로
  return (
    <ThemeContext.Provider value={st.theme}>
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <DemoNav device={st.device} setDevice={actions.setDevice} screen={st.screen} switchScreen={actions.switchScreen} theme={st.theme} setTheme={actions.setTheme} onReset={() => setSt((s) => ({ ...initState(), theme: s.theme, device: s.device, screen: s.screen, layout: s.layout }))} layout={st.layout} setLayout={actions.setLayout} />
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
function DemoNav({ device, setDevice, screen, switchScreen, theme, setTheme, onReset, layout, setLayout }) {
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
        {screen === 'main' && device === 'tablet' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <span style={{ fontSize: 11.5, fontWeight: 700, color: 'rgba(255,255,255,.5)', whiteSpace: 'nowrap' }}>레이아웃</span>
            <div style={{ display: 'flex', gap: 4, background: 'rgba(255,255,255,.1)', padding: 3, borderRadius: 999 }}>
              {[{ k: 'default', l: '기본' }, { k: 'compact', l: '컴팩트' }].map((o) => (
                <button key={o.k} onClick={() => setLayout(o.k)} style={{
                  padding: '6px 14px', borderRadius: 999, fontSize: 13, fontWeight: 800, letterSpacing: '-.02em',
                  color: layout === o.k ? 'var(--ink)' : 'rgba(255,255,255,.75)', background: layout === o.k ? '#fff' : 'transparent',
                }}>{o.l}</button>
              ))}
            </div>
          </div>
        )}
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
