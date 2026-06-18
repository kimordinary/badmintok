// ===== core.jsx — 데이터 + 대기열 정렬 + 매칭 코어 (순수 함수) =====

// 급수 7단계 (앱 BadmintonLevel과 일치)
const LEVEL_ORDER = ['자강', 'S', 'A', 'B', 'C', 'D', '왕초심'];
const LEVEL_SCORE = { 자강: 7, S: 6, A: 5, B: 4, C: 3, D: 2, 왕초심: 1 };
const FEMALE_ADJUST = 1;

// 종목 메타
const DISCIPLINE = {
  혼복: { key: '혼복', label: '혼복', short: '혼', hue: 'mix' },
  남복: { key: '남복', label: '남복', short: '남', hue: 'men' },
  여복: { key: '여복', label: '여복', short: '여', hue: 'women' },
};

// 성향(게임) 프리셋
const PRESETS = {
  밸런스: { w_balance: 3, w_partner: 2, w_opponent: 1, w_fairness: 1 },
  '동일 급수': { w_balance: 5, w_partner: 1, w_opponent: 0.5, w_fairness: 1 },
};

// 모드
const MODES = ['혼복', '남복/여복', '모두'];

// 유효 점수 (혼복 여자 보정)
function effScore(p, type) {
  const base = LEVEL_SCORE[p.level];
  if (type === '혼복' && p.gender === 'F') return Math.max(1, base - FEMALE_ADJUST);
  return base;
}

// 페어 키
function pairKey(a, b) {
  return a < b ? a + '|' + b : b + '|' + a;
}

// 대기열 정렬: ① 경기수 적은 순 → ② 동률이면 쉰 시간(마지막 경기 후 경과) 긴 순
function sortQueue(players, nowTs) {
  return [...players].sort((x, y) => {
    if (x.totalGames !== y.totalGames) return x.totalGames - y.totalGames;
    const rx = x.lastFinished == null ? Infinity : nowTs - x.lastFinished;
    const ry = y.lastFinished == null ? Infinity : nowTs - y.lastFinished;
    return ry - rx; // 더 오래 쉰 사람 먼저
  });
}

// 4명 조합 생성 (top window)
function combinations(arr, k) {
  const res = [];
  const n = arr.length;
  const idx = Array.from({ length: k }, (_, i) => i);
  if (n < k) return res;
  while (true) {
    res.push(idx.map((i) => arr[i]));
    let i = k - 1;
    while (i >= 0 && idx[i] === n - k + i) i--;
    if (i < 0) break;
    idx[i]++;
    for (let j = i + 1; j < k; j++) idx[j] = idx[j - 1] + 1;
  }
  return res;
}

// 주어진 4명 + 종목으로 가능한 팀 split 3가지 → 비용 최소 split 반환
function bestSplit(four, type, weights, ctx) {
  const splits = [
    [[0, 1], [2, 3]],
    [[0, 2], [1, 3]],
    [[0, 3], [1, 2]],
  ];
  let best = null;
  for (const [tA, tB] of splits) {
    const teamA = [four[tA[0]], four[tA[1]]];
    const teamB = [four[tB[0]], four[tB[1]]];
    const sumA = effScore(teamA[0], type) + effScore(teamA[1], type);
    const sumB = effScore(teamB[0], type) + effScore(teamB[1], type);
    const balance = Math.pow(sumA - sumB, 2);
    const partner =
      (ctx.partner[pairKey(teamA[0].id, teamA[1].id)] || 0) +
      (ctx.partner[pairKey(teamB[0].id, teamB[1].id)] || 0);
    let opponent = 0;
    for (const a of teamA) for (const b of teamB) opponent += ctx.opponent[pairKey(a.id, b.id)] || 0;
    const fairness = four.reduce((s, p) => s + p.totalGames, 0);
    const cost =
      weights.w_balance * balance +
      weights.w_partner * partner +
      weights.w_opponent * opponent +
      weights.w_fairness * fairness * 0.15;
    if (!best || cost < best.cost) best = { teamA, teamB, type, cost, sumA, sumB };
  }
  return best;
}

