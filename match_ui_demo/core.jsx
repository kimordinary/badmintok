// ===== core.jsx — 데이터 + 대기열 정렬 + 매칭 코어 (순수 함수) =====

// 급수 7단계 (앱 BadmintonLevel과 일치)
const LEVEL_ORDER = ['자강', 'S', 'A', 'B', 'C', 'D', '초심'];
const LEVEL_SCORE = { 자강: 7, S: 6, A: 5, B: 4, C: 3, D: 2, 초심: 1 };
const FEMALE_ADJUST = 1;

// 종목 메타
const DISCIPLINE = {
  혼복: { key: '혼복', label: '혼복', short: '혼', hue: 'mix' },
  남복: { key: '남복', label: '남복', short: '남', hue: 'men' },
  여복: { key: '여복', label: '여복', short: '여', hue: 'women' },
};

// 성향(게임) 프리셋
// w_span: 매치 4명의 급수 폭(최고-최저) 페널티. 폭0~1(동일·인접급수)=무페널티, 폭2+부터 비용.
const PRESETS = {
  밸런스: { w_balance: 3, w_partner: 2, w_opponent: 1, w_fairness: 1, w_span: 0 },
  '동일 급수': { w_balance: 5, w_partner: 1, w_opponent: 0.5, w_fairness: 1, w_span: 20 },
};

// 직전 1판 강페널티 — 방금 같이/맞서 친 파트너·상대를 사실상 회피 (누적 페널티와 별개, 튜닝값)
const W_PREV_MATCH = 60;

