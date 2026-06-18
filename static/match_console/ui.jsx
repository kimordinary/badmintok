// ===== ui.jsx — 공용 컴포넌트 =====
const { useState, useEffect, useLayoutEffect, useRef, useMemo, useContext } = React;

// 테마 컨텍스트 ('sporty' | 'clean')
const ThemeContext = React.createContext('sporty');
function useTheme() { return useContext(ThemeContext); }

// 급수 칩 — 진하기 순(자강=가장 진함). 종목 색과 안 겹치도록 슬레이트 램프.
const LEVEL_STYLE = {
  자강:   { bg: '#11161f', fg: '#ffd66b', ring: '#3b3320' },
  S:      { bg: '#2b3344', fg: '#ffffff' },
  A:      { bg: '#414b60', fg: '#ffffff' },
  B:      { bg: '#5b6678', fg: '#ffffff' },
  C:      { bg: '#828c9e', fg: '#ffffff' },
  D:      { bg: '#c2cad6', fg: '#2b3344' },
  왕초심: { bg: '#e1e6ee', fg: '#5b6678' },
};
function LevelChip({ level, size = 26 }) {
  const s = LEVEL_STYLE[level] || LEVEL_STYLE.C;
  const isWang = level === '왕초심';
  const isMulti = level.length >= 2; // 자강·왕초심 등 2글자는 알약형
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      minWidth: isMulti ? 'auto' : size, height: size, padding: isMulti ? '0 8px' : '0 6px',
      borderRadius: size / 2, background: s.bg, color: s.fg,
      fontSize: isWang ? 11 : isMulti ? 11.5 : 12.5, fontWeight: 800, letterSpacing: '-.02em',
      boxShadow: s.ring ? `inset 0 0 0 1.5px ${s.ring}` : 'none', flexShrink: 0, whiteSpace: 'nowrap',
    }}>{level}</span>
  );
}

// 성별 점 (작은 표시)
function GenderDot({ gender, size = 7 }) {
  return <span style={{ width: size, height: size, borderRadius: size, background: gender === 'M' ? 'var(--men)' : 'var(--women)', display: 'inline-block', flexShrink: 0 }} />;
}

// 종목 배지
function DisciplineBadge({ type, size = 'md' }) {
  const map = {
    혼복: { fg: 'var(--mix-ink)', bg: 'var(--mix-tint)', ln: 'var(--mix-line)', dot: 'var(--mix)' },
    남복: { fg: 'var(--men-ink)', bg: 'var(--men-tint)', ln: 'var(--men-line)', dot: 'var(--men)' },
    여복: { fg: 'var(--women-ink)', bg: 'var(--women-tint)', ln: 'var(--women-line)', dot: 'var(--women)' },
  };
  const c = map[type] || map.혼복;
  const big = size === 'lg';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: big ? '5px 12px' : '3px 9px', borderRadius: 999,
      background: c.bg, color: c.fg, border: `1px solid ${c.ln}`,
      fontSize: big ? 15 : 12.5, fontWeight: 800, letterSpacing: '-.02em', flexShrink: 0, whiteSpace: 'nowrap',
    }}>
      <span style={{ width: big ? 8 : 7, height: big ? 8 : 7, borderRadius: 8, background: c.dot }} />
      {type}
    </span>
  );
}

function disciplineColor(type) {
  return type === '혼복' ? 'mix' : type === '남복' ? 'men' : 'women';
}

// 아바타 (이니셜)
// 성별 기호 토큰 (이전 이니셜 아바타 대체) — ♂ 파랑 / ♀ 핑크, 작게
function Avatar({ name, gender, size = 34 }) {
  const d = Math.min(size, 26);
  const m = gender === 'M';
  return (
    <span style={{
      width: d, height: d, borderRadius: '50%',
      background: m ? 'var(--men-tint)' : 'var(--women-tint)',
      color: m ? 'var(--men-ink)' : 'var(--women-ink)',
      border: `1px solid ${m ? 'var(--men-line)' : 'var(--women-line)'}`,
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontSize: d * 0.58, fontWeight: 800, flexShrink: 0, lineHeight: 1,
    }}>{m ? '♂' : '♀'}</span>
  );
}

// 인라인 성별 기호 (이름 옆 작게) — 배경 없이 글자만
function GenderMark({ gender, size = 13 }) {
  const m = gender === 'M';
  return <span style={{ fontSize: size, fontWeight: 900, color: m ? 'var(--men)' : 'var(--women)', lineHeight: 1, flexShrink: 0 }}>{m ? '♂' : '♀'}</span>;
}

// 플레이어 행 (이름 + 급수 + 성별점)
function PlayerLine({ p, showAvatar = true, big = false, dim = false }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 9, opacity: dim ? 0.5 : 1 }}>
      {showAvatar && <Avatar name={p.name} gender={p.gender} size={big ? 38 : 30} />}
      <span style={{ fontSize: big ? 18 : 15, fontWeight: 700, color: 'var(--ink)', letterSpacing: '-.02em', whiteSpace: 'nowrap' }}>{p.name}</span>
      <LevelChip level={p.level} size={big ? 24 : 21} />
    </div>
  );
}

// 이름 + 앞에 작은 성별 기호 (한 줄, 재사용)
function NameWithGender({ p, size = 15 }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, minWidth: 0 }}>
      <GenderMark gender={p.gender} size={Math.round(size * 0.82)} />
      <span style={{ fontSize: size, fontWeight: 800, letterSpacing: '-.03em', color: 'var(--ink)', whiteSpace: 'nowrap' }}>{p.name}</span>
    </span>
  );
}