// 4명의 성별 구성으로 모드 내 가능한 종목 후보 결정
function disciplinesFor(four, mode) {
  const m = four.filter((p) => p.gender === 'M').length;
  const f = four.length - m;
  const out = [];
  if (mode === '혼복') {
    // 남>=1 && 여>=1 이면 혼복 가능 (한쪽 부족시 동성페어 허용)
    if (m >= 1 && f >= 1) out.push('혼복');
  } else if (mode === '남복/여복') {
    if (m === 4) out.push('남복');
    else if (f === 4) out.push('여복');
    // 섞여있으면 이 4명 조합은 부적합 (combos에서 동성 4명 세트를 따로 찾음)
  } else {
    // 모두
    if (m === 4) out.push('남복');
    else if (f === 4) out.push('여복');
    else if (m >= 1 && f >= 1) out.push('혼복');
  }
  return out;
}

// 다음 경기 추천. 반환: {match} | {error, suggestion}
function recommendMatch(pool, mode, presetName, nowTs, bias) {
  const weights = PRESETS[presetName];
  const eligible = sortQueue(
    pool.filter((p) => p.status === '참여중' && p.court == null),
    nowTs
  );
  if (eligible.length < 4) return { error: '인원 부족', detail: '참여중 대기 인원이 4명 미만입니다.' };

  // 종목 비율 손잡이(모두 모드)가 켜지면 후보 윈도우를 넓혀 동성 4명 조합 기회를 늘린다.
  const W = bias ? 14 : 9;
  const window = eligible.slice(0, Math.min(W, eligible.length));
  const ctx = { partner: buildPairCount(pool, 'partner'), opponent: buildPairCount(pool, 'opponent') };

  // 종목별 목표 대비 부족분(>0=뒤처짐) → 그 종목을 선택 시 점수 보너스
  const biasFor = (type) => {
    if (!bias) return 0;
    const T = bias.counts.혼복 + bias.counts.남복 + bias.counts.여복;
    const cur = T > 0 ? bias.counts[type] / T : 0;
    return (bias.K || 8) * ((bias.target[type] || 0) - cur); // 부족할수록 점수↓(선호)
  };

  let best = null;
  for (const four of combinations(window, 4)) {
    const types = disciplinesFor(four, mode);
    for (const type of types) {
      const split = bestSplit(four, type, weights, ctx);
      // 대기열 앞 사람 우대: window 내 인덱스 합이 작을수록 보너스(공정성 강화)
      const idxPenalty = four.reduce((s, p) => s + window.indexOf(p), 0) * 0.8;
      const score = split.cost + idxPenalty - biasFor(type);
      if (!best || score < best.score) best = { ...split, score };
    }
  }

  if (best) {
    const diff = Math.abs(best.sumA - best.sumB);
    const pRep = (ctx.partner[pairKey(best.teamA[0].id, best.teamA[1].id)] || 0) + (ctx.partner[pairKey(best.teamB[0].id, best.teamB[1].id)] || 0);
    let oRep = 0;
    for (const a of best.teamA) for (const b of best.teamB) oRep += ctx.opponent[pairKey(a.id, b.id)] || 0;
    const fresh = pRep === 0 && oRep === 0;
    const reason = (diff === 0 ? '실력 합 동일' : `실력 차 ±${diff}`) + (fresh ? ' · 새 조합' : pRep > 0 ? ' · 재호흡' : ' · 리매치');
    return { match: { teamA: best.teamA, teamB: best.teamB, type: best.type, balanced: diff <= 1, reason } };
  }

  // 모드 내 가능한 종목 없음 → 혼복 불가 등. 대안 제안.
  if (mode === '혼복') {
    const m = eligible.filter((p) => p.gender === 'M').length;
    const f = eligible.filter((p) => p.gender === 'F').length;
    const suggestion = m >= 4 ? '남복' : f >= 4 ? '여복' : null;
    return { error: '혼복 불가', detail: '대기 인원의 성비로 혼복을 구성할 수 없습니다.', suggestion, m, f };
  }
  return { error: '구성 불가', detail: '현재 모드로 경기를 만들 수 없습니다.' };
}

