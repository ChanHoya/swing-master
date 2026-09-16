// shared.jsx — primitives used by all page components

const L = (ko, en) => {
  const lang = document.body.dataset.lang || 'ko';
  return lang === 'en' ? en : ko;
};

// Simple sketch icon glyphs (SVG, hand-drawn-ish strokes)
const SkIcon = ({ name, size = 22, color = "currentColor" }) => {
  const s = size;
  const common = { width: s, height: s, viewBox: "0 0 24 24", fill: "none", stroke: color, strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round", style: { filter: "url(#sk-rough)" } };
  const paths = {
    video: <><rect x="2.5" y="6.5" width="13" height="11" rx="2"/><path d="M16 10l5-2v8l-5-2z"/></>,
    upload: <><path d="M12 3v12"/><path d="M7 8l5-5 5 5"/><rect x="3" y="17" width="18" height="4" rx="1"/></>,
    camera: <><rect x="3" y="7" width="18" height="13" rx="2"/><circle cx="12" cy="13" r="4"/><rect x="9" y="4" width="6" height="3" rx="0.5"/></>,
    play: <path d="M7 5l12 7-12 7V5z"/>,
    record: <><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4" fill={color}/></>,
    check: <path d="M4 12l5 5L20 6"/>,
    alert: <><path d="M12 3l10 18H2L12 3z"/><path d="M12 10v5"/><circle cx="12" cy="18" r="0.5" fill={color}/></>,
    target: <><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill={color}/></>,
    graph: <><path d="M3 20h18"/><path d="M5 17l4-6 4 3 6-9"/></>,
    flag: <><path d="M5 3v18"/><path d="M5 4l10 3-3 4 3 4H5"/></>,
    gear: <><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21c1-5 5-7 8-7s7 2 8 7"/></>,
    mic: <><rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 12a7 7 0 0014 0"/><path d="M12 19v3"/></>,
    pause: <><rect x="6" y="5" width="4" height="14"/><rect x="14" y="5" width="4" height="14"/></>,
    arrow: <><path d="M5 12h14"/><path d="M13 6l6 6-6 6"/></>,
    back: <><path d="M19 12H5"/><path d="M11 6l-6 6 6 6"/></>,
    golf: <><circle cx="7" cy="19" r="2"/><path d="M13 3v17"/><path d="M13 5c4 0 6 2 6 4s-2 3-6 3"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    share: <><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M9 11l6-4M9 13l6 4"/></>,
    star: <path d="M12 3l2.8 6 6.2.6-4.7 4.3 1.4 6.1L12 16.8 6.3 20l1.4-6.1L3 9.6 9.2 9 12 3z"/>,
    bolt: <path d="M13 3L5 14h6l-1 7 9-12h-7l1-6z"/>,
    drill: <><rect x="5" y="4" width="10" height="14" rx="1"/><path d="M15 8l5 3-5 3"/></>,
    phone: <><rect x="7" y="2" width="10" height="20" rx="2"/><circle cx="12" cy="18" r="0.8" fill={color}/></>,
    tripod: <><circle cx="12" cy="5" r="3"/><path d="M12 8v4"/><path d="M12 12l-5 9M12 12l5 9M12 12v9"/></>,
    chart: <><rect x="4" y="14" width="3" height="6"/><rect x="10" y="8" width="3" height="12"/><rect x="16" y="11" width="3" height="9"/></>,
    compare: <><rect x="3" y="4" width="8" height="16" rx="1"/><rect x="13" y="4" width="8" height="16" rx="1"/></>,
  };
  return <svg {...common}>{paths[name] || null}</svg>;
};

// Sketchy arrow drawn as SVG — used for annotations
const SkAnnotationArrow = ({ d, color = "var(--accent)" }) => (
  <svg width="100" height="60" viewBox="0 0 100 60" style={{ position: "absolute", pointerEvents: "none" }}>
    <path d={d} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" style={{ filter: "url(#sk-rough)" }}/>
  </svg>
);

// Page shell: title + 3-up variation cards
const VariationPage = ({ title, subtitle, variations, two }) => (
  <>
    <div className="page-title">
      <div>
        <h1>{title}</h1>
        {subtitle && <div className="page-subtitle">{subtitle}</div>}
      </div>
      <div className="label-mono">{two ? "2 variations" : "3 variations"}</div>
    </div>
    <div className="sk-divider" />
    <div className={two ? "variations two" : "variations"}>
      {variations.map((v, i) => (
        <div className="var-card" key={i}>
          <div className="var-head">
            <span className="var-num">VAR {String(i + 1).padStart(2, "0")}</span>
            <span className="var-title">{v.title}</span>
          </div>
          {v.desc && <div className="var-desc">{v.desc}</div>}
          <div className={"var-frame " + (v.frame || "")}>{v.content}</div>
        </div>
      ))}
    </div>
  </>
);

// Mini topbar for PC frames
const FrameTopbar = ({ title, actions }) => (
  <div className="row ac jb mb-12" style={{ paddingBottom: 8, borderBottom: "1.5px dashed var(--rule)" }}>
    <div className="row ac gap-8">
      <div style={{ width: 20, height: 20, background: "var(--highlight)", border: "1.8px solid var(--ink)", borderRadius: 4, filter: "url(#sk-rough)" }} />
      <span className="hand" style={{ fontWeight: 700, fontSize: 15 }}>SwingMaster</span>
      {title && <span className="muted tiny" style={{ marginLeft: 8 }}>/ {title}</span>}
    </div>
    <div className="row ac gap-8">
      {actions}
      <div className="sk-avatar" style={{ width: 24, height: 24, fontSize: 12 }}>C</div>
    </div>
  </div>
);

// Phone status bar
const PhoneStatus = () => (
  <div className="row ac jb tiny muted" style={{ padding: "0 14px 6px", fontFamily: "var(--font-mono)" }}>
    <span>9:41</span>
    <span className="row ac gap-4">
      <span style={{ fontSize: 10 }}>●●●</span>
      <span>100%</span>
    </span>
  </div>
);

// Swing-pose silhouette — sketch stick figure in various stages
const StickFigure = ({ pose = "address", size = 100, showSkeleton = true }) => {
  const poses = {
    address: { arms: "M30,45 L50,65 L70,45", spine: "M50,25 L50,65", legs: "M45,65 L42,90 M55,65 L58,90", club: "M70,45 L78,92" },
    takeaway: { arms: "M30,50 L55,55 L75,40", spine: "M50,25 L52,65", legs: "M45,65 L42,90 M55,65 L58,90", club: "M75,40 L85,20" },
    top: { arms: "M45,30 L55,25 L65,35", spine: "M50,25 L54,65", legs: "M46,65 L42,90 M55,65 L58,90", club: "M65,35 L40,15" },
    downswing: { arms: "M35,45 L50,55 L68,50", spine: "M50,25 L50,65", legs: "M44,65 L40,90 M56,65 L60,90", club: "M68,50 L78,75" },
    impact: { arms: "M40,50 L50,65 L62,80", spine: "M50,25 L50,65", legs: "M44,65 L42,90 M56,65 L60,90", club: "M62,80 L70,92" },
    follow: { arms: "M45,40 L55,55 L55,75", spine: "M52,25 L50,65", legs: "M46,65 L44,90 M54,65 L58,90", club: "M55,75 L70,35" },
    finish: { arms: "M40,35 L55,40 L65,25", spine: "M54,25 L48,65", legs: "M44,65 L42,90 M56,65 L60,90", club: "M65,25 L45,10" },
  };
  const p = poses[pose] || poses.address;
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} style={{ filter: "url(#sk-rough)" }}>
      {/* ground line */}
      <path d="M10,92 L90,92" stroke="var(--pencil)" strokeWidth="1" strokeDasharray="2 3"/>
      {/* head */}
      <circle cx="50" cy="18" r="7" fill="none" stroke="var(--ink)" strokeWidth="1.6"/>
      {/* spine */}
      <path d={p.spine} fill="none" stroke="var(--ink)" strokeWidth="1.8" strokeLinecap="round"/>
      {/* arms */}
      <path d={p.arms} fill="none" stroke="var(--ink)" strokeWidth="1.6" strokeLinecap="round"/>
      {/* legs */}
      <path d={p.legs} fill="none" stroke="var(--ink)" strokeWidth="1.6" strokeLinecap="round"/>
      {/* club */}
      <path d={p.club} fill="none" stroke="var(--accent)" strokeWidth="1.4" strokeLinecap="round"/>
      {/* ball for address/impact */}
      {(pose === "address" || pose === "impact") && (
        <circle cx="78" cy="91" r="1.8" fill="var(--paper)" stroke="var(--ink)" strokeWidth="1"/>
      )}
    </svg>
  );
};

Object.assign(window, { L, SkIcon, SkAnnotationArrow, VariationPage, FrameTopbar, PhoneStatus, StickFigure });