// 선수 셀: [급수칩] ♂이름  — 한 줄. reverse면 우측 정렬용으로 칩이 바깥쪽.
function PlayerCell({ p, levelSize = 20, nameSize = 15, reverse = false, dim = false, gap = 8, flags = null }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap, flexDirection: reverse ? 'row-reverse' : 'row', opacity: dim ? 0.5 : 1, minWidth: 0 }}>
      <LevelChip level={p.level} size={levelSize} />
      <NameWithGender p={p} size={nameSize} />
      {flags}
    </div>
  );
}

// 세그먼트 토글
function Segmented({ options, value, onChange, accent = 'var(--brand)', size = 'md' }) {
  const big = size === 'lg';
  return (
    <div style={{ display: 'inline-flex', background: 'var(--surface-3)', borderRadius: 999, padding: 4, gap: 2 }}>
      {options.map((opt) => {
        const v = typeof opt === 'string' ? opt : opt.value;
        const label = typeof opt === 'string' ? opt : opt.label;
        const active = v === value;
        return (
          <button key={v} onClick={() => onChange(v)} style={{
            padding: big ? '11px 20px' : '8px 16px', borderRadius: 999,
            fontSize: big ? 15.5 : 14, fontWeight: 700, letterSpacing: '-.02em',
            color: active ? '#fff' : 'var(--ink-2)',
            background: active ? accent : 'transparent',
            boxShadow: active ? 'var(--sh-1)' : 'none',
            transition: 'all .18s ease', whiteSpace: 'nowrap',
          }}>{label}</button>
        );
      })}
    </div>
  );
}

// 버튼
function Btn({ children, onClick, variant = 'primary', size = 'md', full = false, disabled = false, style = {} }) {
  const sizes = {
    sm: { p: '8px 14px', fs: 13.5, r: 10 },
    md: { p: '12px 18px', fs: 15, r: 12 },
    lg: { p: '16px 22px', fs: 17, r: 14 },
    xl: { p: '19px 26px', fs: 19, r: 16 },
  }[size];
  const variants = {
    primary: { background: 'var(--brand)', color: '#fff', shadow: '0 2px 0 var(--brand-dk), var(--sh-1)' },
    danger: { background: 'var(--danger)', color: '#fff', shadow: '0 2px 0 #b8383c' },
    ghost: { background: 'var(--surface)', color: 'var(--ink-2)', shadow: 'none', border: '1px solid var(--line-2)' },
    soft: { background: 'var(--surface-3)', color: 'var(--ink)', shadow: 'none' },
  }[variant];
  const [press, setPress] = useState(false);
  return (
    <button
      onClick={disabled ? undefined : onClick}
      onPointerDown={() => setPress(true)} onPointerUp={() => setPress(false)} onPointerLeave={() => setPress(false)}
      style={{
        padding: sizes.p, fontSize: sizes.fs, fontWeight: 800, letterSpacing: '-.02em',
        borderRadius: sizes.r, width: full ? '100%' : 'auto',
        background: variants.background, color: variants.color,
        boxShadow: press ? 'var(--sh-1)' : variants.shadow,
        border: variants.border || 'none',
        opacity: disabled ? 0.45 : 1, cursor: disabled ? 'not-allowed' : 'pointer',
        transform: press ? 'translateY(1px)' : 'none', transition: 'transform .08s, box-shadow .08s',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8, whiteSpace: 'nowrap',
        ...style,
      }}
    >{children}</button>
  );
}

// 셔틀콕 마크
function Shuttle({ size = 22, color = 'var(--brand)' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="18.5" r="3.4" fill={color} />
      <path d="M12 16.5 L7 4 M12 16.5 L10 3.5 M12 16.5 L14 3.5 M12 16.5 L17 4" stroke={color} strokeWidth="1.6" strokeLinecap="round" opacity="0.85" />
      <path d="M7 4 Q12 1.5 17 4" stroke={color} strokeWidth="1.6" fill="none" strokeLinecap="round" opacity="0.55" />
    </svg>
  );
}

// 칩 카운트 (혼복 N · 남복 N · 여복 N)
function CountPills({ games, compact = false }) {
  const items = [
    { t: '혼', n: games.혼복, c: 'var(--mix)', bg: 'var(--mix-tint)', fg: 'var(--mix-ink)' },
    { t: '남', n: games.남복, c: 'var(--men)', bg: 'var(--men-tint)', fg: 'var(--men-ink)' },
    { t: '여', n: games.여복, c: 'var(--women)', bg: 'var(--women-tint)', fg: 'var(--women-ink)' },
  ];
  return (
    <div style={{ display: 'flex', gap: compact ? 4 : 6 }}>
      {items.map((it) => (
        <span key={it.t} title={it.t} style={{
          display: 'inline-flex', alignItems: 'center', gap: 3,
          padding: compact ? '2px 6px' : '3px 8px', borderRadius: 8,
          background: it.n > 0 ? it.bg : 'var(--surface-3)',
          color: it.n > 0 ? it.fg : 'var(--muted)',
          fontSize: compact ? 11.5 : 12.5, fontWeight: 800,
        }}>
          <span style={{ opacity: 0.7, fontWeight: 700 }}>{it.t}</span>{it.n}
        </span>
      ))}
    </div>
  );
}

Object.assign(window, {
  LevelChip, GenderDot, DisciplineBadge, disciplineColor, Avatar, GenderMark, NameWithGender, PlayerCell,
  PlayerLine, Segmented, Btn, Shuttle, CountPills, LEVEL_STYLE,
  ThemeContext, useTheme,
});