function buildPairCount(pool, kind) {
  // 샘플 데이터엔 history가 들어있음. 실서비스에선 누적 카운트.
  const map = {};
  for (const p of pool) {
    const src = kind === 'partner' ? p.partnerCount : p.opponentCount;
    if (!src) continue;
    for (const [qid, c] of Object.entries(src)) map[pairKey(p.id, qid)] = Math.max(map[pairKey(p.id, qid)] || 0, c);
  }
  return map;
}

// ===== 파트너(고정 2인 팀) =====
// pairs: [{ id, members:[pid1,pid2], strict }]. strict=같이만(안 되면 대기), false=따로도 OK.
function pairTypeOf(a, b) {
  const m = (a.gender === 'M' ? 1 : 0) + (b.gender === 'M' ? 1 : 0);
  return m === 2 ? '남복' : m === 0 ? '여복' : '혼복';
}
function modeAllowsType(mode, type) {
  if (mode === '모두') return true;
  if (mode === '혼복') return type === '혼복';
  return type === '남복' || type === '여복'; // '남복/여복'
}
function findPairOpponents(avail, type, excludeIds) {
  const pool = avail.filter((p) => !excludeIds.has(p.id) && p.court == null && p.status === '참여중');
  if (type === '혼복') {
    const m = pool.find((p) => p.gender === 'M');
    const f = pool.find((p) => p.gender === 'F');
    return (m && f) ? [m, f] : null;
  }
  const g = type === '남복' ? 'M' : 'F';
  const same = pool.filter((p) => p.gender === g);
  return same.length >= 2 ? [same[0], same[1]] : null;
}
// 파트너 우선(best-effort) → 안 되면 일반 recommendMatch. strict 쌍 멤버는 일반 풀에서 제외(파트너로만 출전).
function recommendMatchPaired(pool, mode, preset, nowTs, pairs) {
  pairs = pairs || [];
  if (pairs.length) {
    const allPairIds = new Set(pairs.flatMap((p) => p.members));
    const avail = sortQueue(pool.filter((p) => p.status === '참여중' && p.court == null), nowTs);
    const avg = avail.length ? avail.reduce((s, p) => s + p.totalGames, 0) / avail.length : 0;
    for (const pr of pairs) {
      const a = avail.find((x) => x.id === pr.members[0]);
      const b = avail.find((x) => x.id === pr.members[1]);
      if (!a || !b) continue;                       // 둘 다 대기 중이어야 같이 출전
      const type = pairTypeOf(a, b);
      if (!modeAllowsType(mode, type)) continue;    // 종목 안 맞으면 같이 못 침
      if ((a.totalGames + b.totalGames) / 2 > avg + 0.5) continue; // best-effort: 앞서면 양보
      const opp = findPairOpponents(avail, type, allPairIds);      // 상대는 비-파트너에서
      if (opp) return { match: { teamA: [a, b], teamB: opp, type, balanced: true, reason: '파트너', pair: true } };
    }
    const strictIds = new Set(pairs.filter((p) => p.strict).flatMap((p) => p.members));
    if (strictIds.size) pool = pool.filter((p) => !strictIds.has(p.id)); // strict는 따로 안 뜀
  }
  return recommendMatch(pool, mode, preset, nowTs);
}

// ===== 자강(코치) 고정 코트 =====
// 코치는 한 코트에 박혀 있고(큐·카운트 제외), 나머지 3자리만 회전.
// 공동 우선: 만난 코치 수가 적은 사람부터(= 아무 코치도 못 만난 사람 최우선) +
// 같으면 경기수 적은·오래 쉰 순(sortQueue). metCount = { pid: 만난 코치 수 }.
function pickAceThree(pool, metCount, nowTs) {
  const eligible = sortQueue(pool.filter((p) => p.status === '참여중' && p.court == null), nowTs);
  if (eligible.length < 3) return null;
  // sort는 안정 정렬 → 만난 코치 수 동률이면 sortQueue 순서 유지
  const ranked = [...eligible].sort((a, b) => ((metCount && metCount[a.id]) || 0) - ((metCount && metCount[b.id]) || 0));
  return ranked.slice(0, 3);
}
// 코치 + 3명 → 매치. 색은 성비로(혼복 기본), 코치는 최약체와 한 팀(살짝 보정).
function buildAceMatch(ace, three) {
  const M = [ace, ...three].filter((p) => p.gender === 'M').length;
  const F = 4 - M;
  const type = F === 0 ? '남복' : M === 0 ? '여복' : '혼복';
  const s = [...three].sort((a, b) => LEVEL_SCORE[b.level] - LEVEL_SCORE[a.level]); // 강→약
  return { type, ace: true, teamA: [ace, s[2]], teamB: [s[0], s[1]], reason: '코치 고정', balanced: true };
}