// 개인 종목 편중 소프트 페널티 — 한 종목만 계속 치지 않게 (덜 친 종목 유도, 튜닝값)
const W_PERSONAL_TYPE = 3;

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
    const gx = x.totalGames + (x.virtualGames || 0), gy = y.totalGames + (y.virtualGames || 0);
    if (gx !== gy) return gx - gy; // 실효 경기수(실제+가상=늦참 페널티) 적은 순
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
    const fairness = four.reduce((s, p) => s + p.totalGames + (p.virtualGames || 0), 0);
    // 직전 1판 강페널티: 방금 같이/맞서 친 파트너·상대를 사실상 회피 (누적 페널티와 별개)
    let prevRep = 0;
    if (teamA[0].recentP && teamA[0].recentP.includes(teamA[1].id)) prevRep++;
    if (teamB[0].recentP && teamB[0].recentP.includes(teamB[1].id)) prevRep++;
    for (const a of teamA) for (const b of teamB) if (a.recentO && a.recentO.includes(b.id)) prevRep++;
    // 개인 종목 편중 소프트: 이 종목을 이미 많이 친 4명일수록 페널티 → 덜 친 사람이 이 종목에
    const personalPen = four.reduce((s, p) => s + (p.games[type] || 0), 0);
    const cost =
      weights.w_balance * balance +
      weights.w_partner * partner +
      weights.w_opponent * opponent +
      weights.w_fairness * fairness * 0.15 +
      W_PREV_MATCH * prevRep +
      W_PERSONAL_TYPE * personalPen;
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
  // 급수 폭 제한(동일 급수)도 후보를 넓혀야 비슷한 급수 4명을 모을 기회가 는다.
  // 단일 종목 모드(혼복/남여복)는 성별 조합 제약이 커서 후보 윈도우를 넓혀야 조합을 찾음
  // (좁으면 남녀 충분해도 앞칸만 보고 매칭 실패 → 코트 빔. 진짜 성비 부족은 넓혀도 실패=정상)
  const W = bias ? 14 : (weights.w_span ? 16 : (mode !== '모두' ? 12 : 9));
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
    // 급수 폭 페널티(4명 전체): 폭0~1 무페널티, 폭2부터 비용. 먼 급수(A-D) 매치 억제.
    let spanPen = 0;
    if (weights.w_span) {
      const sc = four.map((p) => LEVEL_SCORE[p.level]);
      const sp = Math.max(...sc) - Math.min(...sc);
      spanPen = sp <= 1 ? 0 : weights.w_span * (sp - 1) * (sp - 1);
    }
    for (const type of types) {
      const split = bestSplit(four, type, weights, ctx);
      // 대기열 앞 사람 우대: window 내 인덱스 합이 작을수록 보너스(공정성 강화)
      const idxPenalty = four.reduce((s, p) => s + window.indexOf(p), 0) * 0.8;
      const score = split.cost + idxPenalty - biasFor(type) + spanPen;
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
function recommendMatchPaired(pool, mode, preset, nowTs, pairs, bias) {
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
  return recommendMatch(pool, mode, preset, nowTs, bias);
}

// ===== 자강(코치) 고정 코트 =====
// 코치는 한 코트에 박혀 있고(큐·카운트 제외), 나머지 3자리만 회전.
// 공동 우선: 만난 코치 수가 적은 사람부터(= 아무 코치도 못 만난 사람 최우선) +
// 같으면 경기수 적은·오래 쉰 순(sortQueue). metCount = { pid: 만난 코치 수 }.
// 코치 + 3명 선발. 종목 모드 규칙 그대로: 남복/여복=코치와 동성 3명, 혼복=반대성별2+동성1(→남2여2), 모두=유연.
// 3명은 급수 근접(재미) + 아직 코치 못 만난 사람 우선(커버리지).
function pickAceThree(pool, metCount, nowTs, mode, coachGender) {
  const eligible = sortQueue(pool.filter((p) => p.status === '참여중' && p.court == null), nowTs);
  const met = (p) => (metCount && metCount[p.id]) || 0;
  const anchorOf = (list) => (list.length ? [...list].sort((a, b) => met(a) - met(b))[0] : null);
  const band = (p, ref) => { const d = Math.abs(LEVEL_SCORE[p.level] - LEVEL_SCORE[ref.level]); return d <= 1 ? 0 : d; };
  // ref와 급수 근접(±1 동급) → 동률이면 커버리지 우선, list에서 n명
  const near = (list, ref, n) => list.filter((p) => p.id !== ref.id).sort((a, b) => (band(a, ref) !== band(b, ref) ? band(a, ref) - band(b, ref) : met(a) - met(b))).slice(0, n);

  if (mode === '남복/여복') {
    // 동성복 — 코치와 같은 성별 3명
    const same = eligible.filter((p) => p.gender === coachGender);
    const anchor = anchorOf(same);
    if (!anchor) return null;
    const rest = near(same, anchor, 2);
    if (rest.length < 2) return null;
    return [anchor, ...rest];
  }
  if (mode === '혼복') {
    // 혼복(남2여2) — 코치 반대 성별 2 + 코치 성별 1
    const opp = coachGender === 'M' ? 'F' : 'M';
    const oppList = eligible.filter((p) => p.gender === opp);
    const sameList = eligible.filter((p) => p.gender === coachGender);
    const anchor = anchorOf(oppList);
    if (!anchor || sameList.length < 1) return null;
    const opp2 = [anchor, ...near(oppList, anchor, 1)];
    if (opp2.length < 2) return null;
    const same1 = near(sameList, anchor, 1); // 앵커 급수 기준 코치 성별 1명
    if (same1.length < 1) return null;
    return [opp2[0], opp2[1], same1[0]];
  }
  // 모두 — 성별 유연
  const anchor = anchorOf(eligible);
  if (!anchor) return null;
  const rest = near(eligible, anchor, 2);
  if (rest.length < 2) return null;
  return [anchor, ...rest];
}
// 코치 + 3명 → 매치. 종목은 4명(코치 포함) 성비로 결정, 코치는 최약체와 한 팀(밸런스).
function buildAceMatch(ace, three) {
  const M = [ace, ...three].filter((p) => p.gender === 'M').length;
  const type = (4 - M) === 0 ? '남복' : M === 0 ? '여복' : '혼복';
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
  // 테스트 명단 53명. 성별 미입력자는 이름으로 유추(※표). 부거산은 급수 미입력 → 임시 D.
  const raw = [
    ['김형규', 'M', '자강'], ['김동건', 'M', 'C'], ['박민희', 'F', 'B'], ['송유하', 'F', 'B'], // ※박민희·송유하 성별 추정
    ['현광민', 'M', '자강'], ['박기영', 'M', 'C'], ['박유진', 'F', 'C'], ['김현아', 'F', 'D'], // ※박기영 성별 추정
    ['김형준', 'M', '초심'], ['손진옥', 'F', '초심'], ['김유미', 'F', '초심'], ['강병성', 'M', 'C'], // ※김유미 성별 추정
    ['정지혜', 'F', 'D'], ['정재윤', 'M', '초심'], ['양우범', 'M', '초심'], ['이원영', 'F', 'A'],
    ['이용호', 'M', '초심'], ['강윤영', 'F', '초심'], ['정다복', 'F', 'D'], ['문영빈', 'M', 'D'],
    ['김지혜', 'F', 'D'], ['한동휘', 'M', 'D'], ['유상수', 'M', 'C'], ['배명훈', 'M', 'D'], // ※한동휘 성별 추정
    ['이다현', 'F', '초심'], ['강민준', 'M', '초심'], ['최정로', 'M', 'D'], ['조연수', 'F', 'B'],
    ['송정훈', 'M', '초심'], ['양윤성', 'F', 'C'], ['문채은', 'F', 'C'], ['윤영광', 'M', '초심'],
    ['박소영', 'F', 'C'], ['유동훈', 'M', 'A'], ['오지원', 'F', '초심'], ['양윤혁', 'M', 'D'],
    ['현은수', 'F', '초심'], ['이민규', 'M', 'B'], ['이명수', 'M', '초심'], ['강용성', 'M', 'C'], // ※이명수 성별 추정
    ['김미현', 'F', 'D'], ['부거산', 'M', 'D'], // ※부거산 급수 미입력 → 임시 D
    ['오승미', 'F', 'B'], ['강수정', 'F', 'B'], ['송아람', 'F', 'A'], ['김민선', 'F', 'C'],
    ['김가영', 'F', 'C'], ['허지은', 'F', 'A'], ['현채영', 'F', 'D'], ['고아라', 'F', 'C'],
    ['이정란', 'F', 'C'], ['허이진', 'F', '초심'], ['김예찬', 'M', 'A'], ['박혜지', 'F', 'B'],
  ];
  const mkP = (id, name, gender, level) => ({
    id, name, gender, level,
    status: '참여중', court: null, team: null,
    games: { 혼복: 0, 남복: 0, 여복: 0 },
    totalGames: 0, lastFinished: null,
    partnerCount: {}, opponentCount: {},
  });
  const base = raw.map((r, i) => mkP('p' + (i + 1), r[0], r[1], r[2]));

  // 랜덤 50명 추가 (급수·성별 랜덤)
  const LEVELS = ['자강', 'S', 'A', 'B', 'C', 'D', '초심'];
  const SUR = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임', '한', '오', '서', '신', '권', '황', '안', '송', '류', '홍'];
  const GIV = ['민준', '서연', '도윤', '하은', '시우', '지우', '주원', '서현', '예준', '수아', '지호', '지민', '현우', '유진', '건우', '채원', '우진', '다은', '선우', '예은', '민서', '준서', '지안', '하윤', '정우', '수빈', '태윤', '가은', '동현', '나연'];
  const rnd = (a) => a[Math.floor(Math.random() * a.length)];
  const extra = Array.from({ length: 50 }, (_, i) =>
    mkP('r' + (i + 1), rnd(SUR) + rnd(GIV), Math.random() < 0.5 ? 'M' : 'F', rnd(LEVELS))
  );

  return [...base, ...extra].slice(0, 50);
}

Object.assign(window, {
  LEVEL_ORDER, LEVEL_SCORE, DISCIPLINE, PRESETS, MODES,
  effScore, sortQueue, recommendMatch, makeParticipants, pairKey,
  pickAceThree, buildAceMatch,
  recommendMatchPaired, pairTypeOf,
});