// ===== 샘플 참가자 데이터 =====
// status: 미출석 | 참여중 | 퇴장,  court: 코트번호 or null,  team: 'A'|'B'|null
function makeParticipants() {
  // 실제 연동: window.__BM_PARTICIPANTS__ = [{name, gender:'M'|'F', level, id?}] 주입 시 그걸 사용.
  if (typeof window !== 'undefined' && Array.isArray(window.__BM_PARTICIPANTS__)) {
    return window.__BM_PARTICIPANTS__.map((p, i) => ({
      id: p.id != null ? String(p.id) : 'p' + (i + 1),
      name: p.name, gender: p.gender, level: p.level,
      status: p.status || '미출석', court: null, team: null,
      games: { 혼복: 0, 남복: 0, 여복: 0 }, totalGames: 0, lastFinished: null,
      partnerCount: {}, opponentCount: {},
    }));
  }
  // schedule 21 실제 참가자 51명. 성별 미입력자는 이름으로 유추(아래 ※표는 추정).
  const raw = [
    ['황세빈', 'F', 'S'], ['정유림', 'F', 'B'], ['이채우', 'M', 'B'], ['권혁준', 'M', 'A'],
    ['신예지', 'F', 'D'], ['최미르', 'M', 'D'], ['김준완', 'M', 'A'], ['이일금', 'M', 'B'],
    ['주완호', 'M', 'A'], ['정수호', 'M', 'A'], ['김재옥', 'F', 'A'], ['구현명', 'M', 'A'],
    ['이재복', 'M', 'B'], ['이현우', 'M', 'S'], ['양지원', 'F', 'A'], ['전혜지', 'F', 'B'],
    ['오승현', 'M', 'D'], ['정진현', 'F', 'B'], ['김교린', 'F', 'S'], ['한예준', 'M', 'D'],
    ['조진우', 'M', 'A'], ['허제식', 'M', 'A'], ['김태현', 'M', 'D'], ['송창현', 'M', 'S'],
    ['김수빈', 'F', 'B'], ['이하경', 'F', '자강'], ['정용준', 'M', 'B'], ['김정규', 'M', 'A'],
    ['박아현', 'F', 'D'], ['이임규', 'M', 'B'], ['김영동', 'M', 'B'], ['유리연', 'F', 'S'],
    ['김재혁', 'M', 'A'], ['최은지', 'F', 'S'], ['서정호', 'M', 'A'], ['유동호', 'M', 'A'],
    ['구본진', 'M', 'B'], ['강수진', 'F', 'D'], ['박지현', 'F', 'D'], ['김이준', 'M', 'C'],
    ['조우성', 'M', 'B'], ['최문태', 'M', 'S'], ['최정원', 'F', 'S'], ['김태현', 'M', 'A'],
    ['김락원', 'M', 'S'], ['문정호', 'M', 'A'], ['최정민', 'M', 'A'], ['신경진', 'M', 'A'],
    ['박성민', 'M', '왕초심'], ['고민재', 'M', '자강'], ['조장휘', 'M', 'B'],
  ];
  return raw.map((r, i) => ({
    id: 'p' + (i + 1),
    name: r[0],
    gender: r[1],
    level: r[2],
    status: '미출석',
    court: null,
    team: null,
    games: { 혼복: 0, 남복: 0, 여복: 0 },
    totalGames: 0,
    lastFinished: null,
    partnerCount: {},
    opponentCount: {},
  }));
}

Object.assign(window, {
  LEVEL_ORDER, LEVEL_SCORE, DISCIPLINE, PRESETS, MODES,
  effScore, sortQueue, recommendMatch, makeParticipants, pairKey,
  pickAceThree, buildAceMatch,
  recommendMatchPaired, pairTypeOf,
});
